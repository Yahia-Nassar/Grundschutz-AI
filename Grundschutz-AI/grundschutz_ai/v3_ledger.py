"""Schema-3 trusted enrollment/registration/capture only. Never parses sources.

The initialized-only API is unchanged. Every connection is operation-owned;
there is no public append, descriptor enrollment or writable connection API.
"""
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import sqlite3
import stat
from threading import RLock
import time
from uuid import uuid4

from . import v3_codec as c, v3_schema as schema, v3_store as foundation
from . import v2_a0 as paths, v3_native_catalog as catalog
from .v3_native_contract import SheetSelection, NativeBridgeError, policy_config
from ._v3_capture import (
    LedgerError, CorruptLedgerError, UnsupportedLedgerError, InvalidCommandError,
    StaleWriteError, LedgerBusyError, LedgerLimitError, RegistryExhaustedError,
    LedgerLimits, DEFAULT_LIMITS, LedgerHead, SourceStatus, Blob, RegistryState,
    PolicyActivation, SourceRegistration, LedgerState, Replay, need,
)

__all__ = ("SourceLedger", "load_ledger", "LedgerLimits", "LedgerHead", "LedgerState",
           "RegistryState", "SourceStatus", "SourceRegistration", "SheetSelection",
           "LedgerError", "CorruptLedgerError", "UnsupportedLedgerError", "InvalidCommandError",
           "StaleWriteError", "LedgerBusyError", "LedgerLimitError", "RegistryExhaustedError")


def _deadline(deadline):
    if time.monotonic() >= deadline:
        raise LedgerLimitError("Capture-ledger cumulative deadline exceeded")


def _trust(limits):
    if type(limits) is not LedgerLimits:
        raise InvalidCommandError("Exact typed ledger limits required")
    base = foundation.StoreLimits(**{k: v for k, v in asdict(limits).items() if k != "max_registries"})
    foundation._trust(base)
    # Availability only: never call the reader bridge or broaden its capabilities.
    for profile in catalog.native_catalog():
        catalog.verify_available(profile)


def _checked_path(path, limits):
    return foundation._checked_path(path, limits)


def _connect(path, *, readonly):
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
                                uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        if readonly:
            connection.execute("PRAGMA query_only=ON")
        else:
            # Preflight already checked DELETE mode; never convert another format.
            connection.execute("PRAGMA synchronous=FULL")
        if (connection.execute("PRAGMA foreign_keys").fetchone() != (1,) or
                connection.execute("PRAGMA trusted_schema").fetchone() != (0,) or
                connection.execute("PRAGMA journal_mode").fetchone() != ("delete",) or
                (readonly and connection.execute("PRAGMA query_only").fetchone() != (1,)) or
                (not readonly and connection.execute("PRAGMA synchronous").fetchone() != (2,))):
            raise UnsupportedLedgerError("Unsupported capture-ledger connection discipline")
        return connection
    except BaseException:
        connection.close()
        raise


def _verify(connection, limits, deadline, *, mirrors=True):
    _deadline(deadline)
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    try:
        foundation._check_schema(connection, deadline)
        count, total_envelopes, largest = connection.execute(
            "SELECT count(*),coalesce(sum(length(envelope_json)),0),coalesce(max(length(envelope_json)),0) FROM events").fetchone()
        if not 1 <= count <= limits.max_events or total_envelopes > limits.max_metadata_bytes:
            raise LedgerLimitError("Event or metadata budget exceeded")
        need(largest <= c.DEFAULT_LIMITS.max_bytes)
        blob_count, total, largest = connection.execute(
            "SELECT count(*),coalesce(sum(byte_length),0),coalesce(max(byte_length),0) FROM content_blobs").fetchone()
        if (blob_count > 2 * limits.max_events + 8 or
                total > limits.max_original_bytes + limits.max_metadata_bytes or largest > c.DEFAULT_LIMITS.max_bytes):
            raise LedgerLimitError("BLOB admission budget exceeded")
        pages = connection.execute("PRAGMA page_count").fetchone()[0]
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        if pages * page_size > limits.max_database_bytes:
            raise LedgerLimitError("Database page budget exceeded")
        blobs = {}
        for key, length, raw in connection.execute("SELECT * FROM content_blobs"):
            _deadline(deadline)
            need(type(raw) is bytes and length == len(raw) and c.sha256(raw) == key)
            blobs[key] = raw
        links = {key: (implementation, blob) for key, implementation, blob in
                 connection.execute("SELECT * FROM policy_specs")}
        replay = Replay(blobs, links, limits)
        for row in connection.execute("SELECT * FROM events ORDER BY sequence"):
            _deadline(deadline)
            envelope = c.Envelope(row[-1])
            e = envelope.data()
            need(row == tuple(e[name] for name in foundation._ROW_FIELDS) + (envelope.canonical,))
            event = c.Event(envelope, c.Payload(blobs[e["payload_sha256"]]))
            replay.accept(event)
        state = replay.finish()
        if mirrors:
            for table, expected in replay.rows.items():
                _deadline(deadline)
                need(set(connection.execute("SELECT * FROM " + table)) == expected)
        _deadline(deadline)
        return state, replay
    finally:
        connection.set_progress_handler(None, 0)


