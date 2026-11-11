"""Strict inert schema-3 contracts; recognition grants no write capability.

canonical-json/v1 and SourceRef deliberately reuse unchanged v2 primitives.
There is no database, reader, handler dispatch or event-append operation here.
"""
from dataclasses import dataclass
from enum import StrEnum

from .v2_codec import (
    CodecError, CodecLimits, DEFAULT_LIMITS, SourceRef, Spec,
    canonical_dumps, canonical_loads, sha256, fingerprint,
    text, integer, identity, digest, timestamp, utc_now, exact, sheet_identity,
)

SERIALIZATION_VERSION = "canonical-json/v1"
EVENT_CODEC = "ledger-event/v3"
SCHEMA_VERSION = 3
FEATURE_PROFILE = "verified-source/v1"
PHYSICAL_PROFILE = "sqlite-source-validation/v1"


def require(condition):
    if not condition:
        raise CodecError("Invalid or unsupported v3 contract")


class EventKind(StrEnum):
    INITIALIZED = "store.initialized"
    IMPLEMENTATION = "implementation.registered"
    HANDLER = "reader.handler_registered"
    REGISTRY = "registry.created"
    POLICY = "policy.activated"
    STARTED = "source.started"
    CAPTURED = "source.captured"
    FAILED = "source.failed"
    VALIDATED = "source.validated"
    EXHAUSTED = "registry.exhausted"


_SHAPES = {
    EventKind.INITIALIZED: ("store-init/v2", "store_uuid schema_version serialization_version feature_profile"),
    EventKind.IMPLEMENTATION: ("implementation-register/v1", "implementation_hash descriptor_blob_sha256"),
    EventKind.HANDLER: ("reader-handler-register/v1", "handler_spec_hash descriptor_blob_sha256"),
    EventKind.REGISTRY: ("registry-create/v1", "registry_id kind session_id initial_policy_revision policy_spec_hash baseline_registry_epoch baseline_history_units"),
    EventKind.POLICY: ("policy-activate/v1", "registry_id revision predecessor_revision policy_spec_hash policy_fingerprint activated_at"),
    EventKind.STARTED: ("source-start/v2", "registry_id registration predecessor_registration_id policy_revision reader_spec_hash handler_spec_hash selection declared_lineage observed_at"),
    EventKind.CAPTURED: ("source-capture/v1", "registration blob_sha256 byte_length observed_at"),
    EventKind.FAILED: ("source-fail/v2", "registration phase issue_codes observed_at"),
    EventKind.VALIDATED: ("source-valid/v1", "registration capture_event_sequence derivation_sha256 derivation_blob_sha256 source_head_at_validation observed_at"),
    EventKind.EXHAUSTED: ("registry-exhaust/v1", "registry_id budget_name observed_at"),
}
_TAGS = {shape[0]: kind for kind, shape in _SHAPES.items()}
EVENT_CONTRACTS = tuple((kind.value, shape[0]) for kind, shape in _SHAPES.items())
FAILURE_PHASES = ("capture", "validation", "environment", "interrupted", "capacity")
FAILURE_CODES = (
    "capture_failed", "source_limit", "unsupported_input", "invalid_source",
    "unsupported_structure", "parse_timeout", "operator_failed", "abandoned",
    "resource_exhausted",
)
BUDGET_NAMES = ("events", "sources", "history", "raw_bytes", "policy_capacity", "metadata_bytes")
_MACHINE_KINDS = (EventKind.CAPTURED, EventKind.FAILED, EventKind.VALIDATED, EventKind.EXHAUSTED)


