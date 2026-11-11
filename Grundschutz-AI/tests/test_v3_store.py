"""Windows synthetic foundation stores, tamper/rollback/crash boundaries."""
from contextlib import ExitStack, closing
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from grundschutz_ai import v3_store as store, v3_codec as c, v3_schema as schema
from grundschutz_ai import v2_ledger, v2_compat
from tests.test_v3_codec import GENESIS_RAW, GENESIS_SHA, EVENT_SHA, STAMP, samples

ACTOR = "synthetic:human"


@unittest.skipUnless(os.name == "nt", "Reviewed Windows fixed-local NTFS/ReFS profile")
class V3StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grundschutz-ai-schema3-tests-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.assertFalse(self.directory.resolve().is_relative_to(Path(__file__).resolve().parents[2]))
        self.path = self.directory / "initialized.sqlite"

    def create(self, **changes):
        return store.create_initialized_store(self.path, actor_id=ACTOR, **changes)

    def load(self, **changes):
        return store.load_initialized_store(self.path, **changes)

    def mutate(self, action):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            triggers = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'").fetchall()
            for name, _ in triggers:
                connection.execute("DROP TRIGGER " + name)
            action(connection)
            for _, sql in triggers:
                connection.execute(sql)
            connection.commit()

    def refuse(self, **changes):
        before = self.path.read_bytes()
        with self.assertRaises(store.StoreError):
            self.load(**changes)
        self.assertEqual(before, self.path.read_bytes())

    def test_fresh_create_is_one_atomic_genesis_and_all_other_tables_empty(self):
        result = self.create()
        self.assertEqual(result.head.sequence, 1)
        self.assertEqual(result.schema_fingerprint, schema.SCHEMA_FINGERPRINT)
        self.assertEqual(result.physical_profile, "sqlite-source-validation/v1")
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone(), (3,))
            for table in schema.TABLES:
                count = connection.execute("SELECT count(*) FROM " + table).fetchone()[0]
                self.assertEqual(count, 1 if table in ("events", "content_blobs", "store_metadata") else 0)
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_independent_literal_initialized_store_vector(self):
        with patch.object(store, "uuid4", side_effect=[UUID(int=0), UUID(hex="1" * 32), UUID(hex="2" * 32)]), \
             patch.object(c, "utc_now", return_value=STAMP):
            state = self.create()
        self.assertEqual(state.genesis.payload.canonical, GENESIS_RAW)
        self.assertEqual(state.genesis.envelope.data()["payload_sha256"], GENESIS_SHA)
        self.assertEqual(state.head.event_sha256, EVENT_SHA)

    def test_readonly_reopen_preserves_entire_file_and_closes_handle(self):
        expected = self.create()
        before = self.path.read_bytes()
        self.assertEqual(self.load(), expected)
        self.assertEqual(before, self.path.read_bytes())
        self.path.unlink()  # Real Windows handle-release check.
        self.assertFalse(self.path.exists())

    def test_returned_metadata_is_immutable_and_cannot_claim_source_state(self):
        state = self.create()
        with self.assertRaises(FrozenInstanceError):
            state.head = None
        with self.assertRaises(c.CodecError):
            replace(state, feature_profile="approved")
        self.assertFalse(hasattr(state, "sources"))
        self.assertFalse(hasattr(state, "approved_records"))

    def test_existing_unrelated_file_never_opened_or_overwritten(self):
        self.path.write_bytes(b"FICTITIOUS EXISTING FILE")
        with patch.object(store.sqlite3, "connect", side_effect=AssertionError("must not open existing file")):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertEqual(self.path.read_bytes(), b"FICTITIOUS EXISTING FILE")

    def test_existing_initialized_store_never_overwritten(self):
        self.create()
        before = self.path.read_bytes()
        with self.assertRaises(store.StoreError):
            self.create()
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_readonly_target_not_created(self):
        with self.assertRaises(store.StoreError):
            self.load()
        self.assertFalse(self.path.exists())

    def test_empty_or_malformed_existing_file_is_not_initialized(self):
        for raw in (b"", b"FICTITIOUS INVALID SQLITE"):
            self.path.write_bytes(raw)
            self.refuse()

    def test_unsupported_schema_version_refused(self):
        self.create()
        for version in (0, 1, 2, 4, 99):
            self.mutate(lambda con: con.execute("PRAGMA user_version=" + str(version)))
            self.refuse()

    def test_extra_table_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("CREATE TABLE future_candidate(id TEXT)"))
        self.refuse()

    def test_extra_user_index_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("CREATE INDEX unreviewed ON events(kind)"))
        self.refuse()

    def test_extra_trigger_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("CREATE TRIGGER unreviewed BEFORE INSERT ON events BEGIN SELECT 1; END"))
        self.refuse()

    def test_missing_guard_refused(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as con:
            con.execute("DROP TRIGGER events_no_update")
        self.refuse()

    def test_changed_guard_refused(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as con:
            con.execute("DROP TRIGGER events_no_update")
            con.execute("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT 1; END")
        self.refuse()

    def test_missing_table_refused(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as con:
            con.execute("DROP TABLE derivations")
        self.refuse()

    def test_wrong_metadata_feature_profile_and_codec_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE store_metadata SET feature_profile='approved'"))
        self.refuse()

    def test_wrong_metadata_event_codec_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE store_metadata SET event_codec='ledger-event/v2'"))
        self.refuse()

    def test_metadata_store_uuid_mismatch_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE store_metadata SET store_uuid=?", ("f" * 32,)))
        self.refuse()

    def test_missing_genesis_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("DELETE FROM events"))
        self.refuse()

    def test_metadata_head_broken_foreign_key_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE store_metadata SET last_sequence=2"))
        self.refuse()

    def test_unknown_envelope_codec_refused(self):
        self.create()
        def change(con):
            raw = con.execute("SELECT envelope_json FROM events").fetchone()[0]
            data = c.canonical_loads(raw)
            data["codec"] = "ledger-event/v99"
            data.pop("event_sha256")
            data["event_sha256"] = c.fingerprint("ledger-event/v3", data)
            con.execute("UPDATE events SET envelope_json=?,event_sha256=?",
                        (c.canonical_dumps(data), data["event_sha256"]))
            con.execute("UPDATE store_metadata SET last_event_hash=?", (data["event_sha256"],))
        self.mutate(change)
        self.refuse()

    def test_unknown_payload_version_refused(self):
        self.create()
        self.coherent_genesis_change(lambda data: data.update(payload_codec="store-init/v99"))
        self.refuse()

    def coherent_genesis_change(self, mutate):
        def action(con):
            row = con.execute("SELECT * FROM events").fetchone()
            envelope = c.canonical_loads(row[-1])
            raw = con.execute("SELECT content FROM content_blobs").fetchone()[0]
            data = c.canonical_loads(raw)
            mutate(data)
            raw = c.canonical_dumps(data)
            key = c.sha256(raw)
            con.execute("DELETE FROM content_blobs")
            con.execute("INSERT INTO content_blobs VALUES (?,?,?)", (key, len(raw), raw))
            envelope["payload_sha256"] = key
            envelope["payload_codec"] = data["payload_codec"]
            envelope.pop("event_sha256")
            envelope["event_sha256"] = c.fingerprint("ledger-event/v3", envelope)
            con.execute("DELETE FROM events")
            con.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        tuple(envelope[key] for key in store._ROW_FIELDS) + (c.canonical_dumps(envelope),))
            con.execute("UPDATE store_metadata SET last_event_hash=?", (envelope["event_sha256"],))
        self.mutate(action)

    def test_coherently_rehashed_false_genesis_feature_refused(self):
        self.create()
        self.coherent_genesis_change(lambda data: data.update(feature_profile="approved"))
        self.refuse()

    def test_payload_bytes_hash_mismatch_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE content_blobs SET content=CAST(substr(content,2)||x'20' AS BLOB)"))
        self.refuse()

    def test_event_sequence_and_previous_hash_corruption_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE events SET sequence=2,previous_event_sha256=?", ("0" * 64,)))
        self.refuse()

    def test_rewritten_event_hash_refused(self):
        self.create()
        self.mutate(lambda con: con.execute("UPDATE events SET event_sha256=?", ("0" * 64,)))
        self.refuse()

    def test_unknown_source_table_data_never_becomes_trusted_projection(self):
        self.create()
        self.mutate(lambda con: con.execute("INSERT INTO registries VALUES (?,?,?,?)",
                                           ("3" * 32, "docx", "4" * 32, 1)))
        self.refuse()

    def test_recognized_source_validated_event_still_inapplicable(self):
        self.create()
        p = c.Payload(c.canonical_dumps(samples()[8][1]))
        with closing(sqlite3.connect(self.path)) as con:
            previous = con.execute("SELECT last_event_hash FROM store_metadata").fetchone()[0]
            uid = con.execute("SELECT store_uuid FROM store_metadata").fetchone()[0]
        e = c.make_envelope(p, store_uuid=uid, sequence=2, previous=previous, event_id="a" * 32,
                            transaction_id="b" * 32, occurred_at=STAMP, actor_id=None)
        def action(con):
            data = e.data()
            con.execute("INSERT INTO content_blobs VALUES (?,?,?)",
                        (data["payload_sha256"], len(p.canonical), p.canonical))
            con.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        tuple(data[key] for key in store._ROW_FIELDS) + (e.canonical,))
            con.execute("UPDATE store_metadata SET last_sequence=2,last_event_hash=?", (data["event_sha256"],))
        self.mutate(action)
        self.refuse()

    def test_all_source_and_later_public_operations_absent(self):
        for name in ("append", "append_event", "register_implementation", "register_handler",
                     "begin_registration", "capture_source", "fail_source", "validate_source",
                     "source_validated", "activate_policy", "stage", "triage", "approve", "migrate", "export"):
            self.assertFalse(hasattr(store, name), name)

    def test_private_rw_connection_cannot_open_published_target(self):
        self.create()
        with self.assertRaises(store.StoreError):
            store._connect(self.path, readonly=False)

    def test_metadata_limit_exact_boundary_and_failure_leave_no_target(self):
        state = self.create()
        exact = len(state.genesis.payload.canonical) + len(state.genesis.envelope.canonical)
        self.assertEqual(self.load(limits=store.StoreLimits(max_metadata_bytes=exact)), state)
        self.refuse(limits=store.StoreLimits(max_metadata_bytes=exact-1))
        self.path.unlink()
        with self.assertRaises(store.StoreError):
            self.create(limits=store.StoreLimits(max_metadata_bytes=exact-1))
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_database_file_and_page_budget_boundaries(self):
        state = self.create()
        size = self.path.stat().st_size
        self.assertEqual(self.load(limits=store.StoreLimits(max_database_bytes=size)), state)
        self.refuse(limits=store.StoreLimits(max_database_bytes=size-1))
        self.path.unlink()
        with self.assertRaises(store.StoreError):
            self.create(limits=store.StoreLimits(max_database_bytes=1))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_one_event_and_zero_original_data_fit_tightened_limits(self):
        state = self.create(limits=store.StoreLimits(max_events=1, max_original_bytes=1))
        self.assertEqual(self.load(limits=store.StoreLimits(max_events=1, max_original_bytes=1)), state)

    def test_limits_cannot_relax_or_accept_bool(self):
        for name in store.StoreLimits.__dataclass_fields__:
            default = getattr(store.StoreLimits(), name)
            for value in (default+1, 0, True):
                with self.subTest(name=name, value=value), self.assertRaises(c.CodecError):
                    store.StoreLimits(**{name: value})
        with self.assertRaises(store.StoreError):
            self.create(limits=object())

    def test_replay_deadline_refuses_without_writes(self):
        self.create()
        with patch.object(store.time, "monotonic", side_effect=iter([0] + [2] * 100)):
            self.refuse(limits=store.StoreLimits(max_replay_seconds=1))

    def test_initialization_deadline_does_not_publish_target(self):
        with patch.object(store.time, "monotonic", side_effect=iter([0] + [2] * 100)):
            with self.assertRaises(store.StoreError):
                self.create(limits=store.StoreLimits(max_replay_seconds=1))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_wrong_runtime_refused(self):
        with patch.object(store.sys, "version_info", (3, 12, 7)):
            with self.assertRaises(store.StoreError):
                self.create()
        with patch.object(store.sqlite3, "sqlite_version", "3.45.4"):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertFalse(self.path.exists())

    def test_wrong_filesystem_and_untrusted_path_forms_refused(self):
        with patch.object(store._paths, "_fixed_local_volume", side_effect=store._paths.UnsafePathError("Unsupported")):
            with self.assertRaises(store.StoreError):
                self.create()
        for path in (":memory:", "relative.sqlite", "file:C:/unknown.sqlite", "\\\\server\\share\\file.sqlite"):
            with self.subTest(path=path), self.assertRaises(store.StoreError):
                store.create_initialized_store(path, actor_id=ACTOR)
        self.assertFalse(self.path.exists())

    def test_repository_and_reserved_staging_paths_refused(self):
        with self.assertRaises(store.StoreError):
            store.create_initialized_store(Path(__file__).resolve().parent / "must-not-exist.sqlite", actor_id=ACTOR)
        with self.assertRaises(store.StoreError):
            store.create_initialized_store(self.directory / (store._STAGING_PREFIX + "chosen.sqlite"), actor_id=ACTOR)

    def test_reserved_staging_prefix_is_case_insensitive_on_windows(self):
        for prefix in (store._STAGING_PREFIX, store._STAGING_PREFIX.upper()):
            with self.subTest(prefix=prefix), self.assertRaises(store.StoreError):
                store.create_initialized_store(self.directory / (prefix + "chosen.sqlite"), actor_id=ACTOR)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_sqlite_sidecars_refused_and_not_repaired(self):
        self.create()
        before = self.path.read_bytes()
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = Path(str(self.path)+suffix)
            sidecar.write_bytes(b"FICTITIOUS UNTRUSTED SIDECAR")
            self.refuse()
            self.assertEqual(sidecar.read_bytes(), b"FICTITIOUS UNTRUSTED SIDECAR")
            sidecar.unlink()
        self.assertEqual(before, self.path.read_bytes())

    def test_hard_linked_target_refused(self):
        self.create()
        link = self.directory / "hardlink.sqlite"
        os.link(self.path, link)
        self.refuse()

    def test_rollback_after_partial_ddl_does_not_publish_target(self):
        with patch.object(schema, "STATEMENTS", (*schema.STATEMENTS[:2], "INVALID SQL")):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_rollback_after_insert_failure_does_not_publish_target(self):
        original = store._connect
        trace = []
        class Fault:
            def __init__(self, connection):
                self.connection = connection
            def __getattr__(self, name):
                return getattr(self.connection, name)
            def execute(self, sql, *args):
                trace.append(sql)
                if sql.startswith("INSERT INTO events"):
                    raise sqlite3.IntegrityError("Synthetic insertion failure")
                return self.connection.execute(sql, *args)
        def connect(path, *, readonly):
            conn = original(path, readonly=readonly)
            return conn if readonly else Fault(conn)
        with patch.object(store, "_connect", connect):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertIn("ROLLBACK", trace)
        self.assertNotIn("COMMIT", trace)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_postcommit_verification_failure_does_not_publish_target(self):
        with patch.object(store, "_read", side_effect=store.CorruptStoreError("Synthetic verification failure")):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_atomic_publication_never_overwrites_a_racing_existing_file(self):
        rename = store.os.rename
        def occupy(source, target):
            target.write_bytes(b"FICTITIOUS RACING EXISTING FILE")
            return rename(source, target)
        with patch.object(store.os, "rename", occupy):
            with self.assertRaises(store.StoreError):
                self.create()
        self.assertEqual(self.path.read_bytes(), b"FICTITIOUS RACING EXISTING FILE")
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_sqlite_discipline_and_readonly_trace(self):
        original = store._connect
        modes, statements = [], []
        def connect(path, *, readonly):
            con = original(path, readonly=readonly)
            modes.append((path.name, readonly))
            self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone(), (1,))
            self.assertEqual(con.execute("PRAGMA trusted_schema").fetchone(), (0,))
            self.assertEqual(con.execute("PRAGMA journal_mode").fetchone(), ("delete",))
            if readonly:
                self.assertEqual(con.execute("PRAGMA query_only").fetchone(), (1,))
                con.set_trace_callback(statements.append)
            else:
                self.assertTrue(path.name.startswith(store._STAGING_PREFIX))
                self.assertEqual(con.execute("PRAGMA synchronous").fetchone(), (2,))
            return con
        with patch.object(store, "_connect", connect):
            self.create()
            self.load()
        self.assertTrue(modes)
        self.assertFalse(any(s.lstrip().upper().startswith(("INSERT", "DELETE", "UPDATE", "DROP", "ALTER", "CREATE"))
                             for s in statements))

    def test_v2_mutual_refusal_and_unchanged_historical_export(self):
        self.create()
        before = self.path.read_bytes()
        for load, error in ((v2_ledger.load_ledger, v2_ledger.LedgerError),
                            (v2_ledger.SourceLedger.open, v2_ledger.LedgerError),
                            (v2_compat.load_historical_ledger, v2_compat.HistoricalLedgerError)):
            with self.subTest(load=load), self.assertRaises(error):
                load(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        raw = (Path(__file__).parent / "fixtures/a0-ledger.sql").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "a89ea981a57ffbe1328ed8aee7ff9e916099ee2196aa4c055d7d81af133b8d61")
        with closing(sqlite3.connect(self.path)) as con:
            con.executescript(raw.decode("utf-8"))
        self.assertEqual(v2_compat.load_historical_ledger(self.path).head.sequence, 13)
        self.refuse()
        before = self.path.read_bytes()
        with self.assertRaises(store.StoreError):
            self.create()
        self.assertEqual(self.path.read_bytes(), before)

    def test_no_native_model_domain_or_legacy_storage_side_effects(self):
        targets = ("socket.create_connection", "urllib.request.urlopen",
                   "grundschutz_ai.docx_ingestion.ingest_docx", "grundschutz_ai.xlsx_ingestion.ingest_xlsx",
                   "grundschutz_ai.domain.Evidence", "grundschutz_ai.inventory.Inventory.add",
                   "grundschutz_ai.storage.InventoryStore")
        with ExitStack() as stack:
            spies = [stack.enter_context(patch(name, side_effect=AssertionError("side effect"))) for name in targets]
            self.create()
            self.load()
            for spy in spies:
                spy.assert_not_called()

    def crash(self, phase, expected):
        script = r"""
import os,sys
from pathlib import Path
from grundschutz_ai import v3_store as s
path, phase = Path(sys.argv[1]), sys.argv[2]
if phase == 'published':
    original = s.os.rename
    def rename(a,b):
        original(a,b)
        os._exit(73)
    s.os.rename = rename
else:
    original = s._connect
    class Stop:
        def __init__(self,c): self.c=c
        def __getattr__(self,n): return getattr(self.c,n)
        def execute(self,sql,*args):
            if sql == 'COMMIT':
                if phase == 'before_commit': os._exit(71)
                result=self.c.execute(sql,*args)
                os._exit(72)
            return self.c.execute(sql,*args)
    def connect(path,*,readonly):
        con=original(path,readonly=readonly)
        return con if readonly else Stop(con)
    s._connect=connect
s.create_initialized_store(path,actor_id='synthetic:crash-test')
"""
        result = subprocess.run([sys.executable, "-c", script, str(self.path), phase],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stderr.decode("utf-8", errors="replace"))

    def test_abrupt_exit_before_sql_commit_has_no_trusted_target(self):
        self.crash("before_commit", 71)
        self.assertFalse(self.path.exists())
        stages = [p for p in self.directory.glob(store._STAGING_PREFIX + "*.sqlite")]
        self.assertTrue(stages)
        for stage in stages:
            with self.assertRaises(store.StoreError):
                store.load_initialized_store(stage)

    def test_abrupt_exit_after_sql_commit_before_publication_stays_private(self):
        self.crash("after_commit", 72)
        self.assertFalse(self.path.exists())
        stages = [p for p in self.directory.glob(store._STAGING_PREFIX + "*.sqlite")]
        self.assertEqual(len(stages), 1)
        with self.assertRaises(store.StoreError):
            store.load_initialized_store(stages[0])

    def test_abrupt_exit_after_publication_reopens_complete_genesis(self):
        self.crash("published", 73)
        state = self.load()
        self.assertEqual(state.head.sequence, 1)
        self.assertEqual(list(self.directory.iterdir()), [self.path])
