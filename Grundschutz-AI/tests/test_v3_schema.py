"""Actual SQLite schema, constraints, guard and fixed-identity regressions."""
from contextlib import closing
from dataclasses import FrozenInstanceError
import sqlite3
import unittest

from grundschutz_ai import v3_schema as s

FINGERPRINT = "75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c"
TABLE_NAMES = frozenset(("store_metadata", "content_blobs", "implementation_specs",
    "reader_handler_specs", "policy_specs", "registries", "policy_activations",
    "logical_sources", "registrations", "source_captures", "derivations",
    "source_terminals", "source_heads", "registry_state", "events"))


class V3SchemaTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        for sql in s.STATEMENTS:
            self.connection.execute(sql)

    def test_exact_fifteen_tables_and_twenty_four_guards(self):
        self.assertEqual(set(s.TABLES), TABLE_NAMES)
        self.assertEqual(len(s.TRIGGERS), 24)
        self.assertEqual(len(s.STATEMENTS), 39)
        self.assertNotIn("registration_observations", s.TABLES)
        self.assertFalse(any("candidate" in n or "queue" in n or "inventory" in n for n in s.TABLES))

    def test_literal_schema_fingerprint_independently_dotnet_verified(self):
        self.assertEqual(s.SCHEMA_FINGERPRINT, FINGERPRINT)
        self.assertEqual(s.schema_fingerprint(), FINGERPRINT)

    def test_exact_sqlite_master_objects_including_generated_indexes(self):
        actual = {n: (k, sql) for n, k, sql in self.connection.execute("SELECT name,type,sql FROM sqlite_master")}
        self.assertEqual(actual, s.expected_objects())
        self.assertEqual(len(actual), 75)
        self.assertEqual(len(s.INDEX_CONTRACT), 36)

    def test_all_tables_are_strict_rowid_tables(self):
        tables = {row[1]: row for row in self.connection.execute("PRAGMA table_list")}
        for name in TABLE_NAMES:
            with self.subTest(table=name):
                self.assertEqual(tables[name][-2:], (0, 1))

    def test_exact_index_names_origins_columns_order_and_collation(self):
        actual = []
        for table in TABLE_NAMES:
            for _, name, unique, origin, partial in self.connection.execute("PRAGMA index_list(" + table + ")"):
                rows = self.connection.execute("PRAGMA index_xinfo(" + name + ")").fetchall()
                keys = [r for r in rows if r[5]]
                actual.append(dict(table=table, name=name, unique=unique, origin=origin, partial=partial,
                                   columns=[r[2] for r in keys], collations=[r[4] for r in keys],
                                   descending=[r[3] for r in keys]))
        self.assertEqual(sorted(actual, key=lambda i: i["name"]), s.expected_indexes())

    def test_sql_maps_are_immutable_and_outputs_detached(self):
        for mapping in (s.TABLES, s.TRIGGERS):
            with self.assertRaises(TypeError):
                mapping["evil"] = "CREATE TABLE evil(x)"
        data = s.expected_objects()
        data.clear()
        self.assertEqual(len(s.expected_objects()), 75)

    def test_all_twenty_four_guards_abort_actual_row_mutation(self):
        # SQL-only hostile dummy rows: no production source/event API is enabled.
        self.connection.execute("PRAGMA ignore_check_constraints=ON")
        for table in TABLE_NAMES - s.MUTABLE:
            info = self.connection.execute("PRAGMA table_info(" + table + ")").fetchall()
            values = [1 if row[2] == "INTEGER" else b"{}" if row[2] == "BLOB" else "synthetic"
                      for row in info]
            self.connection.execute("INSERT INTO " + table + " VALUES (" + ",".join("?" for _ in values) + ")", values)
            for sql in ("UPDATE " + table + " SET " + info[0][1] + "=" + info[0][1], "DELETE FROM " + table):
                with self.subTest(table=table, sql=sql), self.assertRaisesRegex(sqlite3.IntegrityError, "immutable schema-3 history"):
                    self.connection.execute(sql)

    def test_literal_events_guard_sql(self):
        self.assertEqual(s.TRIGGERS["events_no_update"],
            "CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END")

    def test_content_blob_length_and_hash_format_checks(self):
        for digest, length, raw in (("x" * 64, 1, b"x"), ("a" * 64, 2, b"x"), ("a" * 64, -1, b"")):
            with self.subTest(digest=digest, length=length), self.assertRaises(sqlite3.IntegrityError):
                self.connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", (digest, length, raw))

    def test_strict_types_are_enforced_by_sql(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", ("a" * 64, "not-an-integer", b"x"))

    def test_all_foreign_keys_are_well_formed(self):
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
        total = sum(len(self.connection.execute("PRAGMA foreign_key_list(" + table + ")").fetchall())
                    for table in TABLE_NAMES)
        self.assertGreater(total, 40)

    def test_broken_foreign_keys_rejected_at_commit(self):
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("INSERT INTO implementation_specs VALUES (?,?)", ("a" * 64, "b" * 64))
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.commit()
        self.connection.rollback()

    def test_terminal_check_requires_exclusive_valid_or_failed_shape(self):
        sql = "INSERT INTO source_terminals VALUES (?,?,?,?,?,?)"
        for state, derivation, phase, issues in (
                ("approved", None, None, b"[]"), ("valid", None, None, b"[]"),
                ("valid", "a" * 64, "validation", b"[]"), ("valid", "a" * 64, None, b'["invalid_source"]'),
                ("failed", "a" * 64, "validation", b'["invalid_source"]'),
                ("failed", None, None, b'["invalid_source"]'), ("failed", None, "validation", b"[]")):
            with self.subTest(state=state, phase=phase), self.assertRaises(sqlite3.IntegrityError):
                self.connection.execute(sql, ("1" * 32, 1, state, derivation, phase, issues))

    def test_source_capture_unique_per_registration(self):
        row = ("1" * 32, 1, "a" * 64, 27)
        self.connection.execute("INSERT INTO source_captures VALUES (?,?,?,?)", row)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO source_captures VALUES (?,?,?,?)",
                                    ("1" * 32, 2, "b" * 64, 27))

    def test_physical_profile_is_bound_to_schema_not_a_mutable_database_flag(self):
        self.assertEqual(s.fingerprint_preimage()["physical_profile"], "sqlite-source-validation/v1")
        self.assertEqual(s.fingerprint_preimage()["encoding"], "UTF-8")
        self.assertEqual(s.fingerprint_preimage()["user_version"], 3)
        columns = [r[1] for r in self.connection.execute("PRAGMA table_info(store_metadata)")]
        self.assertNotIn("physical_profile", columns)
