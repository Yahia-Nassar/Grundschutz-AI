"""Synthetic DOCX staging only: no AI, domain construction, approval or store.

Use DocxStaging.is_eligible against live session state. Immutable outputs are
historical snapshots, not enduring eligibility certificates or authenticated data.
"""

from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from tempfile import TemporaryDirectory, gettempdir
from threading import RLock
from uuid import uuid4

from . import docx_ingestion as reader, ooxml_safety
from . import support, validation
from .domain import Predicate, ReviewState
from .extraction import MAX_SOURCE_CHARS


POLICY_VERSION = "docx-single-assertion/v1"
IMPLEMENTATION = "grundschutz_ai.docx_staging/1.0.1"
REMEDIATION_VERSION = "docx-assertion-remediation/v1"
_QUEUE_STATES = (ReviewState.PROPOSED, ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION)


class StagingError(ValueError):
    """Static application diagnostic, never source text or a fabricated review."""

    def __init__(self, code="invalid_argument"):
        self.code = code
        super().__init__(f"DOCX staging refused: {code}")


def _text(value, maximum=256):
    if type(value) is not str or not value.strip():
        raise StagingError()
    try:
        if len(value.encode("utf-8")) > maximum:
            raise StagingError()
    except UnicodeError as exc:
        raise StagingError() from exc


def _positive(value):
    if type(value) is not int or value < 1:
        raise StagingError()


