"""Bounded literal XLSX ingestion; returned text is untrusted, never inventory."""

from dataclasses import asdict, dataclass, field, fields
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib

from .ooxml_safety import OOXMLSafetyError, parse_xml, read_package


S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
MAIN_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
SHEET_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
STRINGS_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"
WORKBOOK = "xl/workbook.xml"
WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
STRINGS = "xl/sharedStrings.xml"
_REQUIRED = {"[Content_Types].xml", "_rels/.rels", WORKBOOK, WORKBOOK_RELS}
_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_ESCAPE = re.compile(r"_x[0-9a-fA-F]{4}_")


class XlsxIngestionError(ValueError):
    """Input failed the literal profile; no partial extraction is returned."""


@dataclass(frozen=True, slots=True)
class XlsxLimits:
    max_file_bytes: int = 2 * 1024 * 1024
    max_uncompressed_bytes: int = 8 * 1024 * 1024
    max_entries: int = 64
    max_ratio: int = 100
    max_xml_bytes: int = 2 * 1024 * 1024
    max_xml_depth: int = 32
    max_xml_nodes: int = 20_000
    max_xml_attributes: int = 16
    max_attribute_chars: int = 4096
    max_namespaces: int = 32
    max_xml_chars: int = 2 * 1024 * 1024
    max_worksheets: int = 16
    max_cells: int = 10_000
    max_shared_strings: int = 10_000
    max_cell_chars: int = 16_384
    max_shared_text_chars: int = 1_000_000
    max_text_chars: int = 1_000_000

    def __post_init__(self):
        if any(type(getattr(self, item.name)) is not int or getattr(self, item.name) < 1 for item in fields(self)):
            raise ValueError("XLSX limits must be positive integers supplied by trusted code")


DEFAULT_LIMITS = XlsxLimits()


class CellKind(StrEnum):
    TEXT = "text"
    BLANK = "blank"


def _source_id(value):
    if type(value) is not str or not value.strip():
        raise XlsxIngestionError("A trusted nonempty workbook source ID is required")


def _sheet_name(value):
    if type(value) is not str or not value.strip() or len(value) > 31 or re.search(r"[\[\]:*?/\\\x00-\x1f]", value) or value.startswith("'") or value.endswith("'") or _ESCAPE.search(value):
        raise XlsxIngestionError("Unsupported worksheet name")


def _positive(value, maximum):
    if type(value) is not str or not re.fullmatch(r"[1-9][0-9]{0,9}", value) or int(value) > maximum:
        raise XlsxIngestionError("Invalid explicit spreadsheet index")
    return int(value)


def _coordinate(value):
    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", value) if type(value) is str else None
    if not match:
        raise XlsxIngestionError("A canonical explicit cell address is required")
    column = 0
    for character in match[1]:
        column = column * 26 + ord(character) - ord("A") + 1
    row = int(match[2])
    if column > 16_384 or row > 1_048_576:
        raise XlsxIngestionError("Cell address exceeds XLSX coordinate bounds")
    return row, column


@dataclass(frozen=True, slots=True)
class CellRecord:
    source_id: str
    sheet_name: str
    sheet_ordinal: int
    part: str
    coordinate: str
    row: int
    column: int
    text: str
    kind: CellKind
    text_sha256: str = field(init=False)

    def __post_init__(self):
        _source_id(self.source_id)
        _sheet_name(self.sheet_name)
        if type(self.sheet_ordinal) is not int or self.sheet_ordinal < 1 or type(self.part) is not str or not re.fullmatch(r"xl/worksheets/sheet[1-9][0-9]*\.xml", self.part):
            raise XlsxIngestionError("Invalid typed worksheet locator")
        if type(self.row) is not int or type(self.column) is not int or (self.row, self.column) != _coordinate(self.coordinate):
            raise XlsxIngestionError("Cell address and row/column disagree")
        if type(self.text) is not str or type(self.kind) is not CellKind or (self.kind is CellKind.BLANK and self.text != ""):
            raise XlsxIngestionError("Cell needs literal text and an explicit supported kind")
        object.__setattr__(self, "text_sha256", hashlib.sha256(self.text.encode("utf-8")).hexdigest())


