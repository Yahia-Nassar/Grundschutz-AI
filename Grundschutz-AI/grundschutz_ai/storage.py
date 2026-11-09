"""Local, synthetic-only SQLite event store; replay validates all domain actions.

The database path is trusted operator configuration. Source IDs/text are SQL
data only and never paths. This is not authenticated or tamper-proof storage.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3

from .domain import (
    Evidence, ITApplication, ITSystem, Location, Predicate, Provenance, Record,
    RECORD_TYPES, Relationship, ReviewRecord, ReviewState, SourceLocator,
    require_digest, require_text,
)
from .inventory import Inventory
from .support import SUPPORT_POLICY
from .validation import strict_json_loads


SCHEMA_VERSION = 1
EVENT_FORMAT_VERSION = 1
_TYPES = {kind.__name__: kind for kind in (*RECORD_TYPES, ReviewRecord)}
_SCHEMA = (
    """CREATE TABLE metadata (
        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
        schema_version INTEGER NOT NULL, event_format INTEGER NOT NULL,
        support_policy TEXT NOT NULL, last_sequence INTEGER NOT NULL CHECK(last_sequence >= 0)
    )""",
    """CREATE TABLE sources (
        source_id TEXT NOT NULL, sha256 TEXT NOT NULL,
        content BLOB NOT NULL CHECK(typeof(content) = 'blob'),
        PRIMARY KEY(source_id, sha256)
    )""",
    """CREATE TABLE events (
        sequence INTEGER PRIMARY KEY CHECK(sequence > 0),
        operation TEXT NOT NULL CHECK(operation IN ('add', 'revise', 'review')),
        payload TEXT NOT NULL,
        source_id TEXT, source_sha256 TEXT,
        CHECK((source_id IS NULL) = (source_sha256 IS NULL)),
        FOREIGN KEY(source_id, source_sha256) REFERENCES sources(source_id, sha256)
    )""",
    """CREATE TRIGGER sources_no_update BEFORE UPDATE ON sources
        BEGIN SELECT RAISE(ABORT, 'source versions are immutable'); END""",
    """CREATE TRIGGER sources_no_delete BEFORE DELETE ON sources
        BEGIN SELECT RAISE(ABORT, 'source versions are immutable'); END""",
    """CREATE TRIGGER events_no_update BEFORE UPDATE ON events
        BEGIN SELECT RAISE(ABORT, 'events are append-only'); END""",
    """CREATE TRIGGER events_no_delete BEFORE DELETE ON events
        BEGIN SELECT RAISE(ABORT, 'events are append-only'); END""",
)


class StorageError(RuntimeError):
    """Storage operation failed; no partially replayed inventory is returned."""


class CorruptStoreError(StorageError):
    """Stored sources/events cannot be verified and replayed safely."""


class UnsupportedStoreVersion(StorageError):
    """Explicit schema, event-format or support-policy incompatibility."""


class StoreBusyError(StorageError):
    """Another writer owns the SQLite write lock; this operation did not commit."""


class InvalidWriteError(StorageError):
    """A typed action or its evidence did not pass validation."""


@dataclass(frozen=True, slots=True)
class Write:
    operation: str
    value: Record | ReviewRecord
    source_text: str | None = None


def _encode(value: Record | ReviewRecord) -> str:
    if type(value) not in (*RECORD_TYPES, ReviewRecord):
        raise ValueError("Only typed domain records/reviews may be persisted")
    data = asdict(value)
    # Derived caches are deliberately absent from the persisted payload.
    data = {item.name: data[item.name] for item in fields(value) if item.init}
    data["type"] = type(value).__name__
    payload = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=lambda item: item.isoformat() if isinstance(item, datetime) else _unsupported_json(),
        allow_nan=False,
    )
    payload.encode("utf-8", errors="strict")
    return payload


def _unsupported_json():
    raise ValueError("Unsupported domain JSON value")


def _decode(payload: str, source_text: str | None):
    data = strict_json_loads(payload)
    if type(data) is not dict or type(data.get("type")) is not str or data["type"] not in _TYPES:
        raise ValueError("Unknown event record type")
    kind = _TYPES[data.pop("type")]
    if set(data) != {item.name for item in fields(kind) if item.init}:
        raise ValueError("Event record fields do not match the exact domain format")
    if "evidence_ids" in data:
        if type(data["evidence_ids"]) is not list:
            raise ValueError("Evidence references must be a JSON array")
        data["evidence_ids"] = tuple(data["evidence_ids"])
    if kind is Evidence:
        if source_text is None or type(data["locator"]) is not dict or type(data["provenance"]) is not dict:
            raise ValueError("Evidence needs an original source and typed metadata")
        origin = data["provenance"].copy()
        origin["candidate_state"] = ReviewState(origin["candidate_state"])
        origin["extracted_at"] = datetime.fromisoformat(origin["extracted_at"])
        data["provenance"] = Provenance(**origin)
        data["locator"] = SourceLocator(**data["locator"])
        data["source_text"] = source_text
    elif kind is Relationship:
        data["predicate"] = Predicate(data["predicate"])
    elif kind is ReviewRecord:
        data["state"] = ReviewState(data["state"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    return kind(**data)


def _apply(inventory: Inventory, operation: str, value) -> Inventory:
    if operation == "review" and type(value) is ReviewRecord:
        return inventory.record_review(value)
    if operation in ("add", "revise") and type(value) in RECORD_TYPES:
        return inventory.add(value) if operation == "add" else inventory.revise(value)
    raise ValueError("Operation and record type do not match")


class InventoryStore:
    """One explicitly configured local database; all operations use transactions.

    Route actions through this API as they happen. There is no snapshot-save
    operation that guesses the interleaving of separate in-memory histories.
    Concurrent writers serialize via BEGIN IMMEDIATE or receive StoreBusyError.
    Every write replays fresh database state under that lock before validation.
    """

    def __init__(self, database_path: str | Path):
        self._connection = None
        if not isinstance(database_path, (str, Path)) or str(database_path) == ":memory:" or str(database_path).startswith("file:"):
            raise StorageError("Use an explicit local database filesystem path, not a SQLite URI")
        self.path = Path(database_path).resolve()
        try:
            self._connection = sqlite3.connect(self.path, timeout=0, isolation_level=None)
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA trusted_schema = OFF")
            self._connection.execute("PRAGMA synchronous = FULL")
            if self._connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise StorageError("SQLite foreign-key enforcement is unavailable")
            with self._transaction(write=True):
                tables = self._tables()
                version = self._connection.execute("PRAGMA user_version").fetchone()[0]
                if not tables and version == 0:
                    for statement in _SCHEMA:
                        self._connection.execute(statement)
                    self._connection.execute(
                        "INSERT INTO metadata VALUES (1, ?, ?, ?, 0)",
                        (SCHEMA_VERSION, EVENT_FORMAT_VERSION, SUPPORT_POLICY),
                    )
                    self._connection.execute("PRAGMA user_version = 1")
                self._check_schema()
            self.load()  # Refuse to open an inconsistent existing store.
        except BaseException as exc:
            self.close()
            if isinstance(exc, sqlite3.Error):
                raise StorageError("Could not open the configured SQLite database") from exc
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @contextmanager
    def _transaction(self, *, write=False):
        if self._connection is None:
            raise StorageError("Store is closed")
        try:
            self._connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield
                self._connection.execute("COMMIT")
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise
        except sqlite3.Error as exc:
            code = getattr(exc, "sqlite_errorcode", 0) & 255
            if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise StoreBusyError("SQLite writer is busy; no changes committed") from exc
            raise StorageError("SQLite transaction failed; no changes committed") from exc

    def _tables(self):
        return {row[0] for row in self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )}

    def _check_schema(self) -> int:
        version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise UnsupportedStoreVersion("Unsupported SQLite schema version")
        if self._tables() != {"metadata", "sources", "events"}:
            raise CorruptStoreError("Unexpected or missing database tables")
        rows = self._connection.execute(
            "SELECT singleton, schema_version, event_format, support_policy, last_sequence FROM metadata"
        ).fetchall()
        if len(rows) != 1 or rows[0][0] != 1:
            raise CorruptStoreError("Invalid schema metadata")
        _, schema, event_format, policy, sequence = rows[0]
        if (schema, event_format, policy) != (SCHEMA_VERSION, EVENT_FORMAT_VERSION, SUPPORT_POLICY):
            raise UnsupportedStoreVersion("Unsupported schema, event format or support policy")
        if type(sequence) is not int or sequence < 0:
            raise CorruptStoreError("Invalid global event sequence")
        if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise CorruptStoreError("Missing referenced source version")
        return sequence

    def _sources(self) -> dict[tuple[str, str], str]:
        result = {}
        for source_id, digest, content in self._connection.execute("SELECT source_id, sha256, content FROM sources"):
            try:
                require_text(source_id, "source_id")
                require_digest(digest)
                if type(content) is not bytes or hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError("Invalid source bytes/hash")
                result[(source_id, digest)] = content.decode("utf-8", errors="strict")
            except (ValueError, TypeError, UnicodeError) as exc:
                raise CorruptStoreError("Stored source content failed SHA-256/UTF-8 verification") from exc
        return result

    def _replay(self) -> tuple[Inventory, int]:
        head = self._check_schema()
        sources = self._sources()
        used_sources = set()
        inventory, count = Inventory(), 0
        for sequence, operation, payload, source_id, source_hash in self._connection.execute(
            "SELECT sequence, operation, payload, source_id, source_sha256 FROM events ORDER BY sequence"
        ):
            count += 1
            if type(sequence) is not int or sequence != count:
                raise CorruptStoreError("Noncontiguous global event order")
            key = None if source_id is None and source_hash is None else (source_id, source_hash)
            try:
                if type(payload) is not str or (key is not None and key not in sources):
                    raise ValueError("Invalid event payload or source reference")
                value = _decode(payload, sources.get(key))
                if isinstance(value, Evidence):
                    if key != (value.source_id, value.source_sha256):
                        raise ValueError("Evidence source reference mismatch")
                    used_sources.add(key)
                elif key is not None:
                    raise ValueError("Non-evidence event has a source reference")
                inventory = _apply(inventory, operation, value)
            except (ValueError, TypeError, KeyError, RecursionError) as exc:
                raise CorruptStoreError(f"Event {sequence} failed typed/domain validation") from exc
        if count != head or used_sources != set(sources):
            raise CorruptStoreError("Event count or retained source references are inconsistent")
        return inventory, head

    def load(self) -> Inventory:
        with self._transaction():
            return self._replay()[0]

    def read_source(self, source_id: str, source_sha256: str) -> str:
        with self._transaction():
            self._check_schema()
            sources = self._sources()
            try:
                return sources[(source_id, source_sha256)]
            except KeyError as exc:
                raise CorruptStoreError("Requested original source version is unavailable") from exc

    def add(self, value: Record, *, source_text: str | None = None) -> Inventory:
        return self.commit((Write("add", value, source_text),))

    def revise(self, value: Record, *, source_text: str | None = None) -> Inventory:
        return self.commit((Write("revise", value, source_text),))

    def record_review(self, value: ReviewRecord) -> Inventory:
        return self.commit((Write("review", value),))

    def commit(self, actions: tuple[Write, ...]) -> Inventory:
        """Validate/replay and atomically append the supplied action sequence."""
        if type(actions) is not tuple:
            raise InvalidWriteError("Actions must be a tuple of typed Write records")
        with self._transaction(write=True):
            inventory, sequence = self._replay()
            for action in actions:
                try:
                    if type(action) is not Write:
                        raise ValueError("Expected typed Write")
                    payload = _encode(action.value)
                    source_key = (None, None)
                    if type(action.value) is Evidence:
                        if type(action.source_text) is not str:
                            raise ValueError("Evidence writes require the original source_text")
                        source_key = (action.value.source_id, action.value.source_sha256)
                    elif action.source_text is not None:
                        raise ValueError("Only Evidence actions accept original source text")
                    value = _decode(payload, action.source_text)
                    inventory = _apply(inventory, action.operation, value)
                except (ValueError, TypeError, KeyError, RecursionError, AttributeError) as exc:
                    raise InvalidWriteError("Action failed typed/domain/source validation; batch rolled back") from exc
                if isinstance(value, Evidence):
                    content = action.source_text.encode("utf-8")
                    existing = self._connection.execute(
                        "SELECT content FROM sources WHERE source_id = ? AND sha256 = ?", source_key,
                    ).fetchone()
                    if existing is None:
                        self._connection.execute("INSERT INTO sources VALUES (?, ?, ?)", (*source_key, content))
                    elif existing[0] != content:
                        raise CorruptStoreError("Stored source bytes differ from the verified source")
                sequence += 1
                self._connection.execute(
                    "INSERT INTO events(sequence, operation, payload, source_id, source_sha256) VALUES (?, ?, ?, ?, ?)",
                    (sequence, action.operation, payload, *source_key),
                )
            self._connection.execute("UPDATE metadata SET last_sequence = ? WHERE singleton = 1", (sequence,))
            return inventory
