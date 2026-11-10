"""A-only synthetic source ledger: PENDING/FAILED, never staging or inventory."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, replace
from enum import StrEnum
import os
from pathlib import Path
import sqlite3
import stat
import sys
from threading import RLock
import time
from uuid import uuid4

from . import v2_codec as codec, v2_schema as schema
from . import docx_staging, xlsx_staging, docx_ingestion, xlsx_ingestion


class LedgerError(RuntimeError):
    pass


class CorruptLedgerError(LedgerError):
    pass


class UnsupportedLedgerError(LedgerError):
    pass


class LedgerBusyError(LedgerError):
    pass


class StaleWriteError(LedgerError):
    pass


class LedgerLimitError(LedgerError):
    pass


class InvalidCommandError(LedgerError):
    pass


class UnsafePathError(LedgerError):
    pass


@dataclass(frozen=True, slots=True)
class LedgerLimits:
    max_database_bytes: int = 256 * 1024 * 1024
    max_events: int = 10_000
    max_registries: int = 4
    max_original_bytes: int = 32 * 1024 * 1024
    max_metadata_bytes: int = 128 * 1024 * 1024
    max_replay_seconds: int = 60

    def __post_init__(self):
        for f in fields(self):
            codec.require(type(getattr(self, f.name)) is int and 1 <= getattr(self, f.name) <= f.default)
        codec.require(self.max_events > self.max_registries + 1)


DEFAULT_LIMITS = LedgerLimits()


@dataclass(frozen=True, slots=True)
class LedgerHead:
    store_uuid: str
    sequence: int
    event_sha256: str

    def __post_init__(self):
        codec.identity(self.store_uuid)
        codec.integer(self.sequence)
        codec.digest(self.event_sha256)


class SourceStatus(StrEnum):
    PENDING = "pending"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Blob:
    sha256: str
    content: bytes

    def __post_init__(self):
        codec.require(type(self.content) is bytes and codec.sha256(self.content) == self.sha256)


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    envelope: codec.Envelope
    payload: codec.Payload


@dataclass(frozen=True, slots=True)
class PolicyActivation:
    registry_id: str
    revision: int
    spec: codec.Spec
    policy_fingerprint: str
    activated_at: str


@dataclass(frozen=True, slots=True)
class RegistryState:
    registry_id: str
    session_id: str
    kind: str
    policy_revision: int
    epoch: int
    history_units: int
    exhausted: bool
    retained_bytes: int


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    ref: codec.SourceRef
    registry_id: str
    policy_revision: int
    selection_json: bytes
    status: SourceStatus
    binary_sha256: str | None
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LedgerState:
    head: LedgerHead
    events: tuple[LedgerEvent, ...]
    implementations: tuple[codec.Spec, ...]
    policies: tuple[PolicyActivation, ...]
    registries: tuple[RegistryState, ...]
    registrations: tuple[SourceRegistration, ...]
    current_heads: tuple[codec.SourceRef, ...]
    original_blobs: tuple[Blob, ...]

    def registration(self, ref: codec.SourceRef) -> SourceRegistration:
        codec.require(type(ref) is codec.SourceRef)
        result = next((item for item in self.registrations if item.ref == ref), None)
        if result is None:
            raise InvalidCommandError("Unknown registration")
        return result

    def source_head(self, source_id: str) -> codec.SourceRef | None:
        codec.text(source_id)
        return next((ref for ref in self.current_heads if ref.source_id == source_id), None)


def _local_spec(kind):
    if kind not in ("docx", "xlsx"):
        raise InvalidCommandError("Unsupported source kind")
    # Fixed local code allowlist, never a path/module supplied by database data.
    modules = sorted(codec.MODULE_NAMES)
    base = Path(__file__).resolve().parent
    try:
        module_hashes = [{"module_name": name, "sha256": codec.sha256((base / (name + ".py")).read_bytes())} for name in modules]
    except OSError as exc:
        raise UnsupportedLedgerError("Trusted local implementation artifact unavailable") from exc
    return codec.Spec(codec.canonical_dumps({
        "type": "implementation-spec/v1", "family": kind,
        "method_version": "docx-plain/v1" if kind == "docx" else "xlsx-literal/v1",
        "module_hashes": module_hashes,
        "runtime": {"python_version": ".".join(map(str, sys.version_info[:3])),
                    "platform_profile": "windows-fixed-ntfs-refs/v1", "sqlite_version": sqlite3.sqlite_version},
        "serialization_version": codec.SERIALIZATION_VERSION,
    }))


def _policy_object(spec):
    data = spec.data()
    cfg = data["config"].copy()
    limits = cfg.pop("reader_limits")
    if data["kind"] == "docx":
        return docx_staging.StagingPolicy(reader_limits=docx_ingestion.DocxLimits(**limits), **cfg)
    return xlsx_staging.StagingPolicy(reader_limits=xlsx_ingestion.XlsxLimits(**limits), **cfg)


def _policy_spec(kind, policy, implementation_hash):
    expected = docx_staging.StagingPolicy if kind == "docx" else xlsx_staging.StagingPolicy
    if type(policy) is not expected:
        raise InvalidCommandError("Expected exact typed source policy")
    config = {f.name: getattr(policy, f.name) for f in fields(policy) if f.init}
    config["reader_limits"] = asdict(config["reader_limits"])
    spec = codec.Spec(codec.canonical_dumps({"type": "policy-spec/v1", "kind": kind,
        "semantic_version": policy.version, "config": config, "implementation_hash": implementation_hash}))
    _policy_object(spec)  # Independently enforce existing hard caps, not flags.
    return spec


def _fixed_local_volume(path):
    if os.name != "nt":
        raise UnsafePathError("Only the reviewed Windows local-volume profile is supported")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    drive_type = kernel.GetDriveTypeW
    drive_type.argtypes, drive_type.restype = [wintypes.LPCWSTR], wintypes.UINT
    if drive_type(path.anchor) != 3:
        raise UnsafePathError("Database requires a fixed local volume")
    volume_info = kernel.GetVolumeInformationW
    volume_info.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                            ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    volume_info.restype = wintypes.BOOL
    filesystem = ctypes.create_unicode_buffer(32)
    if not volume_info(path.anchor, None, 0, None, None, None, filesystem, len(filesystem)) or filesystem.value.upper() not in ("NTFS", "REFS"):
        raise UnsafePathError("Unsupported local filesystem")


def _path(value, limits):
    if not isinstance(value, (str, Path)) or str(value).startswith(("file:", "\\\\", "//")) or str(value) == ":memory:":
        raise UnsafePathError("Explicit local database path required")
    path = Path(value)
    if not path.is_absolute() or path.is_reserved() or any(":" in part or part.endswith((".", " ")) for part in path.parts[1:]):
        raise UnsafePathError("Absolute database path without alternate streams required")
    _fixed_local_volume(path)  # Refuse remote drives before filesystem traversal.
    try:
        for part in reversed((path, *path.parents)):
            try:
                metadata = part.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024):
                raise UnsafePathError("Database path must not contain links or reparse points")
            if part == path and stat.S_ISREG(metadata.st_mode) and metadata.st_nlink != 1:
                raise UnsafePathError("Hard-linked database paths are unsupported")
        path = path.resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[2]):
            raise UnsafePathError("Database must be outside Git")
        if not path.parent.is_dir() or (path.exists() and (not path.is_file() or path.stat().st_size > limits.max_database_bytes)):
            raise UnsafePathError("Database type, parent or size is unsupported")
        # WAL is deliberately unsupported in A; never ignore bytes in a sidecar.
        if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm")):
            raise UnsafePathError("WAL sidecars are outside the A filesystem profile")
        return path
    except OSError as exc:
        raise UnsafePathError("Database path verification failed") from exc


def _connect(path, *, readonly):
    # URI is constructed from an already checked absolute path, not caller URI.
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        if readonly:
            connection.execute("PRAGMA query_only=ON")
        else:
            connection.execute("PRAGMA synchronous=FULL")
        if connection.execute("PRAGMA foreign_keys").fetchone() != (1,) or connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise UnsupportedLedgerError("Unsupported SQLite connection profile")
        return connection
    except BaseException:
        connection.close()
        raise


def _sql_error(exc):
    code = getattr(exc, "sqlite_errorcode", 0) & 255
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return LedgerBusyError("Ledger writer is busy; command did not commit")
    return LedgerError("SQLite ledger operation failed; no partial command published")


@contextmanager
def _transaction(connection, *, write=False):
    try:
        connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    except sqlite3.Error as exc:
        raise _sql_error(exc) from exc


def _schema(connection):
    if connection.execute("PRAGMA user_version").fetchone() != (2,):
        raise UnsupportedLedgerError("Only schema 2 source ledgers are supported")
    actual = {name: (kind, sql) for name, kind, sql in connection.execute(
        "SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    if actual != schema.expected_objects():
        raise CorruptLedgerError("Unexpected ledger schema objects")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise CorruptLedgerError("Ledger foreign-key failure")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise CorruptLedgerError("Ledger integrity failure")


class _Replay:
    """Transient verified builder, never exposed or accepted as an authority."""

    def __init__(self, blobs, implementations, policies, catalog, limits):
        self.blobs, self.impl, self.policies, self.catalog, self.limits = blobs, implementations, policies, catalog, limits
        self.rows = {name: [] for name in schema.TABLES if name not in ("content_blobs", "implementation_specs", "policy_specs", "events")}
        self.registries, self.activations, self.sources, self.registrations, self.heads = {}, {}, {}, {}, {}
        self.raw, self.reg_raw, self.used_impl, self.used_policy = set(), {}, set(), set()
        self.used_blobs, self.events = set(), []
        self.store_uuid = None

    def policy(self, key):
        spec = self.policies[key]
        data = spec.data()
        codec.require(data["implementation_hash"] in self.used_impl)
        codec.require(self.impl[data["implementation_hash"]][0].data()["family"] == data["kind"])
        self.used_policy.add(key)
        return _policy_object(spec), data

    def accept(self, envelope, payload):
        e, p, kind = envelope.data(), payload.data(), payload.kind
        codec.require(e["kind"] == kind.value and codec.sha256(payload.canonical) == e["payload_sha256"])
        codec.require(e["transaction_index"] == e["transaction_count"] == 1)
        codec.require(e["sequence"] == len(self.events) + 1)
        codec.require(kind is codec.EventKind.EXHAUSTED or e["sequence"] <= self.limits.max_events - self.limits.max_registries)
        codec.require(e["previous_event_sha256"] == (None if not self.events else self.events[-1].envelope.data()["event_sha256"]))
        codec.require(not self.events or kind is not codec.EventKind.INITIALIZED)
        if e["actor_id"] is None:
            codec.require(kind in (codec.EventKind.CAPTURED, codec.EventKind.FAILED, codec.EventKind.EXHAUSTED))
        self.used_blobs.add(e["payload_sha256"])
        seq, now = e["sequence"], e["occurred_at"]
        for audit in ("observed_at", "activated_at"):
            if audit in p:
                codec.require(p[audit] == now)
        if not self.events:
            codec.require(kind is codec.EventKind.INITIALIZED and p["store_uuid"] == e["store_uuid"])
            self.store_uuid = p["store_uuid"]
        codec.require(e["store_uuid"] == self.store_uuid)
        if kind is codec.EventKind.IMPLEMENTATION:
            key = p["implementation_hash"]
            codec.require(key in self.impl and key not in self.used_impl)
            spec, blob = self.impl[key]
            codec.require(codec.sha256(spec.canonical) == blob == p["descriptor_blob_sha256"])
            codec.require(spec == self.catalog[spec.data()["family"]])
            self.used_impl.add(key)
        elif kind is codec.EventKind.REGISTRY:
            rid = p["registry_id"]
            codec.require(rid not in self.registries and len(self.registries) < self.limits.max_registries)
            codec.require(p["session_id"] not in {r.session_id for r in self.registries.values()})
            policy, data = self.policy(p["policy_spec_hash"])
            codec.require(data["kind"] == p["kind"])
            self.registries[rid] = RegistryState(rid, p["session_id"], p["kind"], 1, 1, 0, False, 0)
            self.reg_raw[rid] = set()
            self.activations[rid, 1] = PolicyActivation(rid, 1, self.policies[p["policy_spec_hash"]], policy.fingerprint, now)
            self.rows["registries"].append((rid, p["kind"], p["session_id"], seq))
            self.rows["policy_activations"].append((rid, 1, p["policy_spec_hash"], policy.fingerprint, seq, now))
        elif kind is codec.EventKind.POLICY:
            rid = p["registry_id"]
            reg = self.registries[rid]
            codec.require(not reg.exhausted and p["predecessor_revision"] == reg.policy_revision)
            policy, data = self.policy(p["policy_spec_hash"])
            codec.require(data["kind"] == reg.kind and p["policy_fingerprint"] == policy.fingerprint)
            self._capacity(reg, policy, extra_history=1)
            self.registries[rid] = replace(reg, policy_revision=p["revision"], epoch=reg.epoch + 1, history_units=reg.history_units + 1)
            self.activations[rid, p["revision"]] = PolicyActivation(rid, p["revision"], self.policies[p["policy_spec_hash"]], policy.fingerprint, now)
            self.rows["policy_activations"].append((rid, p["revision"], p["policy_spec_hash"], policy.fingerprint, seq, now))
        elif kind is codec.EventKind.STARTED:
            ref = codec.SourceRef.parse(p["registration"])
            rid, sid = p["registry_id"], ref.source_id
            reg = self.registries[rid]
            codec.require(not reg.exhausted and p["policy_revision"] == reg.policy_revision and ref.registration_id not in self.registrations)
            policy, data = self.policy(self.activations[rid, reg.policy_revision].spec.sha256)
            codec.require(p["reader_spec_hash"] == data["implementation_hash"])
            codec.require((p["selection"] is None) == (reg.kind == "docx"))
            old = self.heads.get(sid)
            codec.require(ref.revision == (1 if old is None else old.revision + 1))
            codec.require(p["predecessor_registration_id"] == (None if old is None else old.registration_id))
            self._capacity(reg, policy, extra_history=3, extra_source=0 if sid in self.sources else 1)
            if sid in self.sources:
                codec.require(self.sources[sid] == rid)
            else:
                self.sources[sid] = rid
                self.rows["logical_sources"].append((sid, rid, reg.kind, seq))
            self.heads[sid] = ref
            self.registrations[ref.registration_id] = SourceRegistration(ref, rid, reg.policy_revision, codec.canonical_dumps(p["selection"]), SourceStatus.PENDING, None, ())
            self.registries[rid] = replace(reg, epoch=reg.epoch + 1, history_units=reg.history_units + 3)
            self.rows["registrations"].append((ref.registration_id, sid, rid, ref.revision, p["predecessor_registration_id"], reg.policy_revision, p["reader_spec_hash"], codec.canonical_dumps(p["selection"]), seq))
            self.rows["registration_observations"].append((seq, ref.registration_id, "pending", None, codec.canonical_dumps([])))
        elif kind in (codec.EventKind.CAPTURED, codec.EventKind.FAILED):
            ref = codec.SourceRef.parse(p["registration"])
            previous = self.registrations[ref.registration_id]
            codec.require(previous.ref == ref and previous.status is SourceStatus.PENDING)
            rid = previous.registry_id
            reg = self.registries[rid]
            codec.require(not reg.exhausted)
            if kind is codec.EventKind.CAPTURED:
                codec.require(previous.binary_sha256 is None)
                blob = p["blob_sha256"]
                raw = self.blobs[blob]
                codec.require(len(raw) == p["byte_length"])
                policy = _policy_object(self.activations[rid, previous.policy_revision].spec)
                codec.require(len(raw) <= policy.reader_limits.max_file_bytes)
                extra = 0 if blob in self.reg_raw[rid] else len(raw)
                active = _policy_object(self.activations[rid, reg.policy_revision].spec)
                codec.require(reg.retained_bytes + extra <= active.max_retained_bytes)
                self.raw.add(blob)
                self.reg_raw[rid].add(blob)
                codec.require(sum(len(self.blobs[key]) for key in self.raw) <= self.limits.max_original_bytes)
                self.registrations[ref.registration_id] = replace(previous, binary_sha256=blob)
                self.registries[rid] = replace(reg, epoch=reg.epoch + 1, retained_bytes=reg.retained_bytes + extra)
                self.rows["registration_observations"].append((seq, ref.registration_id, "captured", blob, codec.canonical_dumps([])))
            else:
                self.registrations[ref.registration_id] = replace(previous, status=SourceStatus.FAILED, failure_codes=tuple(p["issue_codes"]))
                self.registries[rid] = replace(reg, epoch=reg.epoch + 1)
                self.rows["registration_observations"].append((seq, ref.registration_id, "failed", previous.binary_sha256, codec.canonical_dumps(p["issue_codes"])))
        elif kind is codec.EventKind.EXHAUSTED:
            rid = p["registry_id"]
            reg = self.registries[rid]
            codec.require(not reg.exhausted)
            self.registries[rid] = replace(reg, exhausted=True, epoch=reg.epoch + 1)
        self.events.append(LedgerEvent(envelope, payload))

    def _capacity(self, reg, policy, *, extra_history=0, extra_source=0):
        codec.require(reg.history_units + extra_history <= policy.max_history_units)
        codec.require(reg.retained_bytes <= policy.max_retained_bytes)
        codec.require(sum(owner == reg.registry_id for owner in self.sources.values()) + extra_source <= policy.max_sources)

    def finalize(self):
        for key in self.used_impl:
            self.used_blobs.add(self.impl[key][1])
        for key in self.used_policy:
            self.used_blobs.add(codec.sha256(self.policies[key].canonical))
        self.metadata = set(self.used_blobs)
        self.used_blobs |= self.raw
        codec.require(self.used_impl == set(self.impl) and self.used_policy == set(self.policies) and self.used_blobs == set(self.blobs))
        codec.require(sum(len(self.blobs[key]) for key in self.metadata) <= self.limits.max_metadata_bytes)
        for sid, ref in self.heads.items():
            start = next(row[-1] for row in self.rows["registrations"] if row[0] == ref.registration_id)
            self.rows["source_heads"].append((sid, ref.revision, ref.registration_id, start))
        for reg in self.registries.values():
            self.rows["registry_state"].append((reg.registry_id, reg.policy_revision, reg.epoch, reg.history_units, int(reg.exhausted), reg.retained_bytes))
        last = self.events[-1].envelope.data()
        self.rows["store_metadata"] = [(1, self.store_uuid, 2, codec.EVENT_CODEC, codec.SERIALIZATION_VERSION, "staging_only", last["sequence"], last["event_sha256"])]
        return LedgerState(LedgerHead(self.store_uuid, last["sequence"], last["event_sha256"]), tuple(self.events),
            tuple(self.impl[key][0] for key in sorted(self.used_impl)), tuple(self.activations.values()),
            tuple(self.registries.values()), tuple(self.registrations.values()),
            tuple(self.heads[key] for key in sorted(self.heads)), tuple(Blob(key, self.blobs[key]) for key in sorted(self.raw)))


def _replay(connection, limits, catalog):
    deadline = time.monotonic() + limits.max_replay_seconds
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        _schema(connection)
        count = connection.execute("SELECT count(*) FROM events").fetchone()[0]
        if not 1 <= count <= limits.max_events:
            raise LedgerLimitError("Event budget exceeded or missing genesis")
        total = connection.execute("SELECT count(*),coalesce(sum(byte_length),0),coalesce(max(byte_length),0) FROM content_blobs").fetchone()
        if total[0] > 4 * limits.max_events or total[1] > limits.max_original_bytes + limits.max_metadata_bytes or total[2] > codec.DEFAULT_LIMITS.max_bytes:
            raise LedgerLimitError("Stored BLOB budget exceeded")
        blobs = {}
        for key, length, content in connection.execute("SELECT * FROM content_blobs"):
            codec.digest(key)
            codec.integer(length, 0)
            codec.require(type(content) is bytes and len(content) == length and codec.sha256(content) == key)
            blobs[key] = content
        implementations, policies = {}, {}
        for key, blob in connection.execute("SELECT * FROM implementation_specs"):
            spec = codec.Spec(blobs[blob])
            codec.require(spec.data()["type"] == "implementation-spec/v1" and spec.sha256 == key)
            implementations[key] = (spec, blob)
        for key, implementation, blob in connection.execute("SELECT * FROM policy_specs"):
            spec = codec.Spec(blobs[blob])
            codec.require(spec.data()["type"] == "policy-spec/v1" and spec.sha256 == key and spec.data()["implementation_hash"] == implementation)
            _policy_object(spec)
            policies[key] = spec
        replay = _Replay(blobs, implementations, policies, catalog, limits)
        transaction_ids, event_ids = set(), set()
        for row in connection.execute("SELECT * FROM events ORDER BY sequence"):
            if time.monotonic() > deadline:
                raise LedgerLimitError("Replay deadline exceeded")
            envelope = codec.Envelope(row[-1])
            e = envelope.data()
            expected = tuple(e[name] for name in ("sequence", "event_id", "transaction_id", "transaction_index", "transaction_count", "kind", "payload_codec", "payload_sha256", "previous_event_sha256", "event_sha256", "occurred_at", "actor_id")) + (envelope.canonical,)
            codec.require(row == expected and e["transaction_id"] not in transaction_ids and e["event_id"] not in event_ids)
            transaction_ids.add(e["transaction_id"])
            event_ids.add(e["event_id"])
            replay.accept(envelope, codec.Payload(blobs[e["payload_sha256"]]))
        state = replay.finalize()
        for table, expected in replay.rows.items():
            # Table names are fixed schema constants; no source-controlled SQL.
            codec.require(set(connection.execute("SELECT * FROM " + table)) == set(expected))
        return state, replay
    except (codec.CodecError, ValueError, TypeError, KeyError, IndexError, RecursionError) as exc:
        raise CorruptLedgerError("Ledger content failed strict verified replay") from exc
    finally:
        connection.set_progress_handler(None, 0)


def load_ledger(path: str | Path, *, limits: LedgerLimits = DEFAULT_LIMITS) -> LedgerState:
    """Read-only verified source/event state. No source parsing or eligibility."""
    codec.require(type(limits) is LedgerLimits)
    checked = _path(path, limits)
    catalog = {kind: _local_spec(kind) for kind in ("docx", "xlsx")}
    try:
        connection = _connect(checked, readonly=True)
        try:
            with _transaction(connection):
                return _replay(connection, limits, catalog)[0]
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise _sql_error(exc) from exc


class SourceLedger:
    """One writer per thread, exact expected-head tokens and no generic append."""

    def __init__(self, path, connection, limits, catalog):
        self.path, self._connection, self.limits, self._catalog = path, connection, limits, catalog
        self._lock, self._capture_authority = RLock(), set()

    @classmethod
    def create(cls, path: str | Path, *, actor_id: str, limits: LedgerLimits = DEFAULT_LIMITS):
        codec.text(actor_id)
        codec.require(type(limits) is LedgerLimits)
        path = _path(path, limits)
        if sqlite3.sqlite_version_info < (3, 37, 0):
            raise UnsupportedLedgerError("STRICT SQLite tables are required")
        try:
            with path.open("xb"):
                pass
        except OSError as exc:
            raise UnsafePathError("New ledger requires an unused explicit path") from exc
        connection = None
        try:
            connection = _connect(path, readonly=False)
            catalog = {kind: _local_spec(kind) for kind in ("docx", "xlsx")}
            store = cls(path, connection, limits, catalog)
            with _transaction(connection, write=True):
                for statement in schema.STATEMENTS:
                    connection.execute(statement)
                connection.execute("PRAGMA user_version=2")
                store_id = uuid4().hex
                payload = codec.make_payload(codec.EventKind.INITIALIZED, store_uuid=store_id, schema_version=2,
                    serialization_version=codec.SERIALIZATION_VERSION, feature_profile="staging_only")
                if len(payload.canonical) > limits.max_metadata_bytes - 1024 * limits.max_registries:
                    raise LedgerLimitError("Insufficient metadata/control capacity for genesis")
                store._append(payload, LedgerHead(store_id, 1, "0" * 64), actor_id, genesis=True)
                connection.execute("INSERT INTO store_metadata VALUES (1,?,?,?,?,?,?,?)", (store_id, 2, codec.EVENT_CODEC,
                    codec.SERIALIZATION_VERSION, "staging_only", 1, connection.execute("SELECT event_sha256 FROM events").fetchone()[0]))
                store._verify_size()
            store.load()
            return store
        except BaseException as exc:
            if connection is not None:
                connection.close()
            if isinstance(exc, sqlite3.Error):
                raise _sql_error(exc) from exc
            raise

    @classmethod
    def open(cls, path: str | Path, *, limits: LedgerLimits = DEFAULT_LIMITS):
        load_ledger(path, limits=limits)  # Refuse v1/unrelated content before RW open.
        checked = _path(path, limits)
        catalog = {kind: _local_spec(kind) for kind in ("docx", "xlsx")}
        try:
            connection = _connect(checked, readonly=False)
        except sqlite3.Error as exc:
            raise _sql_error(exc) from exc
        store = cls(checked, connection, limits, catalog)
        try:
            store.load()
            return store
        except BaseException:
            store.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._capture_authority.clear()

    def _live(self):
        if self._connection is None:
            raise LedgerError("Ledger is closed")
        _path(self.path, self.limits)

    def load(self) -> LedgerState:
        with self._lock:
            self._live()
            with _transaction(self._connection):
                return _replay(self._connection, self.limits, self._catalog)[0]

    def _blob(self, raw):
        key = codec.sha256(raw)
        found = self._connection.execute("SELECT content FROM content_blobs WHERE sha256=?", (key,)).fetchone()
        if found is None:
            self._connection.execute("INSERT INTO content_blobs VALUES (?,?,?)", (key, len(raw), raw))
        elif found != (raw,):
            raise CorruptLedgerError("BLOB identity collision")
        return key

    def _append(self, payload, head, actor, *, genesis=False):
        envelope = codec.make_envelope(payload, store_uuid=head.store_uuid, sequence=1 if genesis else head.sequence + 1,
            previous=None if genesis else head.event_sha256, event_id=uuid4().hex, transaction_id=uuid4().hex,
            occurred_at=payload.data().get("observed_at", payload.data().get("activated_at", codec.utc_now())), actor_id=actor)
        e = envelope.data()
        self._blob(payload.canonical)
        self._connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(e[name] for name in
            ("sequence", "event_id", "transaction_id", "transaction_index", "transaction_count", "kind", "payload_codec", "payload_sha256", "previous_event_sha256", "event_sha256", "occurred_at", "actor_id")) + (envelope.canonical,))
        if not genesis:
            self._connection.execute("UPDATE store_metadata SET last_sequence=?,last_event_hash=? WHERE singleton=1", (e["sequence"], e["event_sha256"]))
        return e["sequence"]

    def _verify_size(self):
        page_count = self._connection.execute("PRAGMA page_count").fetchone()[0]
        page_size = self._connection.execute("PRAGMA page_size").fetchone()[0]
        if page_count * page_size > self.limits.max_database_bytes:
            raise LedgerLimitError("Database size budget exceeded")

    def _mirror(self, replay):
        # Existing immutable rows must never be updated; insert only new rows.
        for table, expected in replay.rows.items():
            if table == "store_metadata":
                continue
            current = set(self._connection.execute("SELECT * FROM " + table))
            if table in schema.MUTABLE:
                self._connection.execute("DELETE FROM " + table)
                current = set()
            for row in expected:
                if row not in current:
                    self._connection.execute("INSERT INTO " + table + " VALUES (" + ",".join("?" for _ in row) + ")", row)

    def _write(self, expected, actor, prepare):
        codec.require(type(expected) is LedgerHead)
        codec.text(actor)
        exhausted = False
        with self._lock:
            self._live()
            with _transaction(self._connection, write=True):
                state, replay = _replay(self._connection, self.limits, self._catalog)
                if state.head != expected:
                    raise StaleWriteError("Expected ledger head is stale")
                payload, extras, result, exhaust_registry = prepare(state, replay)
                if len(state.events) >= self.limits.max_events - self.limits.max_registries:
                    if exhaust_registry is None:
                        raise LedgerLimitError("Normal event capacity exhausted")
                    payload = codec.make_payload(codec.EventKind.EXHAUSTED, registry_id=exhaust_registry, budget_name="events", observed_at=codec.utc_now())
                    extras, result = (), None
                metadata = {key: replay.blobs[key] for key in replay.metadata}
                metadata[codec.sha256(payload.canonical)] = payload.canonical
                for _, _, raw in extras:
                    if raw is not None:
                        metadata[codec.sha256(raw)] = raw
                if payload.kind is not codec.EventKind.EXHAUSTED and sum(map(len, metadata.values())) > self.limits.max_metadata_bytes - 1024 * self.limits.max_registries:
                    if exhaust_registry is None:
                        raise LedgerLimitError("Normal metadata capacity exhausted")
                    payload = self._exhaust_payload(exhaust_registry, "metadata_bytes")
                    extras, result = (), None
                exhausted = payload.kind is codec.EventKind.EXHAUSTED
                if exhausted:
                    if len(state.events) >= self.limits.max_events:
                        raise LedgerLimitError("Control event capacity exhausted")
                    extras = ()
                for table, row, raw in extras:
                    if raw is not None:
                        self._blob(raw)
                    self._connection.execute("INSERT OR IGNORE INTO " + table + " VALUES (" + ",".join("?" for _ in row) + ")", row)
                self._append(payload, state.head, actor)
                # Rebuild rows from events, then compare with a fresh verified
                # replay before commit; all projections share this transaction.
                rebuilt = self._rebuild()
                self._mirror(rebuilt)
                verified = _replay(self._connection, self.limits, self._catalog)[0]
                self._verify_size()
            if exhausted:
                raise LedgerLimitError("Registry exhausted; terminal control event committed")
            return result if result is not None else verified

    def _rebuild(self):
        deadline = time.monotonic() + self.limits.max_replay_seconds
        blobs = {key: raw for key, raw in self._connection.execute("SELECT sha256,content FROM content_blobs")}
        impl = {key: (codec.Spec(blobs[blob]), blob) for key, blob in self._connection.execute("SELECT * FROM implementation_specs")}
        policies = {key: codec.Spec(blobs[blob]) for key, _, blob in self._connection.execute("SELECT * FROM policy_specs")}
        replay = _Replay(blobs, impl, policies, self._catalog, self.limits)
        for envelope, blob in self._connection.execute("SELECT envelope_json,payload_sha256 FROM events ORDER BY sequence"):
            if time.monotonic() > deadline:
                raise LedgerLimitError("Write replay deadline exceeded")
            replay.accept(codec.Envelope(envelope), codec.Payload(blobs[blob]))
        replay.finalize()
        return replay

    def register_implementation(self, kind: str, *, expected: LedgerHead, actor_id: str) -> str:
        spec = self._catalog.get(kind)
        if spec is None:
            raise InvalidCommandError("Only trusted local implementation kinds are supported")
        def prepare(state, replay):
            if spec.sha256 in replay.impl:
                raise InvalidCommandError("Implementation already registered")
            blob = codec.sha256(spec.canonical)
            return codec.make_payload(codec.EventKind.IMPLEMENTATION, implementation_hash=spec.sha256, descriptor_blob_sha256=blob), (("implementation_specs", (spec.sha256, blob), spec.canonical),), spec.sha256, None
        return self._write(expected, actor_id, prepare)

    def create_registry(self, kind: str, policy, *, expected: LedgerHead, actor_id: str) -> str:
        if kind not in self._catalog:
            raise InvalidCommandError("Unsupported registry kind")
        spec = _policy_spec(kind, policy, self._catalog[kind].sha256)
        rid, session = uuid4().hex, uuid4().hex
        def prepare(state, replay):
            if len(state.registries) >= self.limits.max_registries or spec.data()["implementation_hash"] not in replay.impl:
                raise InvalidCommandError("Registry capacity or implementation unavailable")
            payload = codec.make_payload(codec.EventKind.REGISTRY, registry_id=rid, kind=kind, session_id=session,
                initial_policy_revision=1, policy_spec_hash=spec.sha256, baseline_registry_epoch=1, baseline_history_units=0)
            return payload, (("policy_specs", (spec.sha256, spec.data()["implementation_hash"], codec.sha256(spec.canonical)), spec.canonical),), rid, None
        return self._write(expected, actor_id, prepare)

    def _registry(self, replay, registry_id):
        reg = replay.registries.get(registry_id)
        if reg is None or reg.exhausted:
            raise InvalidCommandError("Registry is unknown or exhausted")
        return reg

    def _exhaust_payload(self, rid, budget):
        return codec.make_payload(codec.EventKind.EXHAUSTED, registry_id=rid, budget_name=budget, observed_at=codec.utc_now())

    def activate_policy(self, registry_id: str, policy, *, expected: LedgerHead, actor_id: str) -> LedgerState:
        def prepare(state, replay):
            reg = self._registry(replay, registry_id)
            spec = _policy_spec(reg.kind, policy, self._catalog[reg.kind].sha256)
            current = _policy_object(spec)
            if spec == replay.activations[registry_id, reg.policy_revision].spec:
                raise InvalidCommandError("Policy activation must change configuration")
            if reg.history_units + 1 > current.max_history_units or reg.retained_bytes > current.max_retained_bytes or sum(owner == registry_id for owner in replay.sources.values()) > current.max_sources:
                return self._exhaust_payload(registry_id, "policy_capacity"), (), None, registry_id
            payload = codec.make_payload(codec.EventKind.POLICY, registry_id=registry_id, revision=reg.policy_revision + 1,
                predecessor_revision=reg.policy_revision, policy_spec_hash=spec.sha256, policy_fingerprint=current.fingerprint, activated_at=codec.utc_now())
            return payload, (("policy_specs", (spec.sha256, spec.data()["implementation_hash"], codec.sha256(spec.canonical)), spec.canonical),), None, registry_id
        return self._write(expected, actor_id, prepare)

    def begin_registration(self, registry_id: str, source_id: str, *, expected: LedgerHead,
                           expected_source: codec.SourceRef | None, actor_id: str, selection: xlsx_staging.SheetSelection | None = None) -> codec.SourceRef:
        codec.text(source_id)
        if expected_source is not None:
            codec.require(type(expected_source) is codec.SourceRef)
        def prepare(state, replay):
            reg = self._registry(replay, registry_id)
            old = replay.heads.get(source_id)
            if old != expected_source:
                raise StaleWriteError("Expected source revision is stale")
            if source_id in replay.sources and replay.sources[source_id] != registry_id:
                raise InvalidCommandError("Source ownership is immutable")
            if (reg.kind == "docx" and selection is not None) or (reg.kind == "xlsx" and type(selection) is not xlsx_staging.SheetSelection):
                raise InvalidCommandError("Explicit source-kind selection required")
            policy = _policy_object(replay.activations[registry_id, reg.policy_revision].spec)
            if reg.history_units + 3 > policy.max_history_units:
                return self._exhaust_payload(registry_id, "history"), (), None, registry_id
            if old is None and sum(owner == registry_id for owner in replay.sources.values()) >= policy.max_sources:
                return self._exhaust_payload(registry_id, "sources"), (), None, registry_id
            ref = codec.SourceRef(source_id, 1 if old is None else old.revision + 1, uuid4().hex)
            payload = codec.make_payload(codec.EventKind.STARTED, registry_id=registry_id, registration=ref.data(),
                predecessor_registration_id=None if old is None else old.registration_id, policy_revision=reg.policy_revision,
                reader_spec_hash=replay.activations[registry_id, reg.policy_revision].spec.data()["implementation_hash"],
                selection=None if selection is None else asdict(selection), declared_lineage=[], observed_at=codec.utc_now())
            return payload, (), ref, registry_id
        ref = self._write(expected, actor_id, prepare)
        self._capture_authority.add(ref)
        return ref

    def fail_source(self, ref: codec.SourceRef, *, expected: LedgerHead, actor_id: str, reason_code: str = "abandoned") -> LedgerState:
        codec.require(type(ref) is codec.SourceRef)
        if reason_code not in ("abandoned", "operator_failed"):
            raise InvalidCommandError("Unsupported explicit failure code")
        return self._record_failure(ref, expected, actor_id, reason_code, "interrupted" if reason_code == "abandoned" else "environment")

    def _record_failure(self, ref, expected, actor, code, phase):
        def prepare(state, replay):
            registration = state.registration(ref)
            self._registry(replay, registration.registry_id)
            if registration.status is not SourceStatus.PENDING:
                raise InvalidCommandError("Registration is terminal")
            return codec.make_payload(codec.EventKind.FAILED, registration=ref.data(), phase=phase, issue_codes=[code], observed_at=codec.utc_now()), (), None, registration.registry_id
        return self._write(expected, actor, prepare)

    def capture_source(self, ref: codec.SourceRef, path: str | Path, *, expected: LedgerHead, actor_id: str) -> LedgerState:
        codec.require(type(ref) is codec.SourceRef)
        codec.text(actor_id)
        with self._lock:
            initial = self.load()
            if initial.head != expected:
                raise StaleWriteError("Expected ledger head is stale before capture")
            registration = initial.registration(ref)
            if ref not in self._capture_authority or registration.binary_sha256 is not None or registration.status is not SourceStatus.PENDING:
                raise InvalidCommandError("Capture requires an unused live creating-writer registration")
            reg = next(item for item in initial.registries if item.registry_id == registration.registry_id)
            if reg.exhausted:
                raise InvalidCommandError("Registry is exhausted")
            policy = _policy_object(next(item for item in initial.policies if item.registry_id == reg.registry_id and item.revision == registration.policy_revision).spec)
            self._capture_authority.remove(ref)  # Never reread after an I/O/SQL/stale failure.
            raw, failure = None, None
            try:
                if not isinstance(path, (str, Path)) or Path(path).suffix.casefold() != "." + reg.kind or Path(path).is_symlink():
                    failure = "unsupported_input"
                else:
                    with Path(path).open("rb") as file:
                        metadata = os.fstat(file.fileno())
                        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > policy.reader_limits.max_file_bytes:
                            failure = "source_limit"
                        else:
                            raw = file.read(policy.reader_limits.max_file_bytes + 1)
                    if raw is not None and len(raw) > policy.reader_limits.max_file_bytes:
                        failure, raw = "source_limit", None
            except (OSError, ValueError):
                failure = "capture_failed"
            if failure is not None:
                return self._record_failure(ref, expected, actor_id, failure, "capture")
            def prepare(state, replay):
                current = state.registration(ref)
                registry = self._registry(replay, current.registry_id)
                if current.binary_sha256 is not None or current.status is not SourceStatus.PENDING:
                    raise InvalidCommandError("Registration already captured or terminal")
                key = codec.sha256(raw)
                if key in replay.blobs and replay.blobs[key] != raw:
                    raise CorruptLedgerError("Raw BLOB identity collision")
                active = _policy_object(replay.activations[registry.registry_id, registry.policy_revision].spec)
                extra = 0 if key in replay.reg_raw[registry.registry_id] else len(raw)
                total = sum(len(replay.blobs[h]) for h in replay.raw) + (0 if key in replay.raw else len(raw))
                if registry.retained_bytes + extra > active.max_retained_bytes or total > self.limits.max_original_bytes:
                    return self._exhaust_payload(registry.registry_id, "raw_bytes"), (), None, registry.registry_id
                # content_blobs is the only extras entry that stores raw data.
                return codec.make_payload(codec.EventKind.CAPTURED, registration=ref.data(), blob_sha256=key,
                    byte_length=len(raw), observed_at=codec.utc_now()), (("content_blobs", (key, len(raw), raw), None),), None, registry.registry_id
            return self._write(expected, actor_id, prepare)
