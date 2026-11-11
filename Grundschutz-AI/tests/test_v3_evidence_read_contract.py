"""Existing replay/snapshot prerequisites only; no future consumer is implemented.

Synthetic fixtures and real pinned native workers. These tests do not establish
that the proposed evidence API or its later error/egress contract exists.
"""
from contextlib import contextmanager
import json
import sqlite3
import time
from unittest.mock import patch

from grundschutz_ai import v3_ledger as ledger, v3_native as native
from grundschutz_ai._v3_validation import VerificationBudget
from tests import test_v3_validation as fixtures


class EvidenceReadPrerequisiteTests(fixtures.ValidationFixture):
    @contextmanager
    def snapshot(self):
        # Deliberately keep the transaction open around replay AND inspection.
        # Public load_ledger closes its connection and cannot serve this purpose.
        con = ledger._connect(self.path, readonly=True)
        try:
            self.assertEqual(con.execute("PRAGMA query_only").fetchone(), (1,))
            con.execute("BEGIN")
            budget = VerificationBudget(time.monotonic() + 60)
            state, replay = ledger._verify(con, self.writer._limits, budget.deadline, budget=budget)
            self.assertIs(replay.budget, budget)
            yield con, state, replay
            con.execute("COMMIT")
        finally:
            con.close()

    def exact_snapshot_bytes(self, name):
        _, ref, original, case = self.prepare(name)
        self.validate(ref)
        before_rows, before_bytes = self.rows(), self.path.read_bytes()
        original.unlink()
        with patch.object(native, "extract_captured_bytes", wraps=native.extract_captured_bytes) as bridge, \
                patch.object(native, "_worker", wraps=native._worker) as workers, \
                patch.object(ledger, "_read_original", side_effect=AssertionError("No original path")):
            with self.snapshot() as (con, state, replay):
                self.assertTrue(state.is_current_valid(ref))
                d = state.registration(ref).derivation
                data = d.data()
                self.assertEqual(replay.blobs[d.blob_sha256], d.canonical)
                self.assertEqual(replay.blobs[data["native_text_sha256"]], case["native_text"].encode("utf-8"))
                integration = replay.blobs[data["integration_manifest_sha256"]]
                self.assertEqual(integration, case["integration_manifest_json"].encode("utf-8"))
                if name.startswith("xlsx"):
                    self.assertEqual(replay.blobs[data["native_manifest_sha256"]], case["native_manifest_json"].encode("utf-8"))
                    self.assertEqual(json.loads(integration)["native_manifest_json"], case["native_manifest_json"])
                    self.assertIs(type(json.loads(integration)["native_manifest_json"]), str)
                else:
                    self.assertIsNone(data["native_manifest_sha256"])
                self.assertEqual(con.execute("SELECT count(*) FROM events").fetchone(), (len(state.events),))
                # A real mode=ro/query_only connection rejects writes. No schema
                # or persistent state is changed by this intentional probe.
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("CREATE TABLE forbidden_probe (value TEXT)")
        self.assertEqual(bridge.call_count, 1)
        self.assertEqual([call.args[1] for call in workers.call_args_list], ["derive", "verify"])
        self.assertEqual(self.rows(), before_rows)
        self.assertEqual(self.path.read_bytes(), before_bytes)
        self.assertFalse(hasattr(ledger.SourceLedger, "read_current_native_evidence"))

    def test_docx_exact_bytes_in_live_readonly_snapshot(self):
        self.exact_snapshot_bytes("docx_coverage")

    def test_xlsx_exact_bytes_and_nested_manifest_in_live_snapshot(self):
        self.exact_snapshot_bytes("xlsx_coverage")

    def test_deferred_begin_does_not_establish_snapshot_before_first_read(self):
        rid, old, _, _ = self.prepare()
        self.validate(old)
        args = self.begin_args(rid, old.source_id)
        con = ledger._connect(self.path, readonly=True)
        try:
            con.execute("BEGIN")  # No read in this transaction yet.
            newer = self.writer.begin_registration(rid, old.source_id, **args)
            budget = VerificationBudget(time.monotonic() + 60)
            state, _ = ledger._verify(con, self.writer._limits, budget.deadline, budget=budget)
            self.assertNotEqual(state.head, args["expected"])
            self.assertEqual(state.source_head(old.source_id), newer)
            self.assertEqual(state.registration(newer).status, ledger.SourceStatus.PENDING)
            self.assertFalse(state.is_current_valid(old))
            con.execute("COMMIT")
        finally:
            con.close()

    def test_writer_cannot_commit_while_verified_reader_holds_snapshot(self):
        rid, ref, _, _ = self.prepare()
        self.validate(ref)
        args = self.begin_args(rid, ref.source_id)
        before = self.rows()
        statements = []
        real_connect = ledger._connect

        def connect(path, *, readonly):
            con = real_connect(path, readonly=readonly)
            if not readonly:
                con.set_trace_callback(statements.append)
            return con

        with self.snapshot() as (con, state, _):
            with patch.object(ledger, "_connect", side_effect=connect):
                with self.assertRaises(ledger.LedgerBusyError):
                    self.writer.begin_registration(rid, ref.source_id, **args)
            self.assertIn("COMMIT", statements)
            self.assertIn("ROLLBACK", statements)
            self.assertEqual(con.execute("SELECT count(*) FROM events").fetchone(), (len(state.events),))
            self.assertTrue(state.is_current_valid(ref))
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.state().head, args["expected"])

    def test_closed_snapshot_has_no_later_currentness_or_two_connection_lease(self):
        rid, old, _, _ = self.prepare()
        self.validate(old)
        args = self.begin_args(rid, old.source_id)
        with self.snapshot() as (_, prior, replay):
            d = prior.registration(old).derivation.data()
            exact_old_text = replay.blobs[d["native_text_sha256"]]
            self.assertTrue(prior.is_current_valid(old))
        newer = self.writer.begin_registration(rid, old.source_id, **args)
        with self.snapshot() as (con, current, _):
            self.assertNotEqual(prior.head, current.head)
            self.assertEqual(current.source_head(old.source_id), newer)
            self.assertFalse(current.is_current_valid(old))
            # A second connection can still fetch authentic old bytes. That
            # does not confer eligibility at this new head.
            fetched = con.execute("SELECT content FROM content_blobs WHERE sha256=?",
                                  (d["native_text_sha256"],)).fetchone()[0]
            self.assertEqual(fetched, exact_old_text)
        self.assertTrue(prior.is_current_valid(old))  # Frozen snapshot, not a lease.

    def test_full_replay_reextracts_superseded_and_current_valid(self):
        rid, old, _, _ = self.prepare()
        self.validate(old)
        pending = self.begin(rid, old.source_id)
        _, current, _, _ = self.prepare(sid="synthetic:independent-source", rid=rid)
        self.validate(current)
        before = self.rows()
        with patch.object(native, "extract_captured_bytes", wraps=native.extract_captured_bytes) as bridge, \
                patch.object(native, "_worker", wraps=native._worker) as workers:
            with self.snapshot() as (_, state, _):
                self.assertFalse(state.is_current_valid(old))
                self.assertTrue(state.is_current_valid(current))
                self.assertEqual(state.registration(pending).status, ledger.SourceStatus.PENDING)
        self.assertEqual(bridge.call_count, 2)
        self.assertEqual([call.args[1] for call in workers.call_args_list], ["derive", "verify"] * 2)
        self.assertEqual(self.rows(), before)
