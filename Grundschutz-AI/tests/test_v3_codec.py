"""Independent literal v3 vectors and inert-contract negative regressions."""
from dataclasses import FrozenInstanceError
import unittest

from grundschutz_ai import v3_codec as c, v2_codec as old

STAMP = "2026-11-11T12:00:00.000000Z"
GENESIS_RAW = b'{"feature_profile":"verified-source/v1","payload_codec":"store-init/v2","schema_version":3,"serialization_version":"canonical-json/v1","store_uuid":"00000000000000000000000000000000"}'
GENESIS_SHA = "f7fc5a269b8554c2be78810fe3aeb889fdc2e2357fe1de3f792d0d5961cfccce"
EVENT_SHA = "be5aa16f76c6634fdb14c4bb1238d638ee8ec890923d63d3a95cef702b64252a"
REF_RAW = b'{"registration_id":"11111111111111111111111111111111","revision":2,"source_id":"synthetic:source"}'
REF_SHA = "daa5c8f29826418829af7b9d60aba4511521d215945ea08a23dc99d125b73da3"


def genesis():
    return c.Payload(GENESIS_RAW)


def envelope(payload=None, **changes):
    values = dict(store_uuid="0" * 32, sequence=1, previous=None, event_id="1" * 32,
                  transaction_id="2" * 32, occurred_at=STAMP, actor_id="synthetic:human")
    values.update(changes)
    return c.make_envelope(payload or genesis(), **values)


def ref(revision=1, ident="1"):
    return {"source_id": "synthetic:source", "revision": revision, "registration_id": ident * 32}


def samples():
    return [
        (c.EventKind.INITIALIZED, genesis().data()),
        (c.EventKind.IMPLEMENTATION, dict(payload_codec="implementation-register/v1",
            implementation_hash="1" * 64, descriptor_blob_sha256="2" * 64)),
        (c.EventKind.HANDLER, dict(payload_codec="reader-handler-register/v1",
            handler_spec_hash="3" * 64, descriptor_blob_sha256="4" * 64)),
        (c.EventKind.REGISTRY, dict(payload_codec="registry-create/v1", registry_id="3" * 32,
            kind="docx", session_id="4" * 32, initial_policy_revision=1,
            policy_spec_hash="5" * 64, baseline_registry_epoch=1, baseline_history_units=0)),
        (c.EventKind.POLICY, dict(payload_codec="policy-activate/v1", registry_id="3" * 32,
            revision=2, predecessor_revision=1, policy_spec_hash="5" * 64,
            policy_fingerprint="6" * 64, activated_at=STAMP)),
        (c.EventKind.STARTED, dict(payload_codec="source-start/v2", registry_id="3" * 32,
            registration=ref(), predecessor_registration_id=None, policy_revision=1,
            reader_spec_hash="1" * 64, handler_spec_hash="2" * 64,
            selection=None, declared_lineage=[], observed_at=STAMP)),
        (c.EventKind.CAPTURED, dict(payload_codec="source-capture/v1", registration=ref(),
            blob_sha256="1" * 64, byte_length=27, observed_at=STAMP)),
        (c.EventKind.FAILED, dict(payload_codec="source-fail/v2", registration=ref(),
            phase="validation", issue_codes=["invalid_source"], observed_at=STAMP)),
        (c.EventKind.VALIDATED, dict(payload_codec="source-valid/v1", registration=ref(),
            capture_event_sequence=1, derivation_sha256="1" * 64,
            derivation_blob_sha256="2" * 64, source_head_at_validation=ref(), observed_at=STAMP)),
        (c.EventKind.EXHAUSTED, dict(payload_codec="registry-exhaust/v1",
            registry_id="3" * 32, budget_name="metadata_bytes", observed_at=STAMP)),
    ]


def derivation():
    return dict(type="derivation-ref/v2", store_uuid="0" * 32, registry_id="3" * 32,
        registration=ref(2), kind="docx", capture_event_sequence=1, binary_sha256="1" * 64,
        byte_length=27, reader_spec_hash="2" * 64, handler_spec_hash="8" * 64, policy_revision=1,
        policy_spec_hash="a" * 64, policy_fingerprint="b" * 64, reader_limits_sha256="5" * 64,
        reader_method="docx-plain/v1", reader_implementation_sha256="9" * 64,
        native_text_sha256="6" * 64, native_manifest_sha256=None, integration_manifest_sha256="7" * 64)


