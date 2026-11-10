"""Synthetic XLSX table proposals only; no evidence, domain writes or inference.

Reports are immutable historical snapshots. Check is_eligible() on their owning
live session. This module authenticates neither sources nor human reviewers.
"""

from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import sys
from tempfile import TemporaryDirectory, gettempdir
from threading import RLock
from uuid import uuid4

from . import xlsx_ingestion as reader, ooxml_safety
from .domain import Predicate, ReviewState
# Reuse source-neutral immutable values and pure canonical serialization only.
# No DocxStaging instance or DOCX intake/validation is used or changed.
from .docx_staging import (
    RegistrationRef, RegistrationStatus, ReviewScope, DocumentBinding, QueueDecision,
    _json, _sha, _fingerprint, _init_data,
)


POLICY_VERSION = "synthetic-it-table/v1"
REMEDIATION_VERSION = "xlsx-assertion-remediation/v1"
IMPLEMENTATION = "grundschutz_ai.xlsx_staging/1.0.0"
FIELD_NAMES = ("system_id", "standort", "anwendung_id")
HEADERS = ("System-ID", "Standort", "Anwendung")
_QUEUE_STATES = (ReviewState.PROPOSED, ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION)
_ID = re.compile(r"[A-Z][A-Z0-9]*-[A-Z0-9]+")
_PLACE = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]*(?:-[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]*)*"
_LOCATION = re.compile(rf"Rechenzentrum {_PLACE}(?: {_PLACE})*(?:, Raum [A-Z0-9]+(?:-[A-Z0-9]+)*)?")
_AMBIGUOUS = re.compile(r"\b(?:nicht|kein|keine|keinem|keinen|keiner|keines|ohne|statt|unbekannt|unklar|null|none)\b", re.IGNORECASE)


class StagingError(ValueError):
    """Bounded static error; never a source-text log or human decision."""

    def __init__(self, code="invalid_argument"):
        self.code = code
        super().__init__(f"XLSX staging refused: {code}")


def _require(condition, code="invalid_argument"):
    if not condition:
        raise StagingError(code)


def _text(value, maximum=256):
    _require(type(value) is str and bool(value.strip()))
    try:
        _require(len(value.encode("utf-8")) <= maximum)
    except UnicodeError as exc:
        raise StagingError() from exc


def _positive(value):
    _require(type(value) is int and value > 0)


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _aware(value):
    _require(type(value) is datetime and value.utcoffset() is not None, "aware_timestamp_required")


def _records(value, kind):
    _require(type(value) is tuple and all(type(item) is kind for item in value))


@dataclass(frozen=True, slots=True)
class SheetSelection:
    """Trusted explicit worksheet identity, not header-based discovery."""

    name: str
    ordinal: int
    sheet_id: int
    relationship_id: str
    part: str

    def __post_init__(self):
        _require(self.name == "IT-Systeme")
        _positive(self.ordinal)
        _positive(self.sheet_id)
        _require(self.ordinal <= 16 and self.sheet_id <= 0xFFFFFFFF)
        _require(type(self.relationship_id) is str and re.fullmatch(r"rId[1-9][0-9]{0,5}", self.relationship_id) is not None)
        _require(type(self.part) is str and re.fullmatch(r"xl/worksheets/sheet[1-9][0-9]*\.xml", self.part) is not None)

    def matches(self, sheet: reader.Worksheet) -> bool:
        return type(sheet) is reader.Worksheet and (self.name, self.ordinal, self.sheet_id, self.relationship_id, self.part) == (sheet.name, sheet.ordinal, sheet.sheet_id, sheet.relationship_id, sheet.part)


