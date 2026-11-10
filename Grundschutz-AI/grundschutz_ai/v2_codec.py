"""Strict, bounded source-ledger codecs. No executable deserialization."""

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re


SERIALIZATION_VERSION = "canonical-json/v1"
EVENT_CODEC = "ledger-event/v2"
SCHEMA_VERSION = 2


class CodecError(ValueError):
    """Static diagnostic; untrusted payload text is never interpolated."""


def require(condition):
    if not condition:
        raise CodecError("Invalid or unsupported v2 value")


@dataclass(frozen=True, slots=True)
class CodecLimits:
    max_bytes: int = 8 * 1024 * 1024
    max_depth: int = 64
    max_nodes: int = 100_000
    max_array: int = 10_000
    max_string_bytes: int = 1024 * 1024

    def __post_init__(self):
        for f in fields(self):
            require(type(getattr(self, f.name)) is int and 1 <= getattr(self, f.name) <= f.default)


DEFAULT_LIMITS = CodecLimits()


def text(value, maximum=256):
    require(type(value) is str and bool(value.strip()))
    try:
        require(len(value.encode("utf-8", errors="strict")) <= maximum)
    except UnicodeError as exc:
        raise CodecError("Invalid UTF-8 text") from exc


def integer(value, minimum=1):
    require(type(value) is int and minimum <= value <= 2**63 - 1)


