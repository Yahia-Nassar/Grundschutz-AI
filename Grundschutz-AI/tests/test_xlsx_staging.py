"""Fictional XLSX staging/security fixtures; temporary, offline and unapproved."""

from contextlib import ExitStack
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from grundschutz_ai import xlsx_staging as staging
from grundschutz_ai.domain import Predicate, ReviewState
from grundschutz_ai.xlsx_ingestion import CellKind, ingest_xlsx, S
from tests.test_xlsx_ingestion import text_cell, synthetic_parts, write_synthetic_xlsx, edit


SOURCE = "synthetic:task-0072"
SECOND = "synthetic:task-0072-other"
SELECTION = staging.SheetSelection("IT-Systeme", 1, 1, "rId1", "xl/worksheets/sheet1.xml")
ROW = ("SRV-001", "Rechenzentrum Rostock", "ERP-01")
OTHER = ("SRV-002", "Rechenzentrum Berlin", "CRM-02")
TIME = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
ABSENT = object()


def fictional_parts(values=(ROW,), *, headers=staging.HEADERS, indices=None, extra_sheet=False):
    """Test-only workbook builder; None means physically present BLANK."""
    rows = [(1, [text_cell(f"{column}1", value) for column, value in zip("ABC", headers) if value is not ABSENT])]
    for index, values_row in zip(indices if indices is not None else range(2, len(values) + 2), values):
        cells = []
        for column, value in zip("ABC", values_row):
            if value is ABSENT:
                continue
            cells.append(ET.Element(f"{{{S}}}c", {"r": f"{column}{index}"}) if value is None else text_cell(f"{column}{index}", value))
        rows.append((index, cells))
    sheets = [("IT-Systeme", SELECTION.part, rows)]
    if extra_sheet:
        sheets.append(("Fiktiv-Extra", "xl/worksheets/sheet2.xml", []))
    return synthetic_parts(sheets)


class XlsxStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="grundschutz-ai-xlsx-staging-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.assertFalse(self.directory.resolve().is_relative_to(Path(__file__).resolve().parents[2]))
        self.session = staging.XlsxStaging()
        self.paths = []

    def fixture(self, values=(ROW,), *, parts=None, compression=zipfile.ZIP_STORED):
        path = self.directory / f"fictitious-{len(self.paths) + 1}.xlsx"
        self.paths.append(path)
        return write_synthetic_xlsx(path, fictional_parts(values) if parts is None else parts, compression=compression)

    def register(self, values=(ROW,), *, name=SOURCE, session=None, selection=SELECTION, parts=None):
        return (session or self.session).register_xlsx(name, self.fixture(values, parts=parts), selection)

    def report(self, names=(SOURCE,), *, session=None):
        session = session or self.session
        return session.stage(session.create_scope(names))

    def proposal(self):
        self.register()
        return self.report().proposals[0]

    def decide(self, candidate, state=ReviewState.REJECTED, **changes):
        values = dict(state=state, reviewer_id="synthetic:human", timestamp=TIME,
                      reason="Fictitious queue review", candidate_fingerprint=candidate.fingerprint,
                      context_fingerprint=candidate.context_fingerprint)
        values.update(changes)
        return self.session.triage(candidate.id, **values)

    def assert_blocked(self, report):
        self.assertEqual(report.proposals, ())
        self.assertTrue(report.issues)
        for candidate in report.candidates:
            if not candidate.issues:
                forced = staging.ValidatedProposal(replace(candidate, state=ReviewState.PROPOSED))
                self.assertFalse(self.session.is_eligible(forced))

    def test_valid_single_row_values_exact_headers_and_cell_locators(self):
        proposal = self.proposal()
        candidate = proposal.candidate
        self.assertIs(candidate.state, ReviewState.PROPOSED)
        self.assertEqual(candidate.row, 2)
        self.assertEqual([(item.name, item.value) for item in candidate.fields], list(zip(staging.FIELD_NAMES, ROW)))
        for column, header, value in zip("ABC", staging.HEADERS, candidate.fields):
            self.assertEqual(value.cell.cell.coordinate, column + "2")
            self.assertEqual(value.header.cell.coordinate, column + "1")
            self.assertEqual(value.header.cell.text, header)
            self.assertEqual(value.cell.selection, SELECTION)
            self.assertEqual(value.cell.char_start, 0)
            self.assertEqual(value.cell.char_end, len(value.value))
            self.assertEqual(value.cell.cell.text_sha256, hashlib.sha256(value.value.encode()).hexdigest())
            self.assertEqual(value.cell.binding_fingerprint, candidate.binding.fingerprint)
        self.assertEqual([(item.predicate, item.subject_asset_name, item.object_name) for item in candidate.claims], [(Predicate.HOSTS, ROW[0], ROW[2]), (Predicate.LOCATED_AT, ROW[0], ROW[1])])
        self.assertTrue(self.session.is_eligible(proposal))

    def test_multiple_rows_are_ordered_and_have_full_structural_claim_support(self):
        self.register((ROW, OTHER))
        report = self.report()
        self.assertEqual([item.row for item in report.candidates], [2, 3])
        self.assertEqual(len(report.proposals), 2)
        for candidate in report.candidates:
            for claim in candidate.claims:
                self.assertEqual(claim.support.policy_version, "synthetic-it-table/v1")
                self.assertEqual([ref.cell.coordinate for ref in claim.support.cells], [f"{col}{candidate.row}" for col in "ABC"])
                self.assertEqual([ref.cell.coordinate for ref in claim.support.headers], [col + "1" for col in "ABC"])
                self.assertFalse(hasattr(claim, "evidence_quote"))

    def test_all_hashes_have_distinct_verifiable_contracts(self):
        event = self.register()
        snapshot = self.session.snapshot(event.ref)
        native = snapshot.native
        self.assertEqual(event.original_bytes, self.paths[0].read_bytes())
        self.assertEqual(event.binary_sha256, native.xlsx_sha256)
        self.assertEqual(native.xlsx_sha256, hashlib.sha256(native.original_bytes).hexdigest())
        self.assertEqual(native.text_sha256, hashlib.sha256(native.text.encode("utf-8")).hexdigest())
        self.assertEqual(native.manifest_sha256, hashlib.sha256(native.manifest_json.encode("utf-8")).hexdigest())
        self.assertEqual(snapshot.manifest_sha256, hashlib.sha256(snapshot.manifest_json.encode("utf-8")).hexdigest())
        manifest = json.loads(snapshot.manifest_json)
        self.assertEqual(manifest["native_manifest_json"], native.manifest_json)
        self.assertEqual(manifest["native_manifest_sha256"], native.manifest_sha256)
        self.assertEqual(manifest["binary_sha256"], native.xlsx_sha256)
        self.assertEqual(manifest["selection"], asdict(SELECTION))
        self.assertEqual(manifest["reader_method"], "xlsx-literal/v1")
        self.assertEqual(manifest["reader_limits"], asdict(native.limits))
        self.assertNotIn("registration_id", snapshot.manifest_json)
        self.assertNotEqual(snapshot.manifest_sha256, native.manifest_sha256)

    def test_unicode_text_and_exact_cell_local_offsets(self):
        self.register(((ROW[0], "Rechenzentrum München, Raum A-1", ROW[2]),))
        field = self.report().proposals[0].candidate.fields[1]
        self.assertEqual(field.value, "Rechenzentrum München, Raum A-1")
        self.assertEqual(field.cell.char_end, len(field.value))
        self.assertEqual(field.cell.cell.text_sha256, hashlib.sha256(field.value.encode("utf-8")).hexdigest())

    def test_explicit_blank_location_is_null_without_positive_quote_or_edge(self):
        self.register(((ROW[0], None, ROW[2]),))
        candidate = self.report().proposals[0].candidate
        location = candidate.fields[1]
        self.assertIsNone(location.value)
        self.assertEqual(location.positive_quotes, ())
        self.assertIs(location.cell.cell.kind, CellKind.BLANK)
        self.assertEqual(location.cell.cell.coordinate, "B2")
        self.assertEqual(location.missing.reason, "explicit_blank")
        self.assertEqual([claim.predicate for claim in candidate.claims], [Predicate.HOSTS])

    def test_absent_location_is_not_explicit_blank(self):
        self.register(((ROW[0], ABSENT, ROW[2]),))
        report = self.report()
        self.assert_blocked(report)
        self.assertIn("missing_cell", [item.code for item in report.issues])

    def test_empty_text_location_and_placeholders_are_not_null(self):
        for value in ("", "null", "NULL", "None", "unbekannt", "-", "Rechenzentrum Unbekannt"):
            with self.subTest(value=value):
                self.session = staging.XlsxStaging()
                self.register(((ROW[0], value, ROW[2]),))
                self.assert_blocked(self.report())

    def test_bare_city_and_shortened_or_modified_locations_are_not_inferred(self):
        for value in ("Berlin", "Rostock", "rechenzentrum Rostock", " Rechenzentrum Rostock", "Rechenzentrum Rostock ", "Rechenzentrum Rostock nicht"):
            with self.subTest(value=value):
                self.session = staging.XlsxStaging()
                self.register(((ROW[0], value, ROW[2]),))
                self.assert_blocked(self.report())

    def test_required_identifiers_reject_missing_blank_empty_and_unsupported_values(self):
        for column in (0, 2):
            for value in (ABSENT, None, "", "null", "srv-001", "SRV", "SRV-001!", "123", " SRV-001"):
                with self.subTest(column=column, value=value):
                    self.session = staging.XlsxStaging()
                    row = list(ROW)
                    row[column] = value
                    self.register((tuple(row),))
                    self.assert_blocked(self.report())

    def test_longer_ids_stay_complete_and_partial_candidate_forgery_is_ineligible(self):
        self.register((("SRV-0012", ROW[1], "ERP-010"),))
        proposal = self.report().proposals[0]
        self.assertEqual(proposal.candidate.fields[0].value, "SRV-0012")
        self.assertEqual(proposal.candidate.fields[2].value, "ERP-010")
        with self.assertRaises(ValueError):
            replace(proposal.candidate.fields[0], value="SRV-001")
        forged = staging.ValidatedProposal(replace(proposal.candidate, row=3))
        self.assertFalse(self.session.is_eligible(forged))

    def test_headers_are_exact_text_and_cannot_be_missing_or_blank(self):
        for headers in (("system-id", "Standort", "Anwendung"), ("System-ID ", "Standort", "Anwendung"), ("System-ID", ABSENT, "Anwendung"), ("System-ID", "", "Anwendung")):
            self.session = staging.XlsxStaging()
            self.register(parts=fictional_parts(headers=headers))
            self.assert_blocked(self.report())

    def test_blank_header_and_shifted_header_row_fail_closed(self):
        for change in (lambda root: root[0][0].remove(root[0][0][1]), lambda root: root[0].remove(root[0][0])):
            self.session = staging.XlsxStaging()
            parts = edit(fictional_parts(), SELECTION.part, change)
            self.register(parts=parts)
            self.assert_blocked(self.report())

    def test_header_only_or_empty_sheet_has_no_eligible_rows(self):
        for parts in (fictional_parts(()), synthetic_parts([("IT-Systeme", SELECTION.part, [])])):
            self.session = staging.XlsxStaging()
            self.register(parts=parts)
            self.assert_blocked(self.report())

    def test_extra_visible_sheet_even_empty_blocks_workbook(self):
        event = self.register(parts=fictional_parts(extra_sheet=True))
        self.assertIs(event.status, staging.RegistrationStatus.VALID)
        self.assertEqual(len(self.session.snapshot(event.ref).native.sheets), 2)
        report = self.report()
        self.assert_blocked(report)
        self.assertIn("sheet_count", [item.code for item in report.issues])

    def test_explicit_selection_must_match_every_sheet_identity_component(self):
        for selection in (replace(SELECTION, ordinal=2), replace(SELECTION, sheet_id=2), replace(SELECTION, relationship_id="rId2"), replace(SELECTION, part="xl/worksheets/sheet2.xml")):
            self.session = staging.XlsxStaging()
            self.register(selection=selection)
            report = self.report()
            self.assert_blocked(report)
            self.assertIn("sheet_selection", [item.code for item in report.issues])
        with self.assertRaises(ValueError):
            replace(SELECTION, name="it-systeme")
        with self.assertRaises(TypeError):
            self.session.register_xlsx(SOURCE, self.fixture())

    def test_different_actual_sheet_id_is_accepted_only_when_explicitly_selected(self):
        from grundschutz_ai.xlsx_ingestion import WORKBOOK
        parts = edit(fictional_parts(), WORKBOOK, lambda root: root[0][0].set("sheetId", "7"))
        self.register(parts=parts, selection=replace(SELECTION, sheet_id=7))
        self.assertEqual(len(self.report().proposals), 1)
        self.assertEqual(self.report().candidates[0].fields[0].cell.selection.sheet_id, 7)

    def test_extra_header_or_data_cells_are_never_ignored(self):
        for row_index in (0, 1):
            self.session = staging.XlsxStaging()
            parts = edit(fictional_parts(), SELECTION.part, lambda root: root[0][row_index].append(text_cell(f"D{row_index + 1}", "UNTRUSTED EXTRA")))
            self.register(parts=parts)
            self.assert_blocked(self.report())

    def test_row_gaps_explicit_empty_and_appended_prose_block_entire_workbook(self):
        cases = [fictional_parts((ROW,), indices=(3,)), fictional_parts((ROW, (ABSENT, ABSENT, ABSENT))), fictional_parts((ROW, ("Änderung: Standort nach Berlin verlegt", ABSENT, ABSENT)))]
        for parts in cases:
            self.session = staging.XlsxStaging()
            self.register(parts=parts)
            self.assert_blocked(self.report())

    def test_malformed_formula_hidden_and_external_content_reader_rejections(self):
        for change in (lambda root: ET.SubElement(root[0][1][0], f"{{{S}}}f"), lambda root: root[0][1].set("hidden", "1"), lambda root: ET.SubElement(root, f"{{{S}}}hyperlinks")):
            self.session = staging.XlsxStaging()
            event = self.register(parts=edit(fictional_parts(), SELECTION.part, change))
            self.assertIs(event.status, staging.RegistrationStatus.FAILED)
            self.assert_blocked(self.report())

    def test_duplicate_identical_rows_and_contradictory_locations_or_apps_block_all(self):
        for row in (ROW, (ROW[0], "Rechenzentrum Berlin", ROW[2]), (ROW[0], ROW[1], "CRM-02")):
            self.session = staging.XlsxStaging()
            self.register((ROW, row))
            report = self.report()
            self.assert_blocked(report)
            self.assertEqual(len(report.candidates), 2)
            self.assertEqual(len({item.id for item in report.candidates}), 2)
            self.assertIn("duplicate_asset", [item.code for item in report.issues])
            if row != ROW:
                self.assertIn("conflicting_assertions", [item.code for item in report.issues])

    def test_cross_workbook_duplicate_and_conflicting_assets_block_full_scope(self):
        for row in (ROW, (ROW[0], "Rechenzentrum Berlin", ROW[2])):
            self.session = staging.XlsxStaging()
            self.register()
            self.register((row,), name=SECOND)
            report = self.report((SOURCE, SECOND))
            self.assert_blocked(report)
            self.assertEqual(len(report.context.bindings), 2)
            self.assertIn("duplicate_asset", [item.code for item in report.issues])

    def test_multiple_workbooks_with_distinct_assets_are_eligible_together(self):
        self.register()
        self.register((OTHER,), name=SECOND)
        report = self.report((SOURCE, SECOND))
        self.assertEqual(len(report.proposals), 2)
        self.assertTrue(all(self.session.is_eligible(item) for item in report.proposals))

    def test_missing_pending_failed_sources_block_good_workbook(self):
        for mode in ("missing", "pending", "failed"):
            self.session = staging.XlsxStaging()
            self.register()
            if mode == "pending":
                self.session.begin_registration(SECOND, SELECTION)
            elif mode == "failed":
                self.session.register_xlsx(SECOND, self.directory / "absent.xlsx", SELECTION)
            report = self.report((SOURCE, SECOND))
            self.assert_blocked(report)
            self.assertIn("source_" + mode, [item.code for item in report.issues])

    def test_known_sources_cannot_be_silently_omitted(self):
        self.register()
        self.register((OTHER,), name=SECOND)
        report = self.report()
        self.assert_blocked(report)
        self.assertIn("scope_omits_source", [item.code for item in report.issues])

    def test_scope_is_idempotent_canonical_and_rejects_duplicate_names(self):
        self.register()
        self.register((OTHER,), name=SECOND)
        report = self.report((SOURCE, SECOND))
        self.assertIs(self.session.create_scope((SECOND, SOURCE)), report.context.scope)
        self.assertEqual(self.report((SECOND, SOURCE)), report)
        with self.assertRaises(ValueError):
            self.session.create_scope((SOURCE, SOURCE))

    def test_pending_registration_immediately_invalidates_old_proposal(self):
        old = self.proposal()
        ref = self.session.begin_registration(SOURCE, SELECTION)
        self.assertFalse(self.session.is_eligible(old))
        self.assert_blocked(self.report())
        self.assertEqual(ref.revision, 2)
        self.assertEqual(self.session.current_head(SOURCE).ref, ref)

    def test_failed_new_version_retains_bad_bytes_and_blocks_old(self):
        old = self.proposal()
        path = self.directory / "invalid.xlsx"
        raw = b"FICTITIOUS INVALID XLSX"
        path.write_bytes(raw)
        event = self.session.register_xlsx(SOURCE, path, SELECTION)
        self.assertIs(event.status, staging.RegistrationStatus.FAILED)
        self.assertEqual(event.original_bytes, raw)
        self.assertEqual(event.binary_sha256, hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.session.is_eligible(old))
        self.assert_blocked(self.report())

    def test_identical_registration_new_revision_same_manifest_and_new_fingerprints(self):
        old = self.proposal()
        before = self.session.snapshot(old.candidate.binding.ref)
        event = self.session.register_xlsx(SOURCE, self.paths[0], SELECTION)
        after = self.session.snapshot(event.ref)
        self.assertEqual(before.manifest_sha256, after.manifest_sha256)
        new = self.report().proposals[0]
        self.assertGreater(event.ref.revision, before.ref.revision)
        self.assertNotEqual(event.ref.registration_id, before.ref.registration_id)
        self.assertNotEqual(new.candidate.fingerprint, old.candidate.fingerprint)
        self.assertEqual(new.candidate.remediation_fingerprint, old.candidate.remediation_fingerprint)
        self.assertFalse(self.session.is_eligible(old))
        self.assertTrue(self.session.is_eligible(new))

    def test_capture_once_and_private_copy_are_exact_closed_and_removed(self):
        path = self.fixture()
        expected = path.read_bytes()
        real_reader = staging.reader.ingest_xlsx
        observed = []
        def read(copy, **kwargs):
            self.assertNotEqual(copy, path)
            self.assertFalse(copy.resolve().is_relative_to(Path(__file__).resolve().parents[2]))
            self.assertEqual(copy.read_bytes(), expected)
            path.write_bytes(b"FICTITIOUS PATH CHANGED AFTER CAPTURE")
            observed.append(copy)
            return real_reader(copy, **kwargs)
        with patch.object(staging.reader, "ingest_xlsx", side_effect=read):
            event = self.session.register_xlsx(SOURCE, path, SELECTION)
        self.assertIs(event.status, staging.RegistrationStatus.VALID)
        self.assertEqual(event.original_bytes, expected)
        self.assertTrue(all(not copy.exists() for copy in observed))

    def test_reader_failure_removes_private_temporary_copy(self):
        observed = []
        def fail(path, **kwargs):
            observed.append(path)
            raise staging.reader.XlsxIngestionError("Fictitious failure")
        with patch.object(staging.reader, "ingest_xlsx", side_effect=fail):
            event = self.register()
        self.assertIs(event.status, staging.RegistrationStatus.FAILED)
        self.assertTrue(all(not path.exists() for path in observed))

    def test_temp_root_inside_git_is_rejected_before_creating_copy(self):
        with patch.object(staging, "gettempdir", return_value=str(Path(__file__).resolve().parents[1])), patch.object(staging, "TemporaryDirectory") as temporary:
            event = self.register()
        temporary.assert_not_called()
        self.assertIs(event.status, staging.RegistrationStatus.FAILED)

    def test_claimed_native_results_are_reparsed_and_forged_values_rejected(self):
        path = self.fixture()
        native = ingest_xlsx(path, source_id=SOURCE)
        for forged in (replace(native, original_bytes=b"FICTITIOUS FORGED"), replace(native, sheets=(replace(native.sheets[0], sheet_id=7),)), replace(native, sheets=(replace(native.sheets[0], cells=native.sheets[0].cells[:-1]),))):
            self.session = staging.XlsxStaging()
            event = self.session.register_xlsx(SOURCE, path, SELECTION, claimed_extraction=forged)
            self.assertIs(event.status, staging.RegistrationStatus.FAILED)
            self.assert_blocked(self.report())
        self.session = staging.XlsxStaging()
        self.assertIs(self.session.register_xlsx(SOURCE, path, SELECTION, claimed_extraction=native).status, staging.RegistrationStatus.VALID)

    def test_forged_computed_hashes_or_cell_coordinates_do_not_pass_binding(self):
        path = self.fixture()
        for attribute in ("text_sha256", "manifest_sha256", "xlsx_sha256"):
            native = ingest_xlsx(path, source_id=SOURCE)
            object.__setattr__(native, attribute, "0" * 64)
            self.assertIs(self.session.register_xlsx(SOURCE, path, SELECTION, claimed_extraction=native).status, staging.RegistrationStatus.FAILED)

    def test_late_older_completion_never_replaces_newer_source_head(self):
        older = self.session.begin_registration(SOURCE, SELECTION)
        newer = self.session.begin_registration(SOURCE, SELECTION)
        self.session.finish_registration(newer, self.fixture((OTHER,)))
        self.session.finish_registration(older, self.fixture())
        self.assertEqual(self.session.current_head(SOURCE).ref, newer)
        self.assertEqual(self.report().candidates[0].fields[0].value, OTHER[0])

    def test_registration_events_and_old_history_are_immutable(self):
        first = self.register()
        history = self.session.registration_history(SOURCE)
        self.assertEqual([item.status for item in history], [staging.RegistrationStatus.PENDING, staging.RegistrationStatus.PENDING, staging.RegistrationStatus.VALID])
        self.register((OTHER,))
        self.assertEqual(len(history), 3)
        self.assertEqual(len(self.session.registration_history(SOURCE)), 6)
        self.assertEqual(first.original_bytes, self.paths[0].read_bytes())
        with self.assertRaises(FrozenInstanceError):
            first.status = staging.RegistrationStatus.FAILED

    def test_double_finish_foreign_registration_and_foreign_scope_are_rejected(self):
        event = self.register()
        with self.assertRaises(ValueError):
            self.session.finish_registration(event.ref, self.paths[0])
        foreign = staging.XlsxStaging()
        with self.assertRaises(ValueError):
            self.session.finish_registration(foreign.begin_registration(SOURCE, SELECTION), self.paths[0])
        self.assert_blocked(self.session.stage(foreign.create_scope((SOURCE,))))

    def test_rejection_and_clarification_survive_unrelated_resource_policy_changes(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION):
            self.session = staging.XlsxStaging()
            old = self.proposal()
            decision = self.decide(old.candidate, state)
            self.session.set_policy(replace(staging.StagingPolicy(), max_id_chars=63))
            report = self.report()
            self.assert_blocked(report)
            current = report.candidates[0]
            self.assertIs(current.state, state)
            self.assertEqual(current.remediation_fingerprint, old.candidate.remediation_fingerprint)
            self.assertNotEqual(current.fingerprint, old.candidate.fingerprint)
            self.assertFalse(self.session.is_eligible(old))
            self.assertEqual(self.session.decision_history(), (decision,))

    def test_relaxing_limits_never_clears_human_block_when_fields_were_not_emitted(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION):
            for limits in ({"max_id_chars": 6}, {"max_location_chars": 20}):
                self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), **limits))
                self.register()
                candidate = self.report().candidates[0]
                self.assertEqual(candidate.fields, ())
                self.decide(candidate, state)
                self.session.set_policy(staging.StagingPolicy())
                report = self.report()
                self.assert_blocked(report)
                self.assertEqual(candidate.remediation_fingerprint, report.candidates[0].remediation_fingerprint)

    def test_policy_change_then_reversion_does_not_clear_rejection(self):
        old = self.proposal()
        self.decide(old.candidate)
        self.session.set_policy(replace(staging.StagingPolicy(), max_location_chars=128))
        self.assert_blocked(self.report())
        self.session.set_policy(staging.StagingPolicy())
        self.assert_blocked(self.report())

    def test_relaxing_whole_scope_budgets_cannot_reactivate_human_block(self):
        for state in (ReviewState.REJECTED, ReviewState.NEEDS_CLARIFICATION):
            for limits in ({"max_data_rows": 1}, {"max_scope_rows": 1}, {"max_scope_chars": 1}):
                self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), **limits))
                self.register((ROW, OTHER))
                old = self.report().candidates[0]
                self.decide(old, state)
                self.session.set_policy(staging.StagingPolicy())
                report = self.report()
                self.assert_blocked(report)
                self.assertEqual(old.remediation_fingerprint, report.candidates[0].remediation_fingerprint)
                self.assertIs(report.candidates[0].state, state)

    def test_rejection_survives_zip_repackaging_same_bytes_and_reversion(self):
        old = self.proposal()
        self.decide(old.candidate)
        original = self.session.snapshot(old.candidate.binding.ref)
        repacked = self.fixture(compression=zipfile.ZIP_DEFLATED)
        event = self.session.register_xlsx(SOURCE, repacked, SELECTION)
        new = self.session.snapshot(event.ref)
        self.assertNotEqual(new.native.xlsx_sha256, original.native.xlsx_sha256)
        self.assertEqual(new.native.manifest_sha256, original.native.manifest_sha256)
        self.assertNotEqual(new.manifest_sha256, original.manifest_sha256)
        self.assert_blocked(self.report())
        self.session.register_xlsx(SOURCE, repacked, SELECTION)
        self.assert_blocked(self.report())
        self.session.register_xlsx(SOURCE, self.paths[0], SELECTION)
        report = self.report()
        self.assert_blocked(report)
        self.assertEqual(report.candidates[0].remediation_fingerprint, old.candidate.remediation_fingerprint)

    def test_rejection_survives_unrelated_row_changes_and_blocks_all_rows(self):
        self.register((ROW, OTHER))
        before = self.report()
        old = before.candidates[0]
        self.decide(old)
        self.register((ROW, (OTHER[0], "Rechenzentrum Schwerin", OTHER[2])))
        report = self.report()
        self.assert_blocked(report)
        current = next(item for item in report.candidates if item.id == old.id)
        self.assertEqual(current.remediation_fingerprint, old.remediation_fingerprint)
        self.assertIs(current.state, ReviewState.REJECTED)
        self.assertTrue(all(not self.session.is_eligible(item) for item in before.proposals))

    def test_rejection_follows_substantive_assertion_when_row_moves(self):
        self.register((ROW, OTHER))
        old = self.report().candidates[0]
        decision = self.decide(old)
        self.register((OTHER, ROW))
        report = self.report()
        self.assert_blocked(report)
        moved = next(item for item in report.candidates if item.fields[0].value == ROW[0])
        self.assertEqual(moved.id, old.id)
        self.assertEqual((old.row, moved.row), (2, 3))
        self.assertEqual(moved.remediation_fingerprint, old.remediation_fingerprint)
        self.assertNotEqual(moved.fingerprint, old.fingerprint)
        self.assertIs(moved.state, ReviewState.REJECTED)
        self.assertEqual(self.session.decision_history(), (decision,))

    def test_duplicate_cleanup_cannot_clear_rejection_via_new_candidate_id(self):
        self.register((ROW, ROW))
        blocked = self.report()
        old = blocked.candidates[1]
        self.decide(old)
        self.register()
        report = self.report()
        self.assert_blocked(report)
        self.assertNotEqual(old.id, report.candidates[0].id)
        self.assertEqual(old.remediation_fingerprint, report.candidates[0].remediation_fingerprint)

    def test_rejection_survives_unrelated_source_addition_and_revision(self):
        old = self.proposal()
        self.decide(old.candidate)
        self.register((OTHER,), name=SECOND)
        self.assert_blocked(self.report((SOURCE, SECOND)))
        self.register(((OTHER[0], OTHER[1], "ERP-02"),), name=SECOND)
        self.assert_blocked(self.report((SOURCE, SECOND)))

    def test_block_identity_is_source_bound_not_an_unrelated_corpus_fingerprint(self):
        old = self.proposal()
        self.decide(old.candidate)
        self.register(name=SECOND)
        report = self.report((SOURCE, SECOND))
        self.assert_blocked(report)  # Duplicate facts still block the scope.
        first, second = sorted(report.candidates, key=lambda item: item.binding.ref.source_id)
        self.assertNotEqual(first.remediation_fingerprint, second.remediation_fingerprint)

    def test_corrected_row_new_revision_and_return_to_rejected_assertion(self):
        old = self.proposal()
        rejected = self.decide(old.candidate)
        saved = self.session.decision_history()
        self.register(((ROW[0], "Rechenzentrum Schwerin", ROW[2]),))
        new = self.report().proposals[0]
        self.assertEqual(new.candidate.id, old.candidate.id)
        self.assertGreater(new.candidate.revision, old.candidate.revision)
        self.assertNotEqual(new.candidate.remediation_fingerprint, old.candidate.remediation_fingerprint)
        self.assertTrue(self.session.is_eligible(new))
        decision = self.decide(new.candidate, ReviewState.PROPOSED, timestamp=TIME + timedelta(seconds=1))
        self.register()
        self.assert_blocked(self.report())
        self.assertFalse(self.session.is_eligible(new))
        self.assertEqual(saved, (rejected,))
        self.assertEqual(self.session.decision_history(), (rejected, decision))

    def test_missing_location_is_a_distinct_substantive_assertion(self):
        old = self.proposal()
        self.decide(old.candidate)
        self.register(((ROW[0], None, ROW[2]),))
        new = self.report().proposals[0]
        self.assertNotEqual(new.candidate.remediation_fingerprint, old.candidate.remediation_fingerprint)
        self.assertIsNone(new.candidate.fields[1].value)
        self.register()
        self.assert_blocked(self.report())

    def test_blocked_state_cannot_be_flipped_and_approved_or_strings_are_forbidden(self):
        old = self.proposal()
        self.decide(old.candidate)
        blocked = self.report().candidates[0]
        for state in (ReviewState.PROPOSED, ReviewState.APPROVED, "approved", "proposed", None):
            with self.subTest(state=state), self.assertRaises(ValueError):
                self.decide(blocked, state, timestamp=TIME + timedelta(seconds=1))
        self.assertEqual(len(self.session.decision_history()), 1)

    def test_old_fingerprints_cannot_authorize_queue_decisions_after_relocation(self):
        self.register((ROW, OTHER))
        old = self.report().candidates[0]
        self.register((OTHER, ROW))
        current = next(item for item in self.report().candidates if item.id == old.id)
        for changes in ({"candidate_fingerprint": old.fingerprint}, {"context_fingerprint": old.context_fingerprint}):
            with self.assertRaises(ValueError):
                self.decide(current, **changes)
        self.assertEqual(self.session.decision_history(), ())

    def test_queue_requires_explicit_human_metadata_and_nondecreasing_aware_time(self):
        old = self.proposal()
        for changes in ({"reviewer_id": ""}, {"reason": " "}, {"timestamp": TIME.replace(tzinfo=None)}):
            with self.assertRaises(ValueError):
                self.decide(old.candidate, **changes)
        decision = self.decide(old.candidate, ReviewState.NEEDS_CLARIFICATION)
        with self.assertRaises(ValueError):
            self.decide(self.report().candidates[0], timestamp=TIME - timedelta(seconds=1))
        self.assertEqual(self.session.decision_history(), (decision,))

    def test_policy_history_preserves_original_configs_and_invalidates_old_scope(self):
        old = self.proposal()
        old_scope = self.session.scope_history()[-1]
        history = self.session.policy_history()
        self.session.set_policy(replace(staging.StagingPolicy(), max_id_chars=63))
        self.assertFalse(self.session.is_eligible(old))
        self.assert_blocked(self.session.stage(old_scope))
        self.assertEqual(len(history), 1)
        self.assertEqual(len(self.session.policy_history()), 2)
        self.assertEqual(len(self.report().proposals), 1)

    def test_changed_reader_limits_require_capture_revalidation_not_cached_acceptance(self):
        self.register()
        self.session.set_policy(replace(staging.StagingPolicy(), reader_limits=replace(staging.reader.DEFAULT_LIMITS, max_xml_nodes=1000)))
        self.assert_blocked(self.report())
        self.session.register_xlsx(SOURCE, self.paths[0], SELECTION)
        self.assertEqual(len(self.report().proposals), 1)

    def test_100_row_hard_boundary_and_101_row_failure(self):
        values = tuple((f"SRV-{index:03}", ROW[1], f"ERP-{index:03}") for index in range(1, 102))
        self.register(values[:100])
        self.assertEqual(len(self.report().proposals), 100)
        self.register(values)
        self.assert_blocked(self.report())

    def test_tightened_row_and_scope_budgets_block_without_partial_output(self):
        for policy in (replace(staging.StagingPolicy(), max_data_rows=1), replace(staging.StagingPolicy(), max_scope_rows=1), replace(staging.StagingPolicy(), max_scope_chars=1)):
            self.session = staging.XlsxStaging(policy)
            self.register((ROW, OTHER))
            self.assert_blocked(self.report())

    def test_policy_caps_may_only_tighten_and_reject_boolean_or_invalid_limits(self):
        for changes in ({"max_data_rows": 101}, {"max_sources": 17}, {"max_id_chars": 65}, {"max_scope_rows": 0}, {"max_history_units": True}, {"reader_limits": replace(staging.reader.DEFAULT_LIMITS, max_file_bytes=3 * 1024 * 1024)}):
            with self.assertRaises(ValueError):
                staging.StagingPolicy(**changes)

    def test_retention_and_history_exhaustion_fail_closed_and_preserve_old_history(self):
        for changes in ({"max_retained_bytes": 1}, {"max_retained_text_chars": 1}, {"max_retained_manifest_bytes": 1}):
            self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), **changes))
            scope = self.session.create_scope((SOURCE,))
            self.assertIs(self.register().status, staging.RegistrationStatus.FAILED)
            self.assert_blocked(self.session.stage(scope))
            with self.assertRaises(staging.StagingError):
                self.session.create_scope((SOURCE,))
        self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), max_history_units=5))
        old = self.proposal()
        history = self.session.registration_history(SOURCE)
        with self.assertRaises(ValueError):
            self.session.begin_registration(SOURCE, SELECTION)
        self.assertFalse(self.session.is_eligible(old))
        self.assertEqual(self.session.registration_history(SOURCE), history)

    def test_source_count_and_manifest_size_caps_do_not_silently_drop_context(self):
        self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), max_sources=1))
        old = self.proposal()
        with self.assertRaises(ValueError):
            self.session.begin_registration(SECOND, SELECTION)
        self.assertFalse(self.session.is_eligible(old))
        self.session = staging.XlsxStaging(replace(staging.StagingPolicy(), max_manifest_bytes=1))
        self.assertIs(self.register().status, staging.RegistrationStatus.FAILED)
        self.assert_blocked(self.report())

    def test_oversized_original_rejected_before_reader_and_without_fabricated_digest(self):
        path = self.directory / "oversized.xlsx"
        path.write_bytes(b"X" * (2 * 1024 * 1024 + 1))
        with patch.object(staging.reader, "ingest_xlsx") as read:
            event = self.session.register_xlsx(SOURCE, path, SELECTION)
        read.assert_not_called()
        self.assertIsNone(event.binary_sha256)
        self.assertIs(event.status, staging.RegistrationStatus.FAILED)

    def test_pdf_and_docx_renamed_xlsx_and_artifacts_are_excluded(self):
        from tests.test_pdf_ingestion import synthetic_pdf
        from tests.test_docx_ingestion import synthetic_parts as docx_parts, write_synthetic_docx, paragraph
        from grundschutz_ai.pdf_ingestion import PdfQuote
        paths = [self.directory / "renamed-pdf.xlsx", self.directory / "renamed-docx.xlsx"]
        paths[0].write_bytes(synthetic_pdf([["FIKTIV"]]))
        write_synthetic_docx(paths[1], docx_parts(paragraph("FIKTIV")))
        for value in (*paths, b"PDF", PdfQuote(SOURCE, "0" * 64, 1, 0, 1, "X")):
            self.session = staging.XlsxStaging()
            self.assertIs(self.session.register_xlsx(SOURCE, value, SELECTION).status, staging.RegistrationStatus.FAILED)
            self.assert_blocked(self.report())

    def test_declared_derived_lineage_and_non_xlsx_claimed_results_fail_closed(self):
        for changes in ({"declared_lineage": ("pdf:source",)}, {"claimed_extraction": {"text": "FIKTIV"}}, {"claimed_extraction": "plain text"}):
            self.session = staging.XlsxStaging()
            event = self.session.register_xlsx(SOURCE, self.fixture(), SELECTION, **changes)
            self.assertIs(event.status, staging.RegistrationStatus.FAILED)
            self.assert_blocked(self.report())

    def test_docx_and_xlsx_sessions_do_not_claim_mixed_scope_eligibility(self):
        from grundschutz_ai.docx_staging import DocxStaging
        docx = DocxStaging()
        old = self.proposal()
        scope = docx.create_scope((SOURCE,))
        self.assert_blocked(self.session.stage(scope))
        self.assertFalse(docx.is_eligible(old))
        self.assertFalse(self.session.is_eligible({"candidate": old.candidate}))

    def test_immutable_nested_records_and_forged_locator_candidate_ineligible(self):
        old = self.proposal()
        records = ((old.candidate, "state", ReviewState.APPROVED), (old.candidate.fields[0], "value", "FAKE"), (old.candidate.fields[0].cell.cell, "text", "FAKE"), (self.session.snapshot(old.candidate.binding.ref), "manifest_sha256", "0" * 64))
        for record, name, value in records:
            with self.assertRaises(FrozenInstanceError):
                setattr(record, name, value)
        forged = staging.ValidatedProposal(replace(old.candidate, context_fingerprint="0" * 64))
        self.assertFalse(self.session.is_eligible(forged))

    def test_no_domain_evidence_inventory_store_model_network_or_review_side_effects(self):
        from grundschutz_ai import inventory, storage
        targets = ["grundschutz_ai.domain." + name for name in ("Evidence", "ITSystem", "ITApplication", "Location", "Relationship", "ReviewRecord")]
        targets += ["grundschutz_ai.inventory.Inventory.add", "grundschutz_ai.inventory.Inventory.revise", "grundschutz_ai.inventory.Inventory.record_review", "grundschutz_ai.storage.InventoryStore.commit", "sqlite3.connect", "grundschutz_ai.extraction.extract_inventory", "grundschutz_ai.extraction.OllamaClient.generate", "urllib.request.urlopen", "grundschutz_ai.validation.validate_response", "grundschutz_ai.support.assess_source", "builtins.print"]
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target)) for target in targets]
            self.register((ROW, OTHER))
            report = self.report()
            self.assertEqual(self.session.decision_history(), ())
            self.decide(report.candidates[0])
            self.session.set_policy(replace(staging.StagingPolicy(), max_id_chars=63))
            self.assert_blocked(self.report())
            self.register(((ROW[0], "Rechenzentrum Schwerin", ROW[2]), OTHER))
            self.assertEqual(len(self.report().proposals), 2)
            for mocked in mocks:
                mocked.assert_not_called()
        self.assertEqual(len(self.session.decision_history()), 1)


if __name__ == "__main__":
    unittest.main()
