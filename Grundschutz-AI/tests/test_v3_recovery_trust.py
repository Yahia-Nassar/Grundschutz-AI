"""PUBLIC SYNTHETIC credentials and diagnostic contracts, never recovery authority.

No helper is imported by the application. The independent observer, custody
authority and maintenance service below are TEST ASSUMPTIONS in one process.
Public HMAC keys demonstrate binding/negative cases, NOT operational security.
Only the existing guarded forensic harness touches disposable SQLite copies.
"""
from contextlib import closing
from dataclasses import dataclass, asdict, replace
import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from grundschutz_ai import v3_codec as c, v3_schema as schema, v3_ledger as ledger
from tests import test_v3_recovery_forensics as f

VERIFIED = "TRUST_PREREQUISITES_VERIFIED"
INCOMPLETE = "INCOMPLETE_EVIDENCE"
CONFLICT = "CONFLICTING_EVIDENCE"
UNKNOWN = "QUARANTINED_UNKNOWN"
UNAUTHORIZED = "NOT_OPERATIONALLY_AUTHORIZED"
STAMP = "2026-11-11T14:01:00.000000Z"
CHALLENGE = "11111111111111111111111111111111"
PUBLIC_CHECKPOINT_KEY = bytes(range(32))
PUBLIC_CUSTODY_KEY = bytes(range(32, 64))
LIMITS = c.CodecLimits(max_bytes=32768, max_depth=16, max_nodes=4096,
                       max_array=64, max_string_bytes=2048)
PRODUCER = {"producer_id": "synthetic:observer-A", "key_id": "PUBLIC-TEST-ONLY-A",
            "authorization_context": "synthetic:independent-observation/v1", "authority_epoch": 1}
HEAD_FIELDS = "sequence event_sha256 event_id transaction_id transaction_index transaction_count kind".split()

# Literal UTF-8/no-newline vectors frozen from the independently replayed
# deterministic fixture. SHA/HMAC additionally checked with PowerShell/.NET,
# without calling checkpoint_data(), encode(), or sign(). Keys are PUBLIC.
LITERAL_9 = b'{"acknowledgement_basis":"independent_commit_observation","captures":[{"binary_sha256":"a1abab51aa326d76d1431e636a5ff3d4b5b99dce8fa77763986fbfb2f97bffff","byte_length":42,"event_sequence":6,"registration":{"registration_id":"0000000000000000000000000000000c","revision":1,"source_id":"synthetic:forensic-main"}}],"checkpoint_id":"00000000000000000000000000000001","checkpoint_version":"synthetic-committed-head/v1","encoding":"canonical-json/v1","event_codec":"ledger-event/v3","feature_profile":"verified-source/v1","head":{"event_id":"00000000000000000000000000000017","event_sha256":"5574fc047c06bbf118824837aaa941c0465daa3097c1aef46050abb49de97097","kind":"source.started","sequence":9,"transaction_count":1,"transaction_id":"00000000000000000000000000000018","transaction_index":1},"observed_at":"2026-11-11T14:01:00.000000Z","ordinal":1,"physical_profile":"sqlite-source-validation/v1","previous_sha256":null,"producer":{"authority_epoch":1,"authorization_context":"synthetic:independent-observation/v1","key_id":"PUBLIC-TEST-ONLY-A","producer_id":"synthetic:observer-A"},"recorded_at":"2026-11-11T14:01:00.000000Z","registry_heads":[{"epoch":6,"kind":"docx","policy_revision":1,"registry_id":"00000000000000000000000000000009","session_id":"00000000000000000000000000000008"}],"schema_fingerprint":"75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c","schema_version":3,"source_heads":[{"registration_id":"00000000000000000000000000000011","revision":1,"source_id":"synthetic:forensic-failed"},{"registration_id":"00000000000000000000000000000016","revision":2,"source_id":"synthetic:forensic-main"}],"store_uuid":"00000000000000000000000000000001"}'
LITERAL_10 = b'{"acknowledgement_basis":"independent_commit_observation","captures":[{"binary_sha256":"a1abab51aa326d76d1431e636a5ff3d4b5b99dce8fa77763986fbfb2f97bffff","byte_length":42,"event_sequence":6,"registration":{"registration_id":"0000000000000000000000000000000c","revision":1,"source_id":"synthetic:forensic-main"}},{"binary_sha256":"6def82774045b76e4ff723d04be1f996d115f65e6df78e96279f04eb3850f8f6","byte_length":528384,"event_sequence":10,"registration":{"registration_id":"00000000000000000000000000000016","revision":2,"source_id":"synthetic:forensic-main"}}],"checkpoint_id":"00000000000000000000000000000002","checkpoint_version":"synthetic-committed-head/v1","encoding":"canonical-json/v1","event_codec":"ledger-event/v3","feature_profile":"verified-source/v1","head":{"event_id":"00000000000000000000000000000019","event_sha256":"51ebd38912eb7c092097e1282c3e15a84caaac271b4d712c8dabc7a28b8197dd","kind":"source.captured","sequence":10,"transaction_count":1,"transaction_id":"0000000000000000000000000000001a","transaction_index":1},"observed_at":"2026-11-11T14:01:00.000000Z","ordinal":2,"physical_profile":"sqlite-source-validation/v1","previous_sha256":"3d1e6d0cee2496c1e7cd5dfd7884202065d19bb2147ebc0082d1a373b07c5d89","producer":{"authority_epoch":1,"authorization_context":"synthetic:independent-observation/v1","key_id":"PUBLIC-TEST-ONLY-A","producer_id":"synthetic:observer-A"},"recorded_at":"2026-11-11T14:01:00.000000Z","registry_heads":[{"epoch":7,"kind":"docx","policy_revision":1,"registry_id":"00000000000000000000000000000009","session_id":"00000000000000000000000000000008"}],"schema_fingerprint":"75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c","schema_version":3,"source_heads":[{"registration_id":"00000000000000000000000000000011","revision":1,"source_id":"synthetic:forensic-failed"},{"registration_id":"00000000000000000000000000000016","revision":2,"source_id":"synthetic:forensic-main"}],"store_uuid":"00000000000000000000000000000001"}'
VECTOR_9_SHA = "3d1e6d0cee2496c1e7cd5dfd7884202065d19bb2147ebc0082d1a373b07c5d89"
VECTOR_10_SHA = "fe723bd92d71c0492e80946caa12c8bedb23e5ac8ee9d96d091dc18b21606e2f"
VECTOR_9_MAC = "c5686427f8d5aec58cdc09d0294f3b46e75b371a20c468cbd0f104ccf81d851b"
VECTOR_10_MAC = "19bab497dd32ee7327e0ee8b618fa65cbf34c20c56f79bc0cbc115042e219fb6"


