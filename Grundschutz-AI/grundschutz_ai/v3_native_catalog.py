"""Release-owned static catalog. Hash literals are reviewed, never auto-enrolled."""
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys

from . import v2_codec as c, v2_compat as historical
from .v3_native_contract import ARTIFACT_IDS, GOLDEN_SHA256, NativeHandlerSpec, need

# Root of trust is this application release, not a database-supplied descriptor.
# The catalog cannot hash itself without a cycle. All executable bridge artifacts
# below have literal release hashes; changing one requires a reviewed new identity.
_ARTIFACTS = (
    ("canonical-codec", "v2_codec.py", "577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"),
    ("docx-reader", "docx_ingestion.py", "a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"),
    ("historical-catalog", "v2_compat.py", "0b782ed32aeb8a8e602df916c9d2da1fc0f0f6b97aacdf4e73483737aba0b496"),
    ("historical-path-policy", "v2_a0.py", "a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd"),
    ("historical-schema", "v2_schema.py", "9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"),
    ("native-bridge", "v3_native.py", "73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926"),
    ("native-contract", "v3_native_contract.py", "9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2"),
    ("native-worker", "v3_native_worker.py", "454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319"),
    ("ooxml-safety", "ooxml_safety.py", "35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"),
    ("python-executable", None, "737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae"),
    ("xlsx-reader", "xlsx_ingestion.py", "8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"),
)


@dataclass(frozen=True, slots=True)
class NativeProfile:
    spec: NativeHandlerSpec
    reader_descriptor: bytes
    policy_ceiling: bytes
    capabilities: tuple[str, ...] = ("extract_captured_bytes",)


def _profile(old):
    doc = old.family == "docx"
    return NativeProfile(NativeHandlerSpec(c.canonical_dumps({
        "type": "reader-handler-spec/v1", "handler_id": "a0-" + old.family + "-native/v1",
        "reader_spec_hash": old.implementation_sha256, "family": old.family,
        "reader_method": "docx-plain/v1" if doc else "xlsx-literal/v1",
        "artifact_hashes": [{"artifact_id": name, "sha256": digest} for name, _, digest in _ARTIFACTS],
        "host_runtime": {"python_version": "3.12.6", "sqlite_version": "3.45.3",
                         "platform_profile": "windows-fixed-ntfs-refs/v1"},
        "policy_versions": [old.policy_version], "serialization_version": "canonical-json/v1",
        "native_manifest_version": None if doc else "xlsx-literal/v1",
        "integration_manifest_version": "docx-integration/v1" if doc else "xlsx-integration/v1",
        "golden_fixture_sha256": GOLDEN_SHA256})), old.descriptor, old.policy_ceiling)


_PROFILES = tuple(_profile(old) for old in historical.historical_catalog())
_EXPECTED = _PROFILES


def native_catalog():
    """Exactly two native profiles plus two unchanged historical read profiles."""
    old = historical.historical_catalog()
    need(type(_PROFILES) is tuple and len(_PROFILES) == 2 and len(old) + len(_PROFILES) <= 4,
         "catalog_limit")
    need(_PROFILES == _EXPECTED and tuple(row[0] for row in _ARTIFACTS) == ARTIFACT_IDS,
         "catalog_changed")
    return _PROFILES


def complete_catalog():
    return historical.historical_catalog() + native_catalog()


def select_handler(identity):
    need(type(identity) is str, "handler_mismatch")
    matches = [p for p in native_catalog() if p.spec.sha256 == identity]
    need(len(matches) == 1, "handler_mismatch")
    return matches[0]


def artifact_paths():
    base = Path(__file__).resolve().parent
    return tuple((base / name if name else Path(sys.executable).resolve(), digest)
                 for _, name, digest in _ARTIFACTS)


def verify_available(profile):
    need(profile in native_catalog(), "handler_mismatch")
    need(os.name == "nt" and sys.version_info[:3] == (3, 12, 6) and
         sqlite3.sqlite_version == "3.45.3", "runtime_mismatch")
    for path, expected in artifact_paths():
        need(c.sha256(path.read_bytes()) == expected, "artifact_mismatch")
