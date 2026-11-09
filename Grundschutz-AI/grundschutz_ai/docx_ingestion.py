"""Bounded plain DOCX text ingestion. Output is untrusted text, never inventory.

Only the declared minimal package/XML profile is accepted. No ZIP extraction,
relationship following, network, inference, persistence or document generation.
"""

from dataclasses import dataclass, field, fields, replace
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib

from .ooxml_safety import OOXMLSafetyError, parse_xml, read_package


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
MAIN_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
DOCUMENT_PART = "word/document.xml"
_REQUIRED = {"[Content_Types].xml", "_rels/.rels", DOCUMENT_PART}
_ALLOWED = _REQUIRED | {"word/_rels/document.xml.rels"}
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class DocxIngestionError(ValueError):
    """Malformed, unsupported or over-budget input; no partial result is returned."""


@dataclass(frozen=True, slots=True)
class DocxLimits:
    max_file_bytes: int = 2 * 1024 * 1024
    max_uncompressed_bytes: int = 8 * 1024 * 1024
    max_entries: int = 16
    max_ratio: int = 100
    max_xml_bytes: int = 2 * 1024 * 1024
    max_xml_depth: int = 32
    max_xml_nodes: int = 20_000
    max_xml_attributes: int = 16
    max_attribute_chars: int = 4096
    max_namespaces: int = 32
    max_xml_chars: int = 2 * 1024 * 1024
    max_segments: int = 4096
    max_segment_chars: int = 16_384
    max_text_chars: int = 1_000_000
    max_table_rows: int = 1000
    max_table_columns: int = 128

    def __post_init__(self):
        if any(type(getattr(self, item.name)) is not int or getattr(self, item.name) < 1 for item in fields(self)):
            raise ValueError("DOCX limits must be positive integers supplied by trusted code")


DEFAULT_LIMITS = DocxLimits()


@dataclass(frozen=True, slots=True)
class DocxLocator:
    """One-based structural indices, zero-based half-open segment character span."""

    body_index: int
    paragraph_index: int
    table_index: int | None = None
    row_index: int | None = None
    cell_index: int | None = None
    char_start: int = 0
    char_end: int = 0
    part: str = field(default=DOCUMENT_PART, init=False)

    def __post_init__(self):
        indices = (self.body_index, self.paragraph_index)
        table = (self.table_index, self.row_index, self.cell_index)
        if any(type(value) is not int or value < 1 for value in indices):
            raise ValueError("Structural indices must be positive integers")
        if table != (None, None, None) and any(type(value) is not int or value < 1 for value in table):
            raise ValueError("Table, row and cell indices must all be present and positive")
        if type(self.char_start) is not int or type(self.char_end) is not int or not 0 <= self.char_start <= self.char_end:
            raise ValueError("Character span must satisfy 0 <= start <= end")


@dataclass(frozen=True, slots=True)
class TextSegment:
    text: str
    locator: DocxLocator
    text_sha256: str = field(init=False)

    def __post_init__(self):
        if type(self.text) is not str or type(self.locator) is not DocxLocator:
            raise ValueError("Segment needs text and a typed DOCX locator")
        if self.locator.char_start != 0 or self.locator.char_end != len(self.text):
            raise ValueError("A full segment locator must cover its entire text")
        object.__setattr__(self, "text_sha256", hashlib.sha256(self.text.encode("utf-8")).hexdigest())

    def span(self, start: int, end: int) -> DocxLocator:
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(self.text):
            raise ValueError("Requested span is outside the segment")
        return replace(self.locator, char_start=start, char_end=end)


