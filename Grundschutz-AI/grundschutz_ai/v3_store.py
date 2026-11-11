"""Inert schema-3 initialized stores: fresh create and verified read-only load.

Only genesis is applicable. All other recognized v3 contracts are disabled.
Every connection is closed inside its operation; no writable handle is public.
"""
from dataclasses import dataclass, fields
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from uuid import uuid4

from . import v3_codec as codec, v3_schema as schema
from . import v2_a0 as _paths

__all__ = ("StoreError", "UnsupportedStoreError", "CorruptStoreError", "StoreLimitError",
           "StoreLimits", "InitializedStoreMetadata", "create_initialized_store",
           "load_initialized_store")

_STAGING_PREFIX = ".grundschutz-schema3-init-"
_SHARED_ARTIFACTS = (
    ("v2_codec.py", "577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"),
    ("v2_a0.py", "a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd"),
    ("v2_schema.py", "9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"),
)
_ROW_FIELDS = """sequence event_id transaction_id transaction_index transaction_count kind
    payload_codec payload_sha256 previous_event_sha256 event_sha256 occurred_at actor_id""".split()


class StoreError(RuntimeError):
    """Static diagnostic; never an incomplete trusted state or source text."""


class UnsupportedStoreError(StoreError):
    pass


class CorruptStoreError(StoreError):
    pass


class StoreLimitError(StoreError):
    pass


@dataclass(frozen=True, slots=True)
class StoreLimits:
    max_database_bytes: int = 256 * 1024 * 1024
    max_events: int = 10_000
    max_metadata_bytes: int = 128 * 1024 * 1024
    max_original_bytes: int = 32 * 1024 * 1024
    max_replay_seconds: int = 60

    def __post_init__(self):
        for field in fields(self):
            codec.require(type(getattr(self, field.name)) is int and
                          1 <= getattr(self, field.name) <= field.default)


DEFAULT_LIMITS = StoreLimits()


@dataclass(frozen=True, slots=True)
class StoreHead:
    store_uuid: str
    sequence: int
    event_sha256: str

    def __post_init__(self):
        codec.identity(self.store_uuid)
        codec.require(type(self.sequence) is int and self.sequence == 1)
        codec.digest(self.event_sha256)


@dataclass(frozen=True, slots=True)
class InitializedStoreMetadata:
    head: StoreHead
    genesis: codec.Event
    schema_fingerprint: str = schema.SCHEMA_FINGERPRINT
    physical_profile: str = codec.PHYSICAL_PROFILE
    schema_version: int = 3
    event_codec: str = codec.EVENT_CODEC
    serialization_version: str = codec.SERIALIZATION_VERSION
    feature_profile: str = codec.FEATURE_PROFILE

    def __post_init__(self):
        codec.require(type(self.head) is StoreHead and type(self.genesis) is codec.Event)
        codec.require(self.schema_fingerprint == schema.SCHEMA_FINGERPRINT)
        codec.require(self.physical_profile == codec.PHYSICAL_PROFILE and
                      type(self.schema_version) is int and self.schema_version == 3)
        codec.require(self.event_codec == codec.EVENT_CODEC and
                      self.serialization_version == codec.SERIALIZATION_VERSION and
                      self.feature_profile == codec.FEATURE_PROFILE)
        e = self.genesis.envelope.data()
        codec.require(self.genesis.payload.kind is codec.EventKind.INITIALIZED and
                      (e["store_uuid"], e["sequence"], e["event_sha256"]) ==
                      (self.head.store_uuid, self.head.sequence, self.head.event_sha256))


def _deadline(deadline):
    if time.monotonic() > deadline:
        raise StoreLimitError("Initialized-store operation exceeded deadline")


