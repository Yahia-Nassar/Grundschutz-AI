"""Private schema-3 history reconstruction; native reads only for VALID events.

No SQL writes, mutable original paths, proposals or human approval authority.
"""
from dataclasses import dataclass, replace
from enum import StrEnum

from . import v3_codec as c, v3_schema as schema, v3_store as foundation
from . import v2_a0 as a0
from . import v3_native_catalog as catalog
from .v3_native_contract import NativeHandlerSpec, NativeBridgeError, policy_config


class LedgerError(RuntimeError):
    """Static diagnostic; no partial trusted state or source text."""


class CorruptLedgerError(LedgerError): pass
class UnsupportedLedgerError(LedgerError): pass
class InvalidCommandError(LedgerError): pass
class StaleWriteError(LedgerError): pass
class LedgerBusyError(LedgerError): pass
class LedgerLimitError(LedgerError): pass


class RegistryExhaustedError(LedgerLimitError):
    """A registry.exhausted event actually committed; reload for the new tokens."""


class CommitOutcomeUnknownError(LedgerError):
    """COMMIT durability indeterminate; intent is NOT a committed result."""
    def __init__(self, intent):
        self.intent = intent
        super().__init__("Validation commit outcome unknown; reconcile before retry")


def need(condition, message="Invalid capture-ledger history"):
    if not condition:
        raise CorruptLedgerError(message)


@dataclass(frozen=True, slots=True)
class LedgerLimits(foundation.StoreLimits):
    max_registries: int = 4

    def __post_init__(self):
        foundation.StoreLimits.__post_init__(self)
        c.require(self.max_events > self.max_registries + 1)
        c.require(self.max_metadata_bytes > 1024 * self.max_registries)


DEFAULT_LIMITS = LedgerLimits()


@dataclass(frozen=True, slots=True)
class LedgerHead:
    store_uuid: str
    sequence: int
    event_sha256: str

    def __post_init__(self):
        c.identity(self.store_uuid); c.integer(self.sequence); c.digest(self.event_sha256)


class SourceStatus(StrEnum):
    PENDING = "pending"
    FAILED = "failed"
    VALID = "valid"


@dataclass(frozen=True, slots=True)
class Blob:
    sha256: str
    content: bytes

    def __post_init__(self):
        c.require(type(self.content) is bytes and c.sha256(self.content) == self.sha256)


@dataclass(frozen=True, slots=True)
class RegistryState:
    registry_id: str
    session_id: str
    kind: str
    policy_revision: int
    epoch: int
    history_units: int
    exhausted: bool
    retained_bytes: int
    retained_text_chars: int = 0
    retained_manifest_bytes: int = 0
    derivation_count: int = 0

    def __post_init__(self):
        c.identity(self.registry_id); c.identity(self.session_id)
        c.require(type(self.kind) is str and self.kind in ("docx", "xlsx"))
        c.integer(self.policy_revision); c.integer(self.epoch)
        for value in (self.history_units, self.retained_bytes, self.retained_text_chars,
                      self.retained_manifest_bytes, self.derivation_count):
            c.integer(value, 0)
        c.require(type(self.exhausted) is bool)


