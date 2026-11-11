"""Frozen native wire/manifest contracts. No database or staging workflow."""
from dataclasses import asdict, dataclass, fields, field
import json
from pathlib import Path
import struct

from . import v2_codec as c, v2_a0 as a0
from . import docx_ingestion as docx, xlsx_ingestion as xlsx

GOLDEN_SHA256 = "553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b"
ARTIFACT_IDS = ("canonical-codec", "docx-reader", "historical-catalog", "historical-path-policy",
                "historical-schema", "native-bridge", "native-contract", "native-worker",
                "ooxml-safety", "python-executable", "xlsx-reader")


class NativeBridgeError(RuntimeError):
    """Static diagnostic code; no source text, parser traceback or partial data."""
    def __init__(self, code="native_refused"):
        self.code = code
        super().__init__("Native bridge refused: " + code)


def need(condition, code="invalid_contract"):
    if not condition:
        raise NativeBridgeError(code)


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    max_seconds: int = 10
    max_input_bytes: int = 2 * 1024 * 1024
    max_output_bytes: int = 32 * 1024 * 1024
    max_metadata_bytes: int = 64 * 1024
    max_stderr_bytes: int = 4096

    def __post_init__(self):
        for f in fields(self):
            need(type(getattr(self, f.name)) is int and 1 <= getattr(self, f.name) <= f.default,
                 "limits_may_only_tighten")


DEFAULT_EXECUTION_LIMITS = ExecutionLimits()


@dataclass(frozen=True, slots=True)
class _WireLimits:
    max_bytes: int = 32 * 1024 * 1024
    max_depth: int = 32
    max_nodes: int = 500_000
    max_array: int = 20_000
    max_string_bytes: int = 8 * 1024 * 1024


WIRE = _WireLimits()


