"""Independent literal vectors and strict, bounded A-only codec regressions."""

from dataclasses import FrozenInstanceError, replace
import json
import unittest

from grundschutz_ai import v2_codec as codec


STAMP = "2026-11-10T12:00:00.000000Z"
ZERO = "0" * 32


def genesis():
    return codec.make_payload(codec.EventKind.INITIALIZED, store_uuid=ZERO,
        schema_version=2, serialization_version="canonical-json/v1", feature_profile="staging_only")


class V2CodecTests(unittest.TestCase):
    def test_independent_canonical_utf8_and_hash_golden(self):
        # Fixed literal/hash verified independently with .NET SHA256 over UTF-8.
        expected = '{"a":1,"text":"Ä\\r\\n","z":[null,true,-2]}'.encode("utf-8")
        self.assertEqual(codec.canonical_dumps({"z": [None, True, -2], "text": "Ä\r\n", "a": 1}), expected)
        self.assertEqual(codec.sha256(expected), "0149df147f33e29c3279b9791c21bc3f2760869d0a7259ef5d6f61341c7ac396")
        self.assertEqual(codec.canonical_loads(expected), {"a": 1, "text": "Ä\r\n", "z": [None, True, -2]})

    def test_independent_tagged_fingerprint_golden(self):
        self.assertEqual(codec.fingerprint("golden/v1", {"a": 1}), "cfe2b97340217e4a08d67cb3142e6e9ca2139bed0f5f7a81c2aec1af5fe552a4")
        self.assertNotEqual(codec.fingerprint("golden/v2", {"a": 1}), codec.fingerprint("golden/v1", {"a": 1}))

    def test_independent_initialized_payload_golden(self):
        expected = b'{"feature_profile":"staging_only","payload_codec":"store-init/v1","schema_version":2,"serialization_version":"canonical-json/v1","store_uuid":"00000000000000000000000000000000"}'
        self.assertEqual(genesis().canonical, expected)
        self.assertEqual(codec.sha256(expected), "aad5dbcce9890ed6355f6b34b059023908cddc7139c90e5e745c35820a66bd82")

    def test_duplicate_keys_including_nested_objects_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}'):
            with self.assertRaises(codec.CodecError):
                codec.canonical_loads(raw)

    def test_noncanonical_malformed_bom_and_trailing_json_rejected(self):
        for raw in (b' {"a":1}', b'{"b":2,"a":1}', b'{"a": 1}', b'{}\n', b'{}{}', b'{', b'\xef\xbb\xbf{}', b'"\\u0041"'):
            with self.subTest(raw=raw), self.assertRaises(codec.CodecError):
                codec.canonical_loads(raw)

    def test_floats_nonfinite_and_oversized_integers_rejected(self):
        for raw in (b'1.0', b'1e2', b'NaN', b'Infinity', b'-Infinity', b'9223372036854775808', b'-9223372036854775809'):
            with self.assertRaises(codec.CodecError):
                codec.canonical_loads(raw)
        for value in (1.0, float('nan'), float('inf'), 2**63):
            with self.assertRaises(codec.CodecError):
                codec.canonical_dumps(value)

    def test_lone_surrogates_and_invalid_utf8_rejected(self):
        for raw in (b'"\\ud800"', b'"\\udfff"', b'"\xff"'):
            with self.assertRaises(codec.CodecError):
                codec.canonical_loads(raw)
        with self.assertRaises(codec.CodecError):
            codec.canonical_dumps("\ud800")

    def test_only_exact_json_types_no_arbitrary_objects(self):
        class Malicious:
            def __repr__(self):
                raise AssertionError("Must not execute source representation")
        for value in (Malicious(), b"binary", (1, 2), {1: "key"}):
            with self.assertRaises(codec.CodecError):
                codec.canonical_dumps(value)

    def test_bounded_depth_nodes_arrays_bytes_and_strings(self):
        cases = ((b'[[[0]]]', codec.CodecLimits(max_depth=2)),
                 (b'[1,2,3]', codec.CodecLimits(max_array=2)),
                 (b'[1,2,3]', codec.CodecLimits(max_nodes=3)),
                 (b'"long"', codec.CodecLimits(max_string_bytes=3)),
                 (b'"long"', codec.CodecLimits(max_bytes=5)))
        for raw, limits in cases:
            with self.subTest(raw=raw, limits=limits), self.assertRaises(codec.CodecError):
                codec.canonical_loads(raw, limits)
        self.assertEqual(codec.canonical_loads(b'[1,2]', codec.CodecLimits(max_array=2)), [1, 2])

    def test_string_brackets_and_escapes_do_not_confuse_depth_scanner(self):
        value = {'text': '[[[ ]]] \\" \\ "quoted" Ä🙂'}
        self.assertEqual(codec.canonical_loads(codec.canonical_dumps(value)), value)

    def test_limits_cannot_expand_or_use_boolean(self):
        for changes in ({"max_depth": 65}, {"max_array": True}, {"max_nodes": 0}):
            with self.assertRaises(codec.CodecError):
                codec.CodecLimits(**changes)

    def test_payload_unknown_missing_fields_and_boolean_schema_rejected(self):
        data = genesis().data()
        for bad in ({**data, "approved": True}, {key: value for key, value in data.items() if key != "store_uuid"}, {**data, "schema_version": True}, {**data, "schema_version": 1}):
            with self.assertRaises(codec.CodecError):
                codec.Payload(codec.canonical_dumps(bad))

    def test_all_future_event_tags_are_disabled(self):
        for tag in ("source-valid/v1", "scope-assess/v1", "candidate-stage/v1", "queue-decision/v1", "legacy-import/v1", "legacy-action/v1", "document-domain/v2", "document-review/v1", "export/v1"):
            with self.subTest(tag=tag), self.assertRaises(codec.CodecError):
                codec.Payload(codec.canonical_dumps({"payload_codec": tag}))
        with self.assertRaises(codec.CodecError):
            codec.make_payload("source.validated")

    def test_registration_reference_strict_types_and_fields(self):
        for raw in ({"source_id": "synthetic:test", "revision": True, "registration_id": ZERO},
                    {"source_id": " ", "revision": 1, "registration_id": ZERO},
                    {"source_id": "synthetic:test", "revision": 1, "registration_id": "bad"},
                    {"source_id": "synthetic:test", "revision": 1, "registration_id": ZERO, "path": "private"}):
            with self.assertRaises(codec.CodecError):
                codec.SourceRef.parse(raw)

    def test_payload_state_and_decoded_dictionary_are_not_mutable_authority(self):
        payload = genesis()
        detached = payload.data()
        detached["schema_version"] = 1
        self.assertEqual(payload.data()["schema_version"], 2)
        with self.assertRaises(FrozenInstanceError):
            payload.canonical = b"{}"

    def test_sheet_descriptor_exact_no_paths_or_inferred_selection(self):
        good = dict(name="IT-Systeme", ordinal=1, sheet_id=1, relationship_id="rId1", part="xl/worksheets/sheet1.xml")
        codec.sheet_identity(good)
        for changes in ({"ordinal": True}, {"name": "it-systeme"}, {"part": "../../file"}, {"relationship_id": "https://example.invalid"}):
            with self.assertRaises(codec.CodecError):
                codec.sheet_identity({**good, **changes})

    def test_failed_observation_has_no_caller_supplied_hash(self):
        ref = codec.SourceRef("synthetic:test", 1, ZERO)
        good = codec.make_payload(codec.EventKind.FAILED, registration=ref.data(), phase="interrupted", issue_codes=["abandoned"], observed_at=STAMP)
        self.assertIs(good.kind, codec.EventKind.FAILED)
        for changes in ({"blob_sha256": "0" * 64}, {"phase": "reader"}, {"issue_codes": ["abandoned", "abandoned"]}, {"issue_codes": ["source text leak"]}):
            with self.assertRaises(codec.CodecError):
                codec.Payload(codec.canonical_dumps({**good.data(), **changes}))

    def test_envelope_hash_and_exact_field_validation(self):
        payload = genesis()
        envelope = codec.make_envelope(payload, store_uuid=ZERO, sequence=1, previous=None,
            event_id="1" * 32, transaction_id="2" * 32, occurred_at=STAMP, actor_id="synthetic:human")
        data = envelope.data()
        expected = data.pop("event_sha256")
        self.assertEqual(codec.fingerprint("ledger-event/v2", data), expected)
        # Independently hashed .NET UTF-8 literal, not calculated from codec.
        self.assertEqual(expected, "1309df5825470401c924ed11f3ebebabad13baf6fb90f67702f4976e2c4db36d")
        for changes in ({"sequence": True}, {"occurred_at": "2026-11-10T12:00:00"}, {"event_sha256": "0" * 64}, {"extra": 1}):
            with self.assertRaises(codec.CodecError):
                codec.Envelope(codec.canonical_dumps({**envelope.data(), **changes}))

    def test_valid_a_payloads_round_trip(self):
        ref = codec.SourceRef("synthetic:test", 1, ZERO)
        samples = [
            codec.make_payload(codec.EventKind.IMPLEMENTATION, implementation_hash="0" * 64, descriptor_blob_sha256="1" * 64),
            codec.make_payload(codec.EventKind.REGISTRY, registry_id=ZERO, kind="docx", session_id="1" * 32, initial_policy_revision=1, policy_spec_hash="2" * 64, baseline_registry_epoch=1, baseline_history_units=0),
            codec.make_payload(codec.EventKind.POLICY, registry_id=ZERO, revision=2, predecessor_revision=1, policy_spec_hash="1" * 64, policy_fingerprint="2" * 64, activated_at=STAMP),
            codec.make_payload(codec.EventKind.STARTED, registry_id=ZERO, registration=ref.data(), predecessor_registration_id=None, policy_revision=1, reader_spec_hash="0" * 64, selection=None, declared_lineage=[], observed_at=STAMP),
            codec.make_payload(codec.EventKind.CAPTURED, registration=ref.data(), blob_sha256="1" * 64, byte_length=0, observed_at=STAMP),
            codec.make_payload(codec.EventKind.EXHAUSTED, registry_id=ZERO, budget_name="history", observed_at=STAMP),
        ]
        for payload in samples:
            self.assertEqual(codec.Payload(payload.canonical), payload)

    def test_specs_reject_unknown_fields_versions_and_executable_module_names(self):
        good = dict(type="implementation-spec/v1", family="docx", method_version="docx-plain/v1",
            module_hashes=[{"module_name": "docx_ingestion", "sha256": "0" * 64}],
            runtime=dict(python_version="3.12.6", platform_profile="windows-fixed-ntfs-refs/v1", sqlite_version="3.45.3"), serialization_version="canonical-json/v1")
        self.assertEqual(codec.Spec(codec.canonical_dumps(good)).data(), good)
        for changes in ({"type": "implementation-spec/v2"}, {"execute": "instruction"}, {"module_hashes": [{"module_name": "../../malicious.py", "sha256": "0" * 64}]}):
            with self.assertRaises(codec.CodecError):
                codec.Spec(codec.canonical_dumps({**good, **changes}))


if __name__ == "__main__":
    unittest.main()