def _read(path, limits, deadline):
    checked = _checked_path(path, limits)
    connection = _connect(checked, readonly=True)
    try:
        connection.execute("BEGIN")
        result = _verify(connection, limits, deadline)
        connection.execute("COMMIT")
        return result
    finally:
        connection.close()


def _error(exc):
    if isinstance(exc, sqlite3.Error) and getattr(exc, "sqlite_errorcode", 0) & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return LedgerBusyError("Capture-ledger writer is busy; no automatic retry")
    return CorruptLedgerError("Capture ledger refused; no trusted partial result")


_REFUSALS = (sqlite3.Error, c.CodecError, OSError, KeyError, TypeError, ValueError,
             NativeBridgeError, foundation.StoreError, paths.LedgerError)


def load_ledger(path, *, limits=DEFAULT_LIMITS):
    """Read-only full applicable replay, including every original BLOB and mirror."""
    try:
        deadline = time.monotonic() + limits.max_replay_seconds if type(limits) is LedgerLimits else 0
        _trust(limits)
        return _read(path, limits, deadline)[0]
    except _REFUSALS as exc:
        raise _error(exc) from exc


def _blob(connection, raw):
    key = c.sha256(raw)
    found = connection.execute("SELECT byte_length,content FROM content_blobs WHERE sha256=?", (key,)).fetchone()
    if found is None:
        connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", (key, len(raw), raw))
    else:
        need(found == (len(raw), raw), "BLOB deduplication equality failed")
    return key


def _envelope(payload, head, actor):
    data = payload.data()
    return c.make_envelope(payload, store_uuid=head.store_uuid, sequence=head.sequence + 1,
        previous=head.event_sha256, event_id=uuid4().hex, transaction_id=uuid4().hex,
        occurred_at=data.get("observed_at", c.utc_now()), actor_id=actor)


def _mirror(connection, replay):
    for table, expected in replay.rows.items():
        current = set(connection.execute("SELECT * FROM " + table))
        if table in schema.MUTABLE:
            connection.execute("DELETE FROM " + table)
            current = set()
        else:
            need(current <= expected)
        for row in expected - current:
            connection.execute("INSERT INTO " + table + " VALUES (" + ",".join("?" for _ in row) + ")", row)


@dataclass(frozen=True, slots=True)
class _Plan:
    payload: c.Payload
    metadata: tuple[bytes, ...] = ()
    raw: bytes | None = None
    policy_row: tuple | None = None
    registry_id: str | None = None
    result: str | c.SourceRef | None = None


def _exhaust(rid, budget):
    return _Plan(c.make_payload(c.EventKind.EXHAUSTED, registry_id=rid,
                 budget_name=budget, observed_at=c.utc_now()), registry_id=rid)


def _read_original(path, kind, maximum):
    """Exactly one bounded content read. Never reopen this original later."""
    try:
        if not isinstance(path, (str, Path)) or Path(path).suffix.casefold() != "." + kind:
            return None, "unsupported_input"
        class SourceLimit:
            max_database_bytes = 2**63 - 1  # File size is checked on its open handle below.
        try:
            checked = paths._path(path, SourceLimit())
        except paths.LedgerError:
            return None, "unsupported_input"
        with checked.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                return None, "unsupported_input"
            if metadata.st_size > maximum:
                return None, "source_limit"
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            return None, "source_limit"
        if len(raw) != metadata.st_size:
            return None, "capture_failed"
        return raw, None
    except (OSError, ValueError):
        return None, "capture_failed"