def _payload(data):
    require(type(data) is dict and type(data.get("payload_codec")) is str)
    require(data["payload_codec"] in _TAGS)
    kind = _TAGS[data["payload_codec"]]
    exact(data, ("payload_codec", *_SHAPES[kind][1].split()))
    for name in ("store_uuid", "registry_id", "session_id"):
        if name in data:
            identity(data[name])
    for name in ("implementation_hash", "descriptor_blob_sha256", "handler_spec_hash",
                 "policy_spec_hash", "policy_fingerprint", "reader_spec_hash", "blob_sha256",
                 "derivation_sha256", "derivation_blob_sha256"):
        if name in data:
            digest(data[name])
    for name in ("revision", "predecessor_revision", "policy_revision", "initial_policy_revision",
                 "baseline_registry_epoch", "capture_event_sequence"):
        if name in data:
            integer(data[name])
    for name in ("observed_at", "activated_at"):
        if name in data:
            timestamp(data[name])
    if "registration" in data:
        SourceRef.parse(data["registration"])
    if kind is EventKind.INITIALIZED:
        require(type(data["schema_version"]) is int and data["schema_version"] == 3)
        require(data["serialization_version"] == SERIALIZATION_VERSION)
        require(data["feature_profile"] == FEATURE_PROFILE)
    elif kind is EventKind.REGISTRY:
        require(type(data["kind"]) is str and data["kind"] in ("docx", "xlsx"))
        require(data["initial_policy_revision"] == data["baseline_registry_epoch"] == 1)
        integer(data["baseline_history_units"], 0)
        require(data["baseline_history_units"] == 0)
    elif kind is EventKind.POLICY:
        require(data["revision"] == data["predecessor_revision"] + 1)
    elif kind is EventKind.STARTED:
        ref = SourceRef.parse(data["registration"])
        predecessor = data["predecessor_registration_id"]
        require((ref.revision == 1) == (predecessor is None))
        if predecessor is not None:
            identity(predecessor)
            require(predecessor != ref.registration_id)
        if data["selection"] is not None:
            sheet_identity(data["selection"])
        require(type(data["declared_lineage"]) is list and data["declared_lineage"] == [])
    elif kind is EventKind.CAPTURED:
        integer(data["byte_length"], 0)
        require(data["byte_length"] <= 2 * 1024 * 1024)
    elif kind is EventKind.FAILED:
        require(type(data["phase"]) is str and data["phase"] in FAILURE_PHASES)
        codes = data["issue_codes"]
        require(type(codes) is list and 1 <= len(codes) <= 4)
        require(all(type(code) is str and code in FAILURE_CODES for code in codes))
        require(len(set(codes)) == len(codes))
    elif kind is EventKind.VALIDATED:
        ref = SourceRef.parse(data["registration"])
        head = SourceRef.parse(data["source_head_at_validation"])
        require(head.source_id == ref.source_id and head.revision >= ref.revision)
        require((head.revision == ref.revision) == (head == ref))
        require(head.revision == ref.revision or head.registration_id != ref.registration_id)
    elif kind is EventKind.EXHAUSTED:
        require(type(data["budget_name"]) is str and data["budget_name"] in BUDGET_NAMES)
    return kind


@dataclass(frozen=True, slots=True)
class Payload:
    canonical: bytes

    def __post_init__(self):
        _payload(canonical_loads(self.canonical))

    def data(self):
        return canonical_loads(self.canonical)

    @property
    def kind(self):
        return _TAGS[self.data()["payload_codec"]]


def make_payload(event_kind: EventKind, **values) -> Payload:
    require(type(event_kind) is EventKind and "payload_codec" not in values)
    return Payload(canonical_dumps({"payload_codec": _SHAPES[event_kind][0], **values}))


@dataclass(frozen=True, slots=True)
class DerivationRef:
    """Inert derivation-ref/v2 shape, not a verified source or domain record."""
    canonical: bytes

    def __post_init__(self):
        data = self.data()
        exact(data, """type store_uuid registry_id registration kind capture_event_sequence
            binary_sha256 byte_length reader_spec_hash handler_spec_hash policy_revision
            policy_spec_hash policy_fingerprint reader_limits_sha256 reader_method
            reader_implementation_sha256 native_text_sha256 native_manifest_sha256
            integration_manifest_sha256""".split())
        require(data["type"] == "derivation-ref/v2")
        identity(data["store_uuid"])
        identity(data["registry_id"])
        SourceRef.parse(data["registration"])
        integer(data["capture_event_sequence"])
        integer(data["policy_revision"])
        integer(data["byte_length"], 0)
        require(data["byte_length"] <= 2 * 1024 * 1024)
        for name in ("binary_sha256", "reader_spec_hash", "handler_spec_hash", "policy_spec_hash",
                     "policy_fingerprint", "reader_limits_sha256", "reader_implementation_sha256",
                     "native_text_sha256", "integration_manifest_sha256"):
            digest(data[name])
        require(type(data["kind"]) is str and data["kind"] in ("docx", "xlsx"))
        require(data["reader_method"] == ("docx-plain/v1" if data["kind"] == "docx" else "xlsx-literal/v1"))
        if data["kind"] == "docx":
            require(data["native_manifest_sha256"] is None)
        else:
            digest(data["native_manifest_sha256"])

    def data(self):
        return canonical_loads(self.canonical)

    @property
    def sha256(self):
        data = self.data()
        tag = data.pop("type")
        return fingerprint(tag, data)

    @property
    def blob_sha256(self):
        return sha256(self.canonical)