class Refusal(ValueError):
    def __init__(self, outcome):
        self.outcome = outcome
        super().__init__(outcome)


def need(condition, outcome=CONFLICT):
    if not condition:
        raise Refusal(outcome)


def encode(data):
    return c.canonical_dumps(data, LIMITS)


def decode(raw):
    return c.canonical_loads(raw, LIMITS)


@dataclass(frozen=True, slots=True)
class SignedDiagnostic:
    payload: bytes
    tag: str


def sign(data, purpose, key=PUBLIC_CHECKPOINT_KEY):
    raw = encode(data)
    return SignedDiagnostic(raw, hmac.digest(key, purpose.encode("ascii") + b"\0" + raw, "sha256").hex())


def authenticate(record, purpose, key=PUBLIC_CHECKPOINT_KEY):
    need(type(record) is SignedDiagnostic)
    expected = hmac.digest(key, purpose.encode("ascii") + b"\0" + record.payload, "sha256").hex()
    need(type(record.tag) is str and hmac.compare_digest(expected, record.tag))
    return decode(record.payload)


def state_binding(state):
    """Complete relevant heads/captures, not a hash of database packaging."""
    event = state.events[-1].envelope.data()
    return dict(store_uuid=state.head.store_uuid,
        head={key: event[key] for key in HEAD_FIELDS},
        registry_heads=[{key: asdict(r)[key] for key in
                        ("registry_id", "session_id", "kind", "policy_revision", "epoch")}
                        for r in sorted(state.registries, key=lambda r: r.registry_id)],
        source_heads=[asdict(ref) for ref in sorted(state.current_heads, key=lambda r: r.source_id)],
        captures=[dict(registration=asdict(r.ref), event_sequence=r.capture_event_sequence,
                       binary_sha256=r.binary_sha256, byte_length=r.byte_length)
                  for r in sorted(state.registrations, key=lambda r: r.ref.registration_id)
                  if r.capture_event_sequence is not None])


def checkpoint_data(state, ordinal=1, previous=None):
    return dict(checkpoint_version="synthetic-committed-head/v1", encoding=c.SERIALIZATION_VERSION,
        checkpoint_id=f"{ordinal:032x}", ordinal=ordinal, previous_sha256=previous,
        schema_version=3, physical_profile=c.PHYSICAL_PROFILE, feature_profile=c.FEATURE_PROFILE,
        schema_fingerprint=schema.SCHEMA_FINGERPRINT, event_codec=c.EVENT_CODEC,
        observed_at=STAMP, recorded_at=STAMP, producer=PRODUCER.copy(),
        acknowledgement_basis="independent_commit_observation", **state_binding(state))


def validate_checkpoint(data):
    """Exact bounded test proposal. Unknown members/types/profiles fail closed."""
    c.exact(data, ("checkpoint_version encoding checkpoint_id ordinal previous_sha256 schema_version "
        "physical_profile feature_profile schema_fingerprint event_codec observed_at recorded_at producer "
        "acknowledgement_basis store_uuid head registry_heads source_heads captures").split())
    need(data["checkpoint_version"] == "synthetic-committed-head/v1")
    need(data["encoding"] == c.SERIALIZATION_VERSION and data["event_codec"] == c.EVENT_CODEC)
    need(type(data["schema_version"]) is int and data["schema_version"] == 3)
    need(data["physical_profile"] == c.PHYSICAL_PROFILE and data["feature_profile"] == c.FEATURE_PROFILE)
    need(data["schema_fingerprint"] == schema.SCHEMA_FINGERPRINT)
    c.identity(data["checkpoint_id"]); c.identity(data["store_uuid"]); c.integer(data["ordinal"])
    if data["previous_sha256"] is not None:
        c.digest(data["previous_sha256"])
    need((data["ordinal"] == 1) == (data["previous_sha256"] is None))
    c.timestamp(data["observed_at"]); c.timestamp(data["recorded_at"])
    need(data["recorded_at"] >= data["observed_at"])
    c.exact(data["producer"], PRODUCER)
    c.integer(data["producer"]["authority_epoch"])
    need(data["producer"] == PRODUCER)
    need(data["acknowledgement_basis"] in ("client_commit_receipt", "independent_commit_observation"))
    head = data["head"]; c.exact(head, HEAD_FIELDS)
    c.integer(head["sequence"]); c.digest(head["event_sha256"])
    c.identity(head["event_id"]); c.identity(head["transaction_id"])
    for key in ("transaction_count", "transaction_index"):
        c.integer(head[key]); need(head[key] == 1)
    need(type(head["kind"]) is str and head["kind"] in c.EventKind._value2member_map_)
    for name in ("registry_heads", "source_heads", "captures"):
        need(type(data[name]) is list and len(data[name]) <= 64)
    for r in data["registry_heads"]:
        c.exact(r, "registry_id session_id kind policy_revision epoch".split())
        c.identity(r["registry_id"]); c.identity(r["session_id"])
        need(r["kind"] in ("docx", "xlsx")); c.integer(r["policy_revision"]); c.integer(r["epoch"])
    for ref in data["source_heads"]:
        c.SourceRef(**ref)
    for capture in data["captures"]:
        c.exact(capture, "registration event_sequence binary_sha256 byte_length".split())
        c.SourceRef(**capture["registration"]); c.integer(capture["event_sequence"])
        c.digest(capture["binary_sha256"]); c.integer(capture["byte_length"], 0)
        need(capture["event_sequence"] <= head["sequence"])
    for items, key in ((data["registry_heads"], "registry_id"), (data["source_heads"], "source_id")):
        keys = [item[key] for item in items]
        need(keys == sorted(set(keys)))
    ids = [item["registration"]["registration_id"] for item in data["captures"]]
    need(ids == sorted(set(ids)))