def wire_dump(value, maximum=WIRE.max_bytes):
    """Distinct native-wire JSON budgets; ledger CodecLimits are unchanged."""
    need(type(maximum) is int and 1 <= maximum <= WIRE.max_bytes)
    try:
        c._walk(value, WIRE)
        result, size = [], 0
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True,
                                   separators=(",", ":"))
        for piece in encoder.iterencode(value):
            raw = piece.encode("utf-8", errors="strict")
            size += len(raw)
            need(size <= maximum, "output_limit")
            result.append(raw)
        return b"".join(result)
    except (c.CodecError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise NativeBridgeError("invalid_wire") from exc


def wire_load(raw, maximum=WIRE.max_bytes):
    need(type(raw) is bytes and len(raw) <= maximum, "output_limit")
    try:
        c._preflight(raw, WIRE)
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=c._unique,
                           parse_int=c._parse_integer, parse_float=c._no_float,
                           parse_constant=c._no_float)
        c._walk(value, WIRE)
        need(wire_dump(value, maximum) == raw, "noncanonical_wire")
        return value
    except (c.CodecError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise NativeBridgeError("invalid_wire") from exc


def frame(raw, maximum):
    need(type(raw) is bytes and len(raw) <= maximum, "frame_limit")
    return struct.pack(">Q", len(raw)) + raw


def read_frame(stream, maximum):
    prefix = stream.read(8)
    need(len(prefix) == 8, "incomplete_frame")
    size = struct.unpack(">Q", prefix)[0]
    need(size <= maximum, "frame_limit")
    chunks, remaining = [], size
    while remaining:
        chunk = stream.read(min(65536, remaining))
        need(bool(chunk), "incomplete_frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


@dataclass(frozen=True, slots=True)
class NativeHandlerSpec:
    canonical: bytes

    def __post_init__(self):
        data = self.data()
        c.exact(data, """type handler_id reader_spec_hash family reader_method artifact_hashes
            host_runtime policy_versions serialization_version native_manifest_version
            integration_manifest_version golden_fixture_sha256""".split())
        need(data["type"] == "reader-handler-spec/v1")
        c.text(data["handler_id"], 128)
        c.digest(data["reader_spec_hash"])
        need(type(data["family"]) is str and data["family"] in ("docx", "xlsx"))
        doc = data["family"] == "docx"
        need(data["reader_method"] == ("docx-plain/v1" if doc else "xlsx-literal/v1"))
        need(data["native_manifest_version"] == (None if doc else "xlsx-literal/v1"))
        need(data["integration_manifest_version"] == ("docx-integration/v1" if doc else "xlsx-integration/v1"))
        need(data["policy_versions"] == (["docx-single-assertion/v1"] if doc else ["synthetic-it-table/v1"]))
        need(data["serialization_version"] == "canonical-json/v1" and data["golden_fixture_sha256"] == GOLDEN_SHA256)
        need(data["host_runtime"] == {"python_version": "3.12.6", "sqlite_version": "3.45.3",
                                      "platform_profile": "windows-fixed-ntfs-refs/v1"})
        artifacts = data["artifact_hashes"]
        need(type(artifacts) is list and len(artifacts) == len(ARTIFACT_IDS))
        names = []
        for item in artifacts:
            c.exact(item, ("artifact_id", "sha256"))
            need(type(item["artifact_id"]) is str and item["artifact_id"] in ARTIFACT_IDS)
            c.digest(item["sha256"])
            names.append(item["artifact_id"])
        need(tuple(names) == ARTIFACT_IDS)

    def data(self):
        return c.canonical_loads(self.canonical)

    @property
    def sha256(self):
        data = self.data()
        tag = data.pop("type")
        return c.fingerprint(tag, data)

    @property
    def blob_sha256(self):
        return c.sha256(self.canonical)


@dataclass(frozen=True, slots=True)
class SheetSelection:
    name: str
    ordinal: int
    sheet_id: int
    relationship_id: str
    part: str

    def __post_init__(self):
        c.sheet_identity(asdict(self))

    def matches(self, sheet):
        return (self.name, self.ordinal, self.sheet_id, self.relationship_id, self.part) == (
            sheet.name, sheet.ordinal, sheet.sheet_id, sheet.relationship_id, sheet.part)


def policy_config(policy, profile):
    need(type(policy) is c.Spec, "invalid_policy")
    data = policy.data()
    need(data["type"] == "policy-spec/v1" and data["kind"] == profile.spec.data()["family"],
         "invalid_policy")
    need(data["implementation_hash"] == profile.spec.data()["reader_spec_hash"], "invalid_policy")
    # Frozen pure A0 policy code, never current staging defaults.
    a0._policy_object(policy)
    return data["config"]


def context_policy(context, profile):
    c.exact(context, """protocol request_id source_id handler_spec_sha256 reader_spec_sha256
        policy_spec selection original_sha256 original_length execution_limits""".split())
    need(context["protocol"] == "native-request/v1")
    c.identity(context["request_id"])
    c.text(context["source_id"])
    need(context["handler_spec_sha256"] == profile.spec.sha256 and
         context["reader_spec_sha256"] == profile.spec.data()["reader_spec_hash"], "handler_mismatch")
    policy = c.Spec(c.canonical_dumps(context["policy_spec"]))
    config = policy_config(policy, profile)
    c.digest(context["original_sha256"])
    c.integer(context["original_length"], 0)
    limits = ExecutionLimits(**context["execution_limits"])
    need(context["original_length"] <= min(limits.max_input_bytes, config["max_retained_bytes"],
                                           config["reader_limits"]["max_file_bytes"]),
         "input_limit")
    if profile.spec.data()["family"] == "docx":
        need(context["selection"] is None, "invalid_selection")
    else:
        c.sheet_identity(context["selection"])
    return policy, config, limits


def reader_stamp(profile):
    hashes = {row["artifact_id"]: row["sha256"] for row in profile.spec.data()["artifact_hashes"]}
    family = profile.spec.data()["family"]
    return c.sha256(c.canonical_dumps({"python": [3, 12, 6], "reader": hashes[family + "-reader"],
                                     "ooxml": hashes["ooxml-safety"]}))


def observations(native):
    if type(native) is docx.DocxExtraction:
        return [asdict(segment) for segment in native.segments]
    return [{**asdict(sheet), "row_indices": list(sheet.row_indices),
             "cells": [{**asdict(cell), "kind": cell.kind.value} for cell in sheet.cells]}
            for sheet in native.sheets]


def manifests(native, profile, config, selection):
    doc = type(native) is docx.DocxExtraction
    need(doc or type(native) is xlsx.XlsxExtraction, "native_mismatch")
    need(len(native.text) <= min(config["reader_limits"]["max_text_chars"],
                                  config["max_retained_text_chars"]), "text_limit")
    maximum = min(config["max_manifest_bytes"], config["max_retained_manifest_bytes"])
    stamp = reader_stamp(profile)
    manifest = {"manifest_version": "docx-integration/v1" if doc else "xlsx-integration/v1",
                "source_id": native.source_id,
                "binary_sha256": native.docx_sha256 if doc else native.xlsx_sha256,
                "reader_method": native.method, "reader_implementation_sha256": stamp,
                "reader_limits": asdict(native.limits), "native_text_sha256": native.text_sha256}
    native_manifest = None
    if doc:
        manifest["segments"] = observations(native)
    else:
        selected = SheetSelection(**selection)
        need(sum(selected.matches(sheet) for sheet in native.sheets) == 1, "invalid_selection")
        native_manifest = native.manifest_json.encode("utf-8")
        need(len(native_manifest) <= maximum, "manifest_limit")
        manifest.update(selection=selection, native_manifest_sha256=native.manifest_sha256,
                        native_manifest_json=native.manifest_json)
    return native_manifest, wire_dump(manifest, maximum)


def make_record(context, native, profile):
    policy, config, _ = context_policy(context, profile)
    need(native.source_id == context["source_id"] and
         native.original_bytes is not None and len(native.original_bytes) == context["original_length"] and
         c.sha256(native.original_bytes) == context["original_sha256"], "native_mismatch")
    need(asdict(native.limits) == config["reader_limits"], "invalid_policy")
    native_manifest, integration = manifests(native, profile, config, context["selection"])
    return {"protocol": "native-observations/v1", "request_id": context["request_id"],
            "context_sha256": c.sha256(c.canonical_dumps(context)),
            "family": profile.spec.data()["family"], "source_id": native.source_id,
            "handler_spec_sha256": profile.spec.sha256, "reader_spec_sha256": profile.spec.data()["reader_spec_hash"],
            "policy_spec_sha256": policy.sha256, "reader_method": native.method,
            "binary_sha256": context["original_sha256"], "byte_length": len(native.original_bytes),
            "reader_implementation_sha256": reader_stamp(profile),
            "native_text_sha256": native.text_sha256,
            "native_manifest_sha256": None if native_manifest is None else c.sha256(native_manifest),
            "integration_manifest_sha256": c.sha256(integration), "observations": observations(native)}


def _docx_native(raw, context, config, observed):
    limits = config["reader_limits"]
    need(type(observed) is list and len(observed) <= limits["max_segments"], "observation_limit")
    segments = []
    for item in observed:
        c.exact(item, ("text", "locator", "text_sha256"))
        c.exact(item["locator"], """body_index paragraph_index table_index row_index cell_index
            char_start char_end part""".split())
        loc = item["locator"]
        need(loc["part"] == "word/document.xml" and type(item["text"]) is str)
        need(len(item["text"]) <= limits["max_segment_chars"], "text_limit")
        for key, cap in (("row_index", "max_table_rows"), ("cell_index", "max_table_columns")):
            need(loc[key] is None or (type(loc[key]) is int and 1 <= loc[key] <= limits[cap]))
        locator = docx.DocxLocator(**{k: v for k, v in loc.items() if k != "part"})
        segment = docx.TextSegment(item["text"], locator)
        need(segment.text_sha256 == item["text_sha256"], "native_mismatch")
        segments.append(segment)
    return docx.DocxExtraction(context["source_id"], raw, tuple(segments), docx.DocxLimits(**limits))


def _xlsx_native(raw, context, config, observed):
    limits = config["reader_limits"]
    need(type(observed) is list and 1 <= len(observed) <= limits["max_worksheets"], "observation_limit")
    sheets, count = [], 0
    for item in observed:
        c.exact(item, "source_id name ordinal sheet_id relationship_id part row_indices cells".split())
        need(type(item["cells"]) is list and type(item["row_indices"]) is list)
        need(len(item["row_indices"]) <= limits["max_xml_nodes"], "observation_limit")
        cells = []
        for cell in item["cells"]:
            c.exact(cell, """source_id sheet_name sheet_ordinal part coordinate row column text
                kind text_sha256""".split())
            count += 1
            need(count <= limits["max_cells"], "observation_limit")
            need(type(cell["kind"]) is str and type(cell["text"]) is str)
            need(len(cell["text"]) <= limits["max_cell_chars"], "text_limit")
            record = xlsx.CellRecord(**{**{k: v for k, v in cell.items() if k not in ("kind", "text_sha256")},
                                       "kind": xlsx.CellKind(cell["kind"])})
            need(record.text_sha256 == cell["text_sha256"], "native_mismatch")
            cells.append(record)
        sheets.append(xlsx.Worksheet(**{**{k: v for k, v in item.items() if k not in ("row_indices", "cells")},
                                       "row_indices": tuple(item["row_indices"]), "cells": tuple(cells)}))
    return xlsx.XlsxExtraction(context["source_id"], raw, tuple(sheets), xlsx.XlsxLimits(**limits))


@dataclass(frozen=True, slots=True)
class VerifiedNativeExtraction:
    """Nonpersistent mechanics only; no registration, status or approval."""
    original_bytes: bytes = field(repr=False)
    source_id: str
    handler_spec: NativeHandlerSpec
    policy_spec: c.Spec
    selection: SheetSelection | None
    native: docx.DocxExtraction | xlsx.XlsxExtraction
    native_manifest: bytes | None = field(repr=False)
    integration_manifest: bytes = field(repr=False)
    reader_implementation_sha256: str

    @property
    def binary_sha256(self):
        return c.sha256(self.original_bytes)

    @property
    def byte_length(self):
        return len(self.original_bytes)

    @property
    def native_manifest_sha256(self):
        return None if self.native_manifest is None else c.sha256(self.native_manifest)

    @property
    def integration_manifest_sha256(self):
        return c.sha256(self.integration_manifest)


def materialize(context, record, raw, profile):
    policy, config, _ = context_policy(context, profile)
    c.exact(record, """protocol request_id context_sha256 family source_id handler_spec_sha256
        reader_spec_sha256 policy_spec_sha256 reader_method binary_sha256 byte_length
        reader_implementation_sha256 native_text_sha256 native_manifest_sha256
        integration_manifest_sha256 observations""".split())
    need(type(raw) is bytes and len(raw) == context["original_length"] and
         c.sha256(raw) == context["original_sha256"], "source_mismatch")
    native = (_docx_native if profile.spec.data()["family"] == "docx" else _xlsx_native)(
        raw, context, config, record["observations"])
    need(record == make_record(context, native, profile), "native_mismatch")
    native_manifest, integration = manifests(native, profile, config, context["selection"])
    return VerifiedNativeExtraction(raw, context["source_id"], profile.spec, policy,
        None if context["selection"] is None else SheetSelection(**context["selection"]),
        native, native_manifest, integration, reader_stamp(profile))


def checked_transport(folder, family, raw):
    need(isinstance(folder, Path) and folder.name.startswith(".grundschutz-native-"), "unsafe_transport")
    need(type(raw) is bytes and family in ("docx", "xlsx"), "invalid_input")
    # Reuse pinned A0 local-volume/reparse/link/outside-Git verification only.
    class FileLimit:
        max_database_bytes = 2 * 1024 * 1024
    path = a0._path(folder / ("captured." + family), FileLimit())
    need(path.parent == folder.resolve(), "unsafe_transport")
    with path.open("rb") as stream:
        captured = stream.read(len(raw) + 1)
    need(captured == raw and len(captured) == len(raw) and c.sha256(captured) == c.sha256(raw),
         "transport_mismatch")
    return path