@dataclass(frozen=True, slots=True)
class StagingPolicy:
    reader_limits: reader.XlsxLimits = reader.DEFAULT_LIMITS
    max_sources: int = 16
    max_data_rows: int = 100
    max_scope_rows: int = 100  # Aggregate hard ceiling; configuration may tighten.
    max_id_chars: int = 64
    max_location_chars: int = 256
    max_scope_chars: int = 1_000_000
    max_manifest_bytes: int = 8 * 1024 * 1024
    max_retained_bytes: int = 32 * 1024 * 1024
    max_retained_text_chars: int = 1_000_000
    max_retained_manifest_bytes: int = 32 * 1024 * 1024
    max_history_units: int = 2048
    version: str = field(default=POLICY_VERSION, init=False)
    fingerprint: str = field(init=False)

    def __post_init__(self):
        _require(type(self.reader_limits) is reader.XlsxLimits)
        for item in fields(reader.DEFAULT_LIMITS):
            _require(getattr(self.reader_limits, item.name) <= getattr(reader.DEFAULT_LIMITS, item.name), "limits_may_only_tighten")
        for item in fields(self):
            if item.init and item.name != "reader_limits":
                value = getattr(self, item.name)
                _require(type(value) is int and 1 <= value <= item.default, "limits_may_only_tighten")
        object.__setattr__(self, "fingerprint", _fingerprint({"version": self.version, "implementation": IMPLEMENTATION, "limits": _init_data(self)}))


@dataclass(frozen=True, slots=True)
class PolicyRevision:
    revision: int
    policy: StagingPolicy
    activated_at: datetime

    def __post_init__(self):
        _positive(self.revision)
        _require(type(self.policy) is StagingPolicy)
        _aware(self.activated_at)


@dataclass(frozen=True, slots=True)
class StagingIssue:
    code: str
    source_id: str | None = None
    row: int | None = None

    def __post_init__(self):
        _require(self.code in {
            "unsupported_input", "lineage_excluded", "capture_failed", "reader_rejected",
            "native_mismatch", "source_limit", "session_exhausted", "scope_stale",
            "scope_omits_source", "source_missing", "source_pending", "source_failed",
            "reader_policy_changed", "scope_limit", "sheet_count", "sheet_selection",
            "row_layout", "row_limit", "unexpected_cell", "headers", "missing_cell",
            "invalid_system", "invalid_application", "invalid_location", "field_limit",
            "duplicate_asset", "conflicting_assertions", "queue_blocked",
        })
        if self.source_id is not None:
            _text(self.source_id)
        if self.row is not None:
            _positive(self.row)
            _require(self.row <= 1_048_576)


@dataclass(frozen=True, slots=True)
class RegistrationEvent:
    sequence: int
    ref: RegistrationRef
    status: RegistrationStatus
    observed_at: datetime
    selection: SheetSelection
    reader_limits: reader.XlsxLimits
    original_bytes: bytes | None = field(default=None, repr=False)
    issues: tuple[StagingIssue, ...] = ()
    binary_sha256: str | None = field(init=False)

    def __post_init__(self):
        _positive(self.sequence)
        _aware(self.observed_at)
        _require(type(self.ref) is RegistrationRef and type(self.status) is RegistrationStatus)
        _require(type(self.selection) is SheetSelection and type(self.reader_limits) is reader.XlsxLimits)
        _require(self.original_bytes is None or type(self.original_bytes) is bytes)
        _records(self.issues, StagingIssue)
        _require(self.status is not RegistrationStatus.VALID or (self.original_bytes is not None and not self.issues))
        _require(self.status is not RegistrationStatus.FAILED or bool(self.issues))
        object.__setattr__(self, "binary_sha256", None if self.original_bytes is None else _sha(self.original_bytes))


@dataclass(frozen=True, slots=True)
class WorkbookSnapshot:
    ref: RegistrationRef
    selection: SheetSelection
    native: reader.XlsxExtraction
    reader_implementation_sha256: str
    manifest_json: str = field(init=False)
    manifest_sha256: str = field(init=False)

    def __post_init__(self):
        _require(type(self.ref) is RegistrationRef and type(self.selection) is SheetSelection)
        _require(type(self.native) is reader.XlsxExtraction and self.native.source_id == self.ref.source_id)
        _digest(self.reader_implementation_sha256)
        manifest = _json({"manifest_version": "xlsx-integration/v1", "source_id": self.ref.source_id,
                          "binary_sha256": self.native.xlsx_sha256, "reader_method": self.native.method,
                          "reader_implementation_sha256": self.reader_implementation_sha256,
                          "reader_limits": asdict(self.native.limits), "selection": asdict(self.selection),
                          "native_text_sha256": self.native.text_sha256,
                          "native_manifest_sha256": self.native.manifest_sha256,
                          "native_manifest_json": self.native.manifest_json})
        object.__setattr__(self, "manifest_json", manifest)
        object.__setattr__(self, "manifest_sha256", _sha(manifest.encode("utf-8")))