def _digest(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise StagingError()


def _aware(value):
    if type(value) is not datetime or value.utcoffset() is None:
        raise StagingError("aware_timestamp_required")


def _tuple(value, kind):
    if type(value) is not tuple or any(type(item) is not kind for item in value):
        raise StagingError()


def _json(value):
    return json.dumps(value, default=asdict, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _fingerprint(value):
    return _sha(_json(value).encode("utf-8"))


def _init_data(record):
    return {item.name: getattr(record, item.name) for item in fields(record) if item.init}


@dataclass(frozen=True, slots=True)
class StagingPolicy:
    reader_limits: reader.DocxLimits = reader.DEFAULT_LIMITS
    max_sources: int = 16
    max_retained_bytes: int = 32 * 1024 * 1024
    max_retained_text_chars: int = 1_000_000
    max_retained_manifest_bytes: int = 32 * 1024 * 1024
    max_scope_chars: int = 1_000_000
    max_source_chars: int = MAX_SOURCE_CHARS
    max_id_chars: int = 64
    max_location_chars: int = 256
    max_field_bytes: int = 16 * 1024
    max_manifest_bytes: int = 8 * 1024 * 1024
    max_history_units: int = 512
    version: str = field(default=POLICY_VERSION, init=False)
    fingerprint: str = field(init=False)

    def __post_init__(self):
        if type(self.reader_limits) is not reader.DocxLimits:
            raise StagingError()
        for item in fields(reader.DEFAULT_LIMITS):
            if getattr(self.reader_limits, item.name) > getattr(reader.DEFAULT_LIMITS, item.name):
                raise StagingError("limits_may_only_tighten")
        for item in fields(self):
            if item.init and item.name != "reader_limits":
                value = getattr(self, item.name)
                if type(value) is not int or not 1 <= value <= item.default:
                    raise StagingError("limits_may_only_tighten")
        object.__setattr__(self, "fingerprint", _fingerprint({"version": self.version, "implementation": IMPLEMENTATION, "support": support.SUPPORT_POLICY, "limits": _init_data(self)}))


class RegistrationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PolicyRevision:
    revision: int
    policy: StagingPolicy
    activated_at: datetime

    def __post_init__(self):
        _positive(self.revision)
        _aware(self.activated_at)
        if type(self.policy) is not StagingPolicy:
            raise StagingError()


@dataclass(frozen=True, slots=True)
class StagingIssue:
    code: str
    source_id: str | None = None

    def __post_init__(self):
        if self.code not in {
            "unsupported_input", "lineage_excluded", "capture_failed", "source_limit",
            "reader_rejected", "native_mismatch", "session_exhausted", "source_missing",
            "source_pending", "source_failed", "scope_stale", "scope_omits_source",
            "reader_policy_changed", "scope_limit", "extra_structure", "source_text_limit",
            "unsupported_assertion", "validator_disagreement", "field_limit", "duplicate_asset",
            "conflicting_assertions", "queue_blocked",
        }:
            raise StagingError()
        if self.source_id is not None:
            _text(self.source_id)


@dataclass(frozen=True, slots=True)
class RegistrationRef:
    source_id: str
    revision: int
    registration_id: str

    def __post_init__(self):
        _text(self.source_id)
        _positive(self.revision)
        if type(self.registration_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", self.registration_id):
            raise StagingError()


@dataclass(frozen=True, slots=True)
class RegistrationEvent:
    sequence: int
    ref: RegistrationRef
    status: RegistrationStatus
    observed_at: datetime
    reader_limits: reader.DocxLimits
    original_bytes: bytes | None = field(default=None, repr=False)
    issues: tuple[StagingIssue, ...] = ()
    binary_sha256: str | None = field(init=False)

    def __post_init__(self):
        _positive(self.sequence)
        _aware(self.observed_at)
        if type(self.ref) is not RegistrationRef or type(self.status) is not RegistrationStatus or type(self.reader_limits) is not reader.DocxLimits or (self.original_bytes is not None and type(self.original_bytes) is not bytes):
            raise StagingError()
        _tuple(self.issues, StagingIssue)
        if self.status is RegistrationStatus.VALID and (self.original_bytes is None or self.issues):
            raise StagingError()
        if self.status is RegistrationStatus.FAILED and not self.issues:
            raise StagingError()
        object.__setattr__(self, "binary_sha256", None if self.original_bytes is None else _sha(self.original_bytes))


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    ref: RegistrationRef
    native: reader.DocxExtraction
    reader_implementation_sha256: str
    manifest_json: str = field(init=False)
    manifest_sha256: str = field(init=False)

    def __post_init__(self):
        if type(self.ref) is not RegistrationRef or type(self.native) is not reader.DocxExtraction or self.native.source_id != self.ref.source_id:
            raise StagingError()
        _digest(self.reader_implementation_sha256)
        manifest = _json({"manifest_version": "docx-integration/v1", "source_id": self.ref.source_id, "binary_sha256": self.native.docx_sha256, "reader_method": self.native.method, "reader_implementation_sha256": self.reader_implementation_sha256, "reader_limits": asdict(self.native.limits), "native_text_sha256": self.native.text_sha256, "segments": [asdict(segment) for segment in self.native.segments]})
        object.__setattr__(self, "manifest_json", manifest)
        object.__setattr__(self, "manifest_sha256", _sha(manifest.encode("utf-8")))


@dataclass(frozen=True, slots=True)
class ReviewScope:
    session_id: str
    revision: int
    registry_epoch: int
    source_ids: tuple[str, ...]
    heads: tuple[RegistrationRef | None, ...]
    policy_fingerprint: str
    policy_revision: int
    fingerprint: str = field(init=False)

    def __post_init__(self):
        _text(self.session_id)
        _positive(self.revision)
        _positive(self.registry_epoch)
        _digest(self.policy_fingerprint)
        _positive(self.policy_revision)
        if type(self.source_ids) is not tuple or not self.source_ids or len(self.source_ids) > 16 or len(set(self.source_ids)) != len(self.source_ids) or type(self.heads) is not tuple or len(self.heads) != len(self.source_ids):
            raise StagingError()
        for name, ref in zip(self.source_ids, self.heads):
            _text(name)
            if ref is not None and (type(ref) is not RegistrationRef or ref.source_id != name):
                raise StagingError()
        object.__setattr__(self, "fingerprint", _fingerprint(_init_data(self)))


@dataclass(frozen=True, slots=True)
class DocumentBinding:
    ref: RegistrationRef
    manifest_sha256: str
    scope_fingerprint: str
    policy_fingerprint: str
    fingerprint: str = field(init=False)

    def __post_init__(self):
        if type(self.ref) is not RegistrationRef:
            raise StagingError()
        for value in (self.manifest_sha256, self.scope_fingerprint, self.policy_fingerprint):
            _digest(value)
        object.__setattr__(self, "fingerprint", _fingerprint(_init_data(self)))


@dataclass(frozen=True, slots=True)
class DocxQuote:
    binding_fingerprint: str
    segment_ordinal: int
    segment_sha256: str
    locator: reader.DocxLocator
    text: str

    def __post_init__(self):
        _digest(self.binding_fingerprint)
        _digest(self.segment_sha256)
        if type(self.segment_ordinal) is not int or self.segment_ordinal != 1 or type(self.locator) is not reader.DocxLocator:
            raise StagingError()
        _text(self.text, 8000)
        if self.locator.char_end - self.locator.char_start != len(self.text) or self.locator.table_index is not None:
            raise StagingError()


@dataclass(frozen=True, slots=True)
class MissingObservation:
    field_name: str = "standort"
    reason: str = "not_present_in_complete_assertion"

    def __post_init__(self):
        if self.field_name != "standort" or self.reason != "not_present_in_complete_assertion":
            raise StagingError()


@dataclass(frozen=True, slots=True)
class FieldValue:
    name: str
    value: str | None
    quotes: tuple[DocxQuote, ...]
    missing: MissingObservation | None = None

    def __post_init__(self):
        if self.name not in validation.FIELDS:
            raise StagingError()
        _tuple(self.quotes, DocxQuote)
        if self.value is None:
            if self.name != "standort" or self.quotes or type(self.missing) is not MissingObservation:
                raise StagingError()
        else:
            _text(self.value, 1024)
            if len(self.quotes) != 1 or self.missing is not None:
                raise StagingError()


@dataclass(frozen=True, slots=True)
class IntendedClaim:
    predicate: Predicate
    subject_asset_name: str
    object_name: str
    quote: DocxQuote
    support_policy: str = field(default=support.SUPPORT_POLICY, init=False)

    def __post_init__(self):
        if type(self.predicate) is not Predicate or type(self.quote) is not DocxQuote:
            raise StagingError()
        _text(self.subject_asset_name)
        _text(self.object_name, 1024)


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    scope: ReviewScope
    bindings: tuple[DocumentBinding, ...]
    issues: tuple[StagingIssue, ...]
    content_fingerprint: str
    fingerprint: str = field(init=False)

    def __post_init__(self):
        if type(self.scope) is not ReviewScope:
            raise StagingError()
        _tuple(self.bindings, DocumentBinding)
        _tuple(self.issues, StagingIssue)
        _digest(self.content_fingerprint)
        object.__setattr__(self, "fingerprint", _fingerprint(_init_data(self)))


@dataclass(frozen=True, slots=True)
class StagedCandidate:
    id: str
    revision: int
    binding: DocumentBinding
    context_fingerprint: str
    fields: tuple[FieldValue, ...]
    claims: tuple[IntendedClaim, ...]
    issues: tuple[StagingIssue, ...]
    state: ReviewState
    remediation_fingerprint: str
    fingerprint: str = field(init=False)

    def __post_init__(self):
        _text(self.id)
        _positive(self.revision)
        if type(self.binding) is not DocumentBinding or type(self.state) is not ReviewState or self.state not in _QUEUE_STATES:
            raise StagingError("approved_forbidden")
        _digest(self.context_fingerprint)
        _digest(self.remediation_fingerprint)
        _tuple(self.fields, FieldValue)
        _tuple(self.claims, IntendedClaim)
        _tuple(self.issues, StagingIssue)
        if self.state is ReviewState.PROPOSED and (self.issues or tuple(item.name for item in self.fields) != validation.FIELDS):
            raise StagingError()
        data = _init_data(self)
        del data["state"]  # Queue disposition is an append-only operational event.
        object.__setattr__(self, "fingerprint", _fingerprint(data))


@dataclass(frozen=True, slots=True)
class ValidatedProposal:
    candidate: StagedCandidate

    def __post_init__(self):
        if type(self.candidate) is not StagedCandidate or self.candidate.state is not ReviewState.PROPOSED or self.candidate.issues:
            raise StagingError("blocked_revision")


@dataclass(frozen=True, slots=True)
class StageReport:
    context: ContextAssessment
    candidates: tuple[StagedCandidate, ...]
    proposals: tuple[ValidatedProposal, ...]
    issues: tuple[StagingIssue, ...]

    def __post_init__(self):
        if type(self.context) is not ContextAssessment:
            raise StagingError()
        _tuple(self.candidates, StagedCandidate)
        _tuple(self.proposals, ValidatedProposal)
        _tuple(self.issues, StagingIssue)
        if self.issues and self.proposals:
            raise StagingError()


@dataclass(frozen=True, slots=True)
class QueueDecision:
    id: str
    candidate_id: str
    candidate_fingerprint: str
    context_fingerprint: str
    remediation_fingerprint: str
    state: ReviewState
    reviewer_id: str
    timestamp: datetime
    reason: str

    def __post_init__(self):
        _text(self.id)
        _text(self.candidate_id)
        for value in (self.candidate_fingerprint, self.context_fingerprint, self.remediation_fingerprint):
            _digest(value)
        if type(self.state) is not ReviewState or self.state not in _QUEUE_STATES:
            raise StagingError("approved_forbidden")
        _text(self.reviewer_id)
        _text(self.reason, 1024)
        _aware(self.timestamp)


def _remediation_fingerprint(snapshot: DocumentSnapshot) -> str:
    """Match human blocks to this logical source's substantive assertion.

    Operational context, resource limits, packaging and citation coordinates are
    deliberately absent. They still bind candidate/currentness fingerprints.
    Assess the source independently of active field/resource caps: a human block
    must survive relaxing a cap that previously prevented field emission. This
    bounded grammar check only matches blocks, never grants eligibility; _derive
    and full context validation remain mandatory. Unsupported text gets a
    diagnostic-only identity. Whitespace/run changes cannot clear a human block.
    """
    text = snapshot.native.text
    affirmative = support.assess_source(text, 0, len(text)) if len(text) <= MAX_SOURCE_CHARS else None
    assertion = {"unsupported_text_sha256": snapshot.native.text_sha256}
    if affirmative is not None:
        roles = [(Predicate.HOSTS.value, affirmative.system, affirmative.application)]
        if affirmative.location is not None:
            roles.append((Predicate.LOCATED_AT.value, affirmative.system, affirmative.location))
        assertion = {"system_id": affirmative.system, "standort": affirmative.location,
                     "anwendung_id": affirmative.application, "roles": roles}
    return _fingerprint({"version": REMEDIATION_VERSION, "source": snapshot.ref.source_id, "assertion": assertion})


def _capture(path, limits):
    if not isinstance(path, (str, Path)):
        raise StagingError("unsupported_input")
    path = Path(path)
    if path.suffix.casefold() != ".docx" or path.is_symlink():
        raise StagingError("unsupported_input")
    with path.open("rb") as file:
        metadata = os.fstat(file.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limits.max_file_bytes:
            raise StagingError("source_limit")
        raw = file.read(limits.max_file_bytes + 1)
    if len(raw) > limits.max_file_bytes:
        raise StagingError("source_limit")
    return raw


def _read_captured(raw, source_id, limits):
    temporary_root = Path(gettempdir()).resolve()
    repository_root = Path(__file__).resolve().parents[2]
    if temporary_root.is_relative_to(repository_root):
        raise StagingError("capture_failed")
    with TemporaryDirectory(prefix="grundschutz-ai-staging-", dir=temporary_root) as folder:
        path = Path(folder) / "captured.docx"
        # write_bytes closes before the existing path-based reader reopens it.
        path.write_bytes(raw)
        result = reader.ingest_docx(path, source_id=source_id, limits=limits)
        if type(result) is not reader.DocxExtraction or result.original_bytes != raw or result.source_id != source_id or result.limits != limits:
            raise StagingError("native_mismatch")
        return result


class DocxStaging:
    """One small trusted in-memory registry, complete scope and triage queue.

    All known session sources must be explicitly included. Histories are tuples;
    a live lock protects heads/currentness, not reviewer/source authentication.
    """

    def __init__(self, policy: StagingPolicy = StagingPolicy()):
        if type(policy) is not StagingPolicy:
            raise StagingError()
        self._lock, self._policy = RLock(), policy
        self._policies = (PolicyRevision(1, policy, datetime.now(timezone.utc)),)
        self._session_id, self._epoch, self._used = uuid4().hex, 1, 0
        self._exhausted = False
        self._refs, self._events, self._snapshots = (), (), ()
        self._scope, self._scopes, self._candidates, self._decisions = None, (), (), ()
        self._finishing = set()
        self._blobs = {}
        self._retained_bytes = 0
        self._retained_text_chars = self._retained_manifest_bytes = 0
        self._reader_implementation = _fingerprint({"python": tuple(sys.version_info[:3]), "reader": _sha(Path(reader.__file__).read_bytes()), "ooxml": _sha(Path(ooxml_safety.__file__).read_bytes())})

    def _exhaust(self):
        if not self._exhausted:
            self._exhausted = True
            self._epoch += 1
        raise StagingError("session_exhausted")

    def _spend(self, count=1):
        if self._exhausted or self._used + count > self._policy.max_history_units:
            self._exhaust()
        self._used += count

    def _event(self, ref, status, limits, raw=None, issues=()):
        event = RegistrationEvent(len(self._events) + 1, ref, status, datetime.now(timezone.utc), limits, raw, issues)
        self._events += (event,)
        self._epoch += 1
        return event

    def _latest(self, ref):
        if type(ref) is not RegistrationRef or ref not in self._refs:
            raise StagingError("unknown_registration")
        return next(event for event in reversed(self._events) if event.ref == ref)

    def _head_ref(self, source_id):
        return next((ref for ref in reversed(self._refs) if ref.source_id == source_id), None)

    def current_head(self, source_id: str) -> RegistrationEvent | None:
        _text(source_id)
        with self._lock:
            ref = self._head_ref(source_id)
            return None if ref is None else self._latest(ref)

    def registration_history(self, source_id: str) -> tuple[RegistrationEvent, ...]:
        _text(source_id)
        with self._lock:
            return tuple(event for event in self._events if event.ref.source_id == source_id)

    def snapshot(self, ref: RegistrationRef) -> DocumentSnapshot:
        with self._lock:
            self._latest(ref)
            snapshot = next((item for item in self._snapshots if item.ref == ref), None)
            if snapshot is None:
                raise StagingError("snapshot_unavailable")
            return snapshot

    def begin_registration(self, source_id: str) -> RegistrationRef:
        _text(source_id)
        with self._lock:
            old = self._head_ref(source_id)
            if old is None and len({ref.source_id for ref in self._refs}) >= self._policy.max_sources:
                self._exhaust()
            self._spend(3)  # Reserve pending/captured/terminal history capacity.
            ref = RegistrationRef(source_id, 1 if old is None else old.revision + 1, uuid4().hex)
            self._refs += (ref,)
            self._event(ref, RegistrationStatus.PENDING, self._policy.reader_limits)
            return ref

    def finish_registration(self, ref: RegistrationRef, path: str | Path, *, claimed_extraction: reader.DocxExtraction | None = None, declared_lineage: tuple = ()) -> RegistrationEvent:
        with self._lock:
            event = self._latest(ref)
            if event.status is not RegistrationStatus.PENDING or ref in self._finishing:
                raise StagingError("registration_already_completed")
            self._finishing.add(ref)
        raw, snapshot, issues, completed = None, None, (), False
        try:
            if type(declared_lineage) is not tuple or declared_lineage:
                raise StagingError("lineage_excluded")
            if claimed_extraction is not None and type(claimed_extraction) is not reader.DocxExtraction:
                raise StagingError("unsupported_input")
            raw = _capture(path, event.reader_limits)
            with self._lock:
                digest = _sha(raw)
                if digest in self._blobs:
                    if self._blobs[digest] != raw:
                        raise StagingError("native_mismatch")
                    raw = self._blobs[digest]
                else:
                    if self._retained_bytes + len(raw) > self._policy.max_retained_bytes:
                        raw = None
                        self._exhaust()
                    self._blobs[digest] = raw
                    self._retained_bytes += len(raw)
                self._event(ref, RegistrationStatus.PENDING, event.reader_limits, raw)
            fresh = _read_captured(raw, ref.source_id, event.reader_limits)
            if claimed_extraction is not None and claimed_extraction != fresh:
                raise StagingError("native_mismatch")
            with self._lock:
                # Revalidate every time, then share identical immutable results.
                prior = next((item.native for item in self._snapshots if item.native == fresh), None)
                fresh = prior if prior is not None else replace(fresh, original_bytes=raw)
            snapshot = DocumentSnapshot(ref, fresh, self._reader_implementation)
            if len(snapshot.manifest_json.encode("utf-8")) > self._policy.max_manifest_bytes:
                raise StagingError("source_limit")
            completed = True
        except reader.DocxIngestionError:
            issues = (StagingIssue("reader_rejected", ref.source_id),)
        except StagingError as exc:
            issues = (StagingIssue(exc.code, ref.source_id),)
        except (OSError, ValueError, TypeError, RuntimeError):
            issues = (StagingIssue("capture_failed", ref.source_id),)
        finally:
            with self._lock:
                if not completed and not issues:
                    issues = (StagingIssue("capture_failed", ref.source_id),)
                if not issues and snapshot is not None:
                    extra_text = 0 if any(item.native is snapshot.native for item in self._snapshots) else len(snapshot.native.text)
                    extra_manifest = len(snapshot.manifest_json.encode("utf-8"))
                    if self._retained_text_chars + extra_text > self._policy.max_retained_text_chars or self._retained_manifest_bytes + extra_manifest > self._policy.max_retained_manifest_bytes:
                        self._exhausted = True
                        self._epoch += 1
                    else:
                        self._retained_text_chars += extra_text
                        self._retained_manifest_bytes += extra_manifest
                if self._exhausted:
                    issues = (StagingIssue("session_exhausted", ref.source_id),)
                if not issues and snapshot is not None:
                    self._snapshots += (snapshot,)
                terminal = self._event(ref, RegistrationStatus.FAILED if issues else RegistrationStatus.VALID, event.reader_limits, raw, issues)
                self._finishing.remove(ref)
        return terminal

    def register_docx(self, source_id: str, path: str | Path, *, claimed_extraction: reader.DocxExtraction | None = None, declared_lineage: tuple = ()) -> RegistrationEvent:
        return self.finish_registration(self.begin_registration(source_id), path, claimed_extraction=claimed_extraction, declared_lineage=declared_lineage)

    def policy_history(self) -> tuple[PolicyRevision, ...]:
        with self._lock:
            return self._policies

    def set_policy(self, policy: StagingPolicy) -> None:
        if type(policy) is not StagingPolicy:
            raise StagingError()
        with self._lock:
            if policy != self._policy:
                self._spend()
                # New capacity must accommodate already retained history/data.
                if policy.max_history_units < self._used or policy.max_retained_bytes < self._retained_bytes or policy.max_retained_text_chars < self._retained_text_chars or policy.max_retained_manifest_bytes < self._retained_manifest_bytes or policy.max_sources < len({ref.source_id for ref in self._refs}):
                    self._exhaust()
                self._policy = policy
                self._policies += (PolicyRevision(len(self._policies) + 1, policy, datetime.now(timezone.utc)),)
                self._epoch += 1

    def create_scope(self, source_ids: tuple[str, ...]) -> ReviewScope:
        if type(source_ids) is not tuple or not source_ids or len(source_ids) > self._policy.max_sources or len(set(source_ids)) != len(source_ids):
            raise StagingError()
        for name in source_ids:
            _text(name)
        source_ids = tuple(sorted(source_ids))  # Input order cannot clear triage.
        with self._lock:
            heads = tuple(self._head_ref(name) for name in source_ids)
            if self._scope is not None and (source_ids, heads, self._epoch, self._policy.fingerprint) == (self._scope.source_ids, self._scope.heads, self._scope.registry_epoch, self._scope.policy_fingerprint):
                return self._scope
            self._spend()
            self._scope = ReviewScope(self._session_id, len(self._scopes) + 1, self._epoch, source_ids, heads, self._policy.fingerprint, self._policies[-1].revision)
            self._scopes += (self._scope,)
            return self._scope

    def scope_history(self) -> tuple[ReviewScope, ...]:
        with self._lock:
            return self._scopes

    def _current(self, scope):
        return not self._exhausted and type(scope) is ReviewScope and scope == self._scope and scope.registry_epoch == self._epoch and scope.policy_fingerprint == self._policy.fingerprint and scope.heads == tuple(self._head_ref(name) for name in scope.source_ids)

    def _derive(self, snapshot, binding):
        source_id, native = snapshot.ref.source_id, snapshot.native
        if len(native.segments) != 1 or native.segments[0].locator.table_index is not None or native.segments[0].locator.body_index != 1 or native.segments[0].locator.paragraph_index != 1:
            return (), (), (StagingIssue("extra_structure", source_id),)
        text = native.text
        if len(text) > self._policy.max_source_chars:
            return (), (), (StagingIssue("source_text_limit", source_id),)
        start, end = len(text) - len(text.lstrip()), len(text.rstrip())
        affirmative = support.assess_source(text, start, end)
        values = (affirmative.system, affirmative.location, affirmative.application) if affirmative is not None else (None, None, None)
        quote_text = text[start:end]
        envelope = {name: {"value": value, "evidence_quote": quote_text if value is not None else None} for name, value in zip(validation.FIELDS, values)}
        encoded = _json(envelope)
        if len(encoded.encode("utf-8")) > self._policy.max_field_bytes:
            return (), (), (StagingIssue("field_limit", source_id),)
        validated = validation.validate_response(encoded, text)
        if affirmative is None or not validated.valid:
            code = "validator_disagreement" if (affirmative is not None) != validated.valid else "unsupported_assertion"
            return (), (), (StagingIssue(code, source_id),)
        if len(values[0]) > self._policy.max_id_chars or len(values[2]) > self._policy.max_id_chars or (values[1] is not None and len(values[1]) > self._policy.max_location_chars):
            return (), (), (StagingIssue("field_limit", source_id),)
        segment = native.segments[0]
        quote = DocxQuote(binding.fingerprint, 1, segment.text_sha256, segment.span(start, end), quote_text)
        result_fields = tuple(FieldValue(name, value, (quote,) if value is not None else (), None if value is not None else MissingObservation()) for name, value in zip(validation.FIELDS, values))
        claims = (IntendedClaim(Predicate.HOSTS, affirmative.system, affirmative.application, quote),)
        if affirmative.location is not None:
            claims += (IntendedClaim(Predicate.LOCATED_AT, affirmative.system, affirmative.location, quote),)
        return result_fields, claims, ()

    def _assess(self, scope):
        if type(scope) is not ReviewScope:
            raise StagingError()
        issues, bindings, drafts, content, characters = [], [], [], [], 0
        if not self._current(scope):
            issue = StagingIssue("session_exhausted" if self._exhausted else "scope_stale")
            return ContextAssessment(scope, (), (issue,), _fingerprint({"observed_epoch": self._epoch, "policy": self._policy.fingerprint})), ()
        if set(ref.source_id for ref in self._refs) - set(scope.source_ids):
            issues.append(StagingIssue("scope_omits_source"))
        for name, ref in zip(scope.source_ids, scope.heads):
            if ref is None:
                issues.append(StagingIssue("source_missing", name))
                content.append((name, None))
                continue
            event = self._latest(ref)
            if event.status is not RegistrationStatus.VALID:
                issues.append(StagingIssue("source_pending" if event.status is RegistrationStatus.PENDING else "source_failed", name))
                content.append((name, event.status.value, event.binary_sha256))
                continue
            snapshot = self.snapshot(ref)
            content.append((name, snapshot.manifest_sha256))
            binding = DocumentBinding(ref, snapshot.manifest_sha256, scope.fingerprint, self._policy.fingerprint)
            bindings.append(binding)
            characters += len(snapshot.native.text)
            if len(snapshot.manifest_json.encode("utf-8")) > self._policy.max_manifest_bytes:
                issues.append(StagingIssue("source_limit", name))
                continue
            if snapshot.native.limits != self._policy.reader_limits:
                issues.append(StagingIssue("reader_policy_changed", name))
                continue
            derived_fields, claims, errors = self._derive(snapshot, binding)
            issues.extend(errors)
            drafts.append((binding, derived_fields, claims))
        if characters > self._policy.max_scope_chars:
            issues.append(StagingIssue("scope_limit"))
        seen = {}
        for binding, derived_fields, _ in drafts:
            if not derived_fields:
                continue
            asset, location, app = (item.value for item in derived_fields)
            if asset in seen:
                issues.append(StagingIssue("duplicate_asset", binding.ref.source_id))
                if seen[asset] != (location, app):
                    issues.append(StagingIssue("conflicting_assertions", binding.ref.source_id))
            seen[asset] = (location, app)
        assessment = ContextAssessment(scope, tuple(bindings), tuple(issues), _fingerprint({"policy": self._policy.fingerprint, "sources": content}))
        return assessment, tuple(drafts)

    def assess(self, scope: ReviewScope) -> ContextAssessment:
        with self._lock:
            return self._assess(scope)[0]

    def _blocked(self, candidate):
        return any(decision.candidate_id == candidate.id and decision.remediation_fingerprint == candidate.remediation_fingerprint and decision.state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION) for decision in self._decisions)

    def stage(self, scope: ReviewScope) -> StageReport:
        with self._lock:
            context, drafts = self._assess(scope)
            candidates, proposals, issues = [], [], list(context.issues)
            if not self._current(scope):
                return StageReport(context, (), (), tuple(issues))
            for binding, derived_fields, claims in drafts:
                previous = next((candidate for candidate in reversed(self._candidates) if candidate.binding.ref.source_id == binding.ref.source_id), None)
                if previous is not None and previous.context_fingerprint == context.fingerprint:
                    candidate = previous
                else:
                    self._spend()
                    remediation = _remediation_fingerprint(self.snapshot(binding.ref))
                    candidate = StagedCandidate(uuid4().hex if previous is None else previous.id, 1 if previous is None else previous.revision + 1, binding, context.fingerprint, derived_fields, claims, context.issues, ReviewState.NEEDS_CLARIFICATION if context.issues else ReviewState.PROPOSED, remediation)
                    self._candidates += (candidate,)
                if self._blocked(candidate):
                    issues.append(StagingIssue("queue_blocked", binding.ref.source_id))
                    decision = next(item for item in reversed(self._decisions) if item.candidate_id == candidate.id and item.remediation_fingerprint == candidate.remediation_fingerprint and item.state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION))
                    candidate = replace(candidate, state=decision.state)
                candidates.append(candidate)
            if not issues:
                proposals = [ValidatedProposal(candidate) for candidate in candidates]
            return StageReport(context, tuple(candidates), tuple(proposals), tuple(issues))

    def candidate_history(self, source_id: str) -> tuple[StagedCandidate, ...]:
        _text(source_id)
        with self._lock:
            return tuple(candidate for candidate in self._candidates if candidate.binding.ref.source_id == source_id)

    def decision_history(self) -> tuple[QueueDecision, ...]:
        with self._lock:
            return self._decisions

    def is_eligible(self, proposal: ValidatedProposal) -> bool:
        with self._lock:
            if type(proposal) is not ValidatedProposal or not self._current(self._scope):
                return False
            context, _ = self._assess(self._scope)
            if context.issues or proposal.candidate.context_fingerprint != context.fingerprint:
                return False
            current = tuple(next((item for item in reversed(self._candidates) if item.binding.ref == binding.ref and item.context_fingerprint == context.fingerprint), None) for binding in context.bindings)
            return (bool(current) and all(item is not None and item.state is ReviewState.PROPOSED and not self._blocked(item) for item in current) and proposal.candidate in current)

    def triage(self, candidate_id: str, *, state: ReviewState, reviewer_id: str, timestamp: datetime, reason: str, candidate_fingerprint: str, context_fingerprint: str) -> QueueDecision:
        with self._lock:
            if not self._current(self._scope):
                raise StagingError("stale_context")
            report = self.stage(self._scope)
            candidate = next((item for item in report.candidates if item.id == candidate_id), None)
            if candidate is None or candidate.fingerprint != candidate_fingerprint or report.context.fingerprint != context_fingerprint:
                raise StagingError("stale_candidate")
            if type(state) is not ReviewState or state not in _QUEUE_STATES:
                raise StagingError("approved_forbidden")
            if state is ReviewState.PROPOSED and (candidate.issues or self._blocked(candidate)):
                raise StagingError("blocked_revision")
            decision = QueueDecision(uuid4().hex, candidate.id, candidate.fingerprint, context_fingerprint, candidate.remediation_fingerprint, state, reviewer_id, timestamp, reason)
            if self._decisions and decision.timestamp < self._decisions[-1].timestamp:
                raise StagingError("review_history_order")
            self._spend()
            self._decisions += (decision,)
            return decision