class SyntheticObserver:
    """External retained memory is assumed trusted. No file/secret/service writer."""
    def __init__(self):
        self.records = []

    def observe_committed_fixture(self, state):
        # ONLY callers in these tests supply a fully replayed committed state.
        previous = hashlib.sha256(self.records[-1].payload).hexdigest() if self.records else None
        data = checkpoint_data(state, len(self.records) + 1, previous)
        validate_checkpoint(data)
        if self.records:
            prior = decode(self.records[-1].payload)
            need(data["store_uuid"] == prior["store_uuid"])
            need(data["head"]["sequence"] > prior["head"]["sequence"])
        self.records.append(sign(data, "checkpoint"))
        return self.records[-1]

    def witness(self, challenge=CHALLENGE):
        need(bool(self.records), INCOMPLETE)
        latest = decode(self.records[-1].payload)
        return sign(dict(witness_version="synthetic-freshness/v1", challenge=challenge,
            store_uuid=latest["store_uuid"], ordinal=latest["ordinal"], authority_epoch=1,
            checkpoint_sha256=hashlib.sha256(self.records[-1].payload).hexdigest()), "witness")


def verify_chain(records, witness, challenge):
    need(bool(records) and witness is not None, INCOMPLETE)
    need(len(records) <= 64)
    prior, previous = None, None
    for ordinal, record in enumerate(records, 1):
        data = authenticate(record, "checkpoint"); validate_checkpoint(data)
        need(data["ordinal"] == ordinal and data["previous_sha256"] == previous, INCOMPLETE)
        if prior is not None:
            need(data["store_uuid"] == prior["store_uuid"])
            need(data["head"]["sequence"] > prior["head"]["sequence"])
        prior, previous = data, hashlib.sha256(record.payload).hexdigest()
    fresh = authenticate(witness, "witness")
    c.exact(fresh, "witness_version challenge store_uuid ordinal authority_epoch checkpoint_sha256".split())
    c.identity(challenge); c.identity(fresh["challenge"]); c.identity(fresh["store_uuid"])
    c.integer(fresh["ordinal"]); c.integer(fresh["authority_epoch"]); c.digest(fresh["checkpoint_sha256"])
    need(fresh["witness_version"] == "synthetic-freshness/v1" and fresh["authority_epoch"] == 1)
    need(fresh["challenge"] == challenge, INCOMPLETE)
    need(fresh["store_uuid"] == prior["store_uuid"])
    need(fresh["ordinal"] == prior["ordinal"] and fresh["checkpoint_sha256"] == previous, INCOMPLETE)
    return prior


def reconcile(state, records, witness, challenge=CHALLENGE):
    """Pure diagnostic: never appends events/checkpoints or returns an ack."""
    try:
        cp = verify_chain(records, witness, challenge)
        need(cp["store_uuid"] == state.head.store_uuid)
        n = cp["head"]["sequence"]
        need(state.head.sequence >= n)
        actual = state.events[n - 1].envelope.data()
        need({key: actual[key] for key in HEAD_FIELDS} == cp["head"])
        # Check every externally acknowledged intermediate prefix, not just tip.
        for record in records:
            item = decode(record.payload); e = state.events[item["head"]["sequence"] - 1].envelope.data()
            need({key: e[key] for key in HEAD_FIELDS} == item["head"])
        need(state.head.sequence == n, INCOMPLETE)
        need(all(state_binding(state)[key] == cp[key] for key in
                 ("registry_heads", "source_heads", "captures")))
        return VERIFIED
    except Refusal as exc:
        return exc.outcome
    except (c.CodecError, TypeError, KeyError, IndexError):
        return CONFLICT


def command_observation(state, intent):
    """Read-only lost-ack reconciliation against separately retained exact intent."""
    c.exact(intent, "store_uuid prior_sequence prior_sha256 registration binary_sha256 byte_length".split())
    n = intent["prior_sequence"]
    need(state.head.store_uuid == intent["store_uuid"] and type(n) is int and 1 <= n < len(state.events))
    need(state.events[n - 1].envelope.data()["event_sha256"] == intent["prior_sha256"])
    matches = [e for e in state.events[n:] if e.payload.kind is c.EventKind.CAPTURED and
               e.payload.data()["registration"] == intent["registration"]]
    need(len(matches) == 1)
    payload = matches[0].payload.data()
    need(payload["blob_sha256"] == intent["binary_sha256"] and payload["byte_length"] == intent["byte_length"])
    need(any(b.sha256 == payload["blob_sha256"] and len(b.content) == payload["byte_length"]
             for b in state.original_blobs))
    return "COMMITTED_MATCHES_INTENT_DIAGNOSTIC_ONLY"


def grant(store_uuid, challenge=CHALLENGE):
    return sign(dict(grant_version="synthetic-acquisition/v1", case_id="synthetic:case-A",
        store_uuid=store_uuid, operator_id="synthetic:operator-A", role="synthetic:custodian",
        reason="controlled interruption proof", action="acquire_diagnostic_copy",
        interlock_id="synthetic:interlock-A", challenge=challenge), "grant", PUBLIC_CUSTODY_KEY)


def authorized(record, store_uuid):
    need(record is not None, INCOMPLETE)
    actual = authenticate(record, "grant", PUBLIC_CUSTODY_KEY)
    need(actual == decode(grant(store_uuid).payload))


def identities(directory):
    return tuple((p.name, p.lstat().st_dev, p.lstat().st_ino, p.lstat().st_size)
                 for p in sorted(directory.iterdir()))


@dataclass(frozen=True, slots=True)
class AcquiredEvidence:
    """Observed fixture data, NOT an authentication capability or custody root."""
    bundle: f.Bundle
    file_ids: tuple[tuple[str, int, int, int], ...]


