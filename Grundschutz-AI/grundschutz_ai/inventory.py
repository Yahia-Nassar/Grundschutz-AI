"""Immutable in-memory inventory snapshots with append-only revision histories.

No Ollama/extraction imports or raw-candidate promotion API. Callers must be
trusted application code; reviewer authentication is outside this prototype.
"""

from dataclasses import dataclass, field

from .domain import (
    Evidence, ITApplication, ITSystem, Location, Predicate,
    Record, RECORD_TYPES, Relationship, ReviewRecord, ReviewState,
    digest_data, record_data,
)
from .support import SUPPORT_POLICY, complete_name_occurs


class EvidenceSupportError(ValueError):
    """Refused proposal/approval: retain diagnostics outside approved inventory."""

    review_state = ReviewState.NEEDS_CLARIFICATION


@dataclass(frozen=True, slots=True)
class Inventory:
    _records: tuple[Record, ...] = field(default=(), init=False, repr=False)
    _reviews: tuple[ReviewRecord, ...] = field(default=(), init=False, repr=False)

    @property
    def records(self) -> tuple[Record, ...]:
        return tuple({record.id: record for record in self._records}.values())

    def get(self, identifier: str) -> Record:
        for record in reversed(self._records):
            if record.id == identifier:
                return record
        raise ValueError(f"Unknown inventory identifier: {identifier}")

    def record_history(self, identifier: str) -> tuple[Record, ...]:
        self.get(identifier)
        return tuple(record for record in self._records if record.id == identifier)

    def review_history(self, identifier: str | None = None) -> tuple[ReviewRecord, ...]:
        if identifier is not None:
            self.get(identifier)
        return tuple(review for review in self._reviews if identifier is None or review.target_id == identifier)

    def _with(self, *, record=None, review=None) -> "Inventory":
        snapshot = Inventory()
        object.__setattr__(snapshot, "_records", self._records + (() if record is None else (record,)))
        object.__setattr__(snapshot, "_reviews", self._reviews + (() if review is None else (review,)))
        return snapshot

    def _used_id(self, identifier: str) -> bool:
        return any(item.id == identifier for item in (*self._records, *self._reviews))

    def _validate_record(self, record: Record) -> None:
        if type(record) not in RECORD_TYPES:
            raise ValueError("Only typed domain records may enter inventory; raw candidates are diagnostics")
        if isinstance(record, Evidence):
            if record.provenance.candidate_state is not ReviewState.PROPOSED:
                raise ValueError("Only proposed candidate provenance may enter inventory; approval is a human review")
            return
        for identifier in record.evidence_ids:
            if not isinstance(self.get(identifier), Evidence):
                raise ValueError("Evidence reference must resolve to Evidence")
        if isinstance(record, Relationship):
            subject, target = self.get(record.subject_id), self.get(record.object_id)
            expected_type = ITApplication if record.predicate is Predicate.HOSTS else Location
            if not isinstance(subject, ITSystem) or not isinstance(target, expected_type):
                raise ValueError("Relationship endpoint types do not match its predicate")
            if not all(
                (support := self.get(identifier).relationship_support) is not None
                and support.supports(record.predicate.value, subject.name, target.name)
                for identifier in record.evidence_ids
            ):
                raise EvidenceSupportError("Affirmative support for the exact predicate/endpoints is required; clarification needed")
            for existing in self.records:
                if isinstance(existing, Relationship) and existing.id != record.id and (
                    existing.subject_id, existing.predicate, existing.object_id
                ) == (record.subject_id, record.predicate, record.object_id):
                    raise ValueError("Duplicate relationship triple; revise its evidence references instead")
        elif not any(
            complete_name_occurs(
                (evidence := self.get(identifier)).quote, record.name,
                before=evidence.quote_before, after=evidence.quote_after,
            )
            for identifier in record.evidence_ids
        ):
            raise EvidenceSupportError("A complete name must occur in supporting evidence; clarification needed")

    def add(self, record: Record) -> "Inventory":
        self._validate_record(record)
        if self._used_id(record.id):
            raise ValueError(f"Duplicate identifier: {record.id}")
        if record.revision != 1:
            raise ValueError("A new identifier must start at revision 1")
        return self._with(record=record)

    def revise(self, record: Record) -> "Inventory":
        self._validate_record(record)
        previous = self.get(record.id)
        if type(previous) is not type(record) or record.revision != previous.revision + 1:
            raise ValueError("Revision must preserve identity/type and increment by one")
        return self._with(record=record)

    def _current_source(self, source_id: str) -> Evidence:
        for record in reversed(self._records):
            if isinstance(record, Evidence) and record.source_id == source_id:
                return record
        raise ValueError("Unknown evidence source")

    def _evidence_data(self, evidence: Evidence) -> dict:
        current = self._current_source(evidence.source_id)
        return {
            **record_data(evidence), "current_source_sha256": current.source_sha256,
            "source_registration": (current.id, current.revision),
            "support_policy": SUPPORT_POLICY,
        }

    def _object_data(self, record: Record) -> dict:
        if isinstance(record, Evidence):
            return self._evidence_data(record)
        return {
            **record_data(record),
            "evidence": [self._evidence_data(self.get(identifier)) for identifier in record.evidence_ids],
        }

    def revision_digest(self, identifier: str) -> str:
        """Bind data, current evidence/candidate/source versions and endpoints."""
        record = self.get(identifier)
        payload = self._object_data(record)
        if isinstance(record, Relationship):
            payload["subject"] = self._object_data(self.get(record.subject_id))
            payload["object"] = self._object_data(self.get(record.object_id))
        elif isinstance(record, ITSystem):
            payload["relationships"] = [
                {**self._object_data(edge), "object": self._object_data(self.get(edge.object_id))}
                for edge in self.records
                if isinstance(edge, Relationship) and edge.subject_id == record.id
            ]
        return digest_data(payload)

    def _decision(self, identifier: str) -> ReviewRecord | None:
        history = self.review_history(identifier)
        latest = history[-1] if history else None
        return latest if latest and latest.target_revision_sha256 == self.revision_digest(identifier) else None

    def conflicting_relationship_ids(self) -> frozenset[str]:
        groups = {}
        for edge in self.records:
            if isinstance(edge, Relationship) and edge.predicate is Predicate.LOCATED_AT:
                decision = self._decision(edge.id)
                if decision is None or decision.state is not ReviewState.REJECTED:
                    groups.setdefault(edge.subject_id, []).append(edge)
        return frozenset(edge.id for edges in groups.values() if len(edges) > 1 for edge in edges)

    def _dependencies(self, record: Record) -> tuple[str, ...]:
        if isinstance(record, Evidence):
            return ()
        return record.evidence_ids + (
            (record.subject_id, record.object_id) if isinstance(record, Relationship) else ()
        )

    def review_state(self, identifier: str) -> ReviewState:
        record = self.get(identifier)
        conflicts = self.conflicting_relationship_ids()
        if identifier in conflicts or (
            isinstance(record, ITSystem)
            and any(self.get(edge_id).subject_id == identifier for edge_id in conflicts)
        ):
            return ReviewState.NEEDS_CLARIFICATION
        if isinstance(record, Evidence) and record.source_sha256 != self._current_source(record.source_id).source_sha256:
            return ReviewState.NEEDS_CLARIFICATION
        decision = self._decision(identifier)
        if decision is not None and decision.state is ReviewState.REJECTED:
            return ReviewState.REJECTED
        try:
            self._validate_record(record)
        except EvidenceSupportError:
            return ReviewState.NEEDS_CLARIFICATION
        if decision is None:
            return ReviewState.PROPOSED
        if decision.state is ReviewState.APPROVED and any(
            self.review_state(dependency) is not ReviewState.APPROVED for dependency in self._dependencies(record)
        ):
            return ReviewState.NEEDS_CLARIFICATION
        return decision.state

    def record_review(self, review: ReviewRecord) -> "Inventory":
        if type(review) is not ReviewRecord:
            raise ValueError("Reviews must be typed, explicit ReviewRecords")
        self.get(review.target_id)
        if self._used_id(review.id):
            raise ValueError("Duplicate review identifier")
        if review.target_revision_sha256 != self.revision_digest(review.target_id):
            raise ValueError("Review targets an outdated data/evidence/source/candidate revision")
        if self._reviews and review.timestamp < self._reviews[-1].timestamp:
            raise ValueError("Review history timestamps cannot go backwards")
        if review.state in (ReviewState.PROPOSED, ReviewState.APPROVED) and any(
            old.target_revision_sha256 == review.target_revision_sha256
            and old.state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION)
            for old in self.review_history(review.target_id)
        ):
            raise ValueError("A blocked revision must be revised before promotion")
        if review.state is ReviewState.APPROVED:
            record = self.get(review.target_id)
            self._validate_record(record)  # Recheck support after evidence/endpoint revisions.
            if self.review_state(review.target_id) is ReviewState.NEEDS_CLARIFICATION:
                raise ValueError("Unresolved conflict or stale evidence requires clarification")
            if any(self.review_state(item) is not ReviewState.APPROVED for item in self._dependencies(record)):
                raise ValueError("Supporting evidence and endpoints require human approval first")
        return self._with(review=review)

    def approved_records(self) -> tuple[Record, ...]:
        return tuple(record for record in self.records if self.review_state(record.id) is ReviewState.APPROVED)

    def application_ids(self, system_id: str) -> tuple[str, ...]:
        """Proposal query, not an export of approved relationships."""
        return tuple(sorted(edge.object_id for edge in self._active_edges(system_id) if edge.predicate is Predicate.HOSTS))

    def location_id(self, system_id: str) -> str | None:
        """Proposal query; refuse to choose among conflicting alternatives."""
        edges = [edge for edge in self._active_edges(system_id) if edge.predicate is Predicate.LOCATED_AT]
        if len(edges) > 1:
            raise ValueError("Conflicting locations require explicit review")
        return edges[0].object_id if edges else None

    def _active_edges(self, system_id: str) -> tuple[Relationship, ...]:
        if not isinstance(self.get(system_id), ITSystem):
            raise ValueError("Expected an ITSystem")
        return tuple(
            edge for edge in self.records
            if isinstance(edge, Relationship) and edge.subject_id == system_id
            and self.review_state(edge.id) is not ReviewState.REJECTED
        )