class V3CodecTests(unittest.TestCase):
    def test_literal_genesis_bytes_and_dotnet_digest(self):
        self.assertEqual(genesis().canonical, GENESIS_RAW)
        self.assertEqual(c.sha256(GENESIS_RAW), GENESIS_SHA)
        self.assertEqual(c.make_payload(c.EventKind.INITIALIZED, store_uuid="0" * 32,
            schema_version=3, serialization_version="canonical-json/v1",
            feature_profile="verified-source/v1").canonical, GENESIS_RAW)

    def test_literal_genesis_event_hash_independent_dotnet_vector(self):
        event = envelope()
        self.assertEqual(event.data()["event_sha256"], EVENT_SHA)
        self.assertEqual(event.data()["payload_sha256"], GENESIS_SHA)
        self.assertEqual(c.Event(event, genesis()).payload.canonical, GENESIS_RAW)

    def test_original_source_reference_bytes_and_identity_are_unchanged(self):
        self.assertIs(c.SourceRef, old.SourceRef)
        r = c.SourceRef.parse(ref(2))
        self.assertEqual(c.canonical_dumps(r.data()), REF_RAW)
        self.assertEqual(c.sha256(REF_RAW), REF_SHA)
        self.assertEqual(c.fingerprint("golden/v1", {"a": 1}),
                         "cfe2b97340217e4a08d67cb3142e6e9ca2139bed0f5f7a81c2aec1af5fe552a4")

    def test_independent_canonical_unicode_vector(self):
        expected = '{"a":1,"text":"Ä\\r\\n","z":[null,true,-2]}'.encode("utf-8")
        self.assertEqual(c.canonical_dumps({"z": [None, True, -2], "text": "Ä\r\n", "a": 1}), expected)
        self.assertEqual(c.sha256(expected), "0149df147f33e29c3279b9791c21bc3f2760869d0a7259ef5d6f61341c7ac396")

    def test_exact_ten_inert_contracts_and_factory(self):
        self.assertEqual(tuple(k.value for k, _ in samples()), tuple(k.value for k in c.EventKind))
        self.assertEqual(len(c.EVENT_CONTRACTS), 10)
        for kind, data in samples():
            with self.subTest(kind=kind):
                p = c.Payload(c.canonical_dumps(data))
                fields = {key: value for key, value in data.items() if key != "payload_codec"}
                self.assertEqual(c.make_payload(kind, **fields), p)
                self.assertIs(p.kind, kind)

    def test_every_payload_rejects_missing_and_unknown_fields(self):
        for kind, data in samples():
            for key in data:
                with self.subTest(kind=kind, missing=key), self.assertRaises(c.CodecError):
                    c.Payload(c.canonical_dumps({k: v for k, v in data.items() if k != key}))
            with self.subTest(kind=kind), self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({**data, "approved": True}))

    def test_factory_cannot_override_tag_or_take_arbitrary_kind(self):
        for kind in ("source.validated", "store.initialized", None):
            with self.assertRaises(c.CodecError):
                c.make_payload(kind)
        with self.assertRaises(c.CodecError):
            c.make_payload(c.EventKind.INITIALIZED, payload_codec="source-valid/v1")

    def test_unknown_future_legacy_or_wrong_payload_versions(self):
        for tag in ("store-init/v1", "source-start/v1", "source-fail/v1", "source-valid/v2",
                    "queue-decision/v1", "candidate-stage/v1", "document-domain/v2",
                    "document-review/v1", "export/v1", "legacy-import/v1", "pdf-promoted/v1"):
            with self.subTest(tag=tag), self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({"payload_codec": tag}))

    def test_payload_counters_do_not_accept_bool(self):
        for kind, data in samples():
            for key in ("schema_version", "revision", "policy_revision", "initial_policy_revision",
                        "baseline_registry_epoch", "baseline_history_units", "capture_event_sequence", "byte_length"):
                if key in data:
                    with self.subTest(kind=kind, key=key), self.assertRaises(c.CodecError):
                        c.Payload(c.canonical_dumps({**data, key: True}))

    def test_hashes_identifiers_and_timestamps_are_strict(self):
        for kind, data in samples():
            for key in data:
                if key.endswith(("_hash", "_sha256")):
                    with self.subTest(kind=kind, key=key), self.assertRaises(c.CodecError):
                        c.Payload(c.canonical_dumps({**data, key: "G" * 64}))
        for changes in ({"store_uuid": "1" * 31}, {"schema_version": 2},
                        {"feature_profile": "approved"}, {"serialization_version": "json/v99"}):
            with self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({**genesis().data(), **changes}))
        with self.assertRaises(c.CodecError):
            envelope(occurred_at="2026-02-30T12:00:00.000000Z")

    def test_duplicate_keys_and_noncanonical_json_are_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b' {}', b'{}\n',
                    b'{"z":0,"a":0}', b'{}{}', b'\xef\xbb\xbf{}', b'"\\u0041"'):
            with self.subTest(raw=raw), self.assertRaises(c.CodecError):
                c.canonical_loads(raw)

    def test_unsupported_types_numbers_and_unicode_are_rejected(self):
        for raw in (b'1.0', b'NaN', b'Infinity', b'9223372036854775808', b'"\\ud800"', b'"\xff"'):
            with self.subTest(raw=raw), self.assertRaises(c.CodecError):
                c.canonical_loads(raw)
        for obj in (object(), b"binary", (1, 2), {1: "key"}, 1.1, float("inf")):
            with self.assertRaises(c.CodecError):
                c.canonical_dumps(obj)

    def test_canonical_budgets_are_nonrelaxable_and_enforced(self):
        for raw, limits in ((b'[[[0]]]', c.CodecLimits(max_depth=2)),
                            (b'[0,0]', c.CodecLimits(max_array=1)),
                            (b'"abc"', c.CodecLimits(max_string_bytes=2)),
                            (b'{"a":0}', c.CodecLimits(max_bytes=2)),
                            (b'[0,0]', c.CodecLimits(max_nodes=2))):
            with self.assertRaises(c.CodecError):
                c.canonical_loads(raw, limits)
        for changes in ({"max_bytes": 8388609}, {"max_depth": 65}, {"max_nodes": True}):
            with self.assertRaises(c.CodecError):
                c.CodecLimits(**changes)

    def test_failed_codes_and_phases_are_exact_bounded_unique(self):
        data = samples()[7][1]
        for changes in ({"phase": "approved"}, {"issue_codes": []}, {"issue_codes": ["wrong"]},
                        {"issue_codes": ["abandoned"] * 2}, {"issue_codes": list(c.FAILURE_CODES[:5])}):
            with self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({**data, **changes}))

    def test_lineage_selection_and_predecessor_are_strict(self):
        data = samples()[5][1]
        for changes in ({"declared_lineage": ["pdf"]}, {"selection": {"name": "IT-Systeme"}},
                        {"predecessor_registration_id": "2" * 32},
                        {"registration": ref(2), "predecessor_registration_id": None}):
            with self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({**data, **changes}))

    def test_source_validated_shape_allows_late_head_but_no_authority(self):
        data = samples()[8][1]
        p = c.Payload(c.canonical_dumps({**data, "source_head_at_validation": ref(2, "4")}))
        self.assertIs(p.kind, c.EventKind.VALIDATED)
        for changes in ({"source_head_at_validation": ref(1, "4")},
                        {"source_head_at_validation": {**ref(), "source_id": "synthetic:other"}},
                        {"source_head_at_validation": ref(2)}, {"capture_event_sequence": False}):
            with self.assertRaises(c.CodecError):
                c.Payload(c.canonical_dumps({**data, **changes}))

    def test_derivation_ref_independent_blob_and_identity_vectors(self):
        d = c.DerivationRef(c.canonical_dumps(derivation()))
        self.assertEqual(d.blob_sha256, "020ed9f91fd81ba3ce8af47197b74ce336b239eca64d9ffb45492ed7a3d5af43")
        self.assertEqual(d.sha256, "d09be1fa9973c4f4f693ac4550fa1a4c5539fc727aa68814a053d01a0af0e190")

    def test_derivation_exact_fields_and_docx_null_native_manifest(self):
        data = derivation()
        for key in data:
            with self.subTest(key=key), self.assertRaises(c.CodecError):
                c.DerivationRef(c.canonical_dumps({k: v for k, v in data.items() if k != key}))
        for changes in ({"approved": True}, {"type": "derivation-ref/v1"}, {"policy_revision": True},
                        {"native_manifest_sha256": "1" * 64}, {"reader_method": "docx/unknown"},
                        {"binary_sha256": None}, {"byte_length": 2097153}):
            with self.assertRaises(c.CodecError):
                c.DerivationRef(c.canonical_dumps({**data, **changes}))

    def test_xlsx_derivation_requires_native_manifest(self):
        data = {**derivation(), "kind": "xlsx", "reader_method": "xlsx-literal/v1"}
        with self.assertRaises(c.CodecError):
            c.DerivationRef(c.canonical_dumps(data))
        d = c.DerivationRef(c.canonical_dumps({**data, "native_manifest_sha256": "c" * 64}))
        self.assertEqual(d.data()["kind"], "xlsx")

    def test_envelope_rejects_unknown_missing_fields_and_kind_codec_mismatch(self):
        data = envelope().data()
        for key in data:
            with self.subTest(key=key), self.assertRaises(c.CodecError):
                c.Envelope(c.canonical_dumps({k: v for k, v in data.items() if k != key}))
        for changes in ({"codec": "ledger-event/v2"}, {"kind": "queue.approved"}, {"payload_codec": "store-init/v1"},
                        {"transaction_count": 2}, {"transaction_index": True}, {"sequence": True},
                        {"actor_id": None}, {"unexpected": None}):
            with self.assertRaises(c.CodecError):
                c.Envelope(c.canonical_dumps({**data, **changes}))

    def test_envelope_sequence_chain_hash_and_audit_consistency(self):
        for kwargs in ({"sequence": 2, "previous": "0" * 64}, {"previous": "0" * 64},
                       {"event_id": "x" * 32}, {"actor_id": None}):
            with self.assertRaises(c.CodecError):
                envelope(**kwargs)
        p = c.Payload(c.canonical_dumps(samples()[8][1]))
        with self.assertRaises(c.CodecError):
            envelope(p, sequence=1)
        with self.assertRaises(c.CodecError):
            envelope(p, sequence=1, previous=None)
        e = envelope(p, sequence=2, previous="0" * 64)
        self.assertEqual(c.Event(e, p).payload.kind, c.EventKind.VALIDATED)
        p_late = c.Payload(c.canonical_dumps({**p.data(), "capture_event_sequence": 2}))
        with self.assertRaises(c.CodecError):
            envelope(p_late, sequence=2, previous="0" * 64)
        with self.assertRaises(c.CodecError):
            envelope(p, sequence=2, previous="0" * 64, occurred_at="2026-11-11T12:00:01.000000Z")

    def test_pair_checks_payload_digest_store_identity_and_inert_type(self):
        other = c.make_payload(c.EventKind.INITIALIZED, store_uuid="f" * 32,
            schema_version=3, serialization_version="canonical-json/v1", feature_profile="verified-source/v1")
        with self.assertRaises(c.CodecError):
            c.Event(envelope(), other)
        with self.assertRaises(c.CodecError):
            envelope(other)
        with self.assertRaises(c.CodecError):
            c.Event(envelope(), GENESIS_RAW)

    def test_payload_envelope_and_reference_data_are_detached_and_frozen(self):
        p, e = genesis(), envelope()
        data = p.data()
        data["store_uuid"] = "f" * 32
        self.assertEqual(p.canonical, GENESIS_RAW)
        for obj, field in ((p, "canonical"), (e, "canonical"),
                           (c.DerivationRef(c.canonical_dumps(derivation())), "canonical")):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, b"{}")

    def test_v2_codec_stays_distinct_and_refuses_v3(self):
        self.assertEqual(old.SCHEMA_VERSION, 2)
        self.assertEqual(old.EVENT_CODEC, "ledger-event/v2")
        with self.assertRaises(old.CodecError):
            old.Payload(GENESIS_RAW)
        with self.assertRaises(old.CodecError):
            old.Envelope(envelope().canonical)