def acquire_diagnostic(directory, authorization, store_uuid, interlock):
    authorized(authorization, store_uuid)
    need(interlock(), INCOMPLETE)  # simulated maintenance service, NOT an OS guarantee
    directory = f.checked_fixture_directory(directory)
    observed = []
    original = f.exclusive_read_handle

    def acquire_member(path):
        stream = original(path)  # keep the unchanged read-only Windows share=0 safeguards
        try:
            held = os.fstat(stream.fileno())
            observed.append((path.name, held.st_dev, held.st_ino, held.st_size))
            return stream
        except BaseException:
            stream.close()
            raise

    try:
        before = identities(directory)  # local TOCTOU observation, not independent authority
        # The existing harness acquires ALL handles before reading ANY bytes;
        # record identities from those exact handles, never from caller input.
        with patch.object(f, "exclusive_read_handle", side_effect=acquire_member):
            bundle = f.capture_bundle(directory)
        need(interlock(), INCOMPLETE)
        need(tuple(observed) == before == identities(directory))
        need(tuple(item[0] for item in observed) == tuple(name for name, _ in bundle.artifacts))
        return AcquiredEvidence(bundle, tuple(observed))
    except OSError as exc:
        raise Refusal(CONFLICT) from exc  # disappearing/changing members never yield a partial observation


def custody_record(fixture):
    # Controlled fixture-observer role, assumed separately trusted in these tests.
    acquired = acquire_diagnostic(fixture.root / "original", grant(fixture.checkpoint.head.store_uuid),
                                  fixture.checkpoint.head.store_uuid, lambda: True)
    need(acquired.bundle == fixture.evidence)
    return sign(dict(custody_version="synthetic-known-producer/v1", case_id="synthetic:case-A",
        store_uuid=fixture.checkpoint.head.store_uuid, bundle_sha256=fixture.evidence.sha256,
        members=[list(item) for item in fixture.evidence.manifest],
        file_ids=[list(item) for item in acquired.file_ids],
        mode=fixture.mode, producer_exit=fixture.exit_code,
        producer_sha256=hashlib.sha256(f.PRODUCER.encode()).hexdigest(),
        sqlite_source_id=f.SOURCE_ID, journal_mode="delete", attached_databases=False,
        checkpoint_head_sha256=fixture.checkpoint.head.event_sha256), "custody", PUBLIC_CUSTODY_KEY)


def provenance(acquired, supplied, independently_retained, state, checkpoints, witness, challenge=CHALLENGE):
    """Bind protected observations to independently retained custody AND verified history.

    Retained trace/observer independence remains a synthetic authority assumption.
    Public signatures, caller-created DTOs and matching bytes alone confer no trust.
    No journal parsing, engine call, acknowledgement or file write occurs here.
    """
    try:
        need(independently_retained is not None, UNKNOWN)
        need(supplied is not None, INCOMPLETE)
        need(type(acquired) is AcquiredEvidence, INCOMPLETE)
        checkpoint_result = reconcile(state, checkpoints, witness, challenge)
        need(checkpoint_result == VERIFIED, checkpoint_result)
        checkpoint = verify_chain(checkpoints, witness, challenge)
        bundle = acquired.bundle
        data = authenticate(supplied, "custody", PUBLIC_CUSTODY_KEY)
        need(supplied == independently_retained)
        c.exact(data, ("custody_version case_id store_uuid bundle_sha256 members file_ids mode producer_exit "
            "producer_sha256 sqlite_source_id journal_mode attached_databases checkpoint_head_sha256").split())
        need(data["mode"] in f.MODES and data["journal_mode"] == "delete" and
             data["attached_databases"] is False and data["sqlite_source_id"] == f.SOURCE_ID, UNKNOWN)
        need(data["custody_version"] == "synthetic-known-producer/v1" and data["case_id"] == "synthetic:case-A")
        need(type(data["producer_exit"]) is int and data["producer_exit"] == 61 + f.MODES.index(data["mode"]))
        need(data["producer_sha256"] == hashlib.sha256(f.PRODUCER.encode()).hexdigest())
        c.identity(data["store_uuid"]); c.digest(data["checkpoint_head_sha256"])
        need(data["store_uuid"] == checkpoint["store_uuid"] == state.head.store_uuid)
        need(data["checkpoint_head_sha256"] == checkpoint["head"]["event_sha256"] == state.head.event_sha256)
        need(type(data["file_ids"]) is list and type(acquired.file_ids) is tuple)
        need(data["file_ids"] == [list(item) for item in acquired.file_ids])
        need(tuple(item[0] for item in acquired.file_ids) == tuple(name for name, _ in bundle.artifacts))
        for name, device, inode, length in acquired.file_ids:
            c.text(name)
            for value in (device, inode, length):
                need(type(value) is int and value >= 0)  # OS identities need not fit signed codec integers
        need(data["bundle_sha256"] == bundle.sha256 and data["members"] == [list(i) for i in bundle.manifest])
        need(not any(n.endswith(("-wal", "-shm")) for n, _ in bundle.artifacts), UNKNOWN)
        return VERIFIED
    except Refusal as exc:
        return exc.outcome
    except (c.CodecError, KeyError, TypeError, ValueError, IndexError):
        return CONFLICT


def readiness(*, checkpoint, custody, writer_control, operational=False):
    if operational:
        return UNAUTHORIZED  # no actual authentication/interlock/custody/adoption infrastructure
    for result in (custody, checkpoint, writer_control):
        if result != VERIFIED:
            return result
    return VERIFIED


