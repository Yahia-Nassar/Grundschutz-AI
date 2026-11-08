"""Immutable inventory records. These are engineering rules, not BSI rulings."""

from dataclasses import InitVar, asdict, dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
import re
from typing import ClassVar


class ReviewState(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class Predicate(StrEnum):
    HOSTS = "hosts"
    LOCATED_AT = "located_at"


def require_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def require_id(value: object, prefix: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(prefix + r"-[A-Z0-9]+(?:-[A-Z0-9]+)*", value):
        raise ValueError(f"Expected a stable {prefix}-... identifier")


def require_digest(value: object) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Expected a lowercase SHA-256 digest")


def require_timestamp(value: object) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Timestamp must be a timezone-aware datetime")


def require_revision(value: object) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("Revision must be a positive integer")


def require_evidence_ids(value: object) -> None:
    if type(value) is not tuple or not value:
        raise ValueError("At least one evidence ID is required as an immutable tuple")
    for identifier in value:
        require_id(identifier, "EVD")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate evidence references")


def digest_data(value: object) -> str:
    """Internal canonical fingerprint, not a snapshot import/export format."""
    def encode(item):
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError(f"Unsupported fingerprint value: {type(item).__name__}")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=encode)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """Zero-based, half-open Unicode character offsets in the original source."""

    start: int
    end: int

    def __post_init__(self):
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end:
            raise ValueError("Source locator must have integer offsets 0 <= start < end")


@dataclass(frozen=True, slots=True)
class Provenance:
    extraction_method: str
    candidate_id: str
    candidate_revision_sha256: str
    candidate_state: ReviewState
    extracted_at: datetime

    def __post_init__(self):
        require_text(self.extraction_method, "extraction_method")
        require_text(self.candidate_id, "candidate_id")
        require_digest(self.candidate_revision_sha256)
        if type(self.candidate_state) is not ReviewState:
            raise ValueError("candidate_state must be a ReviewState")
        require_timestamp(self.extracted_at)


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    source_id: str
    source_sha256: str
    quote: str
    locator: SourceLocator
    provenance: Provenance
    source_text: InitVar[str]
    revision: int = 1

    def __post_init__(self, source_text):
        require_id(self.id, "EVD")
        require_text(self.source_id, "source_id")
        require_digest(self.source_sha256)
        require_text(self.quote, "quote")
        require_revision(self.revision)
        if type(self.locator) is not SourceLocator or type(self.provenance) is not Provenance:
            raise ValueError("Evidence needs a typed locator and provenance")
        if not isinstance(source_text, str):
            raise ValueError("Evidence construction requires the original synthetic source text")
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != self.source_sha256:
            raise ValueError("Source content does not match its SHA-256")
        if self.locator.end > len(source_text) or source_text[self.locator.start:self.locator.end] != self.quote:
            raise ValueError("Evidence quote does not match the exact source position")


@dataclass(frozen=True, slots=True)
class _NamedRecord:
    id: str
    name: str
    evidence_ids: tuple[str, ...]
    description: str | None = None
    revision: int = 1
    ID_PREFIX: ClassVar[str] = ""

    def __post_init__(self):
        require_id(self.id, self.ID_PREFIX)
        require_text(self.name, "name")
        require_evidence_ids(self.evidence_ids)
        require_revision(self.revision)
        if self.description is not None:
            require_text(self.description, "description")


@dataclass(frozen=True, slots=True)
class ITSystem(_NamedRecord):
    """Location/application references are derived from inventory relationships."""

    ID_PREFIX: ClassVar[str] = "SYS"


@dataclass(frozen=True, slots=True)
class ITApplication(_NamedRecord):
    ID_PREFIX: ClassVar[str] = "APP"


@dataclass(frozen=True, slots=True)
class Location(_NamedRecord):
    location_type: str | None = None
    ID_PREFIX: ClassVar[str] = "LOC"

    def __post_init__(self):
        _NamedRecord.__post_init__(self)
        if self.location_type is not None:
            require_text(self.location_type, "location_type")


@dataclass(frozen=True, slots=True)
class Relationship:
    id: str
    subject_id: str
    predicate: Predicate
    object_id: str
    evidence_ids: tuple[str, ...]
    revision: int = 1

    def __post_init__(self):
        require_id(self.id, "REL")
        require_id(self.subject_id, "SYS")
        if type(self.predicate) is not Predicate:
            raise ValueError("predicate must be a supported Predicate")
        require_id(self.object_id, "APP" if self.predicate is Predicate.HOSTS else "LOC")
        require_evidence_ids(self.evidence_ids)
        require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    id: str
    target_id: str
    target_revision_sha256: str
    state: ReviewState
    reviewer_id: str | None
    timestamp: datetime
    reason: str

    def __post_init__(self):
        require_id(self.id, "REV")
        require_text(self.target_id, "target_id")
        require_digest(self.target_revision_sha256)
        if type(self.state) is not ReviewState:
            raise ValueError("state must be a ReviewState")
        require_timestamp(self.timestamp)
        require_text(self.reason, "reason")
        if self.reviewer_id is not None:
            require_text(self.reviewer_id, "reviewer_id")
        if self.state in (ReviewState.APPROVED, ReviewState.REJECTED) and self.reviewer_id is None:
            raise ValueError("Approval/rejection requires an explicit human reviewer")


Record = ITSystem | ITApplication | Location | Evidence | Relationship
RECORD_TYPES = (ITSystem, ITApplication, Location, Evidence, Relationship)


def record_data(record: Record) -> dict:
    return {"type": type(record).__name__, **asdict(record)}