class SourceLedger:
    """Operation-owned connections, live one-use capture authority, no append API.

    Opening never captures. Closing/reopening permanently loses old uncaptured
    path authority. I/O attempts consume it even on later SQL/stale failure.
    """
    def __init__(self, path, *, limits=DEFAULT_LIMITS):
        self._limits, self._closed, self._lock, self._capture_authority = limits, False, RLock(), set()
        try:
            deadline = time.monotonic() + limits.max_replay_seconds if type(limits) is LedgerLimits else 0
            _trust(limits)
            self._path = _checked_path(path, limits)
            _read(self._path, limits, deadline)
            info = self._path.stat()
            self._identity = info.st_dev, info.st_ino
        except _REFUSALS as exc:
            raise _error(exc) from exc

    @classmethod
    def open(cls, path, *, limits=DEFAULT_LIMITS):
        return cls(path, limits=limits)

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def close(self):
        with self._lock:
            self._capture_authority.clear()
            self._closed = True

    def _live(self):
        if self._closed: raise InvalidCommandError("Capture ledger is closed")
        _trust(self._limits)
        checked = _checked_path(self._path, self._limits)
        info = checked.stat()
        if (info.st_dev, info.st_ino) != self._identity:
            raise UnsupportedLedgerError("Capture-ledger file identity changed")

    def load(self):
        with self._lock:
            try:
                deadline = time.monotonic() + self._limits.max_replay_seconds
                self._live()
                return _read(self._path, self._limits, deadline)[0]
            except _REFUSALS as exc:
                raise _error(exc) from exc

    @staticmethod
    def _tokens(state, expected, registry=None, source_id=None, expected_source=None):
        if type(expected) is not LedgerHead or state.head != expected:
            raise StaleWriteError("Expected global ledger head is stale")
        if registry is not None:
            if type(registry) is not RegistryState or state.registry(registry.registry_id) != registry:
                raise StaleWriteError("Expected registry state is stale")
        if source_id is not None:
            if expected_source is not None and type(expected_source) is not c.SourceRef:
                raise InvalidCommandError("Exact source-head token required")
            if state.source_head(source_id) != expected_source:
                raise StaleWriteError("Expected highest-started source head is stale")

    def _write(self, expected, actor, prepare, *, registry=None, source_id=None, expected_source=None, deadline=None):
        """Private command engine; only fixed named operations supply plans."""
        deadline = deadline if deadline is not None else time.monotonic() + self._limits.max_replay_seconds
        connection = None
        try:
            self._live(); c.text(actor)
            state, _ = _read(self._path, self._limits, deadline)  # RO before any RW handle.
            self._tokens(state, expected, registry, source_id, expected_source)
            connection = _connect(_checked_path(self._path, self._limits), readonly=False)
            connection.execute("BEGIN IMMEDIATE")
            state, replay = _verify(connection, self._limits, deadline)
            self._tokens(state, expected, registry, source_id, expected_source)
            plan = prepare(state, replay)
            envelope = _envelope(plan.payload, state.head, actor)
            metadata = {key: replay.blobs[key] for key in replay.metadata}
            for raw in (plan.payload.canonical, *plan.metadata):
                metadata[c.sha256(raw)] = raw
            budget = None
            if envelope.data()["sequence"] > self._limits.max_events - self._limits.max_registries:
                budget = "events"
            if sum(map(len, metadata.values())) + replay.envelope_bytes + len(envelope.canonical) > self._limits.max_metadata_bytes - 1024 * self._limits.max_registries:
                budget = "metadata_bytes"
            if budget and plan.payload.kind is not c.EventKind.EXHAUSTED:
                if plan.registry_id is None:
                    raise LedgerLimitError("Normal event/control reserve exhausted; command uncommitted")
                replay.active(plan.registry_id)
                plan = _exhaust(plan.registry_id, budget)
                envelope = _envelope(plan.payload, state.head, actor)
            for raw in (*plan.metadata, plan.payload.canonical): _blob(connection, raw)
            if plan.raw is not None: _blob(connection, plan.raw)
            if plan.policy_row is not None:
                found = connection.execute("SELECT * FROM policy_specs WHERE policy_spec_hash=?", (plan.policy_row[0],)).fetchone()
                if found is None: connection.execute("INSERT INTO policy_specs VALUES (?,?,?)", plan.policy_row)
                else: need(found == plan.policy_row)
            e = envelope.data()
            connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(e[name] for name in foundation._ROW_FIELDS) + (envelope.canonical,))
            _, rebuilt = _verify(connection, self._limits, deadline, mirrors=False)
            _mirror(connection, rebuilt)
            verified, _ = _verify(connection, self._limits, deadline)
            _deadline(deadline)
            connection.execute("COMMIT")
            if plan.payload.kind is c.EventKind.EXHAUSTED:
                raise RegistryExhaustedError("Registry exhaustion committed; requested operation was not committed")
            return plan.result if plan.result is not None else verified
        except _REFUSALS as exc:
            raise _error(exc) from exc
        finally:
            if connection is not None:
                try:
                    if connection.in_transaction: connection.execute("ROLLBACK")
                finally:
                    connection.close()

    def register_implementation(self, kind, *, expected, actor_id):
        with self._lock:
            def prepare(state, replay):
                if type(kind) is not str or kind not in ("docx", "xlsx"):
                    raise InvalidCommandError("Only approved DOCX/XLSX families can enroll")
                profile = replay.profile(kind)
                spec = c.Spec(profile.reader_descriptor)
                if spec.sha256 in replay.impl: raise InvalidCommandError("Implementation already registered")
                return _Plan(c.make_payload(c.EventKind.IMPLEMENTATION, implementation_hash=spec.sha256,
                    descriptor_blob_sha256=c.sha256(spec.canonical)), (spec.canonical,), result=spec.sha256)
            return self._write(expected, actor_id, prepare)

    def register_handler(self, handler_spec_hash, *, expected, actor_id):
        with self._lock:
            def prepare(state, replay):
                profile = catalog.select_handler(handler_spec_hash)
                if profile.spec.sha256 in replay.handlers or profile.spec.data()["reader_spec_hash"] not in replay.impl:
                    raise InvalidCommandError("Handler already enrolled or implementation unavailable")
                return _Plan(c.make_payload(c.EventKind.HANDLER, handler_spec_hash=profile.spec.sha256,
                    descriptor_blob_sha256=profile.spec.blob_sha256), (profile.spec.canonical,), result=profile.spec.sha256)
            return self._write(expected, actor_id, prepare)

    def create_registry(self, kind, *, session_id, policy_spec, expected, actor_id):
        with self._lock:
            def prepare(state, replay):
                if type(kind) is not str or kind not in ("docx", "xlsx"):
                    raise InvalidCommandError("Unsupported registry family")
                c.identity(session_id)
                profile = replay.profile(kind)
                if profile.spec.sha256 not in replay.handlers or profile.spec.data()["reader_spec_hash"] not in replay.impl:
                    raise InvalidCommandError("Trusted family implementation and handler must enroll first")
                policy_config(policy_spec, profile)
                if len(replay.registries) >= self._limits.max_registries or session_id in {r.session_id for r in state.registries}:
                    raise InvalidCommandError("Registry/session capacity or uniqueness violated")
                rid = uuid4().hex
                payload = c.make_payload(c.EventKind.REGISTRY, registry_id=rid, kind=kind, session_id=session_id,
                    initial_policy_revision=1, policy_spec_hash=policy_spec.sha256, baseline_registry_epoch=1, baseline_history_units=0)
                row = (policy_spec.sha256, policy_spec.data()["implementation_hash"], c.sha256(policy_spec.canonical))
                return _Plan(payload, (policy_spec.canonical,), policy_row=row, result=rid)
            return self._write(expected, actor_id, prepare)

    def begin_registration(self, registry_id, source_id, *, kind, policy_revision, reader_spec_hash,
                           handler_spec_hash, expected, expected_registry, expected_source,
                           actor_id, selection=None, declared_lineage=()):
        with self._lock:
            def prepare(state, replay):
                c.text(source_id); c.identity(registry_id); c.integer(policy_revision)
                if type(expected_registry) is not RegistryState or expected_registry.registry_id != registry_id:
                    raise InvalidCommandError("Exact matching registry token required")
                reg = replay.active(registry_id)
                profile = replay.profile(reg.kind)
                if (type(kind) is not str or kind != reg.kind or policy_revision != reg.policy_revision or
                        reader_spec_hash != profile.spec.data()["reader_spec_hash"] or handler_spec_hash != profile.spec.sha256):
                    raise InvalidCommandError("Registration family/policy/reader/handler mismatch")
                if (type(declared_lineage) is not tuple or declared_lineage or
                        (reg.kind == "docx" and selection is not None) or
                        (reg.kind == "xlsx" and type(selection) is not SheetSelection)):
                    raise InvalidCommandError("Exact selection and empty original-source lineage required")
                if source_id in replay.sources and replay.sources[source_id] != registry_id:
                    raise InvalidCommandError("Source ownership is immutable store-wide")
                cfg = replay.policy(registry_id).data()["config"]
                if reg.history_units + 3 > cfg["max_history_units"]: return _exhaust(registry_id, "history")
                if source_id not in replay.sources and sum(rid == registry_id for rid in replay.sources.values()) >= cfg["max_sources"]:
                    return _exhaust(registry_id, "sources")
                old = replay.heads.get(source_id)
                ref = c.SourceRef(source_id, 1 if old is None else old.revision + 1, uuid4().hex)
                payload = c.make_payload(c.EventKind.STARTED, registry_id=registry_id, registration=ref.data(),
                    predecessor_registration_id=None if old is None else old.registration_id,
                    policy_revision=policy_revision, reader_spec_hash=reader_spec_hash, handler_spec_hash=handler_spec_hash,
                    selection=None if selection is None else asdict(selection), declared_lineage=[], observed_at=c.utc_now())
                return _Plan(payload, registry_id=registry_id, result=ref)
            result = self._write(expected, actor_id, prepare, registry=expected_registry,
                                 source_id=source_id, expected_source=expected_source)
            self._capture_authority.add(result)
            return result

    def capture_source(self, ref, source_path, *, expected, expected_registry, expected_source, actor_id):
        with self._lock:
            deadline = time.monotonic() + self._limits.max_replay_seconds
            try:
                self._live(); c.text(actor_id); c.require(type(ref) is c.SourceRef)
                state, _ = _read(self._path, self._limits, deadline)
                self._tokens(state, expected, expected_registry, ref.source_id, expected_source)
                previous = state.registration(ref)
                if type(expected_registry) is not RegistryState or expected_registry.registry_id != previous.registry_id:
                    raise InvalidCommandError("Matching registry token required")
                if (ref not in self._capture_authority or previous.status is not SourceStatus.PENDING or
                        previous.binary_sha256 is not None or expected_registry.exhausted):
                    raise InvalidCommandError("Capture requires an unused live creating-session registration")
                self._capture_authority.remove(ref)  # Spent even if I/O, stale checks or COMMIT subsequently fail.
                policy = next(p.spec for p in state.policies if p.registry_id == previous.registry_id and p.revision == previous.policy_revision)
                raw, issue = _read_original(source_path, previous.kind, policy.data()["config"]["reader_limits"]["max_file_bytes"])
                _deadline(deadline)
                def prepare(fresh, replay):
                    current = fresh.registration(ref)
                    reg = replay.active(current.registry_id)
                    if current != previous or reg.policy_revision != current.policy_revision:
                        raise StaleWriteError("Capture registration/policy changed")
                    if issue is not None:
                        return _Plan(c.make_payload(c.EventKind.FAILED, registration=ref.data(), phase="capture",
                            issue_codes=[issue], observed_at=c.utc_now()), registry_id=reg.registry_id)
                    key = c.sha256(raw)
                    cfg = replay.policy(reg.registry_id).data()["config"]
                    total = sum(len(replay.blobs[h]) for h in replay.raw) + (0 if key in replay.raw else len(raw))
                    retained = reg.retained_bytes + (0 if key in replay.reg_raw[reg.registry_id] else len(raw))
                    if total > self._limits.max_original_bytes or retained > cfg["max_retained_bytes"]:
                        return _exhaust(reg.registry_id, "raw_bytes")
                    return _Plan(c.make_payload(c.EventKind.CAPTURED, registration=ref.data(), blob_sha256=key,
                        byte_length=len(raw), observed_at=c.utc_now()), raw=raw, registry_id=reg.registry_id)
                return self._write(expected, actor_id, prepare, registry=expected_registry,
                                   source_id=ref.source_id, expected_source=expected_source, deadline=deadline)
            except _REFUSALS as exc:
                raise _error(exc) from exc