@dataclass(frozen=True, slots=True)
class CellReference:
    binding_fingerprint: str
    selection: SheetSelection
    cell: reader.CellRecord
    char_start: int = field(default=0, init=False)
    char_end: int = field(init=False)

    def __post_init__(self):
        _digest(self.binding_fingerprint)
        _require(type(self.selection) is SheetSelection and type(self.cell) is reader.CellRecord)
        _require((self.selection.name, self.selection.ordinal, self.selection.part) == (self.cell.sheet_name, self.cell.sheet_ordinal, self.cell.part))
        _require(self.cell.text_sha256 == _sha(self.cell.text.encode("utf-8")))
        object.__setattr__(self, "char_end", len(self.cell.text))


@dataclass(frozen=True, slots=True)
class MissingObservation:
    cell: CellReference
    field_name: str = field(default="standort", init=False)
    reason: str = field(default="explicit_blank", init=False)

    def __post_init__(self):
        _require(type(self.cell) is CellReference and self.cell.cell.column == 2 and self.cell.cell.row >= 2)
        _require(self.cell.cell.kind is reader.CellKind.BLANK and self.cell.cell.text == "")


@dataclass(frozen=True, slots=True)
class FieldValue:
    name: str
    value: str | None
    cell: CellReference
    header: CellReference
    missing: MissingObservation | None = None

    def __post_init__(self):
        _require(self.name in FIELD_NAMES)
        _require(type(self.cell) is CellReference and type(self.header) is CellReference)
        column = FIELD_NAMES.index(self.name) + 1
        _require(self.cell.cell.column == column and self.cell.cell.row >= 2)
        _require(self.header.cell.coordinate == f"{'ABC'[column - 1]}1" and self.header.cell.kind is reader.CellKind.TEXT and self.header.cell.text == HEADERS[column - 1])
        _require(self.cell.binding_fingerprint == self.header.binding_fingerprint and self.cell.selection == self.header.selection and self.cell.cell.source_id == self.header.cell.source_id)
        if self.value is None:
            _require(self.name == "standort" and type(self.missing) is MissingObservation and self.missing.cell == self.cell)
        else:
            _require(type(self.value) is str and self.value == self.cell.cell.text and self.cell.cell.kind is reader.CellKind.TEXT and self.missing is None)
            _require(_valid_location(self.value) if column == 2 else _valid_id(self.value))

    @property
    def positive_quotes(self) -> tuple[CellReference, ...]:
        return () if self.value is None else (self.cell,)


@dataclass(frozen=True, slots=True)
class RowSupport:
    """Structural synthetic-policy support, never legacy text Evidence."""

    headers: tuple[CellReference, ...]
    cells: tuple[CellReference, ...]
    policy_version: str = field(default=POLICY_VERSION, init=False)

    def __post_init__(self):
        _records(self.headers, CellReference)
        _records(self.cells, CellReference)
        _require(len(self.headers) == len(self.cells) == 3)
        first = self.cells[0]
        for column, (header, cell) in enumerate(zip(self.headers, self.cells), 1):
            _require(header.cell.coordinate == f"{'ABC'[column - 1]}1" and header.cell.kind is reader.CellKind.TEXT and header.cell.text == HEADERS[column - 1])
            _require(cell.cell.column == column and cell.cell.row == first.cell.row and cell.cell.row >= 2)
            for ref in (header, cell):
                _require(ref.binding_fingerprint == first.binding_fingerprint and ref.selection == first.selection and ref.cell.source_id == first.cell.source_id)


