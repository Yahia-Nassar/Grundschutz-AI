"""FICTITIOUS inventory fixtures and offline domain/review regression tests."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import unittest

from grundschutz_ai.domain import (
    Evidence, ITApplication, ITSystem, Location, Predicate, Provenance,
    Relationship, ReviewRecord, ReviewState, SourceLocator, digest_data,
)
from grundschutz_ai.inventory import Inventory


NOW = datetime(2026, 11, 9, 10, tzinfo=timezone.utc)  # Synthetic fixture time, not an audit event.
QUOTE = "Der Server SRV-001 befindet sich im Rechenzentrum Rostock und betreibt die Anwendung ERP-01."
SOURCE = "FIKTIVES TESTBEISPIEL — keine reale Infrastruktur.\n" + QUOTE


def provenance(state=ReviewState.PROPOSED, candidate_revision=None):
    return Provenance(
        "synthetic-manual-fixture/v1", "synthetic:candidate-001",
        candidate_revision or digest_data({"synthetic": True, "values": ["SRV-001", "Rechenzentrum Rostock", "ERP-01"]}),
        state, NOW,
    )


def evidence(identifier="EVD-001", source=SOURCE, quote=QUOTE, revision=1, origin=None, source_id="synthetic:task-004"):
    start = source.index(quote)
    return Evidence(
        identifier, source_id, hashlib.sha256(source.encode("utf-8")).hexdigest(),
        quote, SourceLocator(start, start + len(quote)), origin or provenance(), source, revision,
    )


def synthetic_fixture():
    """Required fictitious SYS/APP/LOC/EVD inventory; everything starts proposed."""
    inventory = Inventory().add(evidence())
    for record in (
        ITSystem("SYS-001", "SRV-001", ("EVD-001",), "Fiktiver Testserver"),
        ITApplication("APP-001", "ERP-01", ("EVD-001",), "Fiktive Testanwendung"),
        Location("LOC-001", "Rechenzentrum Rostock", ("EVD-001",), location_type="Rechenzentrum"),
        Relationship("REL-001", "SYS-001", Predicate.HOSTS, "APP-001", ("EVD-001",)),
        Relationship("REL-002", "SYS-001", Predicate.LOCATED_AT, "LOC-001", ("EVD-001",)),
    ):
        inventory = inventory.add(record)
    return inventory


def review(inventory, target, state=ReviewState.APPROVED, reviewer="synthetic:human-reviewer", **changes):
    result = ReviewRecord(
        f"REV-{len(inventory.review_history()) + 1:03d}", target, inventory.revision_digest(target),
        state, reviewer, NOW, "Fiktive explizite Testentscheidung",
    )
    return replace(result, **changes) if changes else result


def approved_fixture():
    inventory = synthetic_fixture()
    for target in ("EVD-001", "APP-001", "LOC-001", "SYS-001", "REL-001", "REL-002"):
        inventory = inventory.record_review(review(inventory, target))
    return inventory


def conflicting_fixture():
    inventory = synthetic_fixture()
    quote = QUOTE.replace("Rechenzentrum Rostock", "Rechenzentrum Berlin")
    inventory = inventory.add(evidence("EVD-002", "FIKTIVER KONFLIKT.\n" + quote, quote, source_id="synthetic:other-source"))
    inventory = inventory.add(Location("LOC-002", "Rechenzentrum Berlin", ("EVD-002",)))
    return inventory.add(Relationship("REL-003", "SYS-001", Predicate.LOCATED_AT, "LOC-002", ("EVD-002",)))


class DomainTests(unittest.TestCase):
    def test_valid_fictitious_fixture_has_no_automatic_approval(self):
        inventory = synthetic_fixture()
        self.assertEqual(len(inventory.records), 6)
        self.assertEqual(inventory.get("SYS-001").name, "SRV-001")
        self.assertEqual(inventory.get("LOC-001").name, "Rechenzentrum Rostock")
        self.assertEqual(inventory.approved_records(), ())
        self.assertTrue(all(inventory.review_state(item.id) is ReviewState.PROPOSED for item in inventory.records))

    def test_records_and_inventory_are_immutable(self):
        inventory = synthetic_fixture()
        with self.assertRaises(FrozenInstanceError):
            inventory.get("SYS-001").name = "OTHER"
        with self.assertRaises(FrozenInstanceError):
            inventory._records = ()
        with self.assertRaises(TypeError):
            Inventory(_reviews=())

    def test_empty_or_incorrectly_typed_fields_are_rejected(self):
        for name in ("", " ", None, 123):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ITSystem("SYS-001", name, ("EVD-001",))
        for revision in (0, -1, True, "1"):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                ITSystem("SYS-001", "SRV-001", ("EVD-001",), revision=revision)

    def test_stable_id_prefixes(self):
        with self.assertRaises(ValueError):
            ITSystem("APP-001", "SRV-001", ("EVD-001",))
        with self.assertRaises(ValueError):
            Location("LOC 001", "Rechenzentrum Rostock", ("EVD-001",))

    def test_missing_mutable_or_duplicate_evidence_refs_rejected(self):
        for references in ((), ["EVD-001"], ("EVD-001", "EVD-001"), ("SYS-001",)):
            with self.subTest(references=references), self.assertRaises(ValueError):
                ITSystem("SYS-001", "SRV-001", references)

    def test_description_and_location_type_are_validated(self):
        with self.assertRaises(ValueError):
            ITApplication("APP-001", "ERP-01", ("EVD-001",), description=12)
        with self.assertRaises(ValueError):
            Location("LOC-001", "Rechenzentrum Rostock", ("EVD-001",), location_type="")

    def test_invalid_predicates_and_endpoint_kinds(self):
        for predicate in ("hosts", "runs_on", None):
            with self.subTest(predicate=predicate), self.assertRaises(ValueError):
                Relationship("REL-001", "SYS-001", predicate, "APP-001", ("EVD-001",))
        with self.assertRaises(ValueError):
            Relationship("REL-001", "SYS-001", Predicate.LOCATED_AT, "APP-001", ("EVD-001",))

    def test_unsupported_review_states_are_rejected(self):
        for state in ("approved", "verified", True, None):
            with self.subTest(state=state), self.assertRaises(ValueError):
                replace(review(synthetic_fixture(), "SYS-001"), state=state)
            with self.subTest(origin_state=state), self.assertRaises(ValueError):
                provenance(state)

    def test_approval_and_rejection_require_reviewer(self):
        for state in (ReviewState.APPROVED, ReviewState.REJECTED):
            with self.subTest(state=state), self.assertRaises(ValueError):
                review(synthetic_fixture(), "SYS-001", state, reviewer=None)
        with self.assertRaises(ValueError):
            review(synthetic_fixture(), "SYS-001", reviewer=" ")

    def test_timestamps_and_reasons_required(self):
        for changes in ({"timestamp": datetime(2026, 11, 9)}, {"reason": ""}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                review(synthetic_fixture(), "SYS-001", **changes)
        with self.assertRaises(ValueError):
            replace(provenance(), extracted_at=datetime(2026, 11, 9))

    def test_quote_hash_and_position_are_checked_against_source(self):
        original = evidence()
        for changes in (
            {"source_sha256": "0" * 64}, {"quote": "Unbelegte erfundene Aussage"},
            {"locator": SourceLocator(0, len(QUOTE))}, {"locator": SourceLocator(0, len(SOURCE) + 100)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(original, source_text=SOURCE, **changes)
        self.assertNotIn("source_text", asdict(original))

    def test_locator_and_digest_types(self):
        for offsets in ((-1, 1), (2, 2), (False, 2), (0, "2")):
            with self.subTest(offsets=offsets), self.assertRaises(ValueError):
                SourceLocator(*offsets)
        with self.assertRaises(ValueError):
            replace(provenance(), candidate_revision_sha256="not-a-sha256")

    def test_multiple_supporting_evidence_preserved(self):
        inventory = synthetic_fixture().add(evidence("EVD-002", source_id="synthetic:second-source"))
        item = replace(inventory.get("SYS-001"), revision=2, evidence_ids=("EVD-001", "EVD-002"))
        inventory = inventory.revise(item)
        self.assertEqual(inventory.get("SYS-001").evidence_ids, ("EVD-001", "EVD-002"))


class InventoryTests(unittest.TestCase):
    def test_duplicate_identifiers_do_not_mutate_snapshot(self):
        inventory = synthetic_fixture()
        with self.assertRaises(ValueError):
            inventory.add(inventory.get("SYS-001"))
        self.assertEqual(len(inventory.records), 6)

    def test_invalid_references(self):
        with self.assertRaises(ValueError):
            Inventory().add(ITSystem("SYS-001", "SRV-001", ("EVD-001",)))
        inventory = synthetic_fixture()
        with self.assertRaises(ValueError):
            inventory.add(Relationship("REL-003", "SYS-999", Predicate.HOSTS, "APP-001", ("EVD-001",)))
        with self.assertRaises(ValueError):
            inventory.add(Relationship("REL-003", "SYS-001", Predicate.HOSTS, "APP-999", ("EVD-001",)))

    def test_existing_but_unrelated_evidence_does_not_support_name(self):
        with self.assertRaises(ValueError):
            synthetic_fixture().add(ITApplication("APP-002", "CRM-02", ("EVD-001",)))

    def test_relationship_evidence_needs_both_endpoint_names(self):
        inventory = synthetic_fixture()
        second = evidence("EVD-002", "FIKTIV. Anwendung CRM-02.", "Anwendung CRM-02.", source_id="synthetic:app-only")
        inventory = inventory.add(second).add(ITApplication("APP-002", "CRM-02", ("EVD-002",)))
        with self.assertRaises(ValueError):
            inventory.add(Relationship("REL-003", "SYS-001", Predicate.HOSTS, "APP-002", ("EVD-002",)))

    def test_duplicate_relationship_triple_is_not_an_independent_truth(self):
        inventory = synthetic_fixture()
        with self.assertRaises(ValueError):
            inventory.add(replace(inventory.get("REL-001"), id="REL-003"))

    def test_location_and_application_refs_are_derived(self):
        inventory = synthetic_fixture()
        self.assertEqual(inventory.location_id("SYS-001"), "LOC-001")
        self.assertEqual(inventory.application_ids("SYS-001"), ("APP-001",))
        self.assertNotIn("location_id", asdict(inventory.get("SYS-001")))
        with self.assertRaises(ValueError):
            inventory.application_ids("LOC-001")

    def test_unknown_location_stays_missing(self):
        inventory = Inventory().add(evidence()).add(ITSystem("SYS-001", "SRV-001", ("EVD-001",)))
        self.assertIsNone(inventory.location_id("SYS-001"))
        self.assertEqual(inventory.application_ids("SYS-001"), ())

    def test_revision_numbers_and_history(self):
        inventory = synthetic_fixture()
        original = inventory.get("SYS-001")
        for revision in (1, 3):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                inventory.revise(replace(original, revision=revision))
        updated = inventory.revise(replace(original, revision=2, description="Neue fiktive Revision"))
        self.assertEqual(updated.record_history("SYS-001"), (original, updated.get("SYS-001")))
        self.assertEqual(inventory.get("SYS-001"), original)

    def test_new_record_cannot_skip_initial_revision(self):
        with self.assertRaises(ValueError):
            Inventory().add(evidence(revision=2))

    def test_explicit_approval_requires_dependencies_first(self):
        inventory = synthetic_fixture()
        for identifier in ("SYS-001", "REL-001"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                inventory.record_review(review(inventory, identifier))
        approved = approved_fixture()
        self.assertEqual(len(approved.approved_records()), 6)

    def test_review_history_is_append_only(self):
        initial = synthetic_fixture()
        proposed = review(initial, "EVD-001", ReviewState.PROPOSED, reviewer=None)
        inventory = initial.record_review(proposed)
        approval = review(inventory, "EVD-001")
        inventory = inventory.record_review(approval)
        self.assertEqual(inventory.review_history("EVD-001"), (proposed, approval))
        self.assertEqual(initial.review_history(), ())
        with self.assertRaises(ValueError):
            inventory.record_review(approval)

    def test_review_timestamp_cannot_go_backwards(self):
        inventory = synthetic_fixture()
        inventory = inventory.record_review(review(inventory, "EVD-001"))
        with self.assertRaises(ValueError):
            inventory.record_review(review(inventory, "APP-001", timestamp=NOW - timedelta(seconds=1)))

    def test_rejected_or_clarification_revision_cannot_be_promoted(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION):
            inventory = synthetic_fixture()
            inventory = inventory.record_review(review(inventory, "EVD-001", state))
            for next_state in (ReviewState.PROPOSED, ReviewState.APPROVED):
                with self.subTest(state=state, next_state=next_state), self.assertRaises(ValueError):
                    inventory.record_review(review(inventory, "EVD-001", next_state))

    def test_blocked_candidate_origins_cannot_enter_inventory(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION, ReviewState.APPROVED):
            with self.subTest(state=state), self.assertRaises(ValueError):
                Inventory().add(evidence(origin=provenance(state)))

    def test_raw_model_fields_are_not_domain_records(self):
        from grundschutz_ai.extraction import extract_inventory
        from tests.test_extraction import COMPLETE, fields, mock_client
        for candidate in (
            extract_inventory(COMPLETE, "synthetic:raw", mock_client(fields())),
            extract_inventory(COMPLETE + "\nKommentar.", "synthetic:raw", mock_client(fields())),
        ):
            for value in (candidate, candidate.fields):
                with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError):
                    Inventory().add(value)

    def test_outdated_data_review_is_rejected(self):
        inventory = approved_fixture()
        stale = review(inventory, "SYS-001")
        inventory = inventory.revise(replace(inventory.get("SYS-001"), revision=2, description="Fiktive geänderte Datensatzbeschreibung"))
        self.assertIs(inventory.review_state("SYS-001"), ReviewState.PROPOSED)
        self.assertIs(inventory.review_state("REL-001"), ReviewState.PROPOSED)
        with self.assertRaises(ValueError):
            inventory.record_review(stale)

    def test_outdated_source_review_is_rejected(self):
        inventory = approved_fixture()
        stale = review(inventory, "SYS-001")
        inventory = inventory.revise(evidence(source=SOURCE + "\nFiktiver Revisionshinweis.", revision=2))
        self.assertIs(inventory.review_state("SYS-001"), ReviewState.PROPOSED)
        self.assertNotIn("SYS-001", {record.id for record in inventory.approved_records()})
        with self.assertRaises(ValueError):
            inventory.record_review(stale)
        self.assertEqual(len(inventory.review_history("SYS-001")), 1)

    def test_outdated_candidate_revision_requires_new_review(self):
        inventory = approved_fixture()
        stale = review(inventory, "EVD-001")
        inventory = inventory.revise(evidence(revision=2, origin=provenance(candidate_revision="a" * 64)))
        self.assertIs(inventory.review_state("EVD-001"), ReviewState.PROPOSED)
        self.assertIs(inventory.review_state("REL-001"), ReviewState.PROPOSED)
        with self.assertRaises(ValueError):
            inventory.record_review(stale)

    def test_reapproval_rechecks_support_after_evidence_revision(self):
        inventory = approved_fixture()
        replacement = "FIKTIV. Anwendung ERP-01 ohne Nachweis eines Servers oder Standorts."
        inventory = inventory.revise(evidence(source=replacement, quote=replacement, revision=2))
        inventory = inventory.record_review(review(inventory, "EVD-001"))
        with self.assertRaises(ValueError):
            inventory.record_review(review(inventory, "SYS-001"))

    def test_revised_blocked_record_requires_a_fresh_explicit_review(self):
        inventory = synthetic_fixture()
        inventory = inventory.record_review(review(inventory, "EVD-001", ReviewState.NEEDS_CLARIFICATION))
        inventory = inventory.revise(evidence(revision=2))
        self.assertIs(inventory.review_state("EVD-001"), ReviewState.PROPOSED)
        inventory = inventory.record_review(review(inventory, "EVD-001"))
        self.assertIs(inventory.review_state("EVD-001"), ReviewState.APPROVED)
        self.assertEqual(len(inventory.review_history("EVD-001")), 2)

    def test_source_update_seen_through_another_evidence_invalidates_old_evidence(self):
        inventory = approved_fixture()
        inventory = inventory.add(evidence("EVD-002", source=SOURCE + "\nNeue fiktive Quellrevision."))
        self.assertIs(inventory.review_state("EVD-001"), ReviewState.NEEDS_CLARIFICATION)
        with self.assertRaises(ValueError):
            inventory.record_review(review(inventory, "EVD-001"))

    def test_return_to_previous_source_content_does_not_resurrect_approvals(self):
        inventory = approved_fixture()
        inventory = inventory.add(evidence("EVD-002", source=SOURCE + "\nNeue fiktive Quellrevision."))
        inventory = inventory.add(evidence("EVD-003"))
        self.assertIs(inventory.review_state("EVD-001"), ReviewState.PROPOSED)
        self.assertIs(inventory.review_state("SYS-001"), ReviewState.PROPOSED)

    def test_revoking_evidence_invalidates_approved_dependents(self):
        inventory = approved_fixture()
        inventory = inventory.record_review(review(inventory, "EVD-001", ReviewState.REJECTED))
        self.assertIs(inventory.review_state("SYS-001"), ReviewState.NEEDS_CLARIFICATION)
        self.assertEqual(inventory.approved_records(), ())

    def test_conflicting_locations_block_approval_and_derived_location(self):
        inventory = conflicting_fixture()
        self.assertEqual(inventory.conflicting_relationship_ids(), frozenset({"REL-002", "REL-003"}))
        for identifier in ("SYS-001", "REL-002", "REL-003"):
            self.assertIs(inventory.review_state(identifier), ReviewState.NEEDS_CLARIFICATION)
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                inventory.record_review(review(inventory, identifier))
        with self.assertRaises(ValueError):
            inventory.location_id("SYS-001")

    def test_conflict_resolution_keeps_rejected_alternative_and_review(self):
        inventory = conflicting_fixture()
        decision = review(inventory, "REL-003", ReviewState.REJECTED)
        inventory = inventory.record_review(decision)
        self.assertEqual(inventory.conflicting_relationship_ids(), frozenset())
        self.assertEqual(inventory.location_id("SYS-001"), "LOC-001")
        self.assertIs(inventory.review_state("REL-002"), ReviewState.PROPOSED)
        self.assertEqual(inventory.get("REL-003").object_id, "LOC-002")
        self.assertEqual(inventory.review_history("REL-003"), (decision,))

    def test_new_contradiction_removes_prior_approved_system_from_view(self):
        inventory = approved_fixture()
        quote = QUOTE.replace("Rechenzentrum Rostock", "Rechenzentrum Berlin")
        inventory = inventory.add(evidence("EVD-002", "FIKTIV.\n" + quote, quote, source_id="synthetic:other"))
        inventory = inventory.add(Location("LOC-002", "Rechenzentrum Berlin", ("EVD-002",)))
        inventory = inventory.add(Relationship("REL-003", "SYS-001", Predicate.LOCATED_AT, "LOC-002", ("EVD-002",)))
        self.assertNotIn("SYS-001", {record.id for record in inventory.approved_records()})
        self.assertEqual(len(inventory.review_history("SYS-001")), 1)

    def test_multiple_hosted_applications_are_not_a_location_conflict(self):
        quote = QUOTE.replace("ERP-01", "CRM-02")
        inventory = synthetic_fixture().add(evidence("EVD-002", "FIKTIV.\n" + quote, quote, source_id="synthetic:second-app"))
        inventory = inventory.add(ITApplication("APP-002", "CRM-02", ("EVD-002",)))
        inventory = inventory.add(Relationship("REL-003", "SYS-001", Predicate.HOSTS, "APP-002", ("EVD-002",)))
        self.assertEqual(inventory.application_ids("SYS-001"), ("APP-001", "APP-002"))
        self.assertEqual(inventory.conflicting_relationship_ids(), frozenset())

    def test_fingerprint_is_stable_for_same_snapshot(self):
        self.assertEqual(synthetic_fixture().revision_digest("SYS-001"), synthetic_fixture().revision_digest("SYS-001"))


if __name__ == "__main__":
    unittest.main()