@dataclass(frozen=True, slots=True)
class PolicyActivation:
    registry_id: str
    revision: int
    spec: c.Spec
    policy_fingerprint: str
    activated_at: str


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    ref: c.SourceRef
    registry_id: str
    kind: str
    policy_revision: int
    reader_spec_hash: str
    handler_spec_hash: str
    selection_json: bytes
    start_event: int
    status: SourceStatus = SourceStatus.PENDING
    capture_event_sequence: int | None = None
    binary_sha256: str | None = None
    byte_length: int | None = None
    failure_codes: tuple[str, ...] = ()
    derivation: c.DerivationRef | None = None
    terminal_event_sequence: int | None = None
    failure_phase: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """Committed structural processing metadata, never inventory/review approval."""
    head: LedgerHead
    registration: c.SourceRef
    capture_event_sequence: int
    terminal_event_sequence: int
    terminal_event_sha256: str
    transaction_id: str
    state: SourceStatus
    derivation: c.DerivationRef | None
    failure_phase: str | None
    issue_codes: tuple[str, ...]
    source_head_at_completion: c.SourceRef
    registry: RegistryState

    def __post_init__(self):
        c.require(type(self.head) is LedgerHead and type(self.registration) is c.SourceRef)
        c.integer(self.capture_event_sequence); c.integer(self.terminal_event_sequence)
        c.digest(self.terminal_event_sha256); c.identity(self.transaction_id)
        c.require(self.terminal_event_sequence == self.head.sequence and
                  self.terminal_event_sha256 == self.head.event_sha256 and
                  self.capture_event_sequence < self.head.sequence)
        c.require(type(self.registry) is RegistryState and type(self.source_head_at_completion) is c.SourceRef)
        c.require(self.source_head_at_completion.source_id == self.registration.source_id and
                  self.source_head_at_completion.revision >= self.registration.revision)
        c.require(type(self.state) is SourceStatus and type(self.issue_codes) is tuple)
        if self.state is SourceStatus.VALID:
            c.require(type(self.derivation) is c.DerivationRef and self.failure_phase is None and not self.issue_codes)
            d = self.derivation.data()
            c.require(d["registration"] == self.registration.data() and d["store_uuid"] == self.head.store_uuid and
                      d["registry_id"] == self.registry.registry_id and d["capture_event_sequence"] == self.capture_event_sequence)
        else:
            c.require(self.state is SourceStatus.FAILED and self.derivation is None and
                      self.failure_phase == "validation" and self.issue_codes == ("parse_timeout",))


@dataclass(frozen=True, slots=True)
class _ValidationIntent:
    """Non-durable intended identifiers, bounded by verified command contracts."""
    expected: LedgerHead
    registration: c.SourceRef
    capture_event_sequence: int
    binary_sha256: str
    intended_transaction_id: str
    intended_event_sha256: str
    intended_kind: c.EventKind
    intended_derivation_sha256: str | None


@dataclass(frozen=True, slots=True)
class LedgerState:
    head: LedgerHead
    events: tuple[c.Event, ...]
    implementations: tuple[c.Spec, ...]
    handlers: tuple[NativeHandlerSpec, ...]
    policies: tuple[PolicyActivation, ...]
    registries: tuple[RegistryState, ...]
    registrations: tuple[SourceRegistration, ...]
    current_heads: tuple[c.SourceRef, ...]
    original_blobs: tuple[Blob, ...]

    def registry(self, registry_id):
        c.identity(registry_id)
        result = next((r for r in self.registries if r.registry_id == registry_id), None)
        if result is None: raise InvalidCommandError("Unknown registry")
        return result

    def registration(self, ref):
        c.require(type(ref) is c.SourceRef)
        result = next((r for r in self.registrations if r.ref == ref), None)
        if result is None: raise InvalidCommandError("Unknown registration")
        return result

    def source_head(self, source_id):
        c.text(source_id)
        return next((ref for ref in self.current_heads if ref.source_id == source_id), None)

    def is_current_valid(self, ref):
        """Native structural applicability only; no inventory/approval meaning."""
        source = self.registration(ref)
        reg = self.registry(source.registry_id)
        return (source.status is SourceStatus.VALID and self.source_head(ref.source_id) == ref and
                not reg.exhausted and source.policy_revision == reg.policy_revision)