def _trust(limits):
    if type(limits) is not StoreLimits:
        raise StoreError("Exact typed store limits required")
    if (os.name != "nt" or sys.version_info[:3] != (3, 12, 6) or
            sqlite3.sqlite_version != "3.45.3"):
        raise UnsupportedStoreError("Unsupported initialized-store runtime profile")
    try:
        base = Path(__file__).resolve().parent
        for filename, expected in _SHARED_ARTIFACTS:
            if codec.sha256((base / filename).read_bytes()) != expected:
                raise UnsupportedStoreError("Frozen shared dependency differs")
    except OSError as exc:
        raise UnsupportedStoreError("Frozen shared dependency unavailable") from exc
    if schema.schema_fingerprint() != schema.SCHEMA_FINGERPRINT:
        raise UnsupportedStoreError("Schema-3 application contract differs")


def _checked_path(path, limits, *, internal=False):
    try:
        checked = _paths._path(path, limits)
        if not internal and checked.name.casefold().startswith(_STAGING_PREFIX):
            raise UnsupportedStoreError("Private initialization files are not published stores")
        if any(Path(str(checked) + suffix).exists() for suffix in ("-journal", "-wal", "-shm")):
            raise UnsupportedStoreError("SQLite sidecars require separately reviewed recovery")
        return checked
    except _paths.LedgerError as exc:
        raise UnsupportedStoreError("Unsupported initialized-store filesystem path") from exc


def _connect(path, *, readonly):
    if not readonly and not path.name.casefold().startswith(_STAGING_PREFIX):
        raise UnsupportedStoreError("Writable connections are private initialization only")
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
                                 uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        if readonly:
            connection.execute("PRAGMA query_only=ON")
        else:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
        if (connection.execute("PRAGMA foreign_keys").fetchone() != (1,) or
                connection.execute("PRAGMA trusted_schema").fetchone() != (0,) or
                connection.execute("PRAGMA journal_mode").fetchone() != ("delete",) or
                (readonly and connection.execute("PRAGMA query_only").fetchone() != (1,)) or
                (not readonly and connection.execute("PRAGMA synchronous").fetchone() != (2,))):
            raise UnsupportedStoreError("Unsupported SQLite connection discipline")
        return connection
    except BaseException:
        connection.close()
        raise


def _check_schema(connection, deadline):
    _deadline(deadline)
    if connection.execute("PRAGMA user_version").fetchone() != (3,):
        raise UnsupportedStoreError("Only schema-3 initialized stores are supported")
    if connection.execute("PRAGMA encoding").fetchone() != ("UTF-8",):
        raise UnsupportedStoreError("Unsupported SQLite text encoding")
    expected = schema.expected_objects()
    count, total = connection.execute(
        "SELECT count(*),coalesce(sum(length(CAST(sql AS BLOB))),0) FROM sqlite_master").fetchone()
    max_sql = sum(len(sql.encode("utf-8")) for _, sql in expected.values() if sql is not None)
    if count != len(expected) or total > max_sql:
        raise CorruptStoreError("Unexpected or oversized schema objects")
    actual = {name: (kind, sql) for name, kind, sql in
              connection.execute("SELECT name,type,sql FROM sqlite_master")}
    if actual != expected:
        raise CorruptStoreError("Exact schema-3 DDL differs")
    indexes = []
    for table in schema.TABLES:
        _deadline(deadline)
        for _, name, unique, origin, partial in connection.execute("PRAGMA index_list(" + table + ")"):
            rows = connection.execute("PRAGMA index_xinfo(" + name + ")").fetchall()
            keys = [row for row in rows if row[5]]
            if [row for row in rows if not row[5]] != [(len(keys), -1, None, 0, "BINARY", 0)]:
                raise CorruptStoreError("Unexpected auxiliary index columns")
            indexes.append({"table": table, "name": name, "unique": unique,
                            "origin": origin, "partial": partial, "columns": [r[2] for r in keys],
                            "collations": [r[4] for r in keys], "descending": [r[3] for r in keys]})
    if sorted(indexes, key=lambda item: item["name"]) != schema.expected_indexes():
        raise CorruptStoreError("Schema-3 index contract differs")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise CorruptStoreError("Schema-3 foreign-key violation")
    integrity = connection.execute("PRAGMA integrity_check")
    if integrity.fetchone() != ("ok",) or integrity.fetchone() is not None:
        raise CorruptStoreError("Schema-3 integrity failure")