@dataclass(frozen=True, slots=True)
class Worksheet:
    source_id: str
    name: str
    ordinal: int
    sheet_id: int
    relationship_id: str
    part: str
    row_indices: tuple[int, ...]
    cells: tuple[CellRecord, ...]

    def __post_init__(self):
        _source_id(self.source_id)
        _sheet_name(self.name)
        if type(self.ordinal) is not int or self.ordinal < 1 or type(self.sheet_id) is not int or not 1 <= self.sheet_id <= 0xFFFFFFFF:
            raise XlsxIngestionError("Invalid worksheet identity")
        if type(self.relationship_id) is not str or not re.fullmatch(r"rId[1-9][0-9]{0,5}", self.relationship_id) or type(self.part) is not str or not re.fullmatch(r"xl/worksheets/sheet[1-9][0-9]*\.xml", self.part):
            raise XlsxIngestionError("Invalid worksheet relationship/part")
        if type(self.row_indices) is not tuple or any(type(row) is not int or not 1 <= row <= 1_048_576 for row in self.row_indices) or tuple(sorted(set(self.row_indices))) != self.row_indices:
            raise XlsxIngestionError("Rows must be explicit, unique and ascending")
        if type(self.cells) is not tuple or any(type(cell) is not CellRecord for cell in self.cells):
            raise XlsxIngestionError("Cells must be an immutable typed tuple")
        previous = (0, 0)
        rows = set(self.row_indices)
        for cell in self.cells:
            if (cell.source_id, cell.sheet_name, cell.sheet_ordinal, cell.part) != (self.source_id, self.name, self.ordinal, self.part) or cell.row not in rows or (cell.row, cell.column) <= previous:
                raise XlsxIngestionError("Cell identity/order does not match worksheet")
            previous = (cell.row, cell.column)

    def cell_at(self, coordinate: str) -> CellRecord | None:
        _coordinate(coordinate)
        return next((cell for cell in self.cells if cell.coordinate == coordinate), None)