class Replay:
    """Complete reconstruction, including fresh native verification of VALID.

    Policy table links are untrusted hints, required to equal event-owned rows.
    Stored heads/counters/status mirrors are never inputs to this state machine.
    """
    def __init__(self, blobs, policy_links, limits, budget=None):
        self.blobs, self.policy_links, self.limits = blobs, policy_links, limits
        self.budget = budget
        self.profiles = catalog.native_catalog()
        self.impl_profiles = {p.spec.data()["reader_spec_hash"]: p for p in self.profiles}
        self.handler_profiles = {p.spec.sha256: p for p in self.profiles}
        self.rows = {name: set() for name in schema.TABLES if name not in ("content_blobs", "events")}
        self.impl, self.handlers, self.policies = {}, {}, {}
        self.registries, self.sources, self.registrations, self.heads = {}, {}, {}, {}
        self.raw, self.metadata, self.reg_raw = set(), set(), {}
        self.reg_text, self.reg_manifests = {}, {}
        self.events, self.event_ids, self.transaction_ids = [], set(), set()
        self.envelope_bytes = 0
        self.store_uuid = None

    @property
    def metadata_bytes(self):
        return sum(len(self.blobs[key]) for key in self.metadata) + self.envelope_bytes

    def policy(self, rid):
        return self.policies[rid, self.registries[rid].policy_revision].spec

    def profile(self, kind):
        return next(p for p in self.profiles if p.spec.data()["family"] == kind)

    def active(self, rid):
        need(rid in self.registries and not self.registries[rid].exhausted)
        return self.registries[rid]

    def accept(self, event):
        e, p, kind = event.envelope.data(), event.payload.data(), event.payload.kind
        seq, now = e["sequence"], e["occurred_at"]
        need(seq == len(self.events) + 1)
        need(e["event_id"] not in self.event_ids and e["transaction_id"] not in self.transaction_ids)
        need(e["previous_event_sha256"] == (None if not self.events else self.events[-1].envelope.data()["event_sha256"]))
        if not self.events:
            need(kind is c.EventKind.INITIALIZED and p["store_uuid"] == e["store_uuid"])
            self.store_uuid = e["store_uuid"]
        need(e["store_uuid"] == self.store_uuid)
        self.metadata.add(e["payload_sha256"])
        self.envelope_bytes += len(event.envelope.canonical)
        if kind is c.EventKind.INITIALIZED:
            need(seq == 1)
        elif kind is c.EventKind.IMPLEMENTATION:
            key, blob = p["implementation_hash"], p["descriptor_blob_sha256"]
            need(key in self.impl_profiles and key not in self.impl)
            profile = self.impl_profiles[key]
            need(self.blobs[blob] == profile.reader_descriptor)
            spec = c.Spec(self.blobs[blob])
            need(spec.sha256 == key)
            self.impl[key] = spec
            self.metadata.add(blob)
            self.rows["implementation_specs"].add((key, blob))
        elif kind is c.EventKind.HANDLER:
            key, blob = p["handler_spec_hash"], p["descriptor_blob_sha256"]
            need(key in self.handler_profiles and key not in self.handlers)
            profile = self.handler_profiles[key]
            need(profile.spec.data()["reader_spec_hash"] in self.impl)
            need(profile.capabilities == ("extract_captured_bytes",) and self.blobs[blob] == profile.spec.canonical)
            self.handlers[key] = profile.spec
            self.metadata.add(blob)
            self.rows["reader_handler_specs"].add((key, profile.spec.data()["reader_spec_hash"], blob, seq))
        elif kind is c.EventKind.REGISTRY:
            rid, key = p["registry_id"], p["policy_spec_hash"]
            need(rid not in self.registries and len(self.registries) < self.limits.max_registries)
            need(p["session_id"] not in {r.session_id for r in self.registries.values()})
            profile = self.profile(p["kind"])
            need(profile.spec.sha256 in self.handlers and profile.spec.data()["reader_spec_hash"] in self.impl)
            implementation, blob = self.policy_links[key]
            spec = c.Spec(self.blobs[blob])
            need(spec.sha256 == key and spec.data()["implementation_hash"] == implementation)
            policy_config(spec, profile)
            fingerprint = a0._policy_object(spec).fingerprint
            self.metadata.add(blob)
            self.policies[rid, 1] = PolicyActivation(rid, 1, spec, fingerprint, now)
            self.registries[rid] = RegistryState(rid, p["session_id"], p["kind"], 1, 1, 0, False, 0)
            self.reg_raw[rid] = set()
            self.reg_text[rid] = set()
            self.reg_manifests[rid, "native"] = set()
            self.reg_manifests[rid, "integration"] = set()
            self.rows["policy_specs"].add((key, implementation, blob))
            self.rows["registries"].add((rid, p["kind"], p["session_id"], seq))
            self.rows["policy_activations"].add((rid, 1, key, fingerprint, seq, now))
        elif kind is c.EventKind.STARTED:
            ref = c.SourceRef.parse(p["registration"])
            rid, sid = p["registry_id"], ref.source_id
            reg = self.active(rid)
            profile = self.profile(reg.kind)
            need(p["policy_revision"] == reg.policy_revision and ref.registration_id not in self.registrations)
            need(p["reader_spec_hash"] == profile.spec.data()["reader_spec_hash"] and p["handler_spec_hash"] == profile.spec.sha256)
            need(p["handler_spec_hash"] in self.handlers and p["reader_spec_hash"] in self.impl)
            need((p["selection"] is None) == (reg.kind == "docx") and p["declared_lineage"] == [])
            old = self.heads.get(sid)
            need(ref.revision == (1 if old is None else old.revision + 1))
            need(p["predecessor_registration_id"] == (None if old is None else old.registration_id))
            config = self.policy(rid).data()["config"]
            need(reg.history_units + 3 <= config["max_history_units"])
            need(sum(owner == rid for owner in self.sources.values()) + (sid not in self.sources) <= config["max_sources"])
            if sid in self.sources:
                need(self.sources[sid] == rid)
            else:
                self.sources[sid] = rid
                self.rows["logical_sources"].add((sid, rid, reg.kind, seq))
            self.heads[sid] = ref
            selection = c.canonical_dumps(p["selection"])
            self.registrations[ref.registration_id] = SourceRegistration(ref, rid, reg.kind, reg.policy_revision,
                p["reader_spec_hash"], p["handler_spec_hash"], selection, seq)
            self.registries[rid] = replace(reg, epoch=reg.epoch + 1, history_units=reg.history_units + 3)
            self.rows["registrations"].add((ref.registration_id, sid, rid, ref.revision, p["predecessor_registration_id"],
                reg.policy_revision, p["reader_spec_hash"], p["handler_spec_hash"], selection, seq))
        elif kind in (c.EventKind.CAPTURED, c.EventKind.FAILED):
            ref = c.SourceRef.parse(p["registration"])
            previous = self.registrations[ref.registration_id]
            need(previous.ref == ref and previous.status is SourceStatus.PENDING)
            rid = previous.registry_id
            reg = self.active(rid)
            need(reg.policy_revision == previous.policy_revision)
            if kind is c.EventKind.CAPTURED:
                need(previous.binary_sha256 is None)
                key = p["blob_sha256"]
                raw = self.blobs[key]
                cfg = self.policy(rid).data()["config"]
                need(len(raw) == p["byte_length"] and len(raw) <= min(2097152, cfg["reader_limits"]["max_file_bytes"]))
                extra = 0 if key in self.reg_raw[rid] else len(raw)
                need(reg.retained_bytes + extra <= cfg["max_retained_bytes"])
                self.raw.add(key); self.reg_raw[rid].add(key)
                need(sum(len(self.blobs[h]) for h in self.raw) <= self.limits.max_original_bytes)
                self.registrations[ref.registration_id] = replace(previous, capture_event_sequence=seq,
                    binary_sha256=key, byte_length=len(raw))
                self.registries[rid] = replace(reg, epoch=reg.epoch + 1, retained_bytes=reg.retained_bytes + extra)
                self.rows["source_captures"].add((ref.registration_id, seq, key, len(raw)))
            else:
                if p["phase"] == "capture":
                    need(previous.binary_sha256 is None and len(p["issue_codes"]) == 1 and
                         p["issue_codes"][0] in ("capture_failed", "source_limit", "unsupported_input"))
                else:
                    need(p["phase"] == "validation" and p["issue_codes"] == ["parse_timeout"] and
                         previous.capture_event_sequence is not None and previous.binary_sha256 in self.raw)
                self.registrations[ref.registration_id] = replace(previous, status=SourceStatus.FAILED,
                    failure_codes=tuple(p["issue_codes"]), failure_phase=p["phase"], terminal_event_sequence=seq)
                self.registries[rid] = replace(reg, epoch=reg.epoch + 1)
                self.rows["source_terminals"].add((ref.registration_id, seq, "failed", None, p["phase"],
                                                     c.canonical_dumps(p["issue_codes"])))
        elif kind is c.EventKind.VALIDATED:
            from ._v3_validation import derive, derivation_row, retention
            ref = c.SourceRef.parse(p["registration"])
            previous = self.registrations[ref.registration_id]
            need(previous.ref == ref and previous.status is SourceStatus.PENDING and
                 previous.capture_event_sequence == p["capture_event_sequence"] and previous.binary_sha256 in self.raw)
            rid = previous.registry_id
            reg = self.active(rid)
            need(reg.policy_revision == previous.policy_revision and
                 p["source_head_at_validation"] == self.heads[ref.source_id].data())
            need(previous.handler_spec_hash in self.handlers and previous.reader_spec_hash in self.impl)
            policy = self.policies[rid, previous.policy_revision]
            reference = c.DerivationRef(self.blobs[p["derivation_blob_sha256"]])
            need(reference.sha256 == p["derivation_sha256"] and reference.blob_sha256 == p["derivation_blob_sha256"])
            need(self.budget is not None, "Native verification budget required")
            try:
                derived = derive(self.store_uuid, previous, policy, self.blobs[previous.binary_sha256], self.budget)
            except NativeBridgeError as exc:
                raise UnsupportedLedgerError("Historical native execution refused") from exc
            need(reference == derived.reference, "Stored derivation differs from fresh captured-byte extraction")
            for raw in derived.blobs:
                key = c.sha256(raw)
                need(self.blobs[key] == raw, "Stored native content differs from fresh extraction")
                self.metadata.add(key)
            cfg = policy.spec.data()["config"]
            text_chars, manifest_bytes = retention(self, previous, derived)
            need(text_chars <= cfg["max_retained_text_chars"] and manifest_bytes <= cfg["max_retained_manifest_bytes"])
            self.reg_text[rid].add(reference.data()["native_text_sha256"])
            for role, raw in (("native", derived.native_manifest), ("integration", derived.integration)):
                if raw is not None: self.reg_manifests[rid, role].add(c.sha256(raw))
            self.registrations[ref.registration_id] = replace(previous, status=SourceStatus.VALID,
                derivation=reference, terminal_event_sequence=seq)
            self.registries[rid] = replace(reg, epoch=reg.epoch + 1, retained_text_chars=text_chars,
                retained_manifest_bytes=manifest_bytes, derivation_count=reg.derivation_count + 1)
            self.rows["derivations"].add(derivation_row(reference, seq))
            self.rows["source_terminals"].add((ref.registration_id, seq, "valid", reference.sha256, None, b"[]"))
        elif kind is c.EventKind.EXHAUSTED:
            rid = p["registry_id"]
            reg = self.active(rid)
            need(p["budget_name"] in ("events", "sources", "history", "raw_bytes", "metadata_bytes", "policy_capacity"))
            need(len(event.payload.canonical) + len(event.envelope.canonical) <= 1024)
            self.registries[rid] = replace(reg, exhausted=True, epoch=reg.epoch + 1)
        else:
            raise UnsupportedLedgerError("Event is outside the capture-only profile")
        need(seq <= self.limits.max_events)
        need(self.metadata_bytes <= self.limits.max_metadata_bytes)
        if kind is not c.EventKind.EXHAUSTED:
            need(seq <= self.limits.max_events - self.limits.max_registries)
            need(self.metadata_bytes <= self.limits.max_metadata_bytes - 1024 * self.limits.max_registries)
        self.events.append(event)
        self.event_ids.add(e["event_id"]); self.transaction_ids.add(e["transaction_id"])

    def finish(self):
        need(bool(self.events) and self.metadata | self.raw == set(self.blobs))
        for sid, ref in self.heads.items():
            start = self.registrations[ref.registration_id].start_event
            self.rows["source_heads"].add((sid, ref.revision, ref.registration_id, start))
        for reg in self.registries.values():
            self.rows["registry_state"].add((reg.registry_id, reg.policy_revision, reg.epoch, reg.history_units,
                int(reg.exhausted), reg.retained_bytes, reg.retained_text_chars,
                reg.retained_manifest_bytes, reg.derivation_count))
        last = self.events[-1].envelope.data()
        self.rows["store_metadata"].add((1, self.store_uuid, 3, c.EVENT_CODEC, c.SERIALIZATION_VERSION,
                                      c.FEATURE_PROFILE, last["sequence"], last["event_sha256"]))
        return LedgerState(LedgerHead(self.store_uuid, last["sequence"], last["event_sha256"]), tuple(self.events),
            tuple(self.impl[key] for key in sorted(self.impl)), tuple(self.handlers[key] for key in sorted(self.handlers)),
            tuple(self.policies.values()), tuple(self.registries.values()), tuple(self.registrations.values()),
            tuple(self.heads[key] for key in sorted(self.heads)), tuple(Blob(key, self.blobs[key]) for key in sorted(self.raw)))