@dataclass(frozen=True, slots=True)
class IntendedClaim:
    predicate: Predicate
    subject_asset_name: str
    object_name: str
    support: RowSupport

    def __post_init__(self):
        _require(type(self.predicate) is Predicate and self.predicate in (Predicate.HOSTS, Predicate.LOCATED_AT))
        _require(type(self.support) is RowSupport)
        cells = tuple(item.cell for item in self.support.cells)
        values, error = _row_values(cells, StagingPolicy())
        _require(error is None and self.subject_asset_name == values[0])
        _require(self.object_name == (values[2] if self.predicate is Predicate.HOSTS else values[1]) and type(self.object_name) is str)


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    scope: ReviewScope
    bindings: tuple[DocumentBinding, ...]
    issues: tuple[StagingIssue, ...]
    content_fingerprint: str
    fingerprint: str = field(init=False)

    def __post_init__(self):
        _require(type(self.scope) is ReviewScope)
        _records(self.bindings, DocumentBinding)
        _records(self.issues, StagingIssue)
        _digest(self.content_fingerprint)
        object.__setattr__(self, "fingerprint", _fingerprint(_init_data(self)))


@dataclass(frozen=True, slots=True)
class StagedCandidate:
    id: str
    revision: int
    binding: DocumentBinding
    row: int
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
        _require(type(self.binding) is DocumentBinding and type(self.row) is int and 2 <= self.row <= 101)
        _digest(self.context_fingerprint)
        _digest(self.remediation_fingerprint)
        _records(self.fields, FieldValue)
        _records(self.claims, IntendedClaim)
        _records(self.issues, StagingIssue)
        _require(type(self.state) is ReviewState and self.state in _QUEUE_STATES, "approved_forbidden")
        _require(self.state is not ReviewState.PROPOSED or (not self.issues and tuple(item.name for item in self.fields) == FIELD_NAMES and bool(self.claims)))
        data = _init_data(self)
        del data["state"]
        object.__setattr__(self, "fingerprint", _fingerprint(data))


@dataclass(frozen=True, slots=True)
class ValidatedProposal:
    candidate: StagedCandidate

    def __post_init__(self):
        _require(type(self.candidate) is StagedCandidate and self.candidate.state is ReviewState.PROPOSED and not self.candidate.issues, "blocked_revision")


@dataclass(frozen=True, slots=True)
class StageReport:
    context: ContextAssessment
    candidates: tuple[StagedCandidate, ...]
    proposals: tuple[ValidatedProposal, ...]
    issues: tuple[StagingIssue, ...]

    def __post_init__(self):
        _require(type(self.context) is ContextAssessment)
        _records(self.candidates, StagedCandidate)
        _records(self.proposals, ValidatedProposal)
        _records(self.issues, StagingIssue)
        _require(not (self.issues and self.proposals))


def _valid_id(text):
    return type(text) is str and len(text) <= 64 and _ID.fullmatch(text) is not None


def _valid_location(text):
    return type(text) is str and len(text) <= 256 and _LOCATION.fullmatch(text) is not None and _AMBIGUOUS.search(text) is None


def _row_values(cells, policy):
    """Deterministic structural validator; no invented prose or LLM schema."""
    if len(cells) != 3 or any(cell is None for cell in cells):
        return (), "missing_cell"
    system, location, app = cells
    if system.kind is not reader.CellKind.TEXT or not _valid_id(system.text):
        return (), "invalid_system"
    if app.kind is not reader.CellKind.TEXT or not _valid_id(app.text):
        return (), "invalid_application"
    if location.kind is reader.CellKind.BLANK:
        value = None
    elif location.kind is reader.CellKind.TEXT and _valid_location(location.text):
        value = location.text
    else:
        return (), "invalid_location"
    if len(system.text) > policy.max_id_chars or len(app.text) > policy.max_id_chars or (value is not None and len(value) > policy.max_location_chars):
        return (), "field_limit"
    return (system.text, value, app.text), None