class TrustFixture(unittest.TestCase):
    def setUp(self):
        f.runtime_identity()
        self.temp = tempfile.TemporaryDirectory(prefix="grundschutz-v3-recovery-forensics-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.fixtures = []

    def tearDown(self):
        for fixture in self.fixtures:
            self.assertEqual(f.capture_bundle(fixture.root / "original"), fixture.evidence)
            self.assertEqual(f.capture_bundle(fixture.root / "sealed"), fixture.evidence)

    def fixture(self, mode="before-begin"):
        fixture = f.make_fixture(self.root, mode)
        self.fixtures.append(fixture)
        return fixture

    def observer(self, state):
        observer = SyntheticObserver(); observer.observe_committed_fixture(state)
        return observer

    def recovered(self, fixture):
        work = f.qualified_work_copy(fixture, "work-reconcile")
        if fixture.evidence.content("original.sqlite-journal") is not None:
            probe = f.sqlite_probe(work, readonly=True)
            if probe["sqlite_code"] == sqlite3.SQLITE_READONLY_ROLLBACK:
                self.assertEqual(f.sqlite_probe(work, readonly=False)["integrity"], "ok")
            else:
                work = f.readonly_backup_candidate(fixture, work)
        return work, ledger.load_ledger(work)


class CheckpointProofTests(TrustFixture):
    def test_independent_literal_vectors_match_actual_committed_history(self):
        fx = self.fixture("post-commit"); _, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint); observer.observe_committed_fixture(state)
        for record, raw, sha, tag in zip(observer.records, (LITERAL_9, LITERAL_10),
                                       (VECTOR_9_SHA, VECTOR_10_SHA), (VECTOR_9_MAC, VECTOR_10_MAC)):
            self.assertEqual(record.payload, raw); self.assertEqual(record.tag, tag)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
            self.assertEqual(encode(decode(raw)), raw); validate_checkpoint(decode(raw))

    def test_literal_vectors_verify_without_checkpoint_factory(self):
        records = (SignedDiagnostic(LITERAL_9, VECTOR_9_MAC), SignedDiagnostic(LITERAL_10, VECTOR_10_MAC))
        # Literal witness preimage uses no checkpoint factory or signing helper.
        raw = (b'{"authority_epoch":1,"challenge":"11111111111111111111111111111111",'
               b'"checkpoint_sha256":"fe723bd92d71c0492e80946caa12c8bedb23e5ac8ee9d96d091dc18b21606e2f",'
               b'"ordinal":2,"store_uuid":"00000000000000000000000000000001",'
               b'"witness_version":"synthetic-freshness/v1"}')
        tag = hmac.digest(PUBLIC_CHECKPOINT_KEY, b"witness\0" + raw, "sha256").hex()
        with patch(__name__ + ".checkpoint_data", side_effect=AssertionError("No factory allowed")):
            self.assertEqual(verify_chain(records, SignedDiagnostic(raw, tag), CHALLENGE)["head"]["sequence"], 10)

    def test_clean_commit_matches_independent_checkpoint(self):
        fx = self.fixture(); _, state = self.recovered(fx); observer = self.observer(fx.checkpoint)
        self.assertEqual(reconcile(state, observer.records, observer.witness()), VERIFIED)

    def test_uncommitted_capture_absent_and_pending_bytes_retained_after_rollback(self):
        fx = self.fixture("hot-capture"); _, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint)
        self.assertEqual(reconcile(state, observer.records, observer.witness()), VERIFIED)
        self.assertEqual(state, fx.checkpoint)
        self.assertTrue(any(b.content == f.OLD_BYTES for b in state.original_blobs))
        self.assertFalse(any(b.content == f.NEW_BYTES for b in state.original_blobs))
        self.assertIsNone(state.registration(state.source_head("synthetic:forensic-main")).binary_sha256)

    def test_lost_client_ack_is_observed_not_fabricated(self):
        fx = self.fixture("post-commit"); path, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint); records = tuple(observer.records)
        original = path.read_bytes()
        self.assertEqual(reconcile(state, records, observer.witness()), INCOMPLETE)
        ref = state.source_head("synthetic:forensic-main")
        intent = dict(store_uuid=state.head.store_uuid, prior_sequence=fx.checkpoint.head.sequence,
            prior_sha256=fx.checkpoint.head.event_sha256, registration=asdict(ref),
            binary_sha256=f.digest(f.NEW_BYTES), byte_length=len(f.NEW_BYTES))
        self.assertEqual(command_observation(state, intent), "COMMITTED_MATCHES_INTENT_DIAGNOSTIC_ONLY")
        bad = {**intent, "binary_sha256": f.digest(f.OLD_BYTES)}
        with self.assertRaises(Refusal): command_observation(state, bad)
        self.assertEqual(tuple(observer.records), records)  # no new independent/client acknowledgement
        self.assertEqual(path.read_bytes(), original); self.assertEqual(ledger.load_ledger(path), state)
        self.assertEqual(state.registration(ref).status, ledger.SourceStatus.PENDING)

    def test_complete_independently_observed_commit_and_older_missing_suffix(self):
        fx = self.fixture("post-commit"); path, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint); observer.observe_committed_fixture(state)
        before = path.read_bytes()
        self.assertEqual(reconcile(state, observer.records, observer.witness()), VERIFIED)
        self.assertEqual(reconcile(fx.checkpoint, observer.records, observer.witness()), CONFLICT)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(state.head.sequence, 10); self.assertEqual(fx.checkpoint.head.sequence, 9)

    def test_altered_checkpoint_and_untrusted_self_consistent_checkpoint_rejected(self):
        fx = self.fixture(); observer = self.observer(fx.checkpoint)
        good = observer.records[0]; data = decode(good.payload)
        data["head"]["event_sha256"] = "0" * 64
        altered = replace(good, payload=encode(data))
        self.assertEqual(reconcile(fx.checkpoint, [altered], observer.witness()), CONFLICT)
        outsider = sign(decode(good.payload), "checkpoint", b"PUBLIC-UNTRUSTED-OUTSIDER")
        self.assertEqual(reconcile(fx.checkpoint, [outsider], observer.witness()), CONFLICT)

    def test_timestamp_cannot_establish_freshness(self):
        fx = self.fixture("post-commit"); _, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint); old = tuple(observer.records); old_witness = observer.witness()
        observer.observe_committed_fixture(state)
        self.assertEqual(reconcile(fx.checkpoint, old, observer.witness()), INCOMPLETE)
        self.assertEqual(reconcile(fx.checkpoint, old, old_witness, "2" * 32), INCOMPLETE)
        data = decode(old[0].payload); data["recorded_at"] = "2099-01-01T00:00:00.000000Z"
        self.assertEqual(reconcile(fx.checkpoint, [replace(old[0], payload=encode(data))], old_witness), CONFLICT)
        # Even authenticated future audit time grants no freshness in lieu of fresh external witness.
        signed_future = sign(data, "checkpoint")
        self.assertEqual(reconcile(fx.checkpoint, [signed_future], None), INCOMPLETE)

    def test_missing_checkpoint_gap_epoch_and_replayed_witness_fail_closed(self):
        fx = self.fixture("post-commit"); _, state = self.recovered(fx)
        observer = self.observer(fx.checkpoint); observer.observe_committed_fixture(state)
        self.assertEqual(reconcile(state, [], observer.witness()), INCOMPLETE)
        self.assertEqual(reconcile(state, observer.records[1:], observer.witness()), INCOMPLETE)
        self.assertEqual(reconcile(state, observer.records, None), INCOMPLETE)
        data = decode(observer.records[0].payload); data["producer"]["authority_epoch"] = 2
        self.assertEqual(reconcile(state, [sign(data, "checkpoint")], observer.witness()), CONFLICT)

    def test_exact_shape_types_profile_and_canonical_encoding(self):
        fx = self.fixture(); observer = self.observer(fx.checkpoint); good = decode(observer.records[0].payload)
        for field, value in (("unexpected", 1), ("schema_version", True), ("ordinal", True),
                             ("schema_fingerprint", "0" * 64), ("physical_profile", "unknown")):
            with self.subTest(field=field):
                data = {**good, field: value}
                self.assertEqual(reconcile(fx.checkpoint, [sign(data, "checkpoint")], observer.witness()), CONFLICT)
        noncanonical = replace(observer.records[0], payload=b" " + observer.records[0].payload)
        with self.assertRaises(c.CodecError): decode(noncanonical.payload)

    def test_mismatched_transaction_capture_or_source_head_rejected_even_if_signed(self):
        fx = self.fixture(); observer = self.observer(fx.checkpoint)
        for change in ("transaction", "capture", "source"):
            data = decode(observer.records[0].payload)
            if change == "transaction": data["head"]["transaction_id"] = "f" * 32
            elif change == "capture": data["captures"][0]["binary_sha256"] = "0" * 64
            else: data["source_heads"][0]["registration_id"] = "f" * 32
            record = sign(data, "checkpoint")
            # An external witness must name this exact record, not conceal a payload mismatch.
            fake_observer = SyntheticObserver(); fake_observer.records = [record]
            self.assertEqual(reconcile(fx.checkpoint, [record], fake_observer.witness()), CONFLICT)

    def test_identical_bytes_distinct_registrations_and_new_start_blocks_old_capture(self):
        fx = self.fixture(); path, before = self.recovered(fx); observer = self.observer(before)
        rid = before.registries[0].registry_id
        source = fx.root / "same-bytes.docx"; source.write_bytes(f.OLD_BYTES)
        with ledger.SourceLedger.open(path) as writer:
            profile = writer.load().handlers[0]
            def begin(sid):
                s = writer.load()
                return writer.begin_registration(rid, sid, kind="docx", policy_revision=1,
                    reader_spec_hash=profile.data()["reader_spec_hash"], handler_spec_hash=profile.sha256,
                    expected=s.head, expected_registry=s.registry(rid), expected_source=s.source_head(sid),
                    actor_id="synthetic:trust-fixture")
            sid = "synthetic:forensic-main"; ref = begin(sid); s = writer.load()
            captured = writer.capture_source(ref, source, expected=s.head, expected_registry=s.registry(rid),
                                            expected_source=ref, actor_id="synthetic:trust-fixture")
            old_ref = before.source_head(sid)
            self.assertNotEqual(ref, old_ref)
            self.assertEqual(captured.registration(ref).binary_sha256, before.registration(old_ref).binary_sha256)
            observer.observe_committed_fixture(captured)
            newer = begin(sid); latest = writer.load(); observer.observe_committed_fixture(latest)
        self.assertEqual(reconcile(captured, observer.records, observer.witness()), CONFLICT)
        self.assertEqual(reconcile(latest, observer.records, observer.witness()), VERIFIED)
        self.assertEqual(latest.source_head(sid), newer)
        self.assertIsNone(latest.registration(newer).capture_event_sequence)
        self.assertEqual(latest.registration(old_ref).status, ledger.SourceStatus.PENDING)

    def test_valid_fork_at_same_sequence_conflicts(self):
        fx = self.fixture(); branches = []
        for index in range(2):
            path = f.qualified_work_copy(fx, "work-fork-" + str(index))
            with ledger.SourceLedger.open(path) as writer:
                s = writer.load(); p = s.handlers[0]; rid = s.registries[0].registry_id
                writer.begin_registration(rid, "synthetic:fork-" + str(index), kind="docx", policy_revision=1,
                    reader_spec_hash=p.data()["reader_spec_hash"], handler_spec_hash=p.sha256,
                    expected=s.head, expected_registry=s.registry(rid), expected_source=None,
                    actor_id="synthetic:fork-producer")
                branches.append(writer.load())
        observer = self.observer(branches[0])
        self.assertEqual(branches[0].head.sequence, branches[1].head.sequence)
        self.assertEqual(reconcile(branches[1], observer.records, observer.witness()), CONFLICT)