@dataclass(frozen=True, slots=True)
class DocxExtraction:
    """Deterministic untrusted text/provenance artifact; has no review state."""

    source_id: str
    original_bytes: bytes = field(repr=False)
    segments: tuple[TextSegment, ...]
    limits: DocxLimits = DEFAULT_LIMITS
    method: str = field(default="docx-plain/v1", init=False)
    docx_sha256: str = field(init=False)
    text: str = field(init=False)
    text_sha256: str = field(init=False)

    def __post_init__(self):
        if type(self.source_id) is not str or not self.source_id.strip() or type(self.original_bytes) is not bytes:
            raise ValueError("A source ID and immutable original bytes are required")
        if type(self.segments) is not tuple or any(type(item) is not TextSegment for item in self.segments):
            raise ValueError("Segments must be an immutable typed tuple")
        if type(self.limits) is not DocxLimits:
            raise ValueError("A typed limits profile is required")
        text = "\n".join(item.text for item in self.segments)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "docx_sha256", hashlib.sha256(self.original_bytes).hexdigest())
        object.__setattr__(self, "text_sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())


def _package_parts(raw: bytes, limits: DocxLimits) -> dict[str, bytes]:
    try:
        return read_package(raw, limits, required_parts=_REQUIRED, allowed_parts=_ALLOWED)
    except OOXMLSafetyError as exc:
        raise DocxIngestionError(str(exc)) from exc


def _xml(content: bytes, limits: DocxLimits):
    try:
        return parse_xml(content, limits)
    except OOXMLSafetyError as exc:
        raise DocxIngestionError(str(exc)) from exc


def _container(node, tag, attributes=()):
    if node.tag != tag or set(node.attrib) - set(attributes) or (node.text or "").strip() or (node.tail or "").strip():
        raise DocxIngestionError("Unsupported DOCX element, attributes or mixed text")


def _leaf(node, tag, attributes=()):
    _container(node, tag, attributes)
    if len(node):
        raise DocxIngestionError("Unsupported nested XML content")


def _package_metadata(roots):
    types = roots["[Content_Types].xml"]
    _container(types, f"{{{CT}}}Types")
    defaults, overrides = {}, {}
    for child in types:
        if child.tag == f"{{{CT}}}Default":
            _leaf(child, child.tag, ("Extension", "ContentType"))
            if set(child.attrib) != {"Extension", "ContentType"} or child.attrib["Extension"] in defaults:
                raise DocxIngestionError("Invalid content-type defaults")
            defaults[child.attrib["Extension"]] = child.attrib["ContentType"]
        elif child.tag == f"{{{CT}}}Override":
            _leaf(child, child.tag, ("PartName", "ContentType"))
            if set(child.attrib) != {"PartName", "ContentType"} or child.attrib["PartName"] in overrides:
                raise DocxIngestionError("Invalid content-type overrides")
            overrides[child.attrib["PartName"]] = child.attrib["ContentType"]
        else:
            raise DocxIngestionError("Unsupported content-type declaration")
    if defaults != {"rels": "application/vnd.openxmlformats-package.relationships+xml", "xml": "application/xml"} or overrides != {"/word/document.xml": MAIN_TYPE}:
        raise DocxIngestionError("Macro-enabled or unsupported DOCX content types")
    relationships = roots["_rels/.rels"]
    _container(relationships, f"{{{REL}}}Relationships")
    if len(relationships) != 1:
        raise DocxIngestionError("Only one internal officeDocument relationship is supported")
    relation = relationships[0]
    _leaf(relation, f"{{{REL}}}Relationship", ("Id", "Type", "Target"))
    if set(relation.attrib) != {"Id", "Type", "Target"} or not relation.attrib["Id"] or relation.attrib["Type"] != OFFICE_REL or relation.attrib["Target"] != DOCUMENT_PART:
        raise DocxIngestionError("External or unsupported package relationship")
    if "word/_rels/document.xml.rels" in roots:
        _leaf(roots["word/_rels/document.xml.rels"], f"{{{REL}}}Relationships")


def _paragraph(node):
    _container(node, f"{{{W}}}p")
    pieces = []
    for run in node:
        _container(run, f"{{{W}}}r")
        for child in run:
            if child.tag == f"{{{W}}}t":
                if len(child) or set(child.attrib) - {_XML_SPACE} or (child.tail or "").strip():
                    raise DocxIngestionError("Unsupported text-node structure")
                value = child.text or ""
                space = child.attrib.get(_XML_SPACE, "default")
                if space not in ("default", "preserve") or any(character in value for character in "\r\n\t"):
                    raise DocxIngestionError("Unsupported text whitespace")
                if value != value.strip() and space != "preserve":
                    raise DocxIngestionError("Boundary whitespace needs explicit xml:space preservation")
                pieces.append(value)
            elif child.tag in (f"{{{W}}}tab", f"{{{W}}}cr"):
                _leaf(child, child.tag)
                pieces.append("\t" if child.tag.endswith("tab") else "\n")
            elif child.tag == f"{{{W}}}br":
                _leaf(child, child.tag, (f"{{{W}}}type",))
                if child.attrib.get(f"{{{W}}}type", "textWrapping") != "textWrapping":
                    raise DocxIngestionError("Page/column breaks are unsupported")
                pieces.append("\n")
            else:
                raise DocxIngestionError("Unsupported or text-affecting run content")
    return "".join(pieces)


def _segments(root, limits):
    _container(root, f"{{{W}}}document")
    if len(root) != 1:
        raise DocxIngestionError("Only a single document body is supported")
    body = root[0]
    _container(body, f"{{{W}}}body")
    result, characters, paragraph_index, table_index = [], 0, 0, 0

    def append(node, body_index, paragraph_index, table=None, row=None, cell=None):
        nonlocal characters
        text = _paragraph(node)
        characters += len(text) + (1 if result else 0)
        if len(text) > limits.max_segment_chars or len(result) >= limits.max_segments or characters > limits.max_text_chars:
            raise DocxIngestionError("Extracted text/segment limit exceeded")
        locator = DocxLocator(body_index, paragraph_index, table, row, cell, 0, len(text))
        result.append(TextSegment(text, locator))

    for body_index, child in enumerate(body, 1):
        if child.tag == f"{{{W}}}p":
            paragraph_index += 1
            append(child, body_index, paragraph_index)
        elif child.tag == f"{{{W}}}tbl":
            table_index += 1
            _container(child, child.tag)
            rows = list(child)
            grid_columns = None
            if rows and rows[0].tag == f"{{{W}}}tblPr":
                _leaf(rows.pop(0), f"{{{W}}}tblPr")
            if rows and rows[0].tag == f"{{{W}}}tblGrid":
                grid = rows.pop(0)
                _container(grid, grid.tag)
                grid_columns = len(grid)
                for column in grid:
                    _leaf(column, f"{{{W}}}gridCol", (f"{{{W}}}w",))
                    if set(column.attrib) != {f"{{{W}}}w"} or not re.fullmatch(r"[1-9][0-9]{0,5}", column.attrib[f"{{{W}}}w"]):
                        raise DocxIngestionError("Unsupported table grid width")
            if not rows or len(rows) > limits.max_table_rows:
                raise DocxIngestionError("Table row limit or structure invalid")
            width = None
            for row_index, row in enumerate(rows, 1):
                _container(row, f"{{{W}}}tr")
                if not 0 < len(row) <= limits.max_table_columns or (width is not None and len(row) != width):
                    raise DocxIngestionError("Ragged, empty or oversized table row")
                width = len(row)
                if grid_columns is not None and grid_columns != width:
                    raise DocxIngestionError("Table grid does not match cells")
                for cell_index, cell in enumerate(row, 1):
                    _container(cell, f"{{{W}}}tc")
                    if not len(cell):
                        raise DocxIngestionError("Table cell must contain paragraphs")
                    for cell_paragraph, node in enumerate(cell, 1):
                        append(node, body_index, cell_paragraph, table_index, row_index, cell_index)
        elif child.tag == f"{{{W}}}sectPr" and body_index == len(body):
            _leaf(child, child.tag)  # Empty only: no layout, header/footer or page claims.
        else:
            raise DocxIngestionError("Unsupported or text-affecting body content")
    return tuple(result)


def ingest_docx(path: str | Path, *, source_id: str, limits: DocxLimits = DEFAULT_LIMITS) -> DocxExtraction:
    """Read one explicitly trusted synthetic DOCX path with bounded resource use."""
    if not isinstance(path, (str, Path)) or type(source_id) is not str or not source_id.strip() or type(limits) is not DocxLimits:
        raise DocxIngestionError("A trusted path, source ID and typed limits profile are required")
    path = Path(path)
    if path.suffix.casefold() != ".docx" or path.is_symlink():
        raise DocxIngestionError("Only explicit regular synthetic .docx files are supported")
    try:
        with path.open("rb") as file:
            metadata = os.fstat(file.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limits.max_file_bytes:
                raise DocxIngestionError("DOCX file type/size limit exceeded")
            raw = file.read(limits.max_file_bytes + 1)
        if len(raw) > limits.max_file_bytes:
            raise DocxIngestionError("DOCX file size limit exceeded")
        parts = _package_parts(raw, limits)
        roots = {name: _xml(content, limits) for name, content in parts.items()}
        _package_metadata(roots)
        return DocxExtraction(source_id, raw, _segments(roots[DOCUMENT_PART], limits), limits)
    except DocxIngestionError:
        raise
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, struct.error, zlib.error, RuntimeError) as exc:
        raise DocxIngestionError("Malformed, unreadable or unsupported synthetic DOCX") from exc