def _remediation(source_id, cells):
    # Always use literal presence/kind/values, even when caps prevent emission.
    # No row coordinate, source registration, policy, headers or other row enters
    # this matching key. It only preserves blocks; it cannot grant eligibility.
    semantics = tuple({"present": False} if cell is None else {
        "present": True, "kind": cell.kind.value,
        "value": None if cell.kind is reader.CellKind.BLANK else cell.text,
    } for cell in cells)
    roles = [(Predicate.HOSTS.value, "system_id", "anwendung_id")]
    if cells[1] is not None and cells[1].kind is reader.CellKind.TEXT:
        roles.append((Predicate.LOCATED_AT.value, "system_id", "standort"))
    return _fingerprint({"version": REMEDIATION_VERSION, "source": source_id,
                         "fields": dict(zip(FIELD_NAMES, semantics)),
                         "roles": roles})


def _capture(path, limits):
    _require(isinstance(path, (str, Path)), "unsupported_input")
    path = Path(path)
    _require(path.suffix.casefold() == ".xlsx" and not path.is_symlink(), "unsupported_input")
    with path.open("rb") as file:
        metadata = os.fstat(file.fileno())
        _require(stat.S_ISREG(metadata.st_mode) and metadata.st_size <= limits.max_file_bytes, "source_limit")
        raw = file.read(limits.max_file_bytes + 1)
    _require(len(raw) <= limits.max_file_bytes, "source_limit")
    return raw


def _read_captured(raw, source_id, limits):
    temporary_root = Path(gettempdir()).resolve()
    _require(not temporary_root.is_relative_to(Path(__file__).resolve().parents[2]), "capture_failed")
    with TemporaryDirectory(prefix="grundschutz-ai-xlsx-staging-", dir=temporary_root) as folder:
        path = Path(folder) / "captured.xlsx"
        path.write_bytes(raw)  # Closed before the path reader reopens on Windows.
        result = reader.ingest_xlsx(path, source_id=source_id, limits=limits)
        _require(type(result) is reader.XlsxExtraction and result.original_bytes == raw and result.source_id == source_id and result.limits == limits, "native_mismatch")
        return result


