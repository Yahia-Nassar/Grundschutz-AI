"""Frozen A0 read-only source-ledger handler (2ee9bc7).

The DTOs, filesystem, schema, event replay and projection checks below are
verbatim A-stage code. Policy parsing is frozen; connections are read-only.
No writer, reader invocation, staging, migration or domain API is present.
The public catalog pins this complete file and the unchanged A codec/schema.
"""
from contextlib import contextmanager
from dataclasses import dataclass, fields, replace
from enum import StrEnum
import os
from pathlib import Path
import sqlite3
import stat
import time

from . import v2_codec as codec, v2_schema as schema

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



# Literal complete A0 policies: both schema and ceilings are frozen, not read
# from the current staging dataclasses. Hash preimages are also historical.
_DEFAULT_POLICY_BYTES = (
    b'{"config":{"max_field_bytes":16384,"max_history_units":512,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_source_chars":2000,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_entries":16,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_segment_chars":16384,"max_segments":4096,"max_table_columns":128,"max_table_rows":1000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c","kind":"docx","semantic_version":"docx-single-assertion/v1","type":"policy-spec/v1"}',
    b'{"config":{"max_data_rows":100,"max_history_units":2048,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_scope_rows":100,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_cell_chars":16384,"max_cells":10000,"max_entries":64,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_shared_strings":10000,"max_shared_text_chars":1000000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_worksheets":16,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2","kind":"xlsx","semantic_version":"synthetic-it-table/v1","type":"policy-spec/v1"}',
)


@dataclass(frozen=True, slots=True)
class _ReaderPolicy:
    max_file_bytes: int


@dataclass(frozen=True, slots=True)
class _SourcePolicy:
    reader_limits: _ReaderPolicy
    max_sources: int
    max_retained_bytes: int
    max_history_units: int
    fingerprint: str


def _policy_object(spec):
    data = spec.data()
    baseline = next(codec.canonical_loads(raw) for raw in _DEFAULT_POLICY_BYTES
                    if codec.canonical_loads(raw)["kind"] == data["kind"])
    codec.require(data["type"] == "policy-spec/v1")
    codec.require(data["implementation_hash"] == baseline["implementation_hash"])
    codec.require(data["semantic_version"] == baseline["semantic_version"])
    config, ceiling = data["config"], baseline["config"]
    codec.exact(config, ceiling)
    for name, value in config.items():
        if name == "reader_limits":
            codec.exact(value, ceiling[name])
            for key, limit in value.items():
                codec.require(type(limit) is int and 1 <= limit <= ceiling[name][key])
        else:
            codec.require(type(value) is int and 1 <= value <= ceiling[name])
    preimage = {"version": data["semantic_version"], "limits": config,
                "implementation": "grundschutz_ai." + data["kind"] + "_staging/" +
                ("1.0.1" if data["kind"] == "docx" else "1.0.0")}
    if data["kind"] == "docx":
        preimage["support"] = "inventory-affirmative/v1"
    return _SourcePolicy(_ReaderPolicy(config["reader_limits"]["max_file_bytes"]),
                         config["max_sources"], config["max_retained_bytes"],
                         config["max_history_units"],
                         codec.sha256(codec.canonical_dumps(preimage)))

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
    if readonly is not True:
        raise UnsupportedLedgerError("Historical writer access is disabled")
    # URI is constructed from an already checked absolute path, not caller URI.
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only=ON")
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
def _transaction(connection):
    try:
        connection.execute("BEGIN")
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


def _load(path, limits, catalog):
    codec.require(type(limits) is LedgerLimits)
    checked = _path(path, limits)
    try:
        connection = _connect(checked, readonly=True)
        try:
            with _transaction(connection):
                return _replay(connection, limits, catalog)[0]
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise _sql_error(exc) from exc
