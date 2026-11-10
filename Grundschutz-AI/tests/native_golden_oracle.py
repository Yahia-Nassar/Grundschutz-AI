"""Test-only producer of native goldens from a verified 2ee9bc7 LF checkout.

Run as a fresh subprocess; output is synthetic text provenance, never a database.
No current application/staging modules are imported to create expected values.
"""
import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile

# This existing harness has literal ADR-0010 identities and no application import.
from a0_oracle import FROZEN, canonical

HELPER_HASHES = {
    "test_docx_ingestion.py": "b0d4083d19b6295bd29e3840f65d38bd76447d3dc379dd7cc523b764566d46f1",
    "test_xlsx_ingestion.py": "15634d1eefde3552f6eee1cad5ebf75fc247e70ac648b7f41894a238749eb373",
    "test_docx_staging.py": "eeeeba2de87aa716fa1a68527878e2fbdb614192bfb90b85efa5d77f3fc04478",
    "test_xlsx_staging.py": "f3896ae9db2f174e18a757cf34c624f49dad073334d47683d8136562c4e23123",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def produce(checkout, output):
    checkout, output = Path(checkout).resolve(), Path(output).resolve()
    if (os.name != "nt" or sys.version_info[:3] != (3, 12, 6) or
            sqlite3.sqlite_version != "3.45.3"):
        raise RuntimeError("Exact A0 Windows/Python/SQLite profile required")
    if any(name == "tests" or name.startswith("grundschutz_ai") for name in sys.modules):
        raise RuntimeError("Producer requires a fresh isolated-import subprocess")
    for module in FROZEN["descriptors"]["docx"]["module_hashes"]:
        if sha((checkout / "grundschutz_ai" / (module["module_name"] + ".py")).read_bytes()) != module["sha256"]:
            raise RuntimeError("Historical A module differs; refusing goldens")
    for name, expected in HELPER_HASHES.items():
        if sha((checkout / "tests" / name).read_bytes()) != expected:
            raise RuntimeError("Historical fixture helper differs")
    sys.path.insert(0, str(checkout))
    from grundschutz_ai import docx_ingestion as docx, xlsx_ingestion as xlsx
    from grundschutz_ai import docx_staging as ds, xlsx_staging as xs, v2_ledger as ledger
    from tests import test_docx_staging as dt, test_xlsx_staging as xt
    from tests.test_docx_ingestion import paragraph, table, synthetic_parts, write_synthetic_docx
    from tests.test_xlsx_ingestion import write_synthetic_xlsx
    for module in (docx, xlsx, ds, xs, ledger):
        if Path(module.__file__).resolve().parent != checkout / "grundschutz_ai":
            raise RuntimeError("Wrong application imported")
    for kind, policy in (("docx", ds.StagingPolicy()), ("xlsx", xs.StagingPolicy())):
        spec = ledger._local_spec(kind)
        if spec.canonical != canonical(FROZEN["descriptors"][kind]):
            raise RuntimeError("Historical implementation identity differs")
        if ledger._policy_spec(kind, policy, spec.sha256).canonical != canonical(FROZEN["policies"][kind]):
            raise RuntimeError("Historical policy identity differs")
    stamps = {"docx": ds.DocxStaging()._reader_implementation,
              "xlsx": xs.XlsxStaging()._reader_implementation}
    cases = {}
    with tempfile.TemporaryDirectory(prefix="grundschutz-ai-native-a0-") as directory:
        directory = Path(directory)
        ledger._fixed_local_volume(directory)
        def capture(name, kind, parts):
            path = directory / (name + "." + kind)
            (write_synthetic_docx if kind == "docx" else write_synthetic_xlsx)(path, parts)
            source = dt.SOURCE if kind == "docx" else xt.SOURCE
            native = (docx.ingest_docx if kind == "docx" else xlsx.ingest_xlsx)(path, source_id=source)
            ref = ds.RegistrationRef(source, 1, "1" * 32)
            snapshot = (ds.DocumentSnapshot(ref, native, stamps[kind]) if kind == "docx" else
                        xs.WorkbookSnapshot(ref, xt.SELECTION, native, stamps[kind]))
            native_manifest = None if kind == "docx" else native.manifest_json
            observations = ([asdict(segment) for segment in native.segments] if kind == "docx" else
                            [asdict(sheet) for sheet in native.sheets])
            with zipfile.ZipFile(path) as archive:
                entries = [{"name": info.filename, "date_time": list(info.date_time),
                            "compression": info.compress_type, "size": info.file_size,
                            "content_sha256": sha(archive.read(info))}
                           for info in archive.infolist()]
            cases[name] = {
                "synthetic_only": True, "kind": kind, "source_id": source,
                "original_bytes_base64": base64.b64encode(native.original_bytes).decode("ascii"),
                "original_byte_length": len(native.original_bytes),
                "binary_sha256": native.docx_sha256 if kind == "docx" else native.xlsx_sha256,
                "zip_entries": entries, "reader_method": native.method,
                "reader_spec_sha256": ledger._local_spec(kind).sha256,
                "reader_implementation_sha256": stamps[kind],
                "reader_limits": asdict(native.limits),
                "selection": None if kind == "docx" else asdict(xt.SELECTION),
                "native_text": native.text, "native_text_sha256": native.text_sha256,
                "native_manifest_json": native_manifest,
                "native_manifest_sha256": None if kind == "docx" else native.manifest_sha256,
                "observations": observations,
                "cell_spans": ([] if kind == "docx" else
                    [{"sheet_ordinal": cell.sheet_ordinal, "coordinate": cell.coordinate,
                      "char_start": 0, "char_end": len(cell.text)} for cell in native.cells]),
                "integration_manifest_json": snapshot.manifest_json,
                "integration_manifest_sha256": snapshot.manifest_sha256,
            }
        capture("docx_complete", "docx", synthetic_parts(paragraph(dt.COMPLETE)))
        capture("docx_coverage", "docx", synthetic_parts(
            paragraph(dt.COMPLETE),
            table([[("  FIKTIV: Grüße, Cafe\u0301.  ", ""), "Raum Ä-01"]]),
            paragraph("FIKTIVER NACHTRAG")))
        capture("xlsx_complete", "xlsx", xt.fictional_parts())
        capture("xlsx_blank", "xlsx", xt.fictional_parts(values=(("SRV-001", None, "ERP-01"),)))
        capture("xlsx_missing", "xlsx", xt.fictional_parts(values=(("SRV-001", xt.ABSENT, "ERP-01"),)))
        capture("xlsx_empty_text", "xlsx", xt.fictional_parts(values=(("SRV-001", "", "ERP-01"),)))
        capture("xlsx_coverage", "xlsx", xt.fictional_parts(extra_sheet=True))
    data = {"fixture_version": "b0-native-goldens/v1", "synthetic_only": True,
            "producer_commit": "2ee9bc7cf309727e5a9f10e2982791dbc991c464",
            "runtime": FROZEN["descriptors"]["docx"]["runtime"],
            "module_hashes": FROZEN["descriptors"]["docx"]["module_hashes"],
            "fixture_helper_hashes": HELPER_HASHES, "cases": cases}
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if output.exists():
        raise RuntimeError("Golden producer refuses to overwrite an existing output")
    output.write_bytes(raw)
    return {"goldens_sha256": sha(raw), "bytes": len(raw),
            "cases": {key: {field: value[field] for field in
                       ("binary_sha256", "native_text_sha256", "native_manifest_sha256",
                        "integration_manifest_sha256", "reader_implementation_sha256")}
                      for key, value in cases.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(produce(args.checkout, args.output), sort_keys=True))
