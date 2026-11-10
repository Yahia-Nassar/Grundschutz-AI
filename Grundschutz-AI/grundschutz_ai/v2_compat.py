"""Exact, application-owned historical-catalog/v1; A0 read capability only.

No database enrollment, executable lookup, current-reader fallback or writer.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys

from . import v2_a0 as _a0
from . import v2_codec as _codec

__all__ = ("HistoricalLedgerError", "HistoricalLedgerLimits",
           "HistoricalLedgerState", "historical_catalog", "load_historical_ledger")

CATALOG_VERSION = "historical-catalog/v1"
MAX_HISTORICAL_IMPLEMENTATIONS = 4
HANDLER_ID = "a0-source-ledger-read/v1"
SCHEMA_SHA256 = "092b2d5aed6e07ddb99b3a4299d01b05c0f6cc5845b75bec6aa968aaa0fefa32"
PRODUCER_COMMIT = "2ee9bc7cf309727e5a9f10e2982791dbc991c464"
ORACLE_MANIFEST_SHA256 = "3b01d810cadc1058be89b4c9aebcdaf8b0ec4058375b134c4a8336c98b193c15"
# Immutable literal pairs, confirmed by the independent A public-API producer.
A0_EVENT_VECTORS = (
    ("e1a9ccac9447d298a7ad5c361232a7d7d5a03e09b48d46b1e35c8f53c921688a", "593006a5553fcda703f840562bd52722a0826da67d2b15caccbbd186a28656f3"),
    ("e5d5949d7ae4e4195d53d3695b79ef1aae812ff4fbe6385407eb2670beca67f8", "bf7d243e89cbc76c7fac3894ee3c8a9350a4778e1dbebb85832f3e27d22df7ff"),
    ("819356cdc16eb61bbab04fc5950d2a3f22711c79e7972973bc7f41592cbe8ae7", "3b359f36843f00a39ded0a9ac8142cef771626aa033684899a5ba321fcd60172"),
    ("1a4ffd74a078b1c51a67e4a35ac152fd14d73e97a1adf8082bc0449512616c87", "7dc76bd9de8a4621e3f2f43040001c393b5e98e0b0ec38e3d27988d97ddb0fb7"),
    ("8471b484c4013b522904dc9ea291db99277b97e0d3fb2c32aed04927d30f00e1", "657fda49506e500d823ad9070bf978aad6caebc5f1f803d90d47b4aa8eca211a"),
    ("48c5ad667a4b2f4a06d1e606cce1702bca910f821aba81a3ed027346f4e8becf", "17675a2242068dcd8c6f0fa6108de869253001553287f5d99ccb7769b1a9d969"),
    ("7e3d3f577c1f9553387b1a19bfb7fbc3c04e06e6592f36a97fcdc684fe90a44a", "a637f40bf84571cd0a118d6b5c7f05be8bc31b7dc4959a50ab33af9476cea184"),
    ("df5756ed1ffb6c9368d746ce8729669c88502488297a3cc4586ebbe8e3a0b9b5", "6586d65b9ba8509a8386d90ba529ea421dc2707903640cdca653f3b5dd31b158"),
    ("e800031646e5fb1d424150f831222e07fa50659b854987e4f9aa3fbc8b5ed80c", "e8f947c8c407b12850461b601874a5d114d3f63454546a0a3d161916c8d881e4"),
    ("d2f62536f3198775a08193fd5b3613c9e02e11c41340c4fd8ae77566dc0a928e", "cd174093e7d525ba627ffc4f47016df30743b383876057abacac2d8dd98d5f29"),
    ("717c1a84fadf7c79de4379eb7a8ab703267780493d4605116c39ce45c379551b", "77730a8763d4645bc771b83aa45ab032cdbce9c400e6e4f613eea0b621cdd4c2"),
    ("21f3f11cbc00cf0bf48d2b01f0aaab1c43b67cb4524b9bb6f5410c52b0189aed", "40ab7acb208f43b8ffb61beafe59be9020fb2f8c12670f9b2bf918183ecebfd2"),
    ("bd85b230efb9d227d81174d32a0a6aa3edb9fa346b0c6029550efe8263a10832", "e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09"),
)
# Original A v2_ledger identity is preserved in each historical descriptor.
# Its read-only semantics are supplied by this explicitly pinned bridge;
# no old/current SourceLedger writer is imported or granted authority.
_ARTIFACTS = (
    ("docx_ingestion.py", "a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"),
    ("docx_staging.py", "af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a"),
    ("ooxml_safety.py", "35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"),
    ("support.py", "c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb"),
    ("v2_codec.py", "577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"),
    ("v2_schema.py", "9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"),
    ("validation.py", "22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5"),
    ("xlsx_ingestion.py", "8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"),
    ("xlsx_staging.py", "89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06"),
    ("v2_a0.py", "a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd"),
)
_DESCRIPTORS = (
    b'{"family":"docx","method_version":"docx-plain/v1","module_hashes":[{"module_name":"docx_ingestion","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"module_name":"docx_staging","sha256":"af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a"},{"module_name":"ooxml_safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"module_name":"support","sha256":"c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb"},{"module_name":"v2_codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"module_name":"v2_ledger","sha256":"a66d5106fcf7b153088eff24ce0cecf0d9fba9ef0167cf0f40632f5f76b6d2be"},{"module_name":"v2_schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"module_name":"validation","sha256":"22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5"},{"module_name":"xlsx_ingestion","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"},{"module_name":"xlsx_staging","sha256":"89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06"}],"runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"serialization_version":"canonical-json/v1","type":"implementation-spec/v1"}',
    b'{"family":"xlsx","method_version":"xlsx-literal/v1","module_hashes":[{"module_name":"docx_ingestion","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"module_name":"docx_staging","sha256":"af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a"},{"module_name":"ooxml_safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"module_name":"support","sha256":"c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb"},{"module_name":"v2_codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"module_name":"v2_ledger","sha256":"a66d5106fcf7b153088eff24ce0cecf0d9fba9ef0167cf0f40632f5f76b6d2be"},{"module_name":"v2_schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"module_name":"validation","sha256":"22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5"},{"module_name":"xlsx_ingestion","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"},{"module_name":"xlsx_staging","sha256":"89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06"}],"runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"serialization_version":"canonical-json/v1","type":"implementation-spec/v1"}',
)
_IDENTITIES = (
    ("c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c", "c61db30620d92e88e8e69ef8b4bdf786c38bedc5b338373676381a471c552af1"),
    ("22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2", "4e394cd2fe03f2d7e4caef3d2c338fd0b6fa07595fba01005175ef2877e0afee"),
)


class HistoricalLedgerError(RuntimeError):
    """Static fail-closed diagnostic; no partial state or source text."""


HistoricalLedgerLimits = _a0.LedgerLimits
HistoricalLedgerState = _a0.LedgerState


@dataclass(frozen=True, slots=True)
class HistoricalImplementation:
    catalog_version: str
    entry_id: str
    family: str
    descriptor: bytes
    implementation_sha256: str
    descriptor_blob_sha256: str
    producer_commit: str
    runtime: tuple[str, str, str]
    packaging_profile: str
    schema_sha256: str
    schema_version: int
    event_codec: str
    serialization_version: str
    policy_version: str
    policy_ceiling: bytes
    handler_id: str
    capabilities: tuple[str, ...]
    oracle_manifest_sha256: str
    event_vectors: tuple[tuple[str, str], ...]


_ENTRIES = tuple(
    HistoricalImplementation(
        CATALOG_VERSION, "a0-" + kind + "/v1", kind, descriptor,
        identity[0], identity[1], PRODUCER_COMMIT,
        ("3.12.6", "3.45.3", "windows-fixed-ntfs-refs/v1"), "source-lf/v1",
        SCHEMA_SHA256, 2, "ledger-event/v2", "canonical-json/v1", policy,
        ceiling, HANDLER_ID, ("source_ledger_read",),
        ORACLE_MANIFEST_SHA256, A0_EVENT_VECTORS)
    for kind, descriptor, identity, policy, ceiling in zip(
        ("docx", "xlsx"), _DESCRIPTORS, _IDENTITIES,
        ("docx-single-assertion/v1", "synthetic-it-table/v1"),
        _a0._DEFAULT_POLICY_BYTES, strict=True)
)


def historical_catalog() -> tuple[HistoricalImplementation, ...]:
    """Metadata recognition only; availability is verified on every load."""
    if type(_ENTRIES) is not tuple or not 1 <= len(_ENTRIES) <= 4 or len(_ENTRIES) != 2:
        raise HistoricalLedgerError("Historical catalog bounds or membership invalid")
    for index, entry in enumerate(_ENTRIES):
        if (type(entry) is not HistoricalImplementation or
                entry.descriptor != _DESCRIPTORS[index] or
                entry.implementation_sha256 != _IDENTITIES[index][0] or
                entry.descriptor_blob_sha256 != _IDENTITIES[index][1] or
                entry.catalog_version != "historical-catalog/v1" or
                entry.handler_id != "a0-source-ledger-read/v1" or
                entry.capabilities != ("source_ledger_read",) or
                entry != _EXPECTED_ENTRIES[index]):
            raise HistoricalLedgerError("Historical catalog entry is not reviewed")
    return _ENTRIES


# Separate immutable equality anchor also detects accidental entry replacement.
_EXPECTED_ENTRIES = _ENTRIES


def _verify_bundle():
    if (os.name != "nt" or sys.version_info[:3] != (3, 12, 6) or
            sqlite3.sqlite_version != "3.45.3"):
        raise HistoricalLedgerError("Historical host runtime is unsupported")
    base = Path(__file__).resolve().parent
    try:
        for filename, expected in _ARTIFACTS:
            # filenames originate only in this static application tuple.
            if _codec.sha256((base / filename).read_bytes()) != expected:
                raise HistoricalLedgerError("Historical handler bundle differs")
    except OSError as exc:
        raise HistoricalLedgerError("Historical handler bundle unavailable") from exc
    objects = [{"name": name, "kind": kind, "sql": sql}
               for name, (kind, sql) in sorted(_a0.schema.expected_objects().items())]
    if (_codec.fingerprint("a-schema-objects/v1", objects) != SCHEMA_SHA256 or
            _codec.SCHEMA_VERSION != 2 or _codec.EVENT_CODEC != "ledger-event/v2" or
            _codec.SERIALIZATION_VERSION != "canonical-json/v1"):
        raise HistoricalLedgerError("Historical schema or codec handler differs")


def load_historical_ledger(path: str | Path, *,
                           limits: HistoricalLedgerLimits = _a0.DEFAULT_LIMITS
                           ) -> HistoricalLedgerState:
    """Verify the complete A0 ledger read-only; return immutable blocked metadata.

    Captures are not parsed or promoted. All B/C/D and domain/export features
    remain unavailable. No mutable source path or database string selects code.
    """
    if type(limits) is not HistoricalLedgerLimits:
        raise HistoricalLedgerError("Exact typed historical limits required")
    _verify_bundle()
    entries = historical_catalog()
    catalog = {}
    for entry in entries:
        spec = _codec.Spec(entry.descriptor)
        if (spec.sha256 != entry.implementation_sha256 or
                _codec.sha256(spec.canonical) != entry.descriptor_blob_sha256):
            raise HistoricalLedgerError("Historical descriptor identity differs")
        catalog[entry.family] = spec
    try:
        return _a0._load(path, limits, catalog)
    except (_a0.LedgerError, _codec.CodecError, OSError, ValueError, TypeError,
            KeyError, IndexError, RecursionError) as exc:
        raise HistoricalLedgerError("Historical ledger refused; no trusted result") from exc