_ENVELOPE_FIELDS = """codec store_uuid sequence event_id transaction_id transaction_index
    transaction_count kind payload_codec payload_sha256 previous_event_sha256 event_sha256
    occurred_at actor_id""".split()


@dataclass(frozen=True, slots=True)
class Envelope:
    canonical: bytes

    def __post_init__(self):
        data = self.data()
        exact(data, _ENVELOPE_FIELDS)
        require(data["codec"] == EVENT_CODEC)
        for name in ("store_uuid", "event_id", "transaction_id"):
            identity(data[name])
        for name in ("sequence", "transaction_index", "transaction_count"):
            integer(data[name])
        require(data["transaction_index"] == data["transaction_count"] == 1)
        require(type(data["kind"]) is str and data["kind"] in EventKind._value2member_map_)
        kind = EventKind(data["kind"])
        require(data["payload_codec"] == _SHAPES[kind][0])
        digest(data["payload_sha256"])
        digest(data["event_sha256"])
        if data["previous_event_sha256"] is not None:
            digest(data["previous_event_sha256"])
        require((data["sequence"] == 1) == (data["previous_event_sha256"] is None))
        require((data["sequence"] == 1) == (kind is EventKind.INITIALIZED))
        timestamp(data["occurred_at"])
        if data["actor_id"] is None:
            require(kind in _MACHINE_KINDS)
        else:
            text(data["actor_id"])
        claimed = data.pop("event_sha256")
        require(fingerprint(EVENT_CODEC, data) == claimed)

    def data(self):
        return canonical_loads(self.canonical)


@dataclass(frozen=True, slots=True)
class Event:
    """Consistent inert envelope/payload pair; no application side effects."""
    envelope: Envelope
    payload: Payload

    def __post_init__(self):
        require(type(self.envelope) is Envelope and type(self.payload) is Payload)
        e, p = self.envelope.data(), self.payload.data()
        require(e["kind"] == self.payload.kind.value and e["payload_codec"] == p["payload_codec"])
        require(e["payload_sha256"] == sha256(self.payload.canonical))
        if self.payload.kind is EventKind.INITIALIZED:
            require(e["store_uuid"] == p["store_uuid"])
        for name in ("observed_at", "activated_at"):
            if name in p:
                require(p[name] == e["occurred_at"])
        if self.payload.kind is EventKind.VALIDATED:
            require(p["capture_event_sequence"] < e["sequence"])


def make_envelope(payload: Payload, *, store_uuid: str, sequence: int, previous: str | None,
                  event_id: str, transaction_id: str, occurred_at: str, actor_id: str | None) -> Envelope:
    require(type(payload) is Payload)
    data = dict(codec=EVENT_CODEC, store_uuid=store_uuid, sequence=sequence, event_id=event_id,
                transaction_id=transaction_id, transaction_index=1, transaction_count=1,
                kind=payload.kind.value, payload_codec=payload.data()["payload_codec"],
                payload_sha256=sha256(payload.canonical), previous_event_sha256=previous,
                occurred_at=occurred_at, actor_id=actor_id)
    data["event_sha256"] = fingerprint(EVENT_CODEC, data)
    envelope = Envelope(canonical_dumps(data))
    Event(envelope, payload)
    return envelope
