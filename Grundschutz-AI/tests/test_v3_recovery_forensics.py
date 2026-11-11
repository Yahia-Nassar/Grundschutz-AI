"""Disposable synthetic forensic experiments, NOT a recovery application/API.

Only the factory's private temporary fixtures are accepted. Original artifacts
are acquired read-only under exclusive Windows handles, then never opened RW.
The test-only engine operations run on new copies. No journal is manually deleted.
"""
from contextlib import ExitStack, closing
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import _sqlite3
import json
import msvcrt
import os
from pathlib import Path
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from grundschutz_ai import v3_ledger as ledger, v3_schema as schema, v2_a0 as paths

MODES = ("before-begin", "open-transaction", "registration-uncommitted",
         "capture-uncommitted", "page-spill", "hot-capture", "post-commit")
MAGIC = bytes.fromhex("d9d505f920a163d7")
NAMES = frozenset(("original.sqlite", "original.sqlite-journal", "original.sqlite-wal", "original.sqlite-shm"))
APP = Path(__file__).resolve().parents[1]
OLD_BYTES = b"FICTITIOUS retained PENDING revision one\r\n"
NEW_BYTES = (b"FICTITIOUS CAPTURE " + b"x" * 110) * 4096
SOURCE_ID = "2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355"


class Blocked(RuntimeError):
    """Test-only diagnostic block; never an adopted operational result."""


def require(condition):
    if not condition:
        raise Blocked("Synthetic forensic contract refused")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def runtime_identity():
    require(os.name == "nt" and sys.version_info[:3] == (3, 12, 6) and sqlite3.sqlite_version == "3.45.3")
    with closing(sqlite3.connect(":memory:")) as con:
        source = con.execute("SELECT sqlite_source_id()").fetchone()[0]
    require(source == SOURCE_ID)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    module = kernel.GetModuleHandleW
    module.argtypes, module.restype = (wintypes.LPCWSTR,), wintypes.HMODULE
    filename = kernel.GetModuleFileNameW
    filename.argtypes, filename.restype = (wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD), wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    handle = module("sqlite3.dll")
    require(bool(handle) and 0 < filename(handle, buffer, len(buffer)) < len(buffer))
    artifacts = (Path(sys.executable), Path(_sqlite3.__file__), Path(buffer.value))
    hashes = tuple(digest(path.read_bytes()) for path in artifacts)
    require(hashes == ("737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae",
                      "fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e",
                      "054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3"))
    return {"python": "3.12.6", "sqlite": "3.45.3", "sqlite_source_id": source,
            "runtime_artifacts": [(str(path), value) for path, value in zip(artifacts, hashes)]}


@dataclass(frozen=True, slots=True)
class Bundle:
    artifacts: tuple[tuple[str, bytes], ...]

    @property
    def manifest(self):
        return tuple((name, len(raw), digest(raw)) for name, raw in self.artifacts)

    @property
    def sha256(self):
        return digest(json.dumps(self.manifest, separators=(",", ":"), ensure_ascii=False).encode())

    def content(self, name):
        return next((raw for item, raw in self.artifacts if item == name), None)


def checked_fixture_directory(directory):
    """Reuse the frozen parent/volume guard; never weaken its WAL refusal.

    A fixed absent sentinel checks ancestry/volume outside Git without treating
    the examined DB as a loadable store. Fixed leaf checks below also admit WAL
    bytes for evidence retention, NOT for recovery or SQLite interpretation.
    """
    directory = Path(directory)
    require(directory.is_absolute() and directory.resolve() == directory)
    temporary = Path(tempfile.gettempdir()).resolve()
    require(directory.is_relative_to(temporary))
    owner = next((p for p in directory.parents if p.name.startswith("grundschutz-v3-recovery-forensics-")), None)
    require(owner is not None and owner.parent == temporary)
    class Limit:
        max_database_bytes = 256 * 1024 * 1024
    paths._path(directory / ".forensic-ancestry-probe", Limit())
    return directory


