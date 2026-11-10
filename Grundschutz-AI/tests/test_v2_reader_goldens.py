"""Literal A-native vectors and current native-profile conformance tests.

Expected values come only from an isolated 2ee9bc7 producer. Current snapshot
checks test current profile conformance; they never create historical catalog
expectations or participate in Gate A replay. No persistent validation exists.
"""
import base64
from contextlib import ExitStack
from dataclasses import asdict, replace
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import unicodedata
import zipfile

from grundschutz_ai import docx_ingestion as docx, xlsx_ingestion as xlsx
from grundschutz_ai import docx_staging as ds, xlsx_staging as xs

GOLDENS = Path(__file__).parent / "fixtures/b0-native-goldens.json"
GOLDENS_SHA256 = "553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_data(value):
    # Container conversion only; source text/Unicode/whitespace remain exact.
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


class NativeGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = GOLDENS.read_bytes()
        if sha(raw) != GOLDENS_SHA256:
            raise AssertionError("Immutable historical golden text fixture changed")
        cls.golden = json.loads(raw)
        cls.cases = cls.golden["cases"]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grundschutz-ai-native-golden-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def native(self, name):
        case = self.cases[name]
        path = self.directory / (name + "." + case["kind"])
        path.write_bytes(base64.b64decode(case["original_bytes_base64"], validate=True))
        if case["kind"] == "docx":
            return docx.ingest_docx(path, source_id=case["source_id"],
                                    limits=docx.DocxLimits(**case["reader_limits"]))
        return xlsx.ingest_xlsx(path, source_id=case["source_id"],
                               limits=xlsx.XlsxLimits(**case["reader_limits"]))

    def snapshot(self, name, native=None, *, stamp=None, selection=None):
        case = self.cases[name]
        native = native or self.native(name)
        ref = ds.RegistrationRef(case["source_id"], 1, "1" * 32)
        if case["kind"] == "docx":
            observed_stamp = ds.DocxStaging()._reader_implementation if stamp is None else stamp
            return ds.DocumentSnapshot(ref, native, observed_stamp)
        observed_stamp = xs.XlsxStaging()._reader_implementation if stamp is None else stamp
        return xs.WorkbookSnapshot(ref, selection or xs.SheetSelection(**case["selection"]),
                                   native, observed_stamp)

    def assert_native(self, name, native):
        expected = self.cases[name]
        is_docx = expected["kind"] == "docx"
        observed = {
            "source_id": native.source_id, "reader_method": native.method,
            "binary_sha256": native.docx_sha256 if is_docx else native.xlsx_sha256,
            "native_text": native.text, "native_text_sha256": native.text_sha256,
            "reader_limits": asdict(native.limits),
            "native_manifest_json": None if is_docx else native.manifest_json,
            "native_manifest_sha256": None if is_docx else native.manifest_sha256,
            "observations": [asdict(value) for value in (native.segments if is_docx else native.sheets)],
            "cell_spans": ([] if is_docx else
                [{"sheet_ordinal": c.sheet_ordinal, "coordinate": c.coordinate,
                  "char_start": 0, "char_end": len(c.text)} for c in native.cells]),
        }
        self.assertEqual(json_data(observed), {key: expected[key] for key in observed})
        self.assertEqual(native.original_bytes,
                         base64.b64decode(expected["original_bytes_base64"], validate=True))

    def assert_integration(self, name, snapshot):
        expected = self.cases[name]
        self.assertEqual(snapshot.reader_implementation_sha256, expected["reader_implementation_sha256"])
        self.assertEqual(snapshot.manifest_json, expected["integration_manifest_json"])
        self.assertEqual(snapshot.manifest_sha256, expected["integration_manifest_sha256"])

    def test_exact_literal_fixture_identity_and_baseline(self):
        self.assertEqual(sha(GOLDENS.read_bytes()), GOLDENS_SHA256)
        self.assertEqual(self.golden["producer_commit"], "2ee9bc7cf309727e5a9f10e2982791dbc991c464")
        self.assertEqual(self.golden["fixture_version"], "b0-native-goldens/v1")
        self.assertIs(self.golden["synthetic_only"], True)
        self.assertEqual(len(self.cases), 7)

    def test_exact_runtime_and_reader_artifacts(self):
        self.assertEqual(".".join(map(str, sys.version_info[:3])), "3.12.6")
        self.assertEqual(sqlite3.sqlite_version, "3.45.3")
        expected = {v["module_name"]: v["sha256"] for v in self.golden["module_hashes"]}
        for name in ("docx_ingestion", "xlsx_ingestion", "ooxml_safety"):
            self.assertEqual(sha((Path(docx.__file__).parent / (name + ".py")).read_bytes()), expected[name])

    def test_original_bytes_hashes_and_zip_conventions(self):
        for name, case in self.cases.items():
            with self.subTest(name=name):
                raw = base64.b64decode(case["original_bytes_base64"], validate=True)
                self.assertEqual(len(raw), case["original_byte_length"])
                self.assertEqual(sha(raw), case["binary_sha256"])
                with zipfile.ZipFile(BytesIO(raw)) as archive:
                    observed = [{"name": z.filename, "date_time": list(z.date_time),
                                 "compression": z.compress_type, "size": z.file_size,
                                 "content_sha256": sha(archive.read(z))}
                                for z in archive.infolist()]
                self.assertEqual(observed, case["zip_entries"])
                self.assertTrue(all(z["date_time"] == [2020, 1, 1, 0, 0, 0] and z["compression"] == 0
                                    for z in observed))

    def test_all_literal_text_and_manifest_digests(self):
        for name, case in self.cases.items():
            with self.subTest(name=name):
                self.assertEqual(sha(case["native_text"].encode("utf-8")), case["native_text_sha256"])
                self.assertEqual(sha(case["integration_manifest_json"].encode("utf-8")),
                                 case["integration_manifest_sha256"])
                if case["kind"] == "docx":
                    self.assertIsNone(case["native_manifest_json"])
                    self.assertIsNone(case["native_manifest_sha256"])
                else:
                    self.assertEqual(sha(case["native_manifest_json"].encode("utf-8")),
                                     case["native_manifest_sha256"])

    def test_docx_complete_native_exact(self):
        self.assert_native("docx_complete", self.native("docx_complete"))

    def test_docx_complete_current_integration_conformance(self):
        self.assert_integration("docx_complete", self.snapshot("docx_complete"))

    def test_docx_coverage_native_exact(self):
        self.assert_native("docx_coverage", self.native("docx_coverage"))

    def test_docx_coverage_current_integration_conformance(self):
        self.assert_integration("docx_coverage", self.snapshot("docx_coverage"))

    def test_xlsx_complete_native_exact(self):
        self.assert_native("xlsx_complete", self.native("xlsx_complete"))

    def test_xlsx_complete_current_integration_conformance(self):
        self.assert_integration("xlsx_complete", self.snapshot("xlsx_complete"))

    def test_xlsx_coverage_native_exact(self):
        self.assert_native("xlsx_coverage", self.native("xlsx_coverage"))

    def test_xlsx_coverage_current_integration_conformance(self):
        self.assert_integration("xlsx_coverage", self.snapshot("xlsx_coverage"))

    def test_xlsx_blank_missing_empty_native_and_integration(self):
        for name in ("xlsx_blank", "xlsx_missing", "xlsx_empty_text"):
            with self.subTest(name=name):
                native = self.native(name)
                self.assert_native(name, native)
                self.assert_integration(name, self.snapshot(name, native))

    def test_blank_missing_and_empty_text_are_three_distinct_observations(self):
        blank, missing, empty = (self.native(name) for name in ("xlsx_blank", "xlsx_missing", "xlsx_empty_text"))
        self.assertEqual(blank.sheets[0].cell_at("B2").kind, xlsx.CellKind.BLANK)
        self.assertIsNone(missing.sheets[0].cell_at("B2"))
        self.assertEqual(empty.sheets[0].cell_at("B2").kind, xlsx.CellKind.TEXT)
        self.assertEqual(empty.sheets[0].cell_at("B2").text, "")
        self.assertEqual(blank.text_sha256, empty.text_sha256)
        self.assertEqual(len({n.manifest_sha256 for n in (blank, missing, empty)}), 3)

    def test_docx_unicode_whitespace_and_codepoint_offsets_preserved(self):
        native = self.native("docx_coverage")
        segment = native.segments[1]
        self.assertEqual(segment.text, "  FIKTIV: Grüße, Cafe\u0301.  ")
        self.assertEqual(segment.locator.char_end, 25)
        self.assertNotEqual(len(segment.text.encode("utf-8")), segment.locator.char_end)
        self.assertNotEqual(unicodedata.normalize("NFC", segment.text), segment.text)
        self.assertEqual(native.segments[2].text, "")
        self.assertEqual(native.segments[2].locator.char_end, 0)

    def test_xlsx_exact_headers_sheet_identity_and_cell_offsets(self):
        native = self.native("xlsx_complete")
        sheet = native.sheets[0]
        self.assertEqual([c.coordinate for c in sheet.cells], ["A1", "B1", "C1", "A2", "B2", "C2"])
        self.assertEqual([c.text for c in sheet.cells[:3]], ["System-ID", "Standort", "Anwendung"])
        self.assertTrue(xs.SheetSelection(**self.cases["xlsx_complete"]["selection"]).matches(sheet))
        self.assertEqual([(c.coordinate, len(c.text)) for c in sheet.cells],
                         [("A1", 9), ("B1", 8), ("C1", 9), ("A2", 7), ("B2", 21), ("C2", 6)])

    def test_changed_source_bytes_detected(self):
        native = self.native("docx_complete")
        forged = replace(native, original_bytes=native.original_bytes[:-1] + b"X")
        with self.assertRaises(AssertionError):
            self.assert_native("docx_complete", forged)

    def test_changed_extracted_text_detected(self):
        native = self.native("docx_complete")
        segment = replace(native.segments[0], text=native.segments[0].text.replace("Rostock", "Berlin!"))
        forged = replace(native, segments=(segment,))
        with self.assertRaises(AssertionError):
            self.assert_native("docx_complete", forged)

    def test_incorrect_paragraph_locator_detected_without_text_change(self):
        native = self.native("docx_complete")
        segment = replace(native.segments[0], locator=replace(native.segments[0].locator, body_index=2))
        forged = replace(native, segments=(segment,))
        self.assertEqual(native.text_sha256, forged.text_sha256)
        with self.assertRaises(AssertionError):
            self.assert_native("docx_complete", forged)
        with self.assertRaises(AssertionError):
            self.assert_integration("docx_complete", self.snapshot("docx_complete", forged))

    def test_incomplete_docx_coverage_detected(self):
        native = self.native("docx_coverage")
        with self.assertRaises(AssertionError):
            self.assert_native("docx_coverage", replace(native, segments=native.segments[:-1]))

    def test_missing_empty_sheet_detected_despite_identical_text(self):
        native = self.native("xlsx_coverage")
        forged = replace(native, sheets=native.sheets[:1])
        self.assertEqual(native.text_sha256, forged.text_sha256)
        self.assertNotEqual(native.manifest_sha256, forged.manifest_sha256)
        with self.assertRaises(AssertionError):
            self.assert_native("xlsx_coverage", forged)
        with self.assertRaises(AssertionError):
            self.assert_integration("xlsx_coverage", self.snapshot("xlsx_coverage", forged))

    def test_blank_to_text_kind_change_detected_despite_same_text_hash(self):
        native = self.native("xlsx_blank")
        sheet = native.sheets[0]
        cells = tuple(replace(c, kind=xlsx.CellKind.TEXT) if c.coordinate == "B2" else c for c in sheet.cells)
        forged = replace(native, sheets=(replace(sheet, cells=cells),))
        self.assertEqual(native.text_sha256, forged.text_sha256)
        with self.assertRaises(AssertionError):
            self.assert_native("xlsx_blank", forged)

    def test_changed_header_detected(self):
        native = self.native("xlsx_complete")
        sheet = native.sheets[0]
        forged = replace(native, sheets=(replace(sheet, cells=(replace(sheet.cells[0], text="Asset-ID"), *sheet.cells[1:])),))
        with self.assertRaises(AssertionError):
            self.assert_native("xlsx_complete", forged)

    def test_incorrect_cell_coordinates_rejected(self):
        native = self.native("xlsx_complete")
        with self.assertRaises(xlsx.XlsxIngestionError):
            replace(native.sheets[0].cells[0], coordinate="B1")

    def test_changed_explicit_sheet_selection_detected(self):
        selected = xs.SheetSelection(**self.cases["xlsx_complete"]["selection"])
        snapshot = self.snapshot("xlsx_complete", selection=replace(selected, relationship_id="rId2"))
        with self.assertRaises(AssertionError):
            self.assert_integration("xlsx_complete", snapshot)

    def test_changed_reader_stamp_and_integration_detected(self):
        for name in ("docx_complete", "xlsx_complete"):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.assert_integration(name, self.snapshot(name, stamp="0" * 64))

    def test_repackaging_keeps_native_semantics_but_changes_integration(self):
        case = self.cases["xlsx_complete"]
        original = self.native("xlsx_complete")
        repackaged = self.directory / "repackaged.xlsx"
        with zipfile.ZipFile(BytesIO(original.original_bytes)) as before, zipfile.ZipFile(repackaged, "w") as after:
            for info in before.infolist():
                target = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                target.compress_type = zipfile.ZIP_DEFLATED
                after.writestr(target, before.read(info))
        new = xlsx.ingest_xlsx(repackaged, source_id=case["source_id"], limits=original.limits)
        self.assertNotEqual(new.xlsx_sha256, case["binary_sha256"])
        self.assertEqual(new.text_sha256, case["native_text_sha256"])
        self.assertEqual(new.manifest_json, case["native_manifest_json"])
        with self.assertRaises(AssertionError):
            self.assert_integration("xlsx_complete", self.snapshot("xlsx_complete", new))

    def test_A0_quarantine_bytes_do_not_become_native_valid_documents(self):
        for kind, reader, error in (("docx", docx.ingest_docx, docx.DocxIngestionError),
                                    ("xlsx", xlsx.ingest_xlsx, xlsx.XlsxIngestionError)):
            with self.subTest(kind=kind):
                path = self.directory / ("invalid." + kind)
                path.write_bytes(("FICTITIOUS A0 " + kind.upper() + " CAPTURE\n").encode("ascii"))
                with self.assertRaises(error):
                    reader(path, source_id="synthetic:untrusted-capture")

    def test_no_model_database_inventory_or_review_side_effects(self):
        targets = ("urllib.request.urlopen", "socket.create_connection", "sqlite3.connect",
                   "grundschutz_ai.domain.Evidence", "grundschutz_ai.inventory.Inventory.add",
                   "grundschutz_ai.inventory.Inventory.record_review")
        with ExitStack() as stack:
            spies = [stack.enter_context(patch(name, side_effect=AssertionError("side effect"))) for name in targets]
            for name in ("docx_complete", "xlsx_complete"):
                native = self.native(name)
                self.assert_native(name, native)
                self.assert_integration(name, self.snapshot(name, native))
            for spy in spies:
                spy.assert_not_called()

    def test_original_historical_producer_reproduces_literal_vectors(self):
        checkout = os.environ.get("GRUNDSCHUTZ_NATIVE_A_CHECKOUT")
        if not checkout:
            self.skipTest("Set GRUNDSCHUTZ_NATIVE_A_CHECKOUT for the independent historical producer proof")
        output = self.directory / "reproduced-native-goldens.json"
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("native_golden_oracle.py")),
                                 "--checkout", checkout, "--output", str(output)],
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(output.read_bytes(), GOLDENS.read_bytes())