@dataclass(frozen=True, slots=True)
class XlsxExtraction:
    """Untrusted artifact, not authenticated evidence or approved inventory."""

    source_id: str
    original_bytes: bytes = field(repr=False)
    sheets: tuple[Worksheet, ...]
    limits: XlsxLimits = DEFAULT_LIMITS
    method: str = field(default="xlsx-literal/v1", init=False)
    xlsx_sha256: str = field(init=False)
    text: str = field(init=False)
    text_sha256: str = field(init=False)
    manifest_json: str = field(init=False)
    manifest_sha256: str = field(init=False)

    def __post_init__(self):
        _source_id(self.source_id)
        if type(self.original_bytes) is not bytes or type(self.limits) is not XlsxLimits or type(self.sheets) is not tuple or not self.sheets or any(type(sheet) is not Worksheet for sheet in self.sheets):
            raise XlsxIngestionError("Typed immutable workbook data is required")
        if any(sheet.source_id != self.source_id or sheet.ordinal != index for index, sheet in enumerate(self.sheets, 1)):
            raise XlsxIngestionError("Workbook sheet identity/order mismatch")
        for values in ([sheet.name.casefold() for sheet in self.sheets], [sheet.sheet_id for sheet in self.sheets], [sheet.part for sheet in self.sheets], [sheet.relationship_id for sheet in self.sheets]):
            if len(set(values)) != len(values):
                raise XlsxIngestionError("Duplicate worksheet identity")
        text = "\n".join(cell.text for cell in self.cells)
        manifest = json.dumps({"source_id": self.source_id, "method": self.method, "limits": asdict(self.limits), "sheets": [asdict(sheet) for sheet in self.sheets]}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        object.__setattr__(self, "xlsx_sha256", hashlib.sha256(self.original_bytes).hexdigest())
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "text_sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
        object.__setattr__(self, "manifest_json", manifest)
        object.__setattr__(self, "manifest_sha256", hashlib.sha256(manifest.encode("utf-8")).hexdigest())

    @property
    def cells(self) -> tuple[CellRecord, ...]:
        return tuple(cell for sheet in self.sheets for cell in sheet.cells)


def _node(node, tag, attributes=(), *, leaf=False):
    if node.tag != tag or set(node.attrib) - set(attributes) or (node.text or "").strip(" \t\r\n") or (node.tail or "").strip(" \t\r\n") or (leaf and len(node)):
        raise XlsxIngestionError("Unsupported XLSX element, attributes or mixed content")


def _text(node, tag, attributes=()):
    if node.tag != tag or len(node) or set(node.attrib) - set(attributes) or (node.tail or "").strip(" \t\r\n"):
        raise XlsxIngestionError("Unsupported literal text structure")
    return node.text or ""


def _literal(container, tag, limits):
    _node(container, tag)
    if len(container) != 1:
        raise XlsxIngestionError("Only a single plain text node is supported")
    node = container[0]
    value = _text(node, f"{{{S}}}t", (_SPACE,))
    space = node.attrib.get(_SPACE, "default")
    if space not in ("default", "preserve") or (value != value.strip() and space != "preserve") or _ESCAPE.search(value):
        raise XlsxIngestionError("Ambiguous whitespace or unsupported OOXML text escape")
    if len(value) > limits.max_cell_chars:
        raise XlsxIngestionError("Cell text length limit exceeded")
    return value


def _relationships(root):
    _node(root, f"{{{REL}}}Relationships")
    result = {}
    for node in root:
        _node(node, f"{{{REL}}}Relationship", ("Id", "Type", "Target", "TargetMode"), leaf=True)
        if not {"Id", "Type", "Target"} <= set(node.attrib) or node.attrib.get("TargetMode", "Internal") != "Internal":
            raise XlsxIngestionError("External or incomplete relationship")
        identifier = node.attrib["Id"]
        if not re.fullmatch(r"rId[1-9][0-9]{0,5}", identifier) or identifier in result:
            raise XlsxIngestionError("Duplicate or unsupported relationship ID")
        result[identifier] = (node.attrib["Type"], node.attrib["Target"])
    return result


def _metadata(roots, limits):
    package = _relationships(roots["_rels/.rels"])
    if list(package.values()) != [(R + "/officeDocument", WORKBOOK)]:
        raise XlsxIngestionError("Expected one internal workbook relationship")
    root = roots[WORKBOOK]
    _node(root, f"{{{S}}}workbook")
    if len(root) != 1:
        raise XlsxIngestionError("Only a workbook sheets collection is supported")
    sheets = root[0]
    _node(sheets, f"{{{S}}}sheets")
    if not 0 < len(sheets) <= limits.max_worksheets:
        raise XlsxIngestionError("Worksheet count limit exceeded or no worksheets")
    relationships = _relationships(roots[WORKBOOK_RELS])
    definitions, names, identifiers, targets, used = [], set(), set(), set(), set()
    for ordinal, sheet in enumerate(sheets, 1):
        _node(sheet, f"{{{S}}}sheet", ("name", "sheetId", f"{{{R}}}id", "state"), leaf=True)
        if not {"name", "sheetId", f"{{{R}}}id"} <= set(sheet.attrib) or sheet.attrib.get("state", "visible") != "visible":
            raise XlsxIngestionError("Hidden or incomplete worksheet declaration")
        name, rid = sheet.attrib["name"], sheet.attrib[f"{{{R}}}id"]
        _sheet_name(name)
        identifier = _positive(sheet.attrib["sheetId"], 0xFFFFFFFF)
        relation = relationships.get(rid)
        if relation is None or relation[0] != R + "/worksheet" or not re.fullmatch(r"worksheets/sheet[1-9][0-9]*\.xml", relation[1]):
            raise XlsxIngestionError("Missing or unsupported worksheet relationship")
        part = "xl/" + relation[1]
        if part not in roots or name.casefold() in names or identifier in identifiers or part in targets or rid in used:
            raise XlsxIngestionError("Missing, duplicate or ambiguous worksheet identity/target")
        names.add(name.casefold())
        identifiers.add(identifier)
        targets.add(part)
        used.add(rid)
        definitions.append((name, ordinal, identifier, rid, part))
    extras = {rid: relation for rid, relation in relationships.items() if rid not in used}
    if STRINGS in roots:
        if list(extras.values()) != [(R + "/sharedStrings", "sharedStrings.xml")]:
            raise XlsxIngestionError("Missing or ambiguous shared-string relationship")
    elif extras:
        raise XlsxIngestionError("Unsupported or dangling workbook relationship")
    expected = _REQUIRED | targets | ({STRINGS} if STRINGS in roots else set())
    if set(roots) != expected:
        raise XlsxIngestionError("Unreferenced or unknown package part")
    types = roots["[Content_Types].xml"]
    _node(types, f"{{{CT}}}Types")
    defaults, overrides = {}, {}
    for node in types:
        if node.tag == f"{{{CT}}}Default":
            _node(node, node.tag, ("Extension", "ContentType"), leaf=True)
            if set(node.attrib) != {"Extension", "ContentType"} or node.attrib["Extension"] in defaults:
                raise XlsxIngestionError("Invalid content-type defaults")
            defaults[node.attrib["Extension"]] = node.attrib["ContentType"]
        elif node.tag == f"{{{CT}}}Override":
            _node(node, node.tag, ("PartName", "ContentType"), leaf=True)
            if set(node.attrib) != {"PartName", "ContentType"} or node.attrib["PartName"] in overrides:
                raise XlsxIngestionError("Invalid content-type overrides")
            overrides[node.attrib["PartName"]] = node.attrib["ContentType"]
        else:
            raise XlsxIngestionError("Unsupported content-type declaration")
    expected_types = {"/" + WORKBOOK: MAIN_TYPE, **{"/" + part: SHEET_TYPE for part in targets}}
    if STRINGS in roots:
        expected_types["/" + STRINGS] = STRINGS_TYPE
    if defaults != {"rels": "application/vnd.openxmlformats-package.relationships+xml", "xml": "application/xml"} or overrides != expected_types:
        raise XlsxIngestionError("Macro-enabled or unsupported workbook content types")
    return definitions


def _shared_strings(root, limits):
    if root is None:
        return (), None
    _node(root, f"{{{S}}}sst", ("count", "uniqueCount"))
    if len(root) > limits.max_shared_strings:
        raise XlsxIngestionError("Shared-string count limit exceeded")
    result, characters = [], 0
    for node in root:
        value = _literal(node, f"{{{S}}}si", limits)
        characters += len(value)
        if characters > limits.max_shared_text_chars:
            raise XlsxIngestionError("Shared-string text budget exceeded")
        result.append(value)
    if len(set(result)) != len(result):
        raise XlsxIngestionError("Duplicate shared-string definitions are unsupported")
    for attribute, expected in (("count", None), ("uniqueCount", len(result))):
        if attribute in root.attrib:
            raw = root.attrib[attribute]
            if not re.fullmatch(r"0|[1-9][0-9]{0,9}", raw) or int(raw) > limits.max_cells or (expected is not None and int(raw) != expected):
                raise XlsxIngestionError("Inconsistent shared-string metadata")
    return tuple(result), int(root.attrib["count"]) if "count" in root.attrib else None


def _worksheets(roots, definitions, strings, source_id, limits):
    result, used_strings, references, cell_count, characters = [], set(), 0, 0, 0
    for name, ordinal, sheet_id, rid, part in definitions:
        root = roots[part]
        _node(root, f"{{{S}}}worksheet")
        if len(root) != 1:
            raise XlsxIngestionError("Only plain sheetData is supported")
        data = root[0]
        _node(data, f"{{{S}}}sheetData")
        rows, cells, last_row = [], [], 0
        for row in data:
            _node(row, f"{{{S}}}row", ("r",))
            index = _positive(row.attrib.get("r"), 1_048_576)
            if index <= last_row:
                raise XlsxIngestionError("Duplicate or unordered worksheet rows")
            rows.append(index)
            last_row, last_column = index, 0
            for node in row:
                _node(node, f"{{{S}}}c", ("r", "t"))
                coordinate = node.attrib.get("r")
                cell_row, column = _coordinate(coordinate)
                if cell_row != index or column <= last_column:
                    raise XlsxIngestionError("Duplicate, unordered or row-mismatched cell address")
                last_column = column
                cell_count += 1
                if cell_count > limits.max_cells:
                    raise XlsxIngestionError("Workbook cell count limit exceeded")
                cell_type = node.attrib.get("t")
                if cell_type is None and not len(node):
                    text, kind = "", CellKind.BLANK
                elif cell_type == "inlineStr" and len(node) == 1:
                    text, kind = _literal(node[0], f"{{{S}}}is", limits), CellKind.TEXT
                elif cell_type == "s" and len(node) == 1:
                    value = _text(node[0], f"{{{S}}}v")
                    if not re.fullmatch(r"0|[1-9][0-9]{0,9}", value) or int(value) >= len(strings):
                        raise XlsxIngestionError("Invalid shared-string index")
                    used_strings.add(int(value))
                    references += 1
                    text, kind = strings[int(value)], CellKind.TEXT
                else:
                    raise XlsxIngestionError("Formula, numeric, cached or unsupported cell content")
                characters += len(text) + (1 if cell_count > 1 else 0)
                if characters > limits.max_text_chars:
                    raise XlsxIngestionError("Extracted workbook text budget exceeded")
                cells.append(CellRecord(source_id, name, ordinal, part, coordinate, cell_row, column, text, kind))
        result.append(Worksheet(source_id, name, ordinal, sheet_id, rid, part, tuple(rows), tuple(cells)))
    if used_strings != set(range(len(strings))):
        raise XlsxIngestionError("Unreferenced shared-string text is unsupported")
    return tuple(result), references


def ingest_xlsx(path: str | Path, *, source_id: str, limits: XlsxLimits = DEFAULT_LIMITS) -> XlsxExtraction:
    """Read one explicit trusted synthetic XLSX; no inference or persistence."""
    _source_id(source_id)
    if not isinstance(path, (str, Path)) or type(limits) is not XlsxLimits:
        raise XlsxIngestionError("A trusted path and typed limits profile are required")
    try:
        path = Path(path)
        if path.suffix.casefold() != ".xlsx" or path.is_symlink():
            raise XlsxIngestionError("Only explicit regular synthetic .xlsx files are supported")
        with path.open("rb") as file:
            metadata = os.fstat(file.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limits.max_file_bytes:
                raise XlsxIngestionError("XLSX file type/size limit exceeded")
            raw = file.read(limits.max_file_bytes + 1)
        if len(raw) > limits.max_file_bytes:
            raise XlsxIngestionError("XLSX file size limit exceeded")
        allowed = _REQUIRED | {STRINGS} | {f"xl/worksheets/sheet{index}.xml" for index in range(1, limits.max_worksheets + 1)}
        parts = read_package(raw, limits, required_parts=_REQUIRED, allowed_parts=allowed)
        roots = {name: parse_xml(content, limits) for name, content in parts.items()}
        definitions = _metadata(roots, limits)
        strings, count = _shared_strings(roots.get(STRINGS), limits)
        sheets, references = _worksheets(roots, definitions, strings, source_id, limits)
        if count is not None and count != references:
            raise XlsxIngestionError("Shared-string reference count mismatch")
        return XlsxExtraction(source_id, raw, sheets, limits)
    except XlsxIngestionError:
        raise
    except (OOXMLSafetyError, OSError, ValueError, ET.ParseError, zipfile.BadZipFile, struct.error, zlib.error, RuntimeError) as exc:
        raise XlsxIngestionError("Malformed, unreadable, unsupported or over-budget synthetic XLSX") from exc