def exclusive_read_handle(path):
    """OS-enforced deny-sharing acquisition; read-only, no writer termination."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x80000000, 0, None, 3, 0x00200080, None)
    if handle == ctypes.c_void_p(-1).value:
        raise Blocked("Exclusive read acquisition refused")
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close = kernel.CloseHandle
        close.argtypes, close.restype = (wintypes.HANDLE,), wintypes.BOOL
        close(handle)
        raise
    return os.fdopen(fd, "rb")


def capture_bundle(directory):
    directory = checked_fixture_directory(directory)
    names = sorted(p.name for p in directory.iterdir())
    require("original.sqlite" in names and len(names) <= 4 and set(names) <= NAMES)
    captured, total = [], 0
    with ExitStack() as stack:
        streams = []
        # Acquire ALL handles before reading ANY bytes; failure releases all.
        for name in names:
            path = directory / name
            before = path.lstat()
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                    not getattr(before, "st_file_attributes", 0) & 1024)
            require(before.st_size <= 256 * 1024 * 1024)
            stream = stack.enter_context(exclusive_read_handle(path))
            held = os.fstat(stream.fileno())
            require((before.st_dev, before.st_ino, before.st_size) == (held.st_dev, held.st_ino, held.st_size))
            streams.append((name, stream, held.st_size))
            total += held.st_size
            require(total <= 512 * 1024 * 1024)
        require(sorted(p.name for p in directory.iterdir()) == names)
        for name, stream, length in streams:
            raw = stream.read(length + 1)
            require(len(raw) == length)
            captured.append((name, raw))
        require(sorted(p.name for p in directory.iterdir()) == names)
    return Bundle(tuple(captured))


def materialize(bundle, parent):
    parent.mkdir()  # exclusive; never overwrite a supplied/existing destination
    checked_fixture_directory(parent)
    require(len(bundle.artifacts) <= 4 and len(set(n for n, _ in bundle.artifacts)) == len(bundle.artifacts))
    for name, raw in bundle.artifacts:
        require(name in NAMES and type(raw) is bytes)
        with (parent / name).open("xb") as stream:
            stream.write(raw)
    require(capture_bundle(parent) == bundle)
    return parent / "original.sqlite"


PRODUCER = r'''
import itertools,os,sys
from pathlib import Path
from uuid import UUID
from unittest.mock import patch
from grundschutz_ai import v3_ledger as l,v3_store as f,v3_codec as c,v3_native_catalog as catalog
root=Path(sys.argv[1]);mode=sys.argv[2]
path=root/'original'/'original.sqlite'
counter=itertools.count(1)
def uuid():return UUID(int=next(counter))
actor='synthetic:forensic-operator'
def begin(w,rid,sid):
 s=w.load();p=catalog.native_catalog()[0]
 return w.begin_registration(rid,sid,kind='docx',policy_revision=1,
  reader_spec_hash=p.spec.data()['reader_spec_hash'],handler_spec_hash=p.spec.sha256,
  expected=s.head,expected_registry=s.registry(rid),expected_source=s.source_head(sid),actor_id=actor)
def capture(w,rid,ref,source):
 s=w.load()
 return w.capture_source(ref,source,expected=s.head,expected_registry=s.registry(rid),
  expected_source=s.source_head(ref.source_id),actor_id=actor)
with patch.object(f,'uuid4',uuid),patch.object(l,'uuid4',uuid),patch.object(c,'utc_now',return_value='2026-11-11T14:00:00.000000Z'):
 f.create_initialized_store(path,actor_id=actor)
 w=l.SourceLedger.open(path);p=catalog.native_catalog()[0]
 w.register_implementation('docx',expected=w.load().head,actor_id=actor)
 w.register_handler(p.spec.sha256,expected=w.load().head,actor_id=actor)
 rid=w.create_registry('docx',session_id=uuid().hex,policy_spec=c.Spec(p.policy_ceiling),expected=w.load().head,actor_id=actor)
 old=begin(w,rid,'synthetic:forensic-main')
 source=root/'invented.docx';source.write_bytes(b'FICTITIOUS retained PENDING revision one\r\n')
 capture(w,rid,old,source)
 failed=begin(w,rid,'synthetic:forensic-failed');capture(w,rid,failed,root/'nonexistent.docx')
 if mode in ('capture-uncommitted','page-spill','hot-capture','post-commit'):
  target=begin(w,rid,'synthetic:forensic-main')
 # Only this known single producer exists. Each API call closed its handles;
 # this is a quiescent expected-history checkpoint, not acquisition of a live DB.
 (root/'checkpoint.sqlite').write_bytes(path.read_bytes())
 source.write_bytes((b'FICTITIOUS CAPTURE '+b'x'*110)*4096)
 original=l._connect
 class Crash:
  def __init__(self,con):self.con=con
  def __getattr__(self,name):return getattr(self.con,name)
  def execute(self,sql,*args):
   if sql=='BEGIN IMMEDIATE' and mode=='before-begin':os._exit(61)
   result=self.con.execute(sql,*args)
   if sql=='BEGIN IMMEDIATE' and mode=='open-transaction':os._exit(62)
   if sql.startswith('INSERT INTO registrations') and mode=='registration-uncommitted':os._exit(63)
   if sql.startswith('INSERT INTO content_blobs') and mode=='page-spill' and args[0][1]>=524288:os._exit(65)
   if sql.startswith('INSERT INTO source_captures') and mode in ('capture-uncommitted','hot-capture'):
    os._exit(64 if mode=='capture-uncommitted' else 66)
   if sql=='COMMIT' and mode=='post-commit':os._exit(67)
   return result
 def connect(path,*,readonly):
  con=original(path,readonly=readonly)
  if not readonly:
   if mode in ('page-spill','hot-capture'):
    con.execute('PRAGMA cache_size=2');con.execute('PRAGMA cache_spill=ON')
   return Crash(con)
  return con
 l._connect=connect
 if mode in ('before-begin','open-transaction','registration-uncommitted'):begin(w,rid,'synthetic:forensic-main')
 else:capture(w,rid,target,source)
 raise RuntimeError('Synthetic exit hook was not reached')
'''


@dataclass(frozen=True, slots=True)
class Fixture:
    root: Path
    mode: str
    evidence: Bundle
    checkpoint: ledger.LedgerState
    exit_code: int


def make_fixture(parent, mode):
    runtime_identity()
    require(mode in MODES)
    root = parent / ("case-" + mode)
    root.mkdir(); (root / "original").mkdir()
    checked_fixture_directory(root / "original")
    bootstrap = "import sys;sys.path.insert(0," + repr(str(APP)) + ");\n" + PRODUCER
    child = subprocess.run([sys.executable, "-I", "-B", "-c", bootstrap, str(root), mode],
        capture_output=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
    expected_code = 61 + MODES.index(mode)
    require(child.returncode == expected_code and not child.stdout and not child.stderr)
    evidence = capture_bundle(root / "original")
    materialize(evidence, root / "sealed")
    checkpoint = ledger.load_ledger(root / "checkpoint.sqlite")
    return Fixture(root, mode, evidence, checkpoint, child.returncode)


def journal_observation(bundle):
    raw = bundle.content("original.sqlite-journal")
    if raw is None:
        return {"present": False}
    data = {"present": True, "length": len(raw), "sha256": digest(raw), "magic": raw[:8].hex()}
    if len(raw) >= 28:
        data.update(zip(("record_count", "checksum_seed", "original_pages", "sector_bytes", "page_bytes"),
                        struct.unpack(">5I", raw[8:28])))
    return data  # Header observations alone NEVER grant hot/safe authority.


def sqlite_probe(path, *, readonly):
    """Narrow engine operation on a disposable copy; SQL is entirely read-only."""
    require(path.parent.name.startswith("work-") and checked_fixture_directory(path.parent) == path.parent)
    require(path.name == "original.sqlite")
    bundle = capture_bundle(path.parent)
    require(not any(n.endswith(("-wal", "-shm")) for n, _ in bundle.artifacts))
    runtime_identity()
    con = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
                          uri=True, timeout=0, isolation_level=None)
    try:
        con.execute("PRAGMA trusted_schema=OFF")
        con.execute("PRAGMA query_only=ON")
        require(con.execute("PRAGMA query_only").fetchone() == (1,))
        con.execute("BEGIN")
        result = con.execute("PRAGMA integrity_check").fetchall()
        con.execute("COMMIT")
        require(result == [("ok",)])
        return {"integrity": "ok", "sqlite_code": 0, "sqlite_name": "SQLITE_OK"}
    except sqlite3.Error as exc:
        return {"integrity": None, "sqlite_code": getattr(exc, "sqlite_errorcode", None),
                "sqlite_name": getattr(exc, "sqlite_errorname", None)}
    finally:
        con.close()


def qualified_work_copy(fixture, name, *, bundle=None):
    """Only an exact sealed, known synthetic producer case; not a generic tool."""
    bundle = fixture.evidence if bundle is None else bundle
    require(type(fixture) is Fixture and fixture.mode in MODES and bundle == fixture.evidence)
    require(not any(n.endswith(("-wal", "-shm")) for n, _ in bundle.artifacts))
    require(capture_bundle(fixture.root / "sealed") == fixture.evidence)
    require(capture_bundle(fixture.root / "original") == fixture.evidence)
    require(name.startswith("work-") and "/" not in name and "\\" not in name and ":" not in name)
    return materialize(bundle, fixture.root / name)


def readonly_backup_candidate(fixture, working):
    """Non-hot diagnostic backup, never a write to clear the source journal."""
    require(checked_fixture_directory(working.parent) == working.parent and working.parent.name.startswith("work-"))
    require(working.parent.parent == fixture.root and capture_bundle(working.parent) == fixture.evidence)
    require(not any(n.endswith(("-wal", "-shm")) for n, _ in fixture.evidence.artifacts))
    runtime_identity()
    destination = fixture.root / "candidate"
    destination.mkdir(); checked_fixture_directory(destination)
    candidate = destination / "candidate.sqlite"
    with candidate.open("xb"):
        pass
    with closing(sqlite3.connect(working.as_uri() + "?mode=ro", uri=True, timeout=0)) as source:
        source.execute("PRAGMA trusted_schema=OFF"); source.execute("PRAGMA query_only=ON")
        with closing(sqlite3.connect(candidate.as_uri() + "?mode=rw", uri=True, timeout=0)) as target:
            source.backup(target, pages=64, sleep=0.0)
    return candidate


def assert_expected_history(fixture, state):
    require(any(blob.content == OLD_BYTES for blob in state.original_blobs))
    if fixture.mode != "post-commit":
        require(state == fixture.checkpoint)
    else:
        previous = fixture.checkpoint
        require(state.events[:-1] == previous.events and state.head.sequence == previous.head.sequence + 1)
        require(state.events[-1].payload.kind.value == "source.captured")
        require(state.current_heads == previous.current_heads)
        current = state.registration(state.source_head("synthetic:forensic-main"))
        require(current.binary_sha256 == digest(NEW_BYTES) and current.status is ledger.SourceStatus.PENDING)
    require(all(blob in state.original_blobs for blob in fixture.checkpoint.original_blobs))
    require(all(r.status in (ledger.SourceStatus.PENDING, ledger.SourceStatus.FAILED) for r in state.registrations))
    require(state.registration(state.source_head("synthetic:forensic-failed")).failure_codes == ("capture_failed",))


def inspect_case(parent, mode):
    """Reproduce one owned case; return only diagnostic observations, no adoption."""
    fixture = make_fixture(parent, mode)
    original = fixture.root / "original" / "original.sqlite"
    try:
        ledger.load_ledger(original)
        ordinary = "accepted_without_sidecars"
    except ledger.LedgerError:
        ordinary = "refused"
    require(capture_bundle(original.parent) == fixture.evidence)
    work = qualified_work_copy(fixture, "work-probe")
    before = capture_bundle(work.parent)
    ro = sqlite_probe(work, readonly=True)
    require(capture_bundle(work.parent) == before)
    if ro["sqlite_code"] == sqlite3.SQLITE_READONLY_ROLLBACK:
        rw = sqlite_probe(work, readonly=False)
        require(rw["integrity"] == "ok" and not Path(str(work) + "-journal").exists())
        candidate = work
        operation = "engine_rollback_on_working_copy"
    else:
        require(ro["integrity"] == "ok")
        rw = None
        if fixture.evidence.content("original.sqlite-journal") is not None:
            candidate = readonly_backup_candidate(fixture, work)
            require(capture_bundle(work.parent) == before)
            operation = "readonly_backup_to_new_candidate"
        else:
            candidate = work
            operation = "full_replay_of_copy_without_sidecars"
    state = ledger.load_ledger(candidate)
    assert_expected_history(fixture, state)
    require(capture_bundle(original.parent) == fixture.evidence)
    require(capture_bundle(fixture.root / "sealed") == fixture.evidence)
    return {"mode": mode, "producer_exit": fixture.exit_code, "artifacts": fixture.evidence.manifest,
            "bundle_sha256": fixture.evidence.sha256, "journal": journal_observation(fixture.evidence),
            "main_changed_before_recovery": fixture.evidence.content("original.sqlite") != (fixture.root / "checkpoint.sqlite").read_bytes(),
            "ordinary_load": ordinary, "ro_probe": ro, "rw_probe": rw, "operation": operation,
            "verified_sequence": state.head.sequence, "head_sha256": state.head.event_sha256,
            "original_blob_hashes": [b.sha256 for b in state.original_blobs], "adopted": False}


class ForensicFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grundschutz-v3-recovery-forensics-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def case(self, mode="capture-uncommitted"):
        return make_fixture(self.root, mode)

    def unchanged(self, fixture):
        self.assertEqual(capture_bundle(fixture.root / "original"), fixture.evidence)
        self.assertEqual(capture_bundle(fixture.root / "sealed"), fixture.evidence)


class RealInterruptionTests(ForensicFixture):
    def observe(self, mode, sequence):
        observed = inspect_case(self.root, mode)
        self.assertEqual(observed["verified_sequence"], sequence)
        self.assertFalse(observed["adopted"])
        return observed

    def test_exit_before_begin_preserves_committed_history_without_sidecar(self):
        result = self.observe("before-begin", 8)
        self.assertFalse(result["journal"]["present"])
        self.assertFalse(result["main_changed_before_recovery"])
        self.assertEqual(result["ordinary_load"], "accepted_without_sidecars")

    def test_exit_during_empty_open_transaction_has_no_partial_registration(self):
        result = self.observe("open-transaction", 8)
        self.assertFalse(result["journal"]["present"])
        self.assertFalse(result["main_changed_before_recovery"])

    def test_exit_during_registration_retains_original_pending_head(self):
        result = self.observe("registration-uncommitted", 8)
        self.assertEqual(result["ordinary_load"], "refused")
        self.assertFalse(result["main_changed_before_recovery"])
        self.assertEqual(result["operation"], "readonly_backup_to_new_candidate")

    def test_residual_non_hot_journal_not_deleted_or_cleared_by_update(self):
        result = self.observe("capture-uncommitted", 9)
        self.assertEqual(result["journal"]["magic"], "0000000000000000")
        self.assertEqual(result["ro_probe"]["sqlite_code"], 0)
        self.assertEqual(result["operation"], "readonly_backup_to_new_candidate")
        self.assertFalse(result["main_changed_before_recovery"])

    def test_genuine_hot_journal_after_page_spill_requires_engine_rollback(self):
        result = self.observe("page-spill", 9)
        self.assertTrue(result["main_changed_before_recovery"])
        self.assertEqual(result["journal"]["magic"], MAGIC.hex())
        self.assertGreater(result["journal"]["record_count"], 0)
        self.assertEqual(result["ro_probe"]["sqlite_name"], "SQLITE_READONLY_ROLLBACK")
        self.assertEqual(result["rw_probe"]["integrity"], "ok")
        self.assertEqual(result["operation"], "engine_rollback_on_working_copy")

    def test_genuine_hot_capture_rolls_back_event_blob_and_mirrors_together(self):
        result = self.observe("hot-capture", 9)
        self.assertEqual(result["ro_probe"]["sqlite_code"], 776)
        self.assertEqual(result["ordinary_load"], "refused")
        self.assertTrue(result["main_changed_before_recovery"])
        self.assertEqual(result["original_blob_hashes"], [digest(OLD_BYTES)])

    def test_post_commit_lost_ack_preserves_pending_capture_and_bytes(self):
        result = self.observe("post-commit", 10)
        self.assertFalse(result["journal"]["present"])
        self.assertEqual(set(result["original_blob_hashes"]), {digest(OLD_BYTES), digest(NEW_BYTES)})
        self.assertEqual(result["ordinary_load"], "accepted_without_sidecars")


class CustodyAndSuspicionTests(ForensicFixture):
    def test_exact_bundle_bytes_hashes_and_independent_copy_identities(self):
        fixture = self.case()
        path = qualified_work_copy(fixture, "work-exact")
        for name, length, value in fixture.evidence.manifest:
            raw = (fixture.root / "original" / name).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (length, value))
            self.assertEqual((path.parent / name).read_bytes(), raw)
            self.assertNotEqual((fixture.root / "original" / name).stat().st_ino, (path.parent / name).stat().st_ino)
        self.unchanged(fixture)

    def rejected_bundle(self, fixture, bundle):
        with patch(__name__ + ".sqlite_probe", side_effect=AssertionError("must not invoke engine")) as engine:
            with self.assertRaises(Blocked): qualified_work_copy(fixture, "work-suspect", bundle=bundle)
            engine.assert_not_called()
        self.assertFalse((fixture.root / "work-suspect").exists())
        self.unchanged(fixture)

    def test_missing_journal_blocked_by_independent_custody_manifest(self):
        fixture = self.case("hot-capture")
        self.rejected_bundle(fixture, Bundle(tuple(a for a in fixture.evidence.artifacts if not a[0].endswith("-journal"))))

    def test_truncated_header_and_body_blocked_before_sqlite(self):
        fixture = self.case("hot-capture")
        for length in (0, 12, 28, 512):
            with self.subTest(length=length):
                bundle = Bundle(tuple((n, raw[:length] if n.endswith("-journal") else raw) for n, raw in fixture.evidence.artifacts))
                self.rejected_bundle(fixture, bundle)

    def test_journal_transplant_from_another_real_producer_blocked(self):
        first = self.case("hot-capture"); second = self.case("page-spill")
        foreign = second.evidence.content("original.sqlite-journal")
        self.assertNotEqual(foreign, first.evidence.content("original.sqlite-journal"))
        bundle = Bundle(tuple((n, foreign if n.endswith("-journal") else raw) for n, raw in first.evidence.artifacts))
        self.rejected_bundle(first, bundle); self.unchanged(second)

    def test_unknown_origin_remains_blocked_even_with_readable_non_hot_shape(self):
        from dataclasses import replace
        fixture = self.case()
        unqualified = replace(fixture, mode="unknown-origin")
        with self.assertRaises(Blocked): qualified_work_copy(unqualified, "work-unknown")
        self.unchanged(fixture)

    def test_wal_and_shm_preserved_as_evidence_but_never_recovered(self):
        from dataclasses import replace
        fixture = self.case()
        bundle = Bundle(tuple(sorted(fixture.evidence.artifacts + (
            ("original.sqlite-wal", b"FICTITIOUS UNEXPECTED WAL"),
            ("original.sqlite-shm", b"FICTITIOUS UNEXPECTED SHM")))))
        suspect = materialize(bundle, fixture.root / "suspect-wal")
        self.assertEqual(capture_bundle(suspect.parent), bundle)
        with self.assertRaises(ledger.LedgerError): ledger.load_ledger(suspect)
        with self.assertRaises(Blocked): qualified_work_copy(replace(fixture, evidence=bundle), "work-wal")
        self.assertEqual(capture_bundle(suspect.parent), bundle)
        self.unchanged(fixture)

    def test_unexpected_file_stops_acquisition_not_silently_ignored(self):
        fixture = self.case()
        suspect = materialize(fixture.evidence, fixture.root / "unexpected-files")
        extra = suspect.parent / "unexpected.bin"; extra.write_bytes(b"FICTITIOUS UNKNOWN ARTIFACT")
        with self.assertRaises(Blocked): capture_bundle(suspect.parent)
        self.assertEqual(extra.read_bytes(), b"FICTITIOUS UNKNOWN ARTIFACT")
        self.unchanged(fixture)

    def test_exclusive_acquisition_refuses_existing_open_handle(self):
        fixture = self.case()
        with (fixture.root / "original" / "original.sqlite-journal").open("rb"):
            with self.assertRaises(Blocked): capture_bundle(fixture.root / "original")
        # Failure at the second artifact must release the first exclusive handle.
        self.unchanged(fixture)

    def test_live_sqlite_writer_prevents_forensic_acquisition(self):
        fixture = self.case("before-begin")
        with closing(sqlite3.connect(fixture.root / "original" / "original.sqlite")) as writer:
            writer.execute("BEGIN IMMEDIATE")
            with self.assertRaises(Blocked): capture_bundle(fixture.root / "original")
            writer.rollback()
        self.unchanged(fixture)

    def test_hard_link_artifact_refused(self):
        fixture = self.case()
        alias = fixture.root / "linked-evidence.sqlite"
        os.link(fixture.root / "original" / "original.sqlite", alias)
        try:
            with self.assertRaises(Blocked): capture_bundle(fixture.root / "original")
        finally:
            alias.unlink()  # Owned test alias only; never a journal or recovery action.
        self.unchanged(fixture)

    def test_unsafe_outside_git_or_relative_workspace_never_opened(self):
        for path in (APP, Path("relative"), self.root / "not-created" / ".."):
            with self.subTest(path=path), self.assertRaises(Blocked): checked_fixture_directory(path)

    def test_engine_operation_cannot_target_original_artifacts(self):
        fixture = self.case()
        with self.assertRaises(Blocked): sqlite_probe(fixture.root / "original" / "original.sqlite", readonly=False)
        self.unchanged(fixture)

    def test_ordinary_loaders_refuse_journal_before_sqlite_connection(self):
        from grundschutz_ai import v3_store
        fixture = self.case("hot-capture"); original = fixture.root / "original" / "original.sqlite"
        for module, load, error in ((ledger, ledger.load_ledger, ledger.LedgerError),
                                    (v3_store, v3_store.load_initialized_store, v3_store.StoreError)):
            with patch.object(module, "_connect", side_effect=AssertionError("no recovery on ordinary open")) as connect:
                with self.assertRaises(error): load(original)
                connect.assert_not_called()
        self.unchanged(fixture)


class ReplayAndAuthorityTests(ForensicFixture):
    def clean_candidate(self):
        fixture = self.case("before-begin")
        path = qualified_work_copy(fixture, "work-clean")
        self.assertEqual(ledger.load_ledger(path), fixture.checkpoint)
        return fixture, path

    def test_integrity_ok_does_not_accept_forged_projection(self):
        fixture, candidate = self.clean_candidate()
        with closing(sqlite3.connect(candidate)) as con:
            con.execute("UPDATE registry_state SET epoch=epoch+1"); con.commit()
        self.assertEqual(sqlite_probe(candidate, readonly=True)["integrity"], "ok")
        with self.assertRaises(ledger.LedgerError): ledger.load_ledger(candidate)
        self.unchanged(fixture)

    def test_integrity_ok_does_not_accept_corrupt_original_blob(self):
        fixture, candidate = self.clean_candidate()
        with closing(sqlite3.connect(candidate)) as con:
            trigger = con.execute("SELECT sql FROM sqlite_master WHERE name='content_blobs_no_update'").fetchone()[0]
            con.execute("DROP TRIGGER content_blobs_no_update")
            con.execute("UPDATE content_blobs SET content=zeroblob(byte_length) WHERE sha256 IN (SELECT binary_sha256 FROM source_captures)")
            con.execute(trigger); con.commit()
        self.assertEqual(sqlite_probe(candidate, readonly=True)["integrity"], "ok")
        with self.assertRaises(ledger.LedgerError): ledger.load_ledger(candidate)
        self.unchanged(fixture)

    def test_integrity_ok_does_not_accept_missing_event(self):
        fixture, candidate = self.clean_candidate()
        with closing(sqlite3.connect(candidate)) as con:
            trigger = con.execute("SELECT sql FROM sqlite_master WHERE name='events_no_delete'").fetchone()[0]
            con.execute("DROP TRIGGER events_no_delete"); con.execute("DELETE FROM events WHERE sequence=2")
            con.execute(trigger); con.commit()
        self.assertEqual(sqlite_probe(candidate, readonly=True)["integrity"], "ok")
        with self.assertRaises(ledger.LedgerError): ledger.load_ledger(candidate)
        self.unchanged(fixture)

    def test_loss_of_committed_suffix_requires_external_head_evidence(self):
        fixture = self.case("post-commit")
        # A complete older, self-consistent DB can pass replay; it is not the
        # observed committed result. Hash chains alone cannot authenticate it.
        earlier = ledger.load_ledger(fixture.root / "checkpoint.sqlite")
        with self.assertRaises(Blocked): assert_expected_history(fixture, earlier)
        self.unchanged(fixture)

    def test_reopened_recovered_pending_never_regains_mutable_path_capture_authority(self):
        fixture, candidate = self.clean_candidate()
        state = ledger.load_ledger(candidate)
        ref = state.source_head("synthetic:forensic-main")
        with ledger.SourceLedger.open(candidate) as writer:
            with patch.object(ledger, "_read_original", side_effect=AssertionError("no recapture")) as reader:
                with self.assertRaises(ledger.InvalidCommandError):
                    writer.capture_source(ref, fixture.root / "invented.docx", expected=state.head,
                        expected_registry=state.registry(state.registration(ref).registry_id), expected_source=ref,
                        actor_id="synthetic:forensic-operator")
                reader.assert_not_called()
        self.assertEqual(ledger.load_ledger(candidate), state); self.unchanged(fixture)

    def test_runtime_and_physical_schema_remain_exact(self):
        self.assertEqual(runtime_identity()["sqlite_source_id"], SOURCE_ID)
        self.assertEqual(schema.schema_fingerprint(), "75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c")

    def test_wrong_runtime_is_blocked_without_recovery(self):
        with patch.object(sqlite3, "sqlite_version", "3.45.4"):
            with self.assertRaises(Blocked): runtime_identity()


if __name__ == "__main__":
    unittest.main()