def _verify(connection, limits, deadline):
    _deadline(deadline)
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        _check_schema(connection, deadline)
        events = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        if events > limits.max_events:
            raise StoreLimitError("Event budget exceeded")
        if events != 1:
            raise UnsupportedStoreError("Only a single initialization event is applicable")
        for table in schema.TABLES:
            if table not in ("store_metadata", "events", "content_blobs"):
                _deadline(deadline)
                if connection.execute("SELECT count(*) FROM " + table).fetchone() != (0,):
                    raise UnsupportedStoreError("Source and later capabilities remain disabled")
        if (connection.execute("SELECT count(*) FROM store_metadata").fetchone() != (1,) or
                connection.execute("SELECT count(*) FROM content_blobs").fetchone() != (1,)):
            raise CorruptStoreError("Initialization projections or BLOB set differ")
        size, content_size = connection.execute(
            "SELECT byte_length,length(content) FROM content_blobs").fetchone()
        envelope_size = connection.execute("SELECT length(envelope_json) FROM events").fetchone()[0]
        if (size != content_size or content_size > codec.DEFAULT_LIMITS.max_bytes or
                envelope_size > codec.DEFAULT_LIMITS.max_bytes):
            raise CorruptStoreError("Initialization BLOB length differs")
        if content_size + envelope_size > limits.max_metadata_bytes:
            raise StoreLimitError("Initialization metadata budget exceeded")
        pages = connection.execute("PRAGMA page_count").fetchone()[0]
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        if pages * page_size > limits.max_database_bytes:
            raise StoreLimitError("Database page budget exceeded")
        key, _, raw = connection.execute("SELECT * FROM content_blobs").fetchone()
        if codec.sha256(raw) != key:
            raise CorruptStoreError("Initialization payload BLOB digest differs")
        row = connection.execute("SELECT * FROM events").fetchone()
        envelope, payload = codec.Envelope(row[-1]), codec.Payload(raw)
        event = codec.Event(envelope, payload)
        e = envelope.data()
        if row != tuple(e[name] for name in _ROW_FIELDS) + (envelope.canonical,):
            raise CorruptStoreError("Initialization envelope mirror differs")
        if payload.kind is not codec.EventKind.INITIALIZED or e["sequence"] != 1:
            raise UnsupportedStoreError("Non-genesis events are not applicable")
        metadata = connection.execute("SELECT * FROM store_metadata").fetchone()
        expected = (1, e["store_uuid"], 3, codec.EVENT_CODEC, codec.SERIALIZATION_VERSION,
                    codec.FEATURE_PROFILE, 1, e["event_sha256"])
        if metadata != expected or e["payload_sha256"] != key:
            raise CorruptStoreError("Initialization metadata/head differs")
        _deadline(deadline)
        return InitializedStoreMetadata(StoreHead(e["store_uuid"], 1, e["event_sha256"]), event)
    finally:
        connection.set_progress_handler(None, 0)


def _read(path, limits, deadline, *, internal=False):
    checked = _checked_path(path, limits, internal=internal)
    connection = _connect(checked, readonly=True)
    try:
        connection.execute("BEGIN")
        state = _verify(connection, limits, deadline)
        connection.execute("COMMIT")
        return state
    finally:
        connection.close()


def load_initialized_store(path: str | Path, *, limits: StoreLimits = DEFAULT_LIMITS) -> InitializedStoreMetadata:
    """Read-only, complete genesis verification. All source operations disabled."""
    deadline = time.monotonic() + limits.max_replay_seconds if type(limits) is StoreLimits else 0
    _trust(limits)
    try:
        return _read(path, limits, deadline)
    except (sqlite3.Error, codec.CodecError, OSError) as exc:
        raise CorruptStoreError("Initialized store refused; no trusted result") from exc


