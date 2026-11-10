"""Synthetic A-only ledger databases/bytes outside Git, no parser or proposals."""

from contextlib import ExitStack, closing
from dataclasses import FrozenInstanceError, replace
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from grundschutz_ai import v2_codec as codec, v2_ledger as ledger, v2_schema
from grundschutz_ai.docx_staging import StagingPolicy as DocxPolicy
from grundschutz_ai.xlsx_staging import StagingPolicy as XlsxPolicy, SheetSelection


ACTOR = "synthetic:human"
SOURCE = "synthetic:source-A"
SELECTION = SheetSelection("IT-Systeme", 1, 1, "rId1", "xl/worksheets/sheet1.xml")
RAW = b"FICTITIOUS SYNTHETIC DOCX BYTES -- deliberately not parsed"


@unittest.skipUnless(os.name == "nt", "A filesystem profile explicitly supports Windows fixed NTFS/ReFS only")
class V2LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grundschutz-ai-v2-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.assertFalse(self.directory.resolve().is_relative_to(Path(__file__).resolve().parents[2]))
        self.path = self.directory / "source-ledger.sqlite3"
        self.store = None

    def create(self, *, limits=ledger.DEFAULT_LIMITS):
        self.store = ledger.SourceLedger.create(self.path, actor_id=ACTOR, limits=limits)
        self.addCleanup(self.store.close)
        return self.store

    def head(self):
        return self.store.load().head

    def seed(self, kind="docx", policy=None, *, limits=ledger.DEFAULT_LIMITS):
        self.create(limits=limits)
        self.store.register_implementation(kind, expected=self.head(), actor_id=ACTOR)
        return self.store.create_registry(kind, policy or (DocxPolicy() if kind == "docx" else XlsxPolicy()), expected=self.head(), actor_id=ACTOR)

    def begin(self, registry, *, source=SOURCE, expected_source=None, **changes):
        values = dict(expected=self.head(), expected_source=expected_source, actor_id=ACTOR)
        values.update(changes)
        return self.store.begin_registration(registry, source, **values)

    def source(self, raw=RAW, suffix=".docx"):
        path = self.directory / ("fictitious" + suffix)
        path.write_bytes(raw)
        return path

    def capture(self, ref, path=None):
        return self.store.capture_source(ref, path or self.source(), expected=self.head(), actor_id=ACTOR)

    def tamper(self, table, sql, parameters=(), *, operation="update"):
        self.assertIn(table, v2_schema.TABLES)
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                name = f"{table}_no_{operation}"
                row = connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
                if row:
                    connection.execute("DROP TRIGGER " + name)
                connection.execute(sql, parameters)
                if row:
                    connection.execute(row[0])
        finally:
            connection.close()

    def assert_corrupt(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.load_ledger(self.path)

    def test_empty_store_and_readonly_reopen(self):
        self.create()
        state = self.store.load()
        self.assertEqual(state.head.sequence, 1)
        self.assertIs(state.events[0].payload.kind, codec.EventKind.INITIALIZED)
        self.assertEqual(state.registries, ())
        self.store.close()
        before = self.path.read_bytes()
        loaded = ledger.load_ledger(self.path)
        self.assertEqual(loaded, state)
        self.assertEqual(self.path.read_bytes(), before)
        with ledger.SourceLedger.open(self.path) as reopened:
            self.assertEqual(reopened.load(), state)

    def test_create_never_overwrites_existing_unrelated_file(self):
        original = b"FICTITIOUS UNRELATED FILE"
        self.path.write_bytes(original)
        with self.assertRaises(ledger.UnsafePathError):
            self.create()
        self.assertEqual(self.path.read_bytes(), original)
        self.assert_corrupt()

    def test_v1_refused_as_v2_without_mutation(self):
        from grundschutz_ai.storage import InventoryStore
        with InventoryStore(self.path):
            pass
        original = self.path.read_bytes()
        with self.assertRaises(ledger.UnsupportedLedgerError):
            ledger.SourceLedger.open(self.path)
        with self.assertRaises(ledger.UnsafePathError):
            ledger.SourceLedger.create(self.path, actor_id=ACTOR)
        self.assertEqual(self.path.read_bytes(), original)

    def test_old_v1_writer_refuses_v2_without_mutation(self):
        from grundschutz_ai.storage import InventoryStore, UnsupportedStoreVersion
        self.create().close()
        original = self.path.read_bytes()
        with self.assertRaises(UnsupportedStoreVersion):
            InventoryStore(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_source_kind_implementation_and_policy_metadata_round_trip(self):
        registry = self.seed()
        state = self.store.load()
        self.assertEqual(state.registries[0].registry_id, registry)
        self.assertEqual(state.policies[0].spec.data()["config"]["reader_limits"]["max_file_bytes"], 2 * 1024 * 1024)
        self.assertEqual(state.implementations[0].data()["method_version"], "docx-plain/v1")
        self.assertEqual(state, ledger.load_ledger(self.path))

    def test_only_trusted_local_descriptors_can_be_registered(self):
        self.create()
        for value in ("pdf", "../module", "https://example.invalid", "source.validated"):
            with self.assertRaises(ledger.InvalidCommandError):
                self.store.register_implementation(value, expected=self.head(), actor_id=ACTOR)
        self.assertEqual(self.head().sequence, 1)
        spec_hash = self.store.register_implementation("docx", expected=self.head(), actor_id=ACTOR)
        self.assertEqual(self.store.load().implementations[0].sha256, spec_hash)
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.register_implementation("docx", expected=self.head(), actor_id=ACTOR)

    def test_changed_local_implementation_is_not_silently_compatible(self):
        self.seed()
        with patch.object(ledger, "_local_spec", side_effect=ledger.UnsupportedLedgerError("Unavailable pinned implementation")):
            with self.assertRaises(ledger.UnsupportedLedgerError):
                ledger.load_ledger(self.path)

    def test_registry_requires_registered_matching_implementation_and_exact_policy(self):
        self.create()
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.create_registry("docx", DocxPolicy(), expected=self.head(), actor_id=ACTOR)
        self.store.register_implementation("docx", expected=self.head(), actor_id=ACTOR)
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.create_registry("docx", XlsxPolicy(), expected=self.head(), actor_id=ACTOR)
        self.assertEqual(len(self.store.load().registries), 0)

    def test_global_event_sequence_hash_chain_and_unique_transactions(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref)
        self.assertEqual([event.envelope.data()["sequence"] for event in state.events], list(range(1, 6)))
        last = None
        txs, ids = set(), set()
        for event in state.events:
            data = event.envelope.data()
            self.assertEqual(data["previous_event_sha256"], last)
            self.assertEqual(data["payload_sha256"], hashlib.sha256(event.payload.canonical).hexdigest())
            self.assertEqual((data["transaction_index"], data["transaction_count"]), (1, 1))
            txs.add(data["transaction_id"])
            ids.add(data["event_id"])
            last = data["event_sha256"]
        self.assertEqual(len(txs), 5)
        self.assertEqual(len(ids), 5)
        self.assertEqual(state.head.event_sha256, last)

    def test_timestamp_does_not_choose_event_order(self):
        registry = self.seed()
        with patch.object(codec, "utc_now", return_value="2020-01-01T00:00:00.000000Z"):
            first = self.begin(registry)
        with patch.object(codec, "utc_now", return_value="2019-01-01T00:00:00.000000Z"):
            second = self.begin(registry, expected_source=first)
        self.assertEqual(self.store.load().source_head(SOURCE), second)

    def test_pending_registration_persists_across_restart_without_capture(self):
        registry = self.seed()
        ref = self.begin(registry)
        before = self.store.load()
        self.assertIs(before.registration(ref).status, ledger.SourceStatus.PENDING)
        self.assertIsNone(before.registration(ref).binary_sha256)
        self.store.close()
        self.assertEqual(ledger.load_ledger(self.path), before)
        with ledger.SourceLedger.open(self.path) as reopened:
            with self.assertRaises(ledger.InvalidCommandError):
                reopened.capture_source(ref, self.source(), expected=before.head, actor_id=ACTOR)
            failed = reopened.fail_source(ref, expected=before.head, actor_id=ACTOR)
            self.assertIs(failed.registration(ref).status, ledger.SourceStatus.FAILED)

    def test_abrupt_process_exit_after_registration_keeps_committed_pending_head(self):
        registry = self.seed()
        self.store.close()
        script = """import os,sys
from grundschutz_ai.v2_ledger import SourceLedger
s=SourceLedger.open(sys.argv[1])
s.begin_registration(sys.argv[2], 'synthetic:crash', expected=s.load().head, expected_source=None, actor_id='synthetic:human')
os._exit(0)
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.path), registry], capture_output=True,
                                timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        loaded = ledger.load_ledger(self.path)
        ref = loaded.source_head("synthetic:crash")
        self.assertIsNotNone(ref)
        self.assertIs(loaded.registration(ref).status, ledger.SourceStatus.PENDING)
        self.assertIsNone(loaded.registration(ref).binary_sha256)

    def test_original_binary_round_trip_and_capture_stays_pending(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref)
        observed = state.registration(ref)
        self.assertIs(observed.status, ledger.SourceStatus.PENDING)
        self.assertEqual(observed.binary_sha256, hashlib.sha256(RAW).hexdigest())
        self.assertEqual(state.original_blobs[0].content, RAW)
        self.store.close()
        self.assertEqual(ledger.load_ledger(self.path), state)
        self.assertFalse(hasattr(state, "approved_records"))
        self.assertFalse(hasattr(state, "proposals"))

    def test_capture_failure_commits_failed_without_inventing_binary_hash(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref, self.directory / "absent.docx")
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.FAILED)
        self.assertIsNone(state.registration(ref).binary_sha256)
        self.assertEqual(state.original_blobs, ())
        self.assertEqual(ledger.load_ledger(self.path), state)

    def test_explicit_failure_after_capture_preserves_bytes_and_is_terminal(self):
        registry = self.seed()
        ref = self.begin(registry)
        captured = self.capture(ref)
        failed = self.store.fail_source(ref, expected=captured.head, actor_id=ACTOR)
        self.assertEqual(failed.registration(ref).binary_sha256, captured.registration(ref).binary_sha256)
        self.assertIs(failed.registration(ref).status, ledger.SourceStatus.FAILED)
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.fail_source(ref, expected=failed.head, actor_id=ACTOR)

    def test_identical_bytes_deduplicate_blob_but_not_source_registrations(self):
        registry = self.seed()
        first = self.begin(registry)
        self.capture(first)
        second = self.begin(registry, expected_source=first)
        state = self.capture(second)
        self.assertEqual(len(state.original_blobs), 1)
        self.assertEqual(len(state.registrations), 2)
        self.assertNotEqual(first.registration_id, second.registration_id)
        self.assertEqual((first.revision, second.revision), (1, 2))
        self.assertEqual(len([event for event in state.events if event.payload.kind is codec.EventKind.CAPTURED]), 2)
        self.assertEqual(state.source_head(SOURCE), second)

    def test_new_pending_head_supersedes_old_failed_or_captured_head(self):
        registry = self.seed()
        first = self.begin(registry)
        self.capture(first)
        self.store.fail_source(first, expected=self.head(), actor_id=ACTOR)
        second = self.begin(registry, expected_source=first)
        loaded = ledger.load_ledger(self.path)
        self.assertEqual(loaded.source_head(SOURCE), second)
        self.assertIs(loaded.registration(second).status, ledger.SourceStatus.PENDING)
        self.assertIsNone(loaded.registration(second).binary_sha256)

    def test_old_capture_and_failure_finishing_late_never_replace_newer_head(self):
        registry = self.seed()
        old = self.begin(registry)
        newer = self.begin(registry, expected_source=old)
        self.capture(old)
        failed = self.store.fail_source(old, expected=self.head(), actor_id=ACTOR)
        self.assertEqual(failed.source_head(SOURCE), newer)
        self.assertIs(failed.registration(newer).status, ledger.SourceStatus.PENDING)

    def test_source_ownership_is_store_wide_and_immutable(self):
        first = self.seed()
        second = self.store.create_registry("docx", DocxPolicy(), expected=self.head(), actor_id=ACTOR)
        ref = self.begin(first)
        with self.assertRaises(ledger.InvalidCommandError):
            self.begin(second, expected_source=ref)

    def test_xlsx_requires_explicit_sheet_identity_but_does_not_validate_workbook(self):
        registry = self.seed("xlsx")
        with self.assertRaises(ledger.InvalidCommandError):
            self.begin(registry)
        ref = self.begin(registry, selection=SELECTION)
        state = self.capture(ref, self.source(b"FICTITIOUS XLSX CAPTURE, NOT PARSED", ".xlsx"))
        self.assertEqual(codec.canonical_loads(state.registration(ref).selection_json)["name"], "IT-Systeme")
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.PENDING)

    def test_wrong_extension_is_failed_not_a_valid_source(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref, self.source(suffix=".pdf"))
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.FAILED)
        self.assertIsNone(state.registration(ref).binary_sha256)

    def test_zero_length_capture_has_real_empty_digest_and_remains_pending(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref, self.source(b""))
        self.assertEqual(state.registration(ref).binary_sha256, hashlib.sha256(b"").hexdigest())
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.PENDING)

    def test_capture_once_survives_mutation_of_original_path_before_sql_commit(self):
        registry = self.seed()
        ref = self.begin(registry)
        path = self.source()
        original_write = self.store._write
        def write(*args, **kwargs):
            path.write_bytes(b"FICTITIOUS MUTATED PATH")
            return original_write(*args, **kwargs)
        with patch.object(self.store, "_write", side_effect=write):
            state = self.capture(ref, path)
        self.assertEqual(state.original_blobs[0].content, RAW)
        with self.assertRaises(ledger.InvalidCommandError):
            self.capture(ref, path)

    def test_sql_failure_rolls_back_blob_event_projections_and_prevents_reread(self):
        registry = self.seed()
        ref = self.begin(registry)
        before = self.store.load()
        with patch.object(self.store, "_mirror", side_effect=RuntimeError("Synthetic write fault")):
            with self.assertRaises(RuntimeError):
                self.capture(ref)
        self.assertEqual(self.store.load(), before)
        self.assertIs(self.store.load().registration(ref).status, ledger.SourceStatus.PENDING)
        with self.assertRaises(ledger.InvalidCommandError):
            self.capture(ref)
        self.assertEqual(self.store.load().original_blobs, ())

    def test_sql_trigger_failure_rolls_back_implementation_event_and_blob(self):
        self.create()
        before = self.store.load()
        # Controlled test hook: schema is restored after SQLite insertion fails.
        real_append = self.store._append
        def fault(*args, **kwargs):
            self.store._connection.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'synthetic fault'); END")
            return real_append(*args, **kwargs)
        with patch.object(self.store, "_append", side_effect=fault), self.assertRaises(ledger.LedgerError):
            self.store.register_implementation("docx", expected=before.head, actor_id=ACTOR)
        self.assertEqual(self.store.load(), before)

    def test_writer_lock_conflict_is_clear_and_has_no_partial_event(self):
        registry = self.seed()
        before = self.store.load()
        connection = sqlite3.connect(self.path, timeout=0, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            with self.assertRaises(ledger.LedgerBusyError):
                self.begin(registry)
            connection.execute("ROLLBACK")
        finally:
            connection.close()
        self.assertEqual(self.store.load(), before)

    def test_two_writers_reject_stale_global_and_source_head_tokens(self):
        registry = self.seed()
        with ledger.SourceLedger.open(self.path) as second:
            stale = second.load().head
            first = self.begin(registry)
            with self.assertRaises(ledger.StaleWriteError):
                second.begin_registration(registry, SOURCE, expected=stale, expected_source=None, actor_id=ACTOR)
            with self.assertRaises(ledger.StaleWriteError):
                second.begin_registration(registry, SOURCE, expected=second.load().head, expected_source=None, actor_id=ACTOR)
            self.assertEqual(second.load().source_head(SOURCE), first)

    def test_stale_write_after_capture_io_discards_bytes_and_keeps_pending(self):
        registry = self.seed()
        ref = self.begin(registry)
        original_write = self.store._write
        def interleave(*args, **kwargs):
            with ledger.SourceLedger.open(self.path) as other:
                other.begin_registration(registry, "synthetic:other", expected=other.load().head, expected_source=None, actor_id=ACTOR)
            return original_write(*args, **kwargs)
        with patch.object(self.store, "_write", side_effect=interleave), self.assertRaises(ledger.StaleWriteError):
            self.capture(ref)
        self.assertIsNone(self.store.load().registration(ref).binary_sha256)
        with self.assertRaises(ledger.InvalidCommandError):
            self.capture(ref)

    def test_policy_history_preserves_explicit_configs_and_pending_registration_policy(self):
        registry = self.seed()
        ref = self.begin(registry)
        original = self.store.load().policies
        policy = replace(DocxPolicy(), max_id_chars=63)
        self.store.activate_policy(registry, policy, expected=self.head(), actor_id=ACTOR)
        self.store.activate_policy(registry, DocxPolicy(), expected=self.head(), actor_id=ACTOR)
        state = self.capture(ref)
        self.assertEqual(len(original), 1)
        self.assertEqual(len(state.policies), 3)
        self.assertEqual(state.registration(ref).policy_revision, 1)
        self.assertEqual([p.revision for p in state.policies], [1, 2, 3])

    def test_repeated_same_policy_is_not_a_fake_activation(self):
        registry = self.seed()
        before = self.head()
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.activate_policy(registry, DocxPolicy(), expected=before, actor_id=ACTOR)
        self.assertEqual(self.head(), before)

    def test_capture_above_recorded_file_limit_is_terminal_failed_no_hash(self):
        policy = replace(DocxPolicy(), reader_limits=replace(DocxPolicy().reader_limits, max_file_bytes=3))
        registry = self.seed(policy=policy)
        ref = self.begin(registry)
        state = self.capture(ref)
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.FAILED)
        self.assertEqual(state.registration(ref).failure_codes, ("source_limit",))
        self.assertIsNone(state.registration(ref).binary_sha256)

    def test_raw_retention_exhaustion_commits_bounded_control_and_pending_survives(self):
        registry = self.seed(limits=replace(ledger.DEFAULT_LIMITS, max_original_bytes=1))
        ref = self.begin(registry)
        with self.assertRaises(ledger.LedgerLimitError):
            self.capture(ref)
        state = ledger.load_ledger(self.path, limits=self.store.limits)
        self.assertTrue(state.registries[0].exhausted)
        self.assertIs(state.registration(ref).status, ledger.SourceStatus.PENDING)
        self.assertIsNone(state.registration(ref).binary_sha256)
        self.assertIs(state.events[-1].payload.kind, codec.EventKind.EXHAUSTED)

    def test_history_and_source_capacity_exhaustion_survive_reopen(self):
        for policy in (replace(DocxPolicy(), max_history_units=3), replace(DocxPolicy(), max_sources=1)):
            with self.subTest(policy=policy):
                self.path = self.directory / ("history-" + str(policy.max_sources) + ".sqlite3")
                registry = self.seed(policy=policy)
                ref = self.begin(registry)
                with self.assertRaises(ledger.LedgerLimitError):
                    self.begin(registry, source="synthetic:second")
                state = self.store.load()
                self.assertTrue(state.registries[0].exhausted)
                self.assertEqual(state.current_heads, (ref,))
                self.store.close()
                with ledger.SourceLedger.open(self.path) as reopened:
                    self.assertTrue(reopened.load().registries[0].exhausted)

    def test_tightened_capacity_policy_cannot_erase_retained_history(self):
        registry = self.seed()
        self.begin(registry)
        before = self.store.load()
        with self.assertRaises(ledger.LedgerLimitError):
            self.store.activate_policy(registry, replace(DocxPolicy(), max_history_units=1), expected=before.head, actor_id=ACTOR)
        state = self.store.load()
        self.assertEqual(state.registrations, before.registrations)
        self.assertEqual(state.policies, before.policies)
        self.assertTrue(state.registries[0].exhausted)

    def test_reserved_event_slot_records_exhaustion_instead_of_silent_drop(self):
        limits = replace(ledger.DEFAULT_LIMITS, max_registries=1, max_events=4)
        registry = self.seed(limits=limits)
        with self.assertRaises(ledger.LedgerLimitError):
            self.begin(registry)
        state = self.store.load()
        self.assertEqual(state.head.sequence, 4)
        self.assertIs(state.events[-1].payload.kind, codec.EventKind.EXHAUSTED)
        self.assertEqual(state.registrations, ())

    def test_above_database_blob_and_event_budgets_refuse_entire_load(self):
        registry = self.seed()
        ref = self.begin(registry)
        self.capture(ref)
        for limits in (replace(ledger.DEFAULT_LIMITS, max_database_bytes=1), replace(ledger.DEFAULT_LIMITS, max_registries=1, max_events=3), replace(ledger.DEFAULT_LIMITS, max_metadata_bytes=1)):
            with self.subTest(limits=limits), self.assertRaises(ledger.LedgerError):
                ledger.load_ledger(self.path, limits=limits)

    def test_limit_configurations_only_tighten(self):
        for changes in ({"max_events": 10001}, {"max_registries": True}, {"max_replay_seconds": 0}, {"max_events": 2}):
            with self.assertRaises(codec.CodecError):
                ledger.LedgerLimits(**changes)

    def test_missing_raw_blob_is_not_reconstructed_or_ignored(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref)
        self.tamper("content_blobs", "DELETE FROM content_blobs WHERE sha256=?", (state.registration(ref).binary_sha256,), operation="delete")
        self.assert_corrupt()

    def test_corrupted_raw_blob_is_refused_even_when_same_length(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref)
        self.tamper("content_blobs", "UPDATE content_blobs SET content=? WHERE sha256=?", (b"X" * len(RAW), state.registration(ref).binary_sha256))
        self.assert_corrupt()

    def test_orphan_blob_or_extra_future_table_is_refused(self):
        self.create()
        raw = b"FICTITIOUS ORPHAN"
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", (hashlib.sha256(raw).hexdigest(), len(raw), raw))
        self.assert_corrupt()

    def test_reserved_future_tables_do_not_exist_and_are_not_an_activation_path(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, set(v2_schema.TABLES))
            connection.execute("CREATE TABLE derivations(fake TEXT)")
        self.assert_corrupt()

    def test_tampered_payload_deleted_or_reordered_events_are_refused(self):
        registry = self.seed()
        self.begin(registry)
        state = self.store.load()
        payload_hash = state.events[-1].envelope.data()["payload_sha256"]
        raw = state.events[-1].payload.canonical
        self.tamper("content_blobs", "UPDATE content_blobs SET content=? WHERE sha256=?", (b" " * len(raw), payload_hash))
        self.assert_corrupt()

    def test_deleted_terminal_event_is_refused(self):
        registry = self.seed()
        self.begin(registry)
        self.tamper("events", "DELETE FROM events WHERE sequence=(SELECT max(sequence) FROM events)", operation="delete")
        self.assert_corrupt()

    def test_reordered_event_payloads_are_not_valid_history(self):
        self.seed()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            first = connection.execute("SELECT envelope_json FROM events WHERE sequence=1").fetchone()[0]
        self.tamper("events", "UPDATE events SET envelope_json=? WHERE sequence=2", (first,))
        self.assert_corrupt()

    def test_mismatched_valid_older_head_projection_is_refused(self):
        registry = self.seed()
        old = self.begin(registry)
        self.begin(registry, expected_source=old)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            seq = connection.execute("SELECT start_event FROM registrations WHERE registration_id=?", (old.registration_id,)).fetchone()[0]
            connection.execute("UPDATE source_heads SET revision=?,registration_id=?,last_event=? WHERE source_id=?", (old.revision, old.registration_id, seq, SOURCE))
        self.assert_corrupt()

    def test_registry_and_policy_projection_mirrors_are_verified(self):
        registry = self.seed()
        self.begin(registry)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE registry_state SET history_units=0 WHERE registry_id=?", (registry,))
        self.assert_corrupt()

    def test_metadata_head_and_store_identity_are_verified(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE store_metadata SET store_uuid=?", ("0" * 32,))
        self.assert_corrupt()

    def test_unknown_schema_version_is_refused(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("PRAGMA user_version=3")
        with self.assertRaises(ledger.UnsupportedLedgerError):
            ledger.load_ledger(self.path)

    def test_append_only_triggers_and_foreign_keys_reject_ordinary_edits(self):
        self.create()
        self.assertEqual(self.store._connection.execute("PRAGMA foreign_keys").fetchone(), (1,))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            for sql in ("DELETE FROM events", "UPDATE events SET kind=kind", "DELETE FROM content_blobs", "UPDATE content_blobs SET content=content"):
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(sql)

    def test_future_event_kinds_cannot_be_appended_or_read_as_supported(self):
        self.create()
        self.assertFalse(hasattr(self.store, "append"))
        self.assertFalse(hasattr(self.store, "validate_source"))
        self.assertFalse(hasattr(self.store, "approved_records"))
        for kind in ("source.validated", "scope.assessed", "candidate.staged", "queue.decided", "legacy.import_started", "domain.materialized", "domain.reviewed", "export.approved"):
            with self.subTest(kind=kind), self.assertRaises((codec.CodecError, ValueError)):
                codec.EventKind(kind)
        event = self.store.load().events[0].envelope.data()
        event["kind"], event["payload_codec"] = "source.validated", "source-valid/v1"
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        event["event_sha256"] = codec.fingerprint(codec.EVENT_CODEC, body)
        self.tamper("events", "UPDATE events SET kind=?,payload_codec=?,event_sha256=?,envelope_json=? WHERE sequence=1", (event["kind"], event["payload_codec"], event["event_sha256"], codec.canonical_dumps(event)))
        self.assert_corrupt()

    def test_incomplete_or_reused_transaction_group_cannot_be_hydrated(self):
        self.create()
        data = self.store.load().events[0].envelope.data()
        data["transaction_count"] = 2
        data["event_sha256"] = codec.fingerprint(codec.EVENT_CODEC, {k: v for k, v in data.items() if k != "event_sha256"})
        self.tamper("events", "UPDATE events SET envelope_json=? WHERE sequence=1", (codec.canonical_dumps(data),))
        self.assert_corrupt()

    def test_paths_refuse_uri_relative_git_unc_and_alternate_streams(self):
        for path in (":memory:", "file:C:/fake.sqlite3?mode=rw", "relative.sqlite3", "\\\\server\\share\\fake.sqlite3", str(self.directory / "file.sqlite3:stream"), self.directory / "NUL.sqlite3", self.directory / "alias.sqlite3.", Path(__file__).resolve().parents[1] / "fictitious-v2-must-not-create.sqlite3"):
            with self.subTest(path=str(path)), self.assertRaises(ledger.UnsafePathError):
                ledger.SourceLedger.create(path, actor_id=ACTOR)

    def test_remote_and_unapproved_filesystem_profiles_are_refused(self):
        with patch.object(ledger, "_fixed_local_volume", side_effect=ledger.UnsafePathError("Synthetic unsupported volume")):
            with self.assertRaises(ledger.UnsafePathError):
                self.create()
        self.assertFalse(self.path.exists())

    def test_hard_link_database_alias_is_refused(self):
        self.create().close()
        alias = self.directory / "alias.sqlite3"
        os.link(self.path, alias)
        with self.assertRaises(ledger.UnsafePathError):
            ledger.load_ledger(alias)

    def test_foreign_registration_and_stale_before_io_are_refused(self):
        registry = self.seed()
        stale = self.head()
        ref = self.begin(registry)
        path = self.source()
        with patch.object(Path, "open", side_effect=AssertionError("No source I/O with stale token")):
            with self.assertRaises(ledger.StaleWriteError):
                self.store.capture_source(ref, path, expected=stale, actor_id=ACTOR)
        foreign = codec.SourceRef(SOURCE, 1, "0" * 32)
        with self.assertRaises(ledger.InvalidCommandError):
            self.store.fail_source(foreign, expected=self.head(), actor_id=ACTOR)

    def test_snapshots_and_source_event_data_are_immutable(self):
        registry = self.seed()
        ref = self.begin(registry)
        old = self.store.load()
        self.capture(ref)
        self.assertIsNone(old.registration(ref).binary_sha256)
        for value, attr, new in ((old, "head", None), (old.registries[0], "exhausted", False), (old.registration(ref), "status", "valid")):
            with self.assertRaises(FrozenInstanceError):
                setattr(value, attr, new)
        detached = old.events[-1].payload.data()
        detached["registration"]["source_id"] = "invented"
        self.assertEqual(old.events[-1].payload.data()["registration"]["source_id"], SOURCE)

    def test_closed_store_and_missing_file_do_not_create_databases(self):
        self.create().close()
        self.store.close()
        with self.assertRaises(ledger.LedgerError):
            self.store.load()
        missing = self.directory / "missing.sqlite3"
        with self.assertRaises(ledger.LedgerError):
            ledger.load_ledger(missing)
        self.assertFalse(missing.exists())

    def test_no_staging_readers_domain_v1_model_network_or_print_side_effects(self):
        from grundschutz_ai import inventory, storage
        targets = ["grundschutz_ai.domain." + name for name in ("Evidence", "ITSystem", "ITApplication", "Location", "Relationship", "ReviewRecord")]
        targets += ["grundschutz_ai.docx_ingestion.ingest_docx", "grundschutz_ai.xlsx_ingestion.ingest_xlsx", "grundschutz_ai.docx_staging.DocxStaging.stage", "grundschutz_ai.xlsx_staging.XlsxStaging.stage", "grundschutz_ai.storage.InventoryStore.commit", "grundschutz_ai.inventory.Inventory.add", "grundschutz_ai.inventory.Inventory.record_review", "grundschutz_ai.extraction.OllamaClient.generate", "urllib.request.urlopen", "builtins.print"]
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target)) for target in targets]
            registry = self.seed()
            ref = self.begin(registry)
            self.capture(ref)
            self.store.fail_source(ref, expected=self.head(), actor_id=ACTOR)
            state = ledger.load_ledger(self.path)
            self.assertIs(state.registration(ref).status, ledger.SourceStatus.FAILED)
            for mock in mocks:
                mock.assert_not_called()

    def test_source_ids_are_only_parameterized_data_not_paths_or_sql(self):
        registry = self.seed()
        sentinel = self.directory / "not-created.docx"
        source_id = str(sentinel) + "'; DROP TABLE events; --"
        ref = self.begin(registry, source=source_id)
        state = self.capture(ref)
        self.assertEqual(state.source_head(source_id), ref)
        self.assertFalse(sentinel.exists())

    def test_metadata_budget_exhaustion_commits_control_event_when_reserved(self):
        registry = self.seed()
        state = self.store.load()
        # Pin a budget that fits current metadata plus reserved control space,
        # but cannot admit the next ordinary source event.
        with closing(sqlite3.connect(self.path)) as connection:
            present = connection.execute("SELECT sum(byte_length) FROM content_blobs").fetchone()[0]
        self.store.limits = replace(self.store.limits, max_metadata_bytes=present + 1024 * self.store.limits.max_registries)
        with self.assertRaises(ledger.LedgerLimitError):
            self.begin(registry)
        loaded = self.store.load()
        self.assertTrue(loaded.registries[0].exhausted)
        self.assertEqual(loaded.events[-1].payload.data()["budget_name"], "metadata_bytes")
        self.assertEqual(loaded.registrations, ())

    def test_replay_deadline_refuses_entire_load(self):
        self.create()
        with patch.object(ledger.time, "monotonic", side_effect=[0, 100, 100, 100, 100]):
            with self.assertRaises(ledger.LedgerError):
                ledger.load_ledger(self.path)

    def test_connection_setup_failure_closes_handle_before_returning(self):
        self.path.write_bytes(b"FICTITIOUS NON-SQLITE")
        with self.assertRaises(ledger.LedgerError):
            ledger.load_ledger(self.path)
        # Windows refuses unlink if an SQLite connection handle leaked.
        self.path.unlink()
        self.assertFalse(self.path.exists())

    def test_create_connection_error_is_mapped_without_overwrite_or_success(self):
        with patch.object(ledger, "_connect", side_effect=sqlite3.OperationalError("Synthetic open fault")):
            with self.assertRaises(ledger.LedgerError):
                self.create()
        self.assertEqual(self.path.read_bytes(), b"")

    def test_writer_open_connection_error_is_mapped_after_readonly_verification(self):
        self.create().close()
        before = self.path.read_bytes()
        real_connect = ledger._connect
        def fail_writer(path, *, readonly):
            if not readonly:
                raise sqlite3.OperationalError("Synthetic writer-open fault")
            return real_connect(path, readonly=True)
        with patch.object(ledger, "_connect", side_effect=fail_writer), self.assertRaises(ledger.LedgerError):
            ledger.SourceLedger.open(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(ledger.load_ledger(self.path).head.sequence, 1)

    def test_coherently_rehashed_payload_still_cannot_lie_about_source_length(self):
        registry = self.seed()
        ref = self.begin(registry)
        state = self.capture(ref)
        event = state.events[-1]
        data = event.payload.data()
        data["byte_length"] += 1
        payload = codec.Payload(codec.canonical_dumps(data))
        header = event.envelope.data()
        old_payload = header["payload_sha256"]
        header["payload_sha256"] = codec.sha256(payload.canonical)
        header["event_sha256"] = codec.fingerprint(codec.EVENT_CODEC, {k: v for k, v in header.items() if k != "event_sha256"})
        # Every new hash is internally valid; source bytes and semantic mirrors
        # must independently disprove the altered byte_length assertion.
        codec.Envelope(codec.canonical_dumps(header))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            triggers = {name: connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0] for name in ("events_no_update", "content_blobs_no_delete")}
            for name in triggers:
                connection.execute("DROP TRIGGER " + name)
            connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", (header["payload_sha256"], len(payload.canonical), payload.canonical))
            connection.execute("UPDATE events SET payload_sha256=?,event_sha256=?,envelope_json=? WHERE sequence=?", (header["payload_sha256"], header["event_sha256"], codec.canonical_dumps(header), header["sequence"]))
            connection.execute("UPDATE store_metadata SET last_event_hash=?", (header["event_sha256"],))
            connection.execute("DELETE FROM content_blobs WHERE sha256=?", (old_payload,))
            for sql in triggers.values():
                connection.execute(sql)
        self.assert_corrupt()


if __name__ == "__main__":
    unittest.main()