class XlsxStaging:
    """One bounded XLSX-only registry, complete scope and human triage queue."""

    def __init__(self, policy: StagingPolicy = StagingPolicy()):
        _require(type(policy) is StagingPolicy)
        self._lock, self._policy = RLock(), policy
        self._policies = (PolicyRevision(1, policy, datetime.now(timezone.utc)),)
        self._session_id, self._epoch, self._used = uuid4().hex, 1, 0
        self._exhausted = False
        self._refs, self._events, self._snapshots = (), (), ()
        self._scope, self._scopes, self._candidates, self._decisions = None, (), (), ()
        self._candidate_keys = {}
        self._finishing, self._blobs = set(), {}
        self._retained_bytes = self._retained_text_chars = self._retained_manifest_bytes = 0
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

    def _event(self, ref, status, selection, limits, raw=None, issues=()):
        event = RegistrationEvent(len(self._events) + 1, ref, status, datetime.now(timezone.utc), selection, limits, raw, issues)
        self._events += (event,)
        self._epoch += 1
        return event

    def _latest(self, ref):
        _require(type(ref) is RegistrationRef and ref in self._refs, "unknown_registration")
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

    def snapshot(self, ref: RegistrationRef) -> WorkbookSnapshot:
        with self._lock:
            self._latest(ref)
            result = next((item for item in self._snapshots if item.ref == ref), None)
            _require(result is not None, "snapshot_unavailable")
            return result

    def begin_registration(self, source_id: str, selection: SheetSelection) -> RegistrationRef:
        _text(source_id)
        _require(type(selection) is SheetSelection)
        with self._lock:
            old = self._head_ref(source_id)
            if old is None and len({ref.source_id for ref in self._refs}) >= self._policy.max_sources:
                self._exhaust()
            self._spend(3)
            ref = RegistrationRef(source_id, 1 if old is None else old.revision + 1, uuid4().hex)
            self._refs += (ref,)
            self._event(ref, RegistrationStatus.PENDING, selection, self._policy.reader_limits)
            return ref

    def finish_registration(self, ref: RegistrationRef, path: str | Path, *, claimed_extraction: reader.XlsxExtraction | None = None, declared_lineage: tuple = ()) -> RegistrationEvent:
        with self._lock:
            event = self._latest(ref)
            _require(event.status is RegistrationStatus.PENDING and ref not in self._finishing, "registration_already_completed")
            self._finishing.add(ref)
        raw, snapshot, issues, completed = None, None, (), False
        try:
            _require(type(declared_lineage) is tuple and not declared_lineage, "lineage_excluded")
            _require(claimed_extraction is None or type(claimed_extraction) is reader.XlsxExtraction, "unsupported_input")
            raw = _capture(path, event.reader_limits)
            with self._lock:
                digest = _sha(raw)
                if digest in self._blobs:
                    _require(self._blobs[digest] == raw, "native_mismatch")
                    raw = self._blobs[digest]
                else:
                    if self._retained_bytes + len(raw) > self._policy.max_retained_bytes:
                        raw = None
                        self._exhaust()
                    self._blobs[digest] = raw
                    self._retained_bytes += len(raw)
                self._event(ref, RegistrationStatus.PENDING, event.selection, event.reader_limits, raw)
            fresh = _read_captured(raw, ref.source_id, event.reader_limits)
            _require(claimed_extraction is None or claimed_extraction == fresh, "native_mismatch")
            with self._lock:
                prior = next((item.native for item in self._snapshots if item.native == fresh), None)
                fresh = prior if prior is not None else replace(fresh, original_bytes=raw)
            snapshot = WorkbookSnapshot(ref, event.selection, fresh, self._reader_implementation)
            _require(len(snapshot.manifest_json.encode("utf-8")) <= self._policy.max_manifest_bytes, "source_limit")
            completed = True
        except reader.XlsxIngestionError:
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
                terminal = self._event(ref, RegistrationStatus.FAILED if issues else RegistrationStatus.VALID, event.selection, event.reader_limits, raw, issues)
                self._finishing.remove(ref)
        return terminal

    def register_xlsx(self, source_id: str, path: str | Path, selection: SheetSelection, *, claimed_extraction: reader.XlsxExtraction | None = None, declared_lineage: tuple = ()) -> RegistrationEvent:
        return self.finish_registration(self.begin_registration(source_id, selection), path, claimed_extraction=claimed_extraction, declared_lineage=declared_lineage)

    def policy_history(self) -> tuple[PolicyRevision, ...]:
        with self._lock:
            return self._policies

    def set_policy(self, policy: StagingPolicy) -> None:
        _require(type(policy) is StagingPolicy)
        with self._lock:
            if policy != self._policy:
                self._spend()
                for name, retained in (("max_history_units", self._used), ("max_retained_bytes", self._retained_bytes), ("max_retained_text_chars", self._retained_text_chars), ("max_retained_manifest_bytes", self._retained_manifest_bytes), ("max_sources", len({ref.source_id for ref in self._refs}))):
                    if getattr(policy, name) < retained:
                        self._exhaust()
                self._policy = policy
                self._policies += (PolicyRevision(len(self._policies) + 1, policy, datetime.now(timezone.utc)),)
                self._epoch += 1

    def create_scope(self, source_ids: tuple[str, ...]) -> ReviewScope:
        _require(type(source_ids) is tuple and 0 < len(source_ids) <= self._policy.max_sources)
        for name in source_ids:
            _text(name)
        _require(len(set(source_ids)) == len(source_ids))
        source_ids = tuple(sorted(source_ids))
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

    def _workbook(self, snapshot, binding):
        native, selection, name = snapshot.native, snapshot.selection, snapshot.ref.source_id
        if len(native.sheets) != 1:
            return (), (StagingIssue("sheet_count", name),)
        sheet = native.sheets[0]
        if not selection.matches(sheet):
            return (), (StagingIssue("sheet_selection", name),)
        # Hard profile cap is independent of active resource limits. Even invalid
        # rows within that cap retain diagnostic candidates for explicit triage.
        if len(sheet.row_indices) < 2 or sheet.row_indices != tuple(range(1, len(sheet.row_indices) + 1)):
            return (), (StagingIssue("row_layout", name),)
        if len(sheet.row_indices) - 1 > 100:
            return (), (StagingIssue("row_limit", name),)
        if any(cell.column > 3 for cell in sheet.cells):
            return (), (StagingIssue("unexpected_cell", name),)
        by_coordinate = {cell.coordinate: cell for cell in sheet.cells}
        headers = tuple(by_coordinate.get(f"{column}1") for column in "ABC")
        if any(cell is None or cell.kind is not reader.CellKind.TEXT or cell.text != expected for cell, expected in zip(headers, HEADERS)):
            return (), (StagingIssue("headers", name),)
        header_refs = tuple(CellReference(binding.fingerprint, selection, cell) for cell in headers)
        issues, drafts = [], []
        if len(sheet.row_indices) - 1 > self._policy.max_data_rows:
            issues.append(StagingIssue("row_limit", name))
        for row in sheet.row_indices[1:]:
            cells = tuple(by_coordinate.get(f"{column}{row}") for column in "ABC")
            values, error = _row_values(cells, self._policy)
            result_fields, claims = (), ()
            if error:
                issues.append(StagingIssue(error, name, row))
            else:
                refs = tuple(CellReference(binding.fingerprint, selection, cell) for cell in cells)
                result_fields = tuple(FieldValue(field_name, value, cell, header, MissingObservation(cell) if value is None else None) for field_name, value, cell, header in zip(FIELD_NAMES, values, refs, header_refs))
                structural = RowSupport(header_refs, refs)
                claims = (IntendedClaim(Predicate.HOSTS, values[0], values[2], structural),)
                if values[1] is not None:
                    claims += (IntendedClaim(Predicate.LOCATED_AT, values[0], values[1], structural),)
            drafts.append((binding, row, cells, result_fields, claims))
        return tuple(drafts), tuple(issues)

    def _assess(self, scope):
        _require(type(scope) is ReviewScope)
        if not self._current(scope):
            issue = StagingIssue("session_exhausted" if self._exhausted else "scope_stale")
            return ContextAssessment(scope, (), (issue,), _fingerprint({"epoch": self._epoch, "policy": self._policy.fingerprint})), ()
        issues, bindings, drafts, content, characters = [], [], [], [], 0
        if {ref.source_id for ref in self._refs} - set(scope.source_ids):
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
            current, errors = self._workbook(snapshot, binding)
            drafts.extend(current)
            issues.extend(errors)
        if len(drafts) > self._policy.max_scope_rows or characters > self._policy.max_scope_chars:
            issues.append(StagingIssue("scope_limit"))
        seen = {}
        for binding, row, cells, _, _ in drafts:
            if cells[0] is None or cells[0].kind is not reader.CellKind.TEXT or not _valid_id(cells[0].text):
                continue
            asset = cells[0].text
            # Cross-source comparisons exclude source ID, but never replace the
            # source-bound human-block identity with this aggregate conflict key.
            values = tuple(None if cell is None else (cell.kind.value, cell.text) for cell in cells)
            if asset in seen:
                issues.append(StagingIssue("duplicate_asset", binding.ref.source_id, row))
                if seen[asset] != values:
                    issues.append(StagingIssue("conflicting_assertions", binding.ref.source_id, row))
            seen[asset] = values
        context = ContextAssessment(scope, tuple(bindings), tuple(issues), _fingerprint({"policy": self._policy.fingerprint, "sources": content}))
        return context, tuple(drafts)

    def assess(self, scope: ReviewScope) -> ContextAssessment:
        with self._lock:
            return self._assess(scope)[0]

    def _blocking_decision(self, candidate):
        # The source is inside the versioned matching identity. Do not require
        # the old row's slot/UUID: relocation or duplicate cleanup is no override.
        return next((item for item in reversed(self._decisions) if item.remediation_fingerprint == candidate.remediation_fingerprint and item.state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION)), None)

    def stage(self, scope: ReviewScope) -> StageReport:
        with self._lock:
            context, drafts = self._assess(scope)
            if not self._current(scope):
                return StageReport(context, (), (), context.issues)
            issues, candidates = list(context.issues), []
            counts = {}
            for binding, _, cells, _, _ in drafts:
                asset = cells[0].text if cells[0] is not None and cells[0].kind is reader.CellKind.TEXT and _valid_id(cells[0].text) else None
                key = (binding.ref.source_id, asset)
                counts[key] = counts.get(key, 0) + 1
            for binding, row, cells, result_fields, claims in drafts:
                asset = cells[0].text if cells[0] is not None and cells[0].kind is reader.CellKind.TEXT and _valid_id(cells[0].text) else None
                key = (binding.ref.source_id, "asset", asset) if asset is not None and counts[(binding.ref.source_id, asset)] == 1 else (binding.ref.source_id, "ambiguous_row", row)
                previous_id = self._candidate_keys.get(key)
                previous = next((item for item in reversed(self._candidates) if item.id == previous_id), None)
                if previous is not None and previous.context_fingerprint == context.fingerprint:
                    candidate = previous
                else:
                    self._spend()
                    candidate_id = previous.id if previous is not None else uuid4().hex
                    candidate = StagedCandidate(candidate_id, 1 if previous is None else previous.revision + 1, binding, row, context.fingerprint, result_fields, claims, context.issues, ReviewState.NEEDS_CLARIFICATION if context.issues else ReviewState.PROPOSED, _remediation(binding.ref.source_id, cells))
                    self._candidate_keys[key] = candidate_id
                    self._candidates += (candidate,)
                decision = self._blocking_decision(candidate)
                if decision is not None:
                    issues.append(StagingIssue("queue_blocked", binding.ref.source_id, row))
                    candidate = replace(candidate, state=decision.state)
                candidates.append(candidate)
            proposals = () if issues else tuple(ValidatedProposal(item) for item in candidates)
            return StageReport(context, tuple(candidates), proposals, tuple(issues))

    def candidate_history(self, source_id: str) -> tuple[StagedCandidate, ...]:
        _text(source_id)
        with self._lock:
            return tuple(item for item in self._candidates if item.binding.ref.source_id == source_id)

    def decision_history(self) -> tuple[QueueDecision, ...]:
        with self._lock:
            return self._decisions

    def is_eligible(self, proposal: ValidatedProposal) -> bool:
        with self._lock:
            if type(proposal) is not ValidatedProposal or not self._current(self._scope):
                return False
            context, drafts = self._assess(self._scope)
            if context.issues or proposal.candidate.context_fingerprint != context.fingerprint:
                return False
            current = tuple(next((item for item in reversed(self._candidates) if item.binding.ref == binding.ref and item.row == row and item.context_fingerprint == context.fingerprint), None) for binding, row, _, _, _ in drafts)
            return bool(current) and all(item is not None and item.state is ReviewState.PROPOSED and self._blocking_decision(item) is None for item in current) and proposal.candidate in current

    def triage(self, candidate_id: str, *, state: ReviewState, reviewer_id: str, timestamp: datetime, reason: str, candidate_fingerprint: str, context_fingerprint: str) -> QueueDecision:
        with self._lock:
            _require(self._current(self._scope), "stale_context")
            report = self.stage(self._scope)
            candidate = next((item for item in report.candidates if item.id == candidate_id), None)
            _require(candidate is not None and candidate.fingerprint == candidate_fingerprint and report.context.fingerprint == context_fingerprint, "stale_candidate")
            _require(type(state) is ReviewState and state in _QUEUE_STATES, "approved_forbidden")
            _require(state is not ReviewState.PROPOSED or (not candidate.issues and self._blocking_decision(candidate) is None), "blocked_revision")
            _text(reviewer_id)
            _text(reason, 1024)
            _aware(timestamp)
            _require(not self._decisions or timestamp >= self._decisions[-1].timestamp, "review_history_order")
            decision = QueueDecision(uuid4().hex, candidate.id, candidate.fingerprint, context_fingerprint, candidate.remediation_fingerprint, state, reviewer_id, timestamp, reason)
            self._spend()
            self._decisions += (decision,)
            return decision
