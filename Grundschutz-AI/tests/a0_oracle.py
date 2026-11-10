"""Test-only A0 oracle builder: imports only a separately verified 2ee9bc7 checkout.

Run as a subprocess before production changes. No B implementation creates the
oracle. Frozen literals originate in the committed ADR-0010, not current readers.
"""
import argparse
from dataclasses import asdict
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch
from uuid import UUID

FROZEN = json.loads(r'''{"descriptors":{"docx":{"family":"docx","method_version":"docx-plain/v1","module_hashes":[{"module_name":"docx_ingestion","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"module_name":"docx_staging","sha256":"af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a"},{"module_name":"ooxml_safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"module_name":"support","sha256":"c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb"},{"module_name":"v2_codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"module_name":"v2_ledger","sha256":"a66d5106fcf7b153088eff24ce0cecf0d9fba9ef0167cf0f40632f5f76b6d2be"},{"module_name":"v2_schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"module_name":"validation","sha256":"22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5"},{"module_name":"xlsx_ingestion","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"},{"module_name":"xlsx_staging","sha256":"89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06"}],"runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"serialization_version":"canonical-json/v1","type":"implementation-spec/v1"},"xlsx":{"family":"xlsx","method_version":"xlsx-literal/v1","module_hashes":[{"module_name":"docx_ingestion","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"module_name":"docx_staging","sha256":"af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a"},{"module_name":"ooxml_safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"module_name":"support","sha256":"c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb"},{"module_name":"v2_codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"module_name":"v2_ledger","sha256":"a66d5106fcf7b153088eff24ce0cecf0d9fba9ef0167cf0f40632f5f76b6d2be"},{"module_name":"v2_schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"module_name":"validation","sha256":"22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5"},{"module_name":"xlsx_ingestion","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"},{"module_name":"xlsx_staging","sha256":"89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06"}],"runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"serialization_version":"canonical-json/v1","type":"implementation-spec/v1"}},"policies":{"docx":{"config":{"max_field_bytes":16384,"max_history_units":512,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_source_chars":2000,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_entries":16,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_segment_chars":16384,"max_segments":4096,"max_table_columns":128,"max_table_rows":1000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c","kind":"docx","semantic_version":"docx-single-assertion/v1","type":"policy-spec/v1"},"xlsx":{"config":{"max_data_rows":100,"max_history_units":2048,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_scope_rows":100,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_cell_chars":16384,"max_cells":10000,"max_entries":64,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_shared_strings":10000,"max_shared_text_chars":1000000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_worksheets":16,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2","kind":"xlsx","semantic_version":"synthetic-it-table/v1","type":"policy-spec/v1"}},"event_hashes":[["e1a9ccac9447d298a7ad5c361232a7d7d5a03e09b48d46b1e35c8f53c921688a","593006a5553fcda703f840562bd52722a0826da67d2b15caccbbd186a28656f3"],["e5d5949d7ae4e4195d53d3695b79ef1aae812ff4fbe6385407eb2670beca67f8","bf7d243e89cbc76c7fac3894ee3c8a9350a4778e1dbebb85832f3e27d22df7ff"],["819356cdc16eb61bbab04fc5950d2a3f22711c79e7972973bc7f41592cbe8ae7","3b359f36843f00a39ded0a9ac8142cef771626aa033684899a5ba321fcd60172"],["1a4ffd74a078b1c51a67e4a35ac152fd14d73e97a1adf8082bc0449512616c87","7dc76bd9de8a4621e3f2f43040001c393b5e98e0b0ec38e3d27988d97ddb0fb7"],["8471b484c4013b522904dc9ea291db99277b97e0d3fb2c32aed04927d30f00e1","657fda49506e500d823ad9070bf978aad6caebc5f1f803d90d47b4aa8eca211a"],["48c5ad667a4b2f4a06d1e606cce1702bca910f821aba81a3ed027346f4e8becf","17675a2242068dcd8c6f0fa6108de869253001553287f5d99ccb7769b1a9d969"],["7e3d3f577c1f9553387b1a19bfb7fbc3c04e06e6592f36a97fcdc684fe90a44a","a637f40bf84571cd0a118d6b5c7f05be8bc31b7dc4959a50ab33af9476cea184"],["df5756ed1ffb6c9368d746ce8729669c88502488297a3cc4586ebbe8e3a0b9b5","6586d65b9ba8509a8386d90ba529ea421dc2707903640cdca653f3b5dd31b158"],["e800031646e5fb1d424150f831222e07fa50659b854987e4f9aa3fbc8b5ed80c","e8f947c8c407b12850461b601874a5d114d3f63454546a0a3d161916c8d881e4"],["d2f62536f3198775a08193fd5b3613c9e02e11c41340c4fd8ae77566dc0a928e","cd174093e7d525ba627ffc4f47016df30743b383876057abacac2d8dd98d5f29"],["717c1a84fadf7c79de4379eb7a8ab703267780493d4605116c39ce45c379551b","77730a8763d4645bc771b83aa45ab032cdbce9c400e6e4f613eea0b621cdd4c2"],["21f3f11cbc00cf0bf48d2b01f0aaab1c43b67cb4524b9bb6f5410c52b0189aed","40ab7acb208f43b8ffb61beafe59be9020fb2f8c12670f9b2bf918183ecebfd2"],["bd85b230efb9d227d81174d32a0a6aa3edb9fa346b0c6029550efe8263a10832","e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09"]],"schema_hash":"092b2d5aed6e07ddb99b3a4299d01b05c0f6cc5845b75bec6aa968aaa0fefa32"}''')
STAMP = "2026-11-10T12:00:00.000000Z"
ACTOR = "synthetic:compat-reviewer"
RAW = {"docx": b"FICTITIOUS A0 DOCX CAPTURE\n",
       "xlsx": b"FICTITIOUS A0 XLSX CAPTURE\n"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def portable(value):
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, dict):
        return {key: portable(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [portable(child) for child in value]
    return value


def state_manifest(state):
    return portable(asdict(state))


def schema_identity(schema):
    objects = [{"name": name, "kind": kind, "sql": sql}
               for name, (kind, sql) in sorted(schema.expected_objects().items())]
    return sha(canonical({"type": "a-schema-objects/v1", "value": objects}))


def build(checkout, output):
    """Refuse before DB creation unless every A0 code/runtime/contract matches."""
    checkout, output = Path(checkout).resolve(), Path(output).resolve()
    if os.name != "nt" or sys.version_info[:3] != (3, 12, 6) or sqlite3.sqlite_version != "3.45.3":
        raise RuntimeError("Exact A0 Windows/Python/SQLite runtime unavailable")
    if output.is_relative_to(checkout):
        raise RuntimeError("Oracle must be outside the isolated checkout")
    base = checkout / "grundschutz_ai"
    for item in FROZEN["descriptors"]["docx"]["module_hashes"]:
        if sha((base / (item["module_name"] + ".py")).read_bytes()) != item["sha256"]:
            raise RuntimeError("A0 module bytes differ; refusing oracle")
    sys.path.insert(0, str(checkout))
    from grundschutz_ai import v2_ledger as ledger, v2_schema as schema
    from grundschutz_ai.docx_staging import StagingPolicy as DocxPolicy
    from grundschutz_ai.xlsx_staging import StagingPolicy as XlsxPolicy, SheetSelection
    if Path(ledger.__file__).resolve().parent != base:
        raise RuntimeError("Oracle imported the wrong checkout")
    ledger._fixed_local_volume(output)
    if schema_identity(schema) != FROZEN["schema_hash"]:
        raise RuntimeError("A0 schema differs")
    for kind, policy in (("docx", DocxPolicy()), ("xlsx", XlsxPolicy())):
        spec = ledger._local_spec(kind)
        if spec.canonical != canonical(FROZEN["descriptors"][kind]):
            raise RuntimeError("A0 descriptor differs")
        if ledger._policy_spec(kind, policy, spec.sha256).canonical != canonical(FROZEN["policies"][kind]):
            raise RuntimeError("A0 default policy differs")
    output.mkdir(parents=True, exist_ok=True)
    db = output / "oracle.sqlite"
    paths = {kind: output / ("fictitious." + kind) for kind in RAW}
    for kind, path in paths.items():
        path.write_bytes(RAW[kind])
    missing = output / "missing.xlsx"
    if missing.exists():
        raise RuntimeError("Missing-source fixture path unexpectedly exists")
    ids = itertools.count(1)
    with patch.object(ledger, "uuid4", side_effect=lambda: UUID(int=next(ids))), \
         patch.object(ledger.codec, "utc_now", return_value=STAMP):
        with ledger.SourceLedger.create(db, actor_id=ACTOR) as store:
            def command(name, *args, **kwargs):
                return getattr(store, name)(*args, expected=store.load().head,
                                            actor_id=ACTOR, **kwargs)
            command("register_implementation", "docx")
            dr = command("create_registry", "docx", DocxPolicy())
            d1 = command("begin_registration", dr, "synthetic:compat-a0-docx", expected_source=None)
            command("capture_source", d1, paths["docx"])
            command("fail_source", d1, reason_code="operator_failed")
            command("begin_registration", dr, d1.source_id, expected_source=d1)
            command("register_implementation", "xlsx")
            xr = command("create_registry", "xlsx", XlsxPolicy())
            selection = SheetSelection("IT-Systeme", 1, 1, "rId1", "xl/worksheets/sheet1.xml")
            x1 = command("begin_registration", xr, "synthetic:compat-a0-xlsx",
                         expected_source=None, selection=selection)
            command("capture_source", x1, paths["xlsx"])
            y1 = command("begin_registration", xr, "synthetic:compat-a0-missing",
                         expected_source=None, selection=selection)
            command("capture_source", y1, missing)
    state = ledger.load_ledger(db)
    assert len(state.events) == 13
    for event, (payload_hash, event_hash) in zip(state.events, FROZEN["event_hashes"], strict=True):
        envelope = event.envelope.data()
        assert sha(event.payload.canonical) == payload_hash
        assert envelope["event_sha256"] == event_hash
    assert state.head.store_uuid == format(1, "032x")
    assert state.head.sequence == 13
    assert {blob.content for blob in state.original_blobs} == set(RAW.values())
    expected = {"docx": (2, 17, "pending", None),
                "xlsx": (1, 26, "pending", sha(RAW["xlsx"])),
                "missing": (1, 31, "failed", None)}
    for suffix, (revision, number, status, digest) in expected.items():
        ref = state.source_head("synthetic:compat-a0-" + suffix)
        assert (ref.revision, ref.registration_id) == (revision, format(number, "032x"))
        reg = state.registration(ref)
        assert (reg.status.value, reg.binary_sha256) == (status, digest)
    old = next(reg for reg in state.registrations if reg.ref.registration_id == format(10, "032x"))
    assert old.status.value == "failed" and old.binary_sha256 == sha(RAW["docx"])
    assert old.failure_codes == ("operator_failed",)
    # A has already recomputed and compared every persisted projection.
    connection = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    try:
        projections = {table: sorted((portable(row) for row in connection.execute("SELECT * FROM " + table)),
                                    key=canonical) for table in schema.TABLES}
        dump = "\n".join(connection.iterdump()) + "\nPRAGMA user_version=2;\n"
        (output / "oracle.sql").write_bytes(dump.encode("utf-8"))
    finally:
        connection.close()
    manifest = {"producer_commit": "2ee9bc7cf309727e5a9f10e2982791dbc991c464",
                "state": state_manifest(state), "projections": projections}
    raw = canonical(manifest)
    (output / "oracle-manifest.json").write_bytes(raw)
    summary = {"database": str(db), "database_sha256": sha(db.read_bytes()),
               "manifest_sha256": sha(raw), "events": len(state.events),
               "head": asdict(state.head), "identities_verified": True}
    (output / "oracle-summary.json").write_bytes(canonical(summary))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.checkout, args.output), sort_keys=True))
