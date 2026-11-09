"""Synthetic-only SQLite tests: all databases live outside the checkout."""

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from grundschutz_ai.domain import Evidence, ITSystem, Location, Predicate, Relationship, ReviewState
from grundschutz_ai.storage import (
    CorruptStoreError, InventoryStore, InvalidWriteError, StorageError,
    StoreBusyError, UnsupportedStoreVersion, Write,
)
from grundschutz_ai.support import SYNTHETIC_HEADER
from tests.test_domain import QUOTE, SOURCE, evidence, provenance, review, synthetic_fixture


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="grundschutz-ai-task005-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "inventory.sqlite3"
        self.assertFalse(self.path.resolve().is_relative_to(Path(__file__).resolve().parents[2]))

    def store(self):
        store = InventoryStore(self.path)
        self.addCleanup(store.close)
        return store

    def seed(self, store, *, approved=False):
        # A fresh fixture has no prior history: persist these known actions in order.
        for record in synthetic_fixture().records:
            inventory = store.add(record, source_text=SOURCE if isinstance(record, Evidence) else None)
        if approved:
            for identifier in ("EVD-001", "APP-001", "LOC-001", "SYS-001", "REL-001", "REL-002"):
                inventory = store.record_review(review(inventory, identifier))
        return inventory

    @contextmanager
    def connection(self, **options):
        connection = sqlite3.connect(self.path, **options)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def counts(self):
        with self.connection() as connection:
            return (
                connection.execute("SELECT count(*) FROM sources").fetchone()[0],
                connection.execute("SELECT count(*) FROM events").fetchone()[0],
                connection.execute("SELECT last_sequence FROM metadata").fetchone()[0],
            )

    def payload(self, sequence=1):
        with self.connection() as connection:
            return json.loads(connection.execute("SELECT payload FROM events WHERE sequence = ?", (sequence,)).fetchone()[0])

    def tamper(self, sql, args=(), *, trigger=None):
        """Simulate external corruption, restoring normal append-only triggers."""
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if trigger:
                original = connection.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?", (trigger,)).fetchone()[0]
                # Names are fixed test-controlled identifiers, not source data.
                if trigger == "sources_no_update":
                    connection.execute("DROP TRIGGER sources_no_update")
                elif trigger == "sources_no_delete":
                    connection.execute("DROP TRIGGER sources_no_delete")
                elif trigger == "events_no_update":
                    connection.execute("DROP TRIGGER events_no_update")
                elif trigger == "events_no_delete":
                    connection.execute("DROP TRIGGER events_no_delete")
                else:
                    raise AssertionError("Unexpected test trigger")
            connection.execute(sql, args)
            if trigger:
                connection.execute(original)

    def change_payload(self, data, sequence=1):
        payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        self.tamper("UPDATE events SET payload = ? WHERE sequence = ?", (payload, sequence), trigger="events_no_update")

    def test_empty_create_close_reopen(self):
        store = self.store()
        self.assertEqual(store.load().records, ())
        store.close()
        with self.store() as reopened:
            self.assertEqual(reopened.load().records, ())
            self.assertEqual(reopened.load().review_history(), ())
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_complete_round_trip_with_original_source_and_relationships(self):
        store = self.store()
        expected = self.seed(store)
        store.close()
        reopened = self.store()
        actual = reopened.load()
        self.assertEqual(actual, expected)
        self.assertEqual(actual.get("SYS-001").name, "SRV-001")
        self.assertEqual(actual.get("APP-001").name, "ERP-01")
        self.assertEqual(actual.get("LOC-001").name, "Rechenzentrum Rostock")
        self.assertEqual(actual.location_id("SYS-001"), "LOC-001")
        self.assertEqual(actual.application_ids("SYS-001"), ("APP-001",))
        self.assertEqual(reopened.read_source("synthetic:task-004", evidence().source_sha256), SOURCE)
        self.assertEqual(actual.approved_records(), ())

    def test_exact_utf8_bytes_and_character_offsets_survive(self):
        source = "FIKTIV: ÄÖß🙂\r\n" + QUOTE + "\r\n"
        item = evidence(source=source)
        store = self.store()
        expected = store.add(item, source_text=source)
        store.close()
        with self.connection() as connection:
            blob, kind = connection.execute("SELECT content, typeof(content) FROM sources").fetchone()
        self.assertEqual(kind, "blob")
        self.assertEqual(blob, source.encode("utf-8"))
        reopened = self.store()
        self.assertEqual(reopened.load(), expected)
        self.assertEqual(reopened.read_source(item.source_id, item.source_sha256), source)
        self.assertEqual(reopened.load().get("EVD-001").locator, item.locator)

    def test_explicit_approvals_survive_valid_round_trip(self):
        store = self.store()
        expected = self.seed(store, approved=True)
        store.close()
        loaded = self.store().load()
        self.assertEqual(loaded, expected)
        self.assertEqual(len(loaded.approved_records()), 6)
        for record in expected.records:
            self.assertEqual(loaded.review_history(record.id), expected.review_history(record.id))
            self.assertEqual(loaded.revision_digest(record.id), expected.revision_digest(record.id))

    def test_interleaving_reviews_before_revision_is_preserved(self):
        store = self.store()
        inventory = store.add(evidence(), source_text=SOURCE)
        inventory = store.add(ITSystem("SYS-001", "SRV-001", ("EVD-001",)))
        for identifier in ("EVD-001", "SYS-001"):
            inventory = store.record_review(review(inventory, identifier))
        updated_source = SOURCE + "\nFiktiver Quellhinweis."
        inventory = store.revise(evidence(source=updated_source, revision=2), source_text=updated_source)
        store.close()
        loaded = self.store().load()
        self.assertEqual(loaded, inventory)
        self.assertEqual(len(loaded.record_history("EVD-001")), 2)
        self.assertEqual(len(loaded.review_history("SYS-001")), 1)
        self.assertIs(loaded.review_state("SYS-001"), ReviewState.PROPOSED)
        with self.connection() as connection:
            operations = [row[0] for row in connection.execute("SELECT operation FROM events ORDER BY sequence")]
        self.assertEqual(operations, ["add", "add", "review", "review", "revise"])

    def test_source_update_invalidates_approvals_after_reload(self):
        store = self.store()
        self.seed(store, approved=True)
        changed = SOURCE + "\nFiktiver Revisionshinweis."
        expected = store.revise(evidence(source=changed, revision=2), source_text=changed)
        store.close()
        loaded = self.store().load()
        self.assertEqual(loaded, expected)
        self.assertIsNot(loaded.review_state("SYS-001"), ReviewState.APPROVED)
        self.assertEqual(loaded.approved_records(), ())

    def test_rejected_and_clarification_states_cannot_be_promoted_on_reload(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION):
            with self.subTest(state=state):
                path = Path(self.temporary.name) / (state.value + ".sqlite3")
                with InventoryStore(path) as store:
                    inventory = self.seed(store)
                    expected = store.record_review(review(inventory, "EVD-001", state))
                with InventoryStore(path) as reopened:
                    loaded = reopened.load()
                    self.assertEqual(loaded, expected)
                    self.assertIs(loaded.review_state("EVD-001"), state)
                    with self.assertRaises(InvalidWriteError):
                        reopened.record_review(review(loaded, "EVD-001"))
                    self.assertEqual(reopened.load(), expected)

    def test_conflicting_locations_survive_as_unresolved(self):
        store = self.store()
        self.seed(store)
        quote = QUOTE.replace("Rechenzentrum Rostock", "Rechenzentrum Berlin")
        source = SYNTHETIC_HEADER + quote
        inventory = store.add(evidence("EVD-002", source, quote, source_id="synthetic:other"), source_text=source)
        inventory = store.add(Location("LOC-002", "Rechenzentrum Berlin", ("EVD-002",)))
        expected = store.add(Relationship("REL-003", "SYS-001", Predicate.LOCATED_AT, "LOC-002", ("EVD-002",)))
        store.close()
        reopened = self.store()
        loaded = reopened.load()
        self.assertEqual(loaded, expected)
        self.assertIs(loaded.review_state("SYS-001"), ReviewState.NEEDS_CLARIFICATION)
        self.assertEqual(loaded.conflicting_relationship_ids(), frozenset({"REL-002", "REL-003"}))
        with self.assertRaises(ValueError):
            loaded.location_id("SYS-001")
        with self.assertRaises(InvalidWriteError):
            reopened.record_review(review(loaded, "SYS-001"))

    def test_returning_to_old_bytes_does_not_resurrect_approval(self):
        store = self.store()
        self.seed(store, approved=True)
        changed = SOURCE + "\nFiktive Quellenrevision."
        store.revise(evidence(source=changed, revision=2), source_text=changed)
        expected = store.revise(evidence(revision=3), source_text=SOURCE)
        store.close()
        reopened = self.store()
        loaded = reopened.load()
        self.assertEqual(loaded, expected)
        self.assertIs(loaded.review_state("SYS-001"), ReviewState.PROPOSED)
        self.assertIs(loaded.review_state("EVD-001"), ReviewState.PROPOSED)
        self.assertEqual(loaded.approved_records(), ())
        self.assertEqual(self.counts(), (2, 14, 14))
        self.assertEqual(reopened.read_source("synthetic:task-004", evidence(source=changed).source_sha256), changed)
        self.assertEqual(reopened.read_source("synthetic:task-004", evidence().source_sha256), SOURCE)

    def test_derived_support_is_recomputed_and_not_stored(self):
        store = self.store()
        self.seed(store, approved=True)
        payload = self.payload()
        for name in ("relationship_support", "quote_before", "quote_after", "source_text"):
            self.assertNotIn(name, payload)
        negative = "Der Server SRV-001 betreibt die Anwendung ERP-01 nicht."
        expected = store.revise(evidence(source=negative, quote=negative, revision=2), source_text=negative)
        store.close()
        loaded = self.store().load()
        self.assertEqual(loaded, expected)
        self.assertIsNone(loaded.get("EVD-001").relationship_support)
        self.assertIs(loaded.review_state("REL-001"), ReviewState.NEEDS_CLARIFICATION)
        self.assertNotIn("REL-001", {record.id for record in loaded.approved_records()})

    def test_missing_source_fails_closed(self):
        store = self.store()
        self.seed(store)
        store.close()
        self.tamper("DELETE FROM sources", trigger="sources_no_delete")
        with self.assertRaises(CorruptStoreError):
            self.store()

    def test_corrupted_source_bytes_fail_closed(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        self.tamper("UPDATE sources SET content = ?", (b"corrupted synthetic bytes",), trigger="sources_no_update")
        with self.assertRaises(CorruptStoreError):
            store.load()

    def test_matching_hash_of_invalid_utf8_is_rejected(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        store.close()
        # Insert a corrupt retained source version; verifying all bytes must fail
        # even though this byte sequence has a matching SHA-256.
        with self.connection() as connection:
            raw = b"\xff\xfe"
            connection.execute("INSERT INTO sources VALUES (?, ?, ?)", ("synthetic:invalid", hashlib.sha256(raw).hexdigest(), raw))
        with self.assertRaises(CorruptStoreError):
            self.store()

    def test_incorrect_quote_offsets_and_hash_are_detected(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        original = self.payload()
        bad_offset = json.loads(json.dumps(original))
        bad_offset["locator"]["start"] += 1
        bad_hash = {**original, "source_sha256": "0" * 64}
        bad_quote = {**original, "quote": "Frei erfundener Beleg"}
        for data in (bad_offset, bad_hash, bad_quote):
            with self.subTest(data=data):
                self.change_payload(data)
                with self.assertRaises(CorruptStoreError):
                    store.load()

    def test_event_header_and_evidence_source_id_must_agree(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        self.change_payload({**self.payload(), "source_id": "synthetic:substituted"})
        with self.assertRaises(CorruptStoreError):
            store.load()

    def test_malformed_or_unknown_event_payload_rejected(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        original = self.payload()
        for payload in (
            "{", "[]", '{"type":"Evidence","type":"ReviewRecord"}',
            '{"type":"Evidence","revision":NaN}', {**original, "type": "ArbitraryClass"},
            {**original, "relationship_support": {"system": "SRV-001", "application": "ERP-01"}},
            {**original, "source_text": SOURCE},
        ):
            with self.subTest(payload=payload):
                self.change_payload(payload)
                with self.assertRaises(CorruptStoreError):
                    store.load()

    def test_stored_approved_string_without_valid_review_is_not_authority(self):
        store = self.store()
        inventory = store.add(evidence(), source_text=SOURCE)
        store.record_review(review(inventory, "EVD-001", ReviewState.PROPOSED, reviewer=None))
        proposed = self.payload(2)
        for data in ({**proposed, "state": "approved"}, {**proposed, "state": "verified"}):
            with self.subTest(data=data):
                self.change_payload(data, 2)
                with self.assertRaises(CorruptStoreError):
                    store.load()

    def test_unsupported_schema_or_policy_is_explicit(self):
        store = self.store()
        store.close()
        self.tamper("PRAGMA user_version = 42")
        with self.assertRaises(UnsupportedStoreVersion):
            self.store()
        self.tamper("PRAGMA user_version = 1")
        self.tamper("UPDATE metadata SET event_format = 2")
        with self.assertRaises(UnsupportedStoreVersion):
            self.store()
        self.tamper("UPDATE metadata SET event_format = 1, support_policy = ?", ("unknown-policy",))
        with self.assertRaises(UnsupportedStoreVersion):
            self.store()

    def test_unrelated_database_is_not_overwritten(self):
        with self.connection() as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
            connection.execute("INSERT INTO unrelated VALUES (?)", ("Fiktive bestehende Daten",))
        with self.assertRaises(UnsupportedStoreVersion):
            self.store()
        with self.connection() as connection:
            self.assertEqual(connection.execute("SELECT value FROM unrelated").fetchone()[0], "Fiktive bestehende Daten")

    def test_deleted_event_is_detected_by_sequence_metadata(self):
        store = self.store()
        self.seed(store)
        self.tamper("DELETE FROM events WHERE sequence = 6", trigger="events_no_delete")
        with self.assertRaises(CorruptStoreError):
            store.load()

    def test_interior_event_gap_is_rejected(self):
        store = self.store()
        self.seed(store)
        self.tamper("DELETE FROM events WHERE sequence = 2", trigger="events_no_delete")
        with self.assertRaises(CorruptStoreError):
            store.load()

    def test_reordered_historical_review_is_not_replayed_as_valid(self):
        store = self.store()
        inventory = store.add(evidence(), source_text=SOURCE)
        inventory = store.record_review(review(inventory, "EVD-001"))
        store.revise(evidence(revision=2), source_text=SOURCE)
        with self.connection() as connection:
            rows = connection.execute("SELECT operation, payload, source_id, source_sha256 FROM events ORDER BY sequence").fetchall()
            connection.execute("BEGIN IMMEDIATE")
            sql = connection.execute("SELECT sql FROM sqlite_master WHERE name = ?", ("events_no_update",)).fetchone()[0]
            connection.execute("DROP TRIGGER events_no_update")
            for sequence, row in ((2, rows[2]), (3, rows[1])):
                connection.execute("UPDATE events SET operation = ?, payload = ?, source_id = ?, source_sha256 = ? WHERE sequence = ?", (*row, sequence))
            connection.execute(sql)
        with self.assertRaises(CorruptStoreError):
            store.load()

    def test_validation_failure_rolls_back_entire_batch_including_source(self):
        store = self.store()
        with self.assertRaises(InvalidWriteError):
            store.commit((Write("add", evidence(), SOURCE), Write("add", ITSystem("SYS-001", "SRV-001", ("EVD-999",)))))
        self.assertEqual(self.counts(), (0, 0, 0))
        self.assertEqual(store.load().records, ())

    def test_sql_failure_rolls_back_already_inserted_events_and_source(self):
        store = self.store()
        with self.connection() as connection:
            connection.execute("""CREATE TRIGGER synthetic_fail_insert BEFORE INSERT ON events
                WHEN NEW.sequence = 2 BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END""")
        with self.assertRaises(StorageError):
            store.commit((Write("add", evidence(), SOURCE), Write("add", ITSystem("SYS-001", "SRV-001", ("EVD-001",)))))
        self.assertEqual(self.counts(), (0, 0, 0))
        self.assertEqual(store.load().records, ())

    def test_failed_later_action_keeps_existing_approved_history(self):
        store = self.store()
        before = self.seed(store, approved=True)
        before_counts = self.counts()
        revision = replace(before.get("SYS-001"), revision=2, description="Fiktive Änderung")
        with self.assertRaises(InvalidWriteError):
            store.commit((Write("revise", revision), Write("add", before.get("SYS-001"))))
        self.assertEqual(store.load(), before)
        self.assertEqual(self.counts(), before_counts)

    def test_wrong_or_missing_original_source_refuses_evidence_write(self):
        store = self.store()
        for source in (None, SOURCE + "\nAnderer Text"):
            with self.subTest(source=source), self.assertRaises(InvalidWriteError):
                store.add(evidence(), source_text=source)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_unencodable_metadata_fails_before_any_write(self):
        store = self.store()
        with self.assertRaises(InvalidWriteError):
            store.add(evidence(source_id="synthetic:invalid-\ud800"), source_text=SOURCE)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_sources_and_events_have_append_only_guards_and_foreign_keys(self):
        store = self.store()
        store.add(evidence(), source_text=SOURCE)
        self.assertEqual(store._connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        for sql in ("UPDATE sources SET content = content", "DELETE FROM sources", "UPDATE events SET payload = payload", "DELETE FROM events"):
            with self.subTest(sql=sql), self.connection() as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(sql)
        with self.connection() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)", (2, "add", "{}", "synthetic:missing", "0" * 64))

    def test_source_ids_and_text_are_data_not_paths_or_sql(self):
        store = self.store()
        sentinel = Path(self.temporary.name) / "source-must-not-create-this.txt"
        source_id = str(sentinel) + "'; DROP TABLE events; --"
        source = "FIKTIVER Text: ../private.txt; DROP TABLE sources;"
        item = evidence(source=source, quote=source, source_id=source_id)
        store.add(item, source_text=source)
        self.assertEqual(store.read_source(source_id, item.source_sha256), source)
        self.assertFalse(sentinel.exists())
        self.assertEqual(self.counts(), (1, 1, 1))
        self.assertEqual({path.name for path in Path(self.temporary.name).iterdir()}, {"inventory.sqlite3"})

    def test_raw_model_candidates_and_blocked_origins_cannot_be_promoted(self):
        from grundschutz_ai.extraction import extract_inventory
        from tests.test_extraction import COMPLETE, INJECTION, fields, mock_client
        store = self.store()
        for source in (COMPLETE, INJECTION):
            candidate = extract_inventory(source, "synthetic:raw", mock_client(fields()))
            for item in (candidate, candidate.fields, {"state": "approved", "reviewer_id": "model"}):
                with self.subTest(item_type=type(item).__name__), self.assertRaises(InvalidWriteError):
                    store.add(item)
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION, ReviewState.APPROVED):
            with self.subTest(state=state), self.assertRaises(InvalidWriteError):
                store.add(evidence(origin=provenance(state)), source_text=SOURCE)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_concurrent_writer_is_safely_rejected_without_partial_write(self):
        store = self.store()
        with self.connection(timeout=0, isolation_level=None) as other:
            other.execute("BEGIN IMMEDIATE")
            with self.assertRaises(StoreBusyError):
                store.add(evidence(), source_text=SOURCE)
            other.execute("ROLLBACK")
        self.assertEqual(self.counts(), (0, 0, 0))
        store.add(evidence(), source_text=SOURCE)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_second_writer_validates_fresh_state_and_rejects_stale_review(self):
        first, second = self.store(), self.store()
        inventory = first.add(evidence(), source_text=SOURCE)
        stale = review(inventory, "EVD-001")
        first.revise(evidence(revision=2), source_text=SOURCE)
        with self.assertRaises(InvalidWriteError):
            second.record_review(stale)
        self.assertEqual(second.load(), first.load())
        self.assertEqual(self.counts(), (1, 2, 2))

    def test_closed_store_is_explicit_and_close_is_idempotent(self):
        store = self.store()
        store.close()
        store.close()
        with self.assertRaises(StorageError):
            store.load()

    def test_requested_source_missing_fails_without_using_source_id_as_path(self):
        store = self.store()
        with self.assertRaises(CorruptStoreError):
            store.read_source("../../nonexistent-company-file.txt", "0" * 64)

    def test_sqlite_uri_and_memory_paths_are_not_silently_interpreted(self):
        for path in (":memory:", "file:untrusted.sqlite3?mode=ro"):
            with self.subTest(path=path), self.assertRaises(StorageError):
                InventoryStore(path)


if __name__ == "__main__":
    unittest.main()