def _remove_owned_stage(path, owned_identity):
    # Never remove a caller target, scan directories or recover other sessions.
    try:
        current = path.lstat()
        if (path.name.casefold().startswith(_STAGING_PREFIX) and not path.is_symlink() and
                (current.st_dev, current.st_ino) == owned_identity):
            path.unlink()
            journal = Path(str(path) + "-journal")
            if journal.exists() and not journal.is_symlink():
                journal.unlink()
    except OSError:
        # A private orphan remains non-loadable; never report it as published.
        pass


def create_initialized_store(path: str | Path, *, actor_id: str,
                             limits: StoreLimits = DEFAULT_LIMITS) -> InitializedStoreMetadata:
    """Publish a new verified genesis DB atomically; never overwrite/upgrade.

    Successful return has no open handle. No public writer or append exists.
    Private files are not loadable through the public API, even after a crash.
    """
    deadline = time.monotonic() + limits.max_replay_seconds if type(limits) is StoreLimits else 0
    _trust(limits)
    try:
        codec.text(actor_id)
        target = _checked_path(path, limits)
        if target.exists():
            raise UnsupportedStoreError("Initialization requires an unused target")
        fd, name = tempfile.mkstemp(prefix=_STAGING_PREFIX, suffix=".sqlite", dir=target.parent)
        os.close(fd)
        stage, connection = Path(name).resolve(), None
        stat = stage.stat()
        owned = (stat.st_dev, stat.st_ino)
        try:
            _checked_path(stage, limits, internal=True)
            connection = _connect(stage, readonly=False)
            connection.execute("BEGIN IMMEDIATE")
            for statement in schema.STATEMENTS:
                _deadline(deadline)
                connection.execute(statement)
            connection.execute("PRAGMA user_version=3")
            store_id = uuid4().hex
            payload = codec.make_payload(codec.EventKind.INITIALIZED, store_uuid=store_id,
                schema_version=3, serialization_version=codec.SERIALIZATION_VERSION,
                feature_profile=codec.FEATURE_PROFILE)
            envelope = codec.make_envelope(payload, store_uuid=store_id, sequence=1, previous=None,
                event_id=uuid4().hex, transaction_id=uuid4().hex,
                occurred_at=codec.utc_now(), actor_id=actor_id)
            e = envelope.data()
            connection.execute("INSERT INTO content_blobs VALUES (?,?,?)",
                               (e["payload_sha256"], len(payload.canonical), payload.canonical))
            connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                               tuple(e[name] for name in _ROW_FIELDS) + (envelope.canonical,))
            connection.execute("INSERT INTO store_metadata VALUES (1,?,?,?,?,?,?,?)",
                (store_id, 3, codec.EVENT_CODEC, codec.SERIALIZATION_VERSION,
                 codec.FEATURE_PROFILE, 1, e["event_sha256"]))
            state = _verify(connection, limits, deadline)
            connection.execute("COMMIT")
            connection.close()
            connection = None
            if _read(stage, limits, deadline, internal=True) != state:
                raise CorruptStoreError("Post-commit initialization verification differs")
            _checked_path(stage, limits, internal=True)
            target = _checked_path(target, limits)
            if target.exists():
                raise UnsupportedStoreError("Initialization target became occupied")
            _deadline(deadline)
            # Reviewed Windows-only profile: rename fails if the target exists.
            # Source/target are checked absolute paths in the same local parent.
            os.rename(stage, target)
            stage = None
            return state
        finally:
            if connection is not None:
                try:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                finally:
                    connection.close()
            if stage is not None:
                _remove_owned_stage(stage, owned)
    except (sqlite3.Error, codec.CodecError, OSError) as exc:
        raise StoreError("Initialization refused; no target published") from exc