class CustodyProofTests(TrustFixture):
    def acquire(self, fixture, directory=None):
        return acquire_diagnostic(directory or fixture.root / "original",
            grant(fixture.checkpoint.head.store_uuid), fixture.checkpoint.head.store_uuid, lambda: True)

    def assess(self, fixture, acquired, supplied, retained):
        observer = self.observer(fixture.checkpoint)
        return provenance(acquired, supplied, retained, fixture.checkpoint, observer.records, observer.witness())

    def test_known_producer_joint_manifest_and_current_checkpoint_qualify_synthetic_only(self):
        fx = self.fixture("hot-capture"); _, state = self.recovered(fx)
        custody = custody_record(fx); observer = self.observer(fx.checkpoint)
        checkpoint = reconcile(state, observer.records, observer.witness())
        acquired = self.acquire(fx)
        self.assertEqual(acquired.bundle, fx.evidence)
        self.assertEqual([list(item) for item in acquired.file_ids], decode(custody.payload)["file_ids"])
        result = provenance(acquired, custody, custody, state, observer.records, observer.witness())
        self.assertEqual(readiness(checkpoint=checkpoint, custody=result, writer_control=VERIFIED), VERIFIED)
        self.assertEqual(readiness(checkpoint=checkpoint, custody=result, writer_control=VERIFIED,
                                   operational=True), UNAUTHORIZED)

    def test_missing_trace_custody_and_authorization(self):
        fx = self.fixture(); record = custody_record(fx); acquired = self.acquire(fx)
        self.assertEqual(self.assess(fx, acquired, record, None), UNKNOWN)
        self.assertEqual(self.assess(fx, acquired, None, record), INCOMPLETE)
        with patch.object(f, "capture_bundle") as capture:
            with self.assertRaises(Refusal) as error:
                acquire_diagnostic(fx.root / "original", None, fx.checkpoint.head.store_uuid,
                                   lambda: True)
            self.assertEqual(error.exception.outcome, INCOMPLETE); capture.assert_not_called()

    def test_identical_bytes_under_different_file_identities_fail_custody(self):
        fx = self.fixture("hot-capture"); record = custody_record(fx)
        original = self.acquire(fx)
        copy = f.qualified_work_copy(fx, "work-identical-custody")
        copied = self.acquire(fx, copy.parent)
        self.assertEqual(original.bundle, copied.bundle)
        self.assertNotEqual(original.file_ids, copied.file_ids)
        self.assertEqual(self.assess(fx, original, record, record), VERIFIED)
        self.assertEqual(self.assess(fx, copied, record, record), CONFLICT)

    def test_valid_synthetic_custody_for_another_store_fails_binding(self):
        fx = self.fixture(); acquired = self.acquire(fx)
        data = decode(custody_record(fx).payload)
        data["store_uuid"] = "f" * 32
        foreign_record = sign(data, "custody", PUBLIC_CUSTODY_KEY)
        self.assertEqual(authenticate(foreign_record, "custody", PUBLIC_CUSTODY_KEY), data)
        # Even a valid retained record for another store cannot qualify this acquisition.
        self.assertEqual(self.assess(fx, acquired, foreign_record, foreign_record), CONFLICT)

    def test_valid_synthetic_custody_for_another_committed_head_fails_binding(self):
        fx = self.fixture("hot-capture"); acquired = self.acquire(fx)
        data = decode(custody_record(fx).payload)
        data["checkpoint_head_sha256"] = fx.checkpoint.events[-2].envelope.data()["event_sha256"]
        other_head = sign(data, "custody", PUBLIC_CUSTODY_KEY)
        self.assertEqual(authenticate(other_head, "custody", PUBLIC_CUSTODY_KEY), data)
        self.assertEqual(self.assess(fx, acquired, other_head, other_head), CONFLICT)

    def test_changed_or_missing_observed_member_identity_fails_binding(self):
        fx = self.fixture("hot-capture"); record = custody_record(fx); acquired = self.acquire(fx)
        name, device, inode, length = acquired.file_ids[0]
        changed = ((name, device, inode + 1, length),) + acquired.file_ids[1:]
        for observed in (changed, acquired.file_ids[1:], ()):
            with self.subTest(observed=observed):
                self.assertEqual(self.assess(fx, replace(acquired, file_ids=observed), record, record), CONFLICT)

    def test_disappearing_member_after_protected_read_refuses_acquisition(self):
        fx = self.fixture("hot-capture"); copy = f.qualified_work_copy(fx, "work-disappearing")
        original = f.capture_bundle
        def capture(directory):
            result = original(directory)  # unchanged safeguards actually acquire/read all members
            os.replace(Path(str(copy) + "-journal"), fx.root / "retained-copy-journal")
            return result
        with patch.object(f, "capture_bundle", side_effect=capture):
            with self.assertRaises(Refusal) as error:
                self.acquire(fx, copy.parent)
            self.assertEqual(error.exception.outcome, CONFLICT)

    def test_local_signatures_bytes_and_caller_identity_tuples_are_insufficient(self):
        fx = self.fixture(); record = custody_record(fx); acquired = self.acquire(fx)
        observer = self.observer(fx.checkpoint)
        self.assertEqual(self.assess(fx, acquired, record, None), UNKNOWN)
        self.assertEqual(self.assess(fx, acquired.bundle, record, record), INCOMPLETE)
        self.assertEqual(self.assess(fx, acquired.file_ids, record, record), INCOMPLETE)
        self.assertEqual(provenance(acquired, record, record, fx.checkpoint, [], None), INCOMPLETE)
        self.assertEqual(provenance(acquired, record, record, fx.checkpoint, observer.records, None), INCOMPLETE)

    def test_invalid_operator_role_store_scope_and_signature(self):
        fx = self.fixture(); uuid = fx.checkpoint.head.store_uuid
        for field, value in (("operator_id", "unknown"), ("role", "reader"), ("store_uuid", "f" * 32),
                             ("action", "adopt"), ("challenge", "2" * 32)):
            data = decode(grant(uuid).payload); data[field] = value
            with self.subTest(field=field), self.assertRaises(Refusal):
                authorized(sign(data, "grant", PUBLIC_CUSTODY_KEY), uuid)
        with self.assertRaises(Refusal): authorized(replace(grant(uuid), tag="0" * 64), uuid)

    def test_missing_interlock_or_revocation_during_acquisition(self):
        fx = self.fixture(); uuid = fx.checkpoint.head.store_uuid; directory = fx.root / "original"
        for answers in ((False,), (True, False)):
            responses = iter(answers)
            with self.assertRaises(Refusal) as error:
                acquire_diagnostic(directory, grant(uuid), uuid, lambda: next(responses))
            self.assertEqual(error.exception.outcome, INCOMPLETE)

    def test_stale_transplanted_truncated_missing_or_unknown_journal_never_reaches_engine(self):
        fx = self.fixture("hot-capture"); other = self.fixture("registration-uncommitted")
        record = custody_record(fx); acquired = self.acquire(fx)
        raw = fx.evidence.content("original.sqlite-journal")
        altered = (raw[:-1], raw[:20], other.evidence.content("original.sqlite-journal"))
        cases = [f.Bundle(tuple((n, r) for n, r in fx.evidence.artifacts if not n.endswith("-journal")))]
        cases += [f.Bundle(tuple((n, replacement if n.endswith("-journal") else r)
                                 for n, r in fx.evidence.artifacts)) for replacement in altered]
        with patch.object(f, "sqlite_probe") as engine:
            for bundle in cases:
                self.assertEqual(self.assess(fx, replace(acquired, bundle=bundle), record, record), CONFLICT)
            self.assertEqual(self.assess(fx, acquired, record, None), UNKNOWN)
            engine.assert_not_called()

    def test_unsupported_superjournal_trace_or_wal_is_quarantined_without_parsing(self):
        fx = self.fixture("hot-capture"); record = custody_record(fx); acquired = self.acquire(fx)
        for key, value in (("attached_databases", True), ("journal_mode", "wal"), ("mode", "unknown")):
            data = decode(record.payload); data[key] = value
            unsupported = sign(data, "custody", PUBLIC_CUSTODY_KEY)
            self.assertEqual(self.assess(fx, acquired, unsupported, unsupported), UNKNOWN)
        bundle = f.Bundle(fx.evidence.artifacts + (("original.sqlite-wal", b"UNTRUSTED"),))
        self.assertNotEqual(self.assess(fx, replace(acquired, bundle=bundle), record, record), VERIFIED)

    def test_live_sqlite_writer_transaction_blocks_exclusive_acquisition(self):
        fx = self.fixture(); path = f.qualified_work_copy(fx, "work-live")
        with closing(sqlite3.connect(path, timeout=0)) as con:
            con.execute("BEGIN IMMEDIATE")
            with self.assertRaises(f.Blocked): f.capture_bundle(path.parent)
            con.rollback()

    def test_another_owned_process_holds_incompatible_handle(self):
        fx = self.fixture(); path = f.qualified_work_copy(fx, "work-handle")
        script = "import sys; f=open(sys.argv[1],'rb'); print('READY',flush=True); sys.stdin.buffer.read(1); f.close()"
        process = subprocess.Popen([sys.executable, "-I", "-B", "-c", script, str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            # Bound readiness wait; terminate/reap only our own child if it fails.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                ready = pool.submit(process.stdout.readline)
                try: self.assertEqual(ready.result(timeout=5), b"READY\r\n")
                except BaseException:
                    process.kill(); process.wait(timeout=5); raise
            with self.assertRaises(f.Blocked): f.capture_bundle(path.parent)
        finally:
            if process.poll() is None:
                process.communicate(b"x", timeout=5)
            else:
                process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)

    def test_partial_acquisition_releases_all_earlier_handles(self):
        fx = self.fixture("hot-capture"); path = f.qualified_work_copy(fx, "work-partial")
        journal = path.with_name(path.name + "-journal")
        with f.exclusive_read_handle(journal):
            with self.assertRaises(f.Blocked): f.capture_bundle(path.parent)
            # First main handle was released after second acquisition failed.
            with f.exclusive_read_handle(path) as stream: self.assertGreater(len(stream.read(16)), 0)
        self.assertEqual(f.capture_bundle(path.parent), fx.evidence)

    def test_writer_restart_attempt_denied_while_acquisition_handles_held(self):
        fx = self.fixture(); path = f.qualified_work_copy(fx, "work-restart")
        script = "import sqlite3,sys\ntry:\n c=sqlite3.connect(sys.argv[1],timeout=0); c.execute('BEGIN IMMEDIATE')\nexcept sqlite3.Error:\n sys.exit(72)\nelse:\n c.rollback();c.close();sys.exit(0)"
        original = f.exclusive_read_handle
        def acquire(member):
            handle = original(member)
            try:
                child = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(path)],
                    capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                self.assertEqual(child.returncode, 72)
                return handle
            except BaseException:
                handle.close(); raise
        with patch.object(f, "exclusive_read_handle", side_effect=acquire):
            self.assertEqual(f.capture_bundle(path.parent), fx.evidence)
        # Denial lasts only while handles are held; this is NOT a persistent restart interlock.

    def test_identity_change_before_later_member_acquisition_rejected(self):
        fx = self.fixture("hot-capture"); path = f.qualified_work_copy(fx, "work-identity")
        directory = path.parent; original = f.exclusive_read_handle
        journal = Path(str(path) + "-journal"); replacement = fx.root / "replacement-journal"
        replacement.write_bytes(journal.read_bytes())
        def acquire(member):
            if member.name.endswith("-journal"):
                os.replace(replacement, member)  # only a disposable acquisition copy
            return original(member)
        with patch.object(f, "exclusive_read_handle", side_effect=acquire):
            with self.assertRaises(f.Blocked):
                acquire_diagnostic(directory, grant(fx.checkpoint.head.store_uuid), fx.checkpoint.head.store_uuid,
                                   lambda: True)

    def test_unsafe_alias_or_unexpected_member_refused(self):
        fx = self.fixture()
        for mode in ("extra", "alias"):
            path = f.qualified_work_copy(fx, "work-" + mode)
            if mode == "extra": (path.parent / "unknown-journal").write_bytes(b"UNKNOWN")
            else: os.link(path, fx.root / "extra-link.sqlite")
            with self.assertRaises(f.Blocked): f.capture_bundle(path.parent)

    def test_production_request_always_refused_and_labels_are_not_database_states(self):
        self.assertEqual(readiness(checkpoint=VERIFIED, custody=VERIFIED, writer_control=VERIFIED,
                                   operational=True), UNAUTHORIZED)
        self.assertEqual(readiness(checkpoint=INCOMPLETE, custody=VERIFIED, writer_control=VERIFIED), INCOMPLETE)
        self.assertEqual(readiness(checkpoint=VERIFIED, custody=UNKNOWN, writer_control=VERIFIED), UNKNOWN)
        self.assertEqual(readiness(checkpoint=CONFLICT, custody=VERIFIED, writer_control=VERIFIED), CONFLICT)
        # Native VALID was activated separately in TASK-007.3B.2.5.1; these
        # processing states still grant no recovery permission or human approval.
        self.assertEqual({s.value for s in ledger.SourceStatus}, {"pending", "failed", "valid"})


if __name__ == "__main__":
    unittest.main()