def identity(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{32}", value) is not None)


def digest(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def timestamp(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", value) is not None)
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise CodecError("Invalid UTC audit timestamp") from exc


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def exact(data, names):
    require(type(data) is dict and set(data) == set(names))


def _walk(value, limits, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    require(depth <= limits.max_depth and count[0] <= limits.max_nodes)
    if type(value) is str:
        try:
            require(len(value.encode("utf-8", errors="strict")) <= limits.max_string_bytes)
        except UnicodeError as exc:
            raise CodecError("Invalid Unicode scalar") from exc
    elif type(value) is int:
        require(-(2**63) <= value <= 2**63 - 1)
    elif value is None or type(value) is bool:
        pass
    elif type(value) is list:
        require(len(value) <= limits.max_array)
        for child in value:
            _walk(child, limits, depth + 1, count)
    elif type(value) is dict:
        require(len(value) <= limits.max_array)
        for key, child in value.items():
            require(type(key) is str)
            _walk(key, limits, depth + 1, count)
            _walk(child, limits, depth + 1, count)
    else:
        raise CodecError("Unsupported JSON type")


def canonical_dumps(value, limits: CodecLimits = DEFAULT_LIMITS) -> bytes:
    require(type(limits) is CodecLimits)
    try:
        _walk(value, limits)
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
        require(len(raw) <= limits.max_bytes)
        return raw
    except (UnicodeError, RecursionError) as exc:
        raise CodecError("JSON resource or Unicode limit") from exc


def _preflight(raw, limits):
    require(type(raw) is bytes and len(raw) <= limits.max_bytes and not raw.startswith(b"\xef\xbb\xbf"))
    # Bound lexical depth/tokens/array separators before json.loads allocates.
    stack, quoted, escaped, tokens, primitive, string_bytes = [], False, False, 0, False, 0
    for byte in raw:
        if quoted:
            string_bytes += 1
            require(string_bytes <= 6 * limits.max_string_bytes + 2)
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            continue
        if byte == 34:
            quoted, primitive, string_bytes = True, False, 0
            tokens += 1
        elif byte in (123, 91):
            stack.append([byte, 0])
            require(len(stack) <= limits.max_depth)
            tokens += 1
            primitive = False
        elif byte in (125, 93):
            require(bool(stack))
            opening, _ = stack.pop()
            require((opening, byte) in ((123, 125), (91, 93)))
            primitive = False
        elif byte == 44:
            if stack:
                stack[-1][1] += 1
                require(stack[-1][1] < limits.max_array)
            primitive = False
        elif byte in b": \t\r\n":
            primitive = False
        elif not primitive:
            tokens += 1
            primitive = True
        require(tokens <= limits.max_nodes)
    require(not quoted and not stack)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def _no_float(value):
    raise CodecError("Floating or nonfinite numbers are forbidden")


def _parse_integer(value):
    require(len(value) <= 20)
    number = int(value)
    require(-(2**63) <= number <= 2**63 - 1)
    return number


def canonical_loads(raw: bytes, limits: CodecLimits = DEFAULT_LIMITS):
    require(type(limits) is CodecLimits)
    _preflight(raw, limits)
    try:
        result = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique,
                            parse_int=_parse_integer, parse_float=_no_float, parse_constant=_no_float)
        _walk(result, limits)
        require(canonical_dumps(result, limits) == raw)
        return result
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise CodecError("Noncanonical, malformed or over-budget JSON") from exc


def sha256(raw: bytes) -> str:
    require(type(raw) is bytes)
    return hashlib.sha256(raw).hexdigest()


def fingerprint(tag: str, value) -> str:
    text(tag)
    return sha256(canonical_dumps({"type": tag, "value": value}))


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_id: str
    revision: int
    registration_id: str

    def __post_init__(self):
        text(self.source_id)
        integer(self.revision)
        identity(self.registration_id)

    def data(self):
        return {"source_id": self.source_id, "revision": self.revision, "registration_id": self.registration_id}

    @classmethod
    def parse(cls, data):
        exact(data, ("source_id", "revision", "registration_id"))
        return cls(**data)


class EventKind(StrEnum):
    INITIALIZED = "store.initialized"
    IMPLEMENTATION = "implementation.registered"
    REGISTRY = "registry.created"
    POLICY = "policy.activated"
    STARTED = "source.started"
    CAPTURED = "source.captured"
    FAILED = "source.failed"
    EXHAUSTED = "registry.exhausted"


_SHAPES = {
    EventKind.INITIALIZED: ("store-init/v1", "store_uuid schema_version serialization_version feature_profile"),
    EventKind.IMPLEMENTATION: ("implementation-register/v1", "implementation_hash descriptor_blob_sha256"),
    EventKind.REGISTRY: ("registry-create/v1", "registry_id kind session_id initial_policy_revision policy_spec_hash baseline_registry_epoch baseline_history_units"),
    EventKind.POLICY: ("policy-activate/v1", "registry_id revision predecessor_revision policy_spec_hash policy_fingerprint activated_at"),
    EventKind.STARTED: ("source-start/v1", "registry_id registration predecessor_registration_id policy_revision reader_spec_hash selection declared_lineage observed_at"),
    EventKind.CAPTURED: ("source-capture/v1", "registration blob_sha256 byte_length observed_at"),
    EventKind.FAILED: ("source-fail/v1", "registration phase issue_codes observed_at"),
    EventKind.EXHAUSTED: ("registry-exhaust/v1", "registry_id budget_name observed_at"),
}
_TAGS = {shape[0]: kind for kind, shape in _SHAPES.items()}
FAILURE_CODES = frozenset(("capture_failed", "source_limit", "unsupported_input", "abandoned", "operator_failed"))
BUDGET_NAMES = frozenset(("events", "sources", "history", "raw_bytes", "policy_capacity", "metadata_bytes"))


def sheet_identity(data):
    exact(data, ("name", "ordinal", "sheet_id", "relationship_id", "part"))
    require(data["name"] == "IT-Systeme")
    integer(data["ordinal"])
    integer(data["sheet_id"])
    require(data["ordinal"] <= 16 and data["sheet_id"] <= 0xFFFFFFFF)
    require(type(data["relationship_id"]) is str and re.fullmatch(r"rId[1-9][0-9]{0,5}", data["relationship_id"]) is not None)
    require(type(data["part"]) is str and re.fullmatch(r"xl/worksheets/sheet[1-9][0-9]*\.xml", data["part"]) is not None)


def _payload(data):
    require(type(data) is dict and type(data.get("payload_codec")) is str and data["payload_codec"] in _TAGS)
    kind = _TAGS[data["payload_codec"]]
    exact(data, ("payload_codec", *_SHAPES[kind][1].split()))
    for name in ("store_uuid", "registry_id", "session_id"):
        if name in data:
            identity(data[name])
    for name in ("implementation_hash", "descriptor_blob_sha256", "policy_spec_hash", "policy_fingerprint", "reader_spec_hash", "blob_sha256"):
        if name in data:
            digest(data[name])
    for name in ("revision", "predecessor_revision", "policy_revision", "initial_policy_revision", "baseline_registry_epoch"):
        if name in data:
            integer(data[name])
    for name in ("observed_at", "activated_at"):
        if name in data:
            timestamp(data[name])
    if "registration" in data:
        SourceRef.parse(data["registration"])
    if kind is EventKind.INITIALIZED:
        require(type(data["schema_version"]) is int and data["schema_version"] == SCHEMA_VERSION)
        require(data["serialization_version"] == SERIALIZATION_VERSION and data["feature_profile"] == "staging_only")
    elif kind is EventKind.REGISTRY:
        require(data["kind"] in ("docx", "xlsx") and data["initial_policy_revision"] == data["baseline_registry_epoch"] == 1)
        integer(data["baseline_history_units"], 0)
        require(data["baseline_history_units"] == 0)
    elif kind is EventKind.POLICY:
        require(data["revision"] == data["predecessor_revision"] + 1)
    elif kind is EventKind.STARTED:
        if data["predecessor_registration_id"] is not None:
            identity(data["predecessor_registration_id"])
        if data["selection"] is not None:
            sheet_identity(data["selection"])
        require(type(data["declared_lineage"]) is list and not data["declared_lineage"])
    elif kind is EventKind.CAPTURED:
        integer(data["byte_length"], 0)
    elif kind is EventKind.FAILED:
        require(data["phase"] in ("capture", "environment", "interrupted", "capacity"))
        require(type(data["issue_codes"]) is list and 1 <= len(data["issue_codes"]) <= 16)
        require(all(type(code) is str and code in FAILURE_CODES for code in data["issue_codes"]))
        require(len(set(data["issue_codes"])) == len(data["issue_codes"]))
    elif kind is EventKind.EXHAUSTED:
        require(type(data["budget_name"]) is str and data["budget_name"] in BUDGET_NAMES)
    return kind


@dataclass(frozen=True, slots=True)
class Payload:
    """Validated tagged payload bytes; data() returns a detached temporary dict."""
    canonical: bytes

    def __post_init__(self):
        _payload(canonical_loads(self.canonical))

    @property
    def kind(self) -> EventKind:
        return _TAGS[self.data()["payload_codec"]]

    def data(self):
        return canonical_loads(self.canonical)


def make_payload(event_kind: EventKind, **values) -> Payload:
    require(type(event_kind) is EventKind)
    return Payload(canonical_dumps({"payload_codec": _SHAPES[event_kind][0], **values}))


_BASE_READER = set("max_file_bytes max_uncompressed_bytes max_entries max_ratio max_xml_bytes max_xml_depth max_xml_nodes max_xml_attributes max_attribute_chars max_namespaces max_xml_chars max_text_chars".split())
_COMMON_POLICY = set("reader_limits max_sources max_id_chars max_location_chars max_scope_chars max_manifest_bytes max_retained_bytes max_retained_text_chars max_retained_manifest_bytes max_history_units".split())
MODULE_NAMES = frozenset(("docx_ingestion", "xlsx_ingestion", "ooxml_safety", "docx_staging", "xlsx_staging", "support", "validation", "v2_codec", "v2_ledger", "v2_schema"))


@dataclass(frozen=True, slots=True)
class Spec:
    canonical: bytes

    def __post_init__(self):
        data = canonical_loads(self.canonical)
        require(type(data) is dict and type(data.get("type")) is str)
        if data["type"] == "implementation-spec/v1":
            exact(data, ("type", "family", "method_version", "module_hashes", "runtime", "serialization_version"))
            require(data["family"] in ("docx", "xlsx"))
            require(data["method_version"] == ("docx-plain/v1" if data["family"] == "docx" else "xlsx-literal/v1"))
            require(data["serialization_version"] == SERIALIZATION_VERSION)
            require(type(data["module_hashes"]) is list and 1 <= len(data["module_hashes"]) <= len(MODULE_NAMES))
            names = []
            for module in data["module_hashes"]:
                exact(module, ("module_name", "sha256"))
                require(type(module["module_name"]) is str and module["module_name"] in MODULE_NAMES)
                digest(module["sha256"])
                names.append(module["module_name"])
            require(names == sorted(set(names)))
            exact(data["runtime"], ("python_version", "platform_profile", "sqlite_version"))
            for value in data["runtime"].values():
                text(value, 128)
        elif data["type"] == "policy-spec/v1":
            exact(data, ("type", "kind", "semantic_version", "config", "implementation_hash"))
            require(data["kind"] in ("docx", "xlsx"))
            require(data["semantic_version"] == ("docx-single-assertion/v1" if data["kind"] == "docx" else "synthetic-it-table/v1"))
            digest(data["implementation_hash"])
            extra = {"max_source_chars", "max_field_bytes"} if data["kind"] == "docx" else {"max_data_rows", "max_scope_rows"}
            exact(data["config"], _COMMON_POLICY | extra)
            extra_reader = {"max_segments", "max_segment_chars", "max_table_rows", "max_table_columns"} if data["kind"] == "docx" else {"max_worksheets", "max_cells", "max_shared_strings", "max_cell_chars", "max_shared_text_chars"}
            exact(data["config"]["reader_limits"], _BASE_READER | extra_reader)
            for name, value in data["config"].items():
                for limit in value.values() if name == "reader_limits" else (value,):
                    integer(limit)
        else:
            raise CodecError("Unsupported specification version")

    def data(self):
        return canonical_loads(self.canonical)

    @property
    def sha256(self):
        data = self.data()
        tag = data.pop("type")
        return fingerprint(tag, data)


@dataclass(frozen=True, slots=True)
class Envelope:
    canonical: bytes

    def __post_init__(self):
        data = self.data()
        exact(data, "codec store_uuid sequence event_id transaction_id transaction_index transaction_count kind payload_codec payload_sha256 previous_event_sha256 event_sha256 occurred_at actor_id".split())
        require(data["codec"] == EVENT_CODEC)
        for name in ("store_uuid", "event_id", "transaction_id"):
            identity(data[name])
        for name in ("sequence", "transaction_index", "transaction_count"):
            integer(data[name])
        require(data["transaction_index"] <= data["transaction_count"])
        require(type(data["kind"]) is str and data["kind"] in EventKind._value2member_map_)
        require(data["payload_codec"] == _SHAPES[EventKind(data["kind"])][0])
        digest(data["payload_sha256"])
        digest(data["event_sha256"])
        if data["previous_event_sha256"] is not None:
            digest(data["previous_event_sha256"])
        require((data["sequence"] == 1) == (data["previous_event_sha256"] is None))
        timestamp(data["occurred_at"])
        if data["actor_id"] is not None:
            text(data["actor_id"])
        claimed = data.pop("event_sha256")
        require(fingerprint(EVENT_CODEC, data) == claimed)

    def data(self):
        return canonical_loads(self.canonical)


def make_envelope(payload: Payload, *, store_uuid: str, sequence: int, previous: str | None,
                  event_id: str, transaction_id: str, occurred_at: str, actor_id: str | None) -> Envelope:
    require(type(payload) is Payload)
    data = dict(codec=EVENT_CODEC, store_uuid=store_uuid, sequence=sequence, event_id=event_id,
                transaction_id=transaction_id, transaction_index=1, transaction_count=1,
                kind=payload.kind.value, payload_codec=payload.data()["payload_codec"],
                payload_sha256=sha256(payload.canonical), previous_event_sha256=previous,
                occurred_at=occurred_at, actor_id=actor_id)
    data["event_sha256"] = fingerprint(EVENT_CODEC, data)
    return Envelope(canonical_dumps(data))
