# TASK-007.2: Nonpersistent synthetic XLSX proposal staging

Date: 2026-11-10 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`. Initial read-only Git: clean HEAD **`c301020`** (`fix: preserve human queue rejections across irrelevant changes`).

## Outcome and changed files

Implemented deterministic typed XLSX-only proposal staging under the explicit experimental **`synthetic-it-table/v1`** convention. It is neither a normative IT-Grundschutz rule nor authenticated human policy approval. No materialization, Evidence, approved inventory, persistence, inference or combined DOCX/XLSX scope was implemented. TASK-007.3 remains unstarted.

| File | Change |
|---|---|
| `grundschutz_ai/xlsx_staging.py` | New bounded in-memory XLSX registration, trusted sheet selection, structural row validation, immutable provenance/candidates, full-scope conflict/currentness checks and human triage. |
| `tests/test_xlsx_staging.py` | 64 new offline synthetic regressions; all workbook fixtures created in temporary directories outside Git. |
| `docs/tasks/TASK-0072-RESULTS.md` | This report and exact reproduction commands. |
| `docs/decisions/0008-document-proposal-boundary.md` | Clarify implemented experimental table policy, actual APIs, separate hashes/scopes, remediation and remaining boundaries. |

Existing DOCX staging (including TASK-007.1a), all readers/OOXML safety, domain, inventory, storage, support and extraction/validation modules remain unchanged. No new dependencies, downloads, network, real company documents, security/configuration changes, automatic commits or normative BSI baseline changes.

## Actual public APIs

```python
from grundschutz_ai.xlsx_staging import XlsxStaging, SheetSelection, StagingPolicy
from grundschutz_ai.domain import ReviewState

selection = SheetSelection("IT-Systeme", 1, 1, "rId1", "xl/worksheets/sheet1.xml")
session = XlsxStaging(policy=StagingPolicy())
event = session.register_xlsx(trusted_source_id, trusted_path, selection)
# Or expose pending invalidation explicitly:
ref = session.begin_registration(trusted_source_id, selection)
event = session.finish_registration(ref, trusted_path)

head = session.current_head(trusted_source_id)
snapshot = session.snapshot(event.ref)  # structurally valid registrations only
scope = session.create_scope((trusted_source_id,))
assessment = session.assess(scope)
report = session.stage(scope)
eligible_now = session.is_eligible(report.proposals[0])  # only if present

decision = session.triage(
    candidate.id,
    state=ReviewState.REJECTED,
    reviewer_id=explicit_human_id,
    timestamp=aware_timestamp,
    reason=explicit_reason,
    candidate_fingerprint=candidate.fingerprint,
    context_fingerprint=candidate.context_fingerprint,
)
```

`register_xlsx`/`finish_registration` accept optional `claimed_extraction` for complete comparison against fresh parsing, and `declared_lineage`, which must be the empty tuple. They do not accept reader artifacts as source authority, raw text or dictionaries. The explicit selection has no inferred/default sheet. Its name, ordinal, sheet ID, relationship ID and part must match the sole actual worksheet.

`registration_history(source_id)`, `candidate_history(source_id)`, `scope_history()`, `policy_history()` and `decision_history()` expose immutable historical tuples. `set_policy(typed_policy)` activates a changed bounded policy and invalidates old scope bindings. Identical scope membership/staging calls are no-ops. Main API failures use static `StagingError` codes, never source-text logs.

New immutable records include SheetSelection, XLSX StagingPolicy/PolicyRevision, RegistrationEvent, WorkbookSnapshot, CellReference, MissingObservation, FieldValue, RowSupport, IntendedClaim, ContextAssessment, StagedCandidate, ValidatedProposal and StageReport. Source-neutral immutable RegistrationRef/Status, ReviewScope, DocumentBinding and QueueDecision plus pure canonical hash/serialization helpers are reused from DOCX staging. No DOCX coordinator instance, inheritance or broad shared-framework refactor was added. This explicit helper-module coupling is a prototype maintenance limitation; it does not grant mixed-format eligibility.

## Table and whole-context contract

- Exactly one reader-supported visible worksheet, explicitly selected as `IT-Systeme` with all actual identity fields. Extra sheets, even empty, block.
- Exact TEXT headers: A1 `System-ID`, B1 `Standort`, C1 `Anwendung`. No trimming, case folding, extra columns/cells, inferred headings, filters or ignored text.
- Explicit contiguous row indices 1 through N; 1–100 data rows. Empty rows, gaps, missing cells, unexpected prose or rows beyond the hard cap block the full context.
- A/C require exact complete uppercase identifiers matching `[A-Z][A-Z0-9]*-[A-Z0-9]+`, up to 64 characters by default. Longer complete IDs such as SRV-0012/ERP-010 remain distinct from shorter names.
- B accepts the bounded `Rechenzentrum <Place>[, Raum <ID>]` location grammar, including supported German/multiword/hyphenated place tokens, up to 256 characters by default. Unsupported/ambiguous/negative placeholders fail; bare Berlin is never expanded into a fabricated building.
- Only physically present BLANK B means actual null. Its FieldValue has a typed `MissingObservation(reason="explicit_blank")`, a raw blank-cell reference, zero `positive_quotes` and no located_at claim. Absent B, empty TEXT, string null/None/unbekannt and unsupported values remain distinct and invalid.

The pure structural `_row_values()` validator is separate from the DOCX sentence contract. No `validate_response()`, `assess_source()`, generated German sentence or cloud/local model is used. Exact native text/coordinates remain unchanged. Literal strings that resemble commands are untrusted values, never executed.

CellReference retains exact native CellRecord identity/text/kind/hash, explicit SheetSelection, document binding and cell-local half-open character offsets. Each FieldValue retains its exact header. Each IntendedClaim carries `RowSupport(headers, cells, policy_version)` with **all three original headers and all three original row cells**, preserving complete row context. Hosts and located_at roles follow only this versioned experimental mapping. This is not relationship-supporting legacy Evidence, SourceLocator or an approved fact. No binary/cell hash substitutes for `Evidence.source_sha256`.

One session owns one explicit XLSX scope covering all known logical sources. Missing/unknown/pending/failed/unsupported sources block. Duplicate complete system asset names, including identical rows across workbooks, and incompatible locations/applications block the entire scope. Distinct assets may share application/location names without merging records. Any current human block also prevents all proposals; a valid unrelated row is never issued as partial eligible output. DOCX/PDF artifacts and foreign session scopes/proposals are ineligible. No combined-format coordinator is claimed.

## Source, hashes, currentness and human blocking

Every registration has a unique identity and increasing logical-source revision; beginning a replacement immediately invalidates earlier proposals. Captured/pending/terminal events, raw bytes and aware times remain append-only. Late older completion cannot replace a newer head. `valid` denotes reader structural success, not table-policy success, factual truth or approval.

Original bytes are captured once with regular-file/size bounds and retained under separate budgets. Parsing uses a closed private `.xlsx` copy outside Git, then compares reader bytes/source ID/limits and any caller-claimed native artifact in full. Temporary copies are removed on success/failure. TEMP inside Git is refused before copy creation. A changed original path after capture cannot change the registered revision. Wrong-format inputs and any declared derived lineage fail without fallback. Failed captured bytes can remain untrusted bounded diagnostics; failed capture has no invented full digest.

| Identity/hash | Exact contract |
|---|---|
| `RegistrationEvent.binary_sha256` / native `xlsx_sha256` | Exact retained original XLSX binary bytes. |
| Native `text_sha256` | Exact UTF-8 native flattened text; reader order/separators unchanged. |
| Cell `text_sha256` | Exact individual original cell text, including empty string for BLANK/TEXT-empty; kind is separately preserved. |
| Native `manifest_sha256` | Complete ordered workbook structure, identities, rows, cells/kinds/text/hashes, reader method and limits; intentionally excludes binary packaging. |
| `WorkbookSnapshot.manifest_sha256` | New `xlsx-integration/v1` canonical manifest: binary hash, native text and manifest hashes, full native manifest JSON, source ID, explicit selection, reader method/code/Python-version digest and limits. Excludes operational registration UUID/revision/time. |
| DocumentBinding / scope / context / candidate fingerprints | Bind current registration identity/revision, complete document/scope, active policy/revision, current row/cell/header references, values/claims and issues. Old candidate/context tokens cannot authorize new decisions. |
| `xlsx-assertion-remediation/v1` | Logical source plus exact A/B/C presence/kind/value semantics, complete system/application names, location or explicit BLANK null and intended predicate roles. Excludes coordinates, unrelated rows/sources, packaging, operational IDs, scope, active caps/policy and clocks. Only matches human blocks; never grants eligibility. |

The remediation identity is derived from raw literal row semantics even if resource limits prevent fields from being emitted. Thus changing/relaxing limits cannot recreate the TASK-007.1a bypass. Human REJECTED/NEEDS_CLARIFICATION decisions survive unchanged-content re-registration, ZIP repackaging, row relocation, unrelated edits/additions and policy changes/reversion. Corrected substantive assertions require independent full validation; returning to a prior rejected assertion restores its block. Policy-only override is not implemented.

Unique source/asset pairs keep stable candidate IDs through row relocation. Duplicate/malformed row slots use separate diagnostic IDs; blocking matches the source-bound substantive identity rather than old candidate UUID equality, preventing duplicate cleanup from evading history. Explicit triage still requires exact **current** candidate/context fingerprints, reviewer ID, aware nondecreasing timestamp and reason. Queue states are the existing proposed/rejected/needs_clarification enums; APPROVED and arbitrary state strings are forbidden. Machine findings create no human decision or domain ReviewRecord.

Immutable proposed reports are historical snapshots. Call `session.is_eligible(proposal)` on the live owner before any future use; even a state-altered snapshot cannot bypass scope/queue blocks or owned-candidate equality. This is a point-in-time read, not a transactional materialization/export capability. No future write/export pathway exists in this task.

## Executed synthetic demonstration

The public API registered a temporary fictional workbook under `synthetic:task-0072-demo`, with exact headers and two rows:

| Row | A | B | C | Result |
|---|---|---|---|---|
| 2 | SRV-001 | Rechenzentrum Rostock | ERP-01 | proposed; live eligible true |
| 3 | SRV-002 | Rechenzentrum Berlin | CRM-02 | proposed; live eligible true |

Registration revision 1: **valid**. Selected identity: name `IT-Systeme`, ordinal 1, sheet_id 1, relationship_id `rId1`, part `xl/worksheets/sheet1.xml`.

| Provenance | Observed SHA-256 |
|---|---|
| Original XLSX binary | `bae5537e00a0b0fd91c9656e92fef3cdc766be89f4348cac3d0c0d9a21ea6026` |
| Native UTF-8 text | `e15588434c5a98464daf8ec82789a4387a6792d378889c192d324837240b9a17` |
| Native manifest | `0b9faac6b91e0c3efa129f04bfcfcdbbd43676b9edc3cc80a411b0917f41ec95` |
| Integration manifest | `210fc7b1a512053289f6dd1961c20a4d8cccb4c3e0973f3c5f886142eb7aa42c` |

Example exact references: A2 `[0,7)` = `SRV-001`, B2 `[0,21)` = `Rechenzentrum Rostock`, C2 `[0,6)` = `ERP-01`, linked respectively to exact original A1/B1/C1 headers. B2 text SHA-256: `7971e5b627ad354ef6fb24402fb45c8d9063f8f5ff001cac41f875831f223623`. Claims retain all three headers/cells and current binding. No synthetic page numbers or joined prose were introduced. These hashes identify exact bytes/configuration, not authentic origin or truth. Integration hashes depend on reader code bytes/Python version/line endings; operational fingerprints additionally vary with new UUIDs/revisions.

Observed complete-scope blocks:

| Input/action | Eligible proposals | Issue codes / observation |
|---|---:|---|
| Identical duplicate system rows | 0 | duplicate_asset |
| Same system with Rostock/Berlin assertions | 0 | duplicate_asset, conflicting_assertions |
| Physically missing B cell | 0 | missing_cell |
| Human rejects row 2, then max_id_chars 64 to 63 | 0 | queue_blocked; both previously eligible rows now fail live eligibility |

The demonstration directory was removed. Automated regressions additionally exercise cross-workbook conflicts, BLANK null, corrected/reverted rows, failed source registrations, raw/artifact spoofing, PDF/DOCX renamed XLSX and all-or-nothing output.

## Tests and resource bounds

**Final full offline result: 412 tests in 13.894 seconds; OK; 0 failures, 0 errors.** All **348 existing tests** pass unchanged, including all **69 DOCX staging tests**. Added **64 XLSX staging tests**. Optional live Ollama classes were deliberately excluded; no inference/network was requested.

The first isolated run had 63 tests, 1 error and 0 failures: its retention-exhaustion test attempted to create a new scope after terminal session exhaustion. The test was corrected to verify a pre-existing scope's blocked assessment and refusal of further scope creation. Production fail-closed behavior was not weakened. The subsequent 63-test run passed in 1.438 seconds; an intermediate complete 411-test run passed in 13.975 seconds. A final whole-scope-budget relaxation regression and explicit enum predicate roles are included in the final 412-test result above. No unresolved test failure remains.

Coverage includes exact one/multi-row cells/headers/identity/hashes, Unicode, complete-workbook coverage, absent/BLANK/empty TEXT distinctions, placeholders and unsupported locations/IDs, extra sheets/cells, gaps/empty rows, malformed/hidden/formula structures, duplicates/conflicts within/across workbooks, capture/temp lifecycle, currentness/revision/reversion, fake native results, human block propagation/replay/relocation/duplicate cleanup, stale/approved queue actions, metadata/history, resource boundaries and immutable records. The side-effect test patches all six forbidden domain constructors, Inventory writes/reviews, store commit/SQLite connect, extraction/Ollama/network calls, legacy sentence validators and print; none is called while registering, staging, triaging, changing policy or correcting rows. Automated staging creates no human decision by itself.

Default caps: 16 logical sources; 100 data rows/workbook; 1,600 current scope rows; 1,000,000 scope characters; IDs 64 and locations 256 characters; 8 MiB individual integration manifests; 32 MiB retained unique binary bytes; 1,000,000 retained native-text characters; 32 MiB retained manifests; 2,048 history units. Registration reserves three history units; source/queue histories are never silently evicted. Reader defaults can only tighten. Exhaustion invalidates earlier proposals and refuses new work; an existing scope can still report session_exhausted. These application budgets do not constitute hard RSS/OS isolation or parse deadlines.

## Limitations and review recommendation

Only the narrow synthetic literal XLSX reader/profile and this explicit table convention are supported; ordinary styled/formula/merged/hidden Excel workbooks remain unsupported. Location/ID checks are bounded engineering rules, not a general language parser or verified BSI requirements. Structurally supported text is untrusted and does not prove factual or visual truth.

No authenticated source/reviewer registration, filesystem monitor, unknown-document discovery, global identity catalog, mixed DOCX/XLSX eligibility or durable/tamper-resistant audit exists. Session disposal loses history. A dishonest trusted caller can relabel source IDs or conceal copied/PDF ancestry; hashes and frozen Python records cannot detect that or resist malicious code inside the trusted process. Declared derived lineage is always refused. Source safety/authentication, independent visual review and eventual persistence/materialization contracts need separate authorization/review.

Invalid/raw candidates are untrusted diagnostics and must **never** be exported as approved facts. No Evidence, ITSystem, ITApplication, Location, Relationship or ReviewRecord is constructed. No Inventory/store mutation or approved export is provided. No SQLite schema, legacy evidence hash meaning or automatic approval authority changed. Recommended next step is human review of this experimental adapter and test evidence, not automatic continuation to TASK-007.3.

## Exact PowerShell reproduction

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_xlsx_staging -v
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging tests.test_xlsx_staging
```

Public-API demonstration (temporary synthetic fixture only):

```powershell
@'
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.xlsx_staging import XlsxStaging, SheetSelection
from tests.test_xlsx_staging import fictional_parts, ROW, OTHER
from tests.test_xlsx_ingestion import write_synthetic_xlsx

selection = SheetSelection('IT-Systeme', 1, 1, 'rId1', 'xl/worksheets/sheet1.xml')
source = 'synthetic:task-0072-demo'
with TemporaryDirectory(prefix='grundschutz-ai-xlsx-staging-demo-') as folder:
    path = Path(folder) / 'fictitious.xlsx'
    write_synthetic_xlsx(path, fictional_parts((ROW, OTHER)))
    session = XlsxStaging()
    event = session.register_xlsx(source, path, selection)
    report = session.stage(session.create_scope((source,)))
    snapshot = session.snapshot(event.ref)
    print(event.status, event.ref.revision)
    print('Hashes:', event.binary_sha256, snapshot.native.text_sha256,
          snapshot.native.manifest_sha256, snapshot.manifest_sha256)
    for proposal in report.proposals:
        print('Row:', proposal.candidate.row, 'eligible:', session.is_eligible(proposal))
        for value in proposal.candidate.fields:
            print(value.name, repr(value.value), value.cell.cell.coordinate,
                  value.cell.selection, (value.cell.char_start, value.cell.char_end),
                  value.cell.cell.text_sha256, 'header:', value.header.cell.coordinate)
print('Removed:', not path.exists())
'@ | py -3.12 -
```

Executable blocked-scope demonstrations:

```powershell
py -3.12 -m unittest tests.test_xlsx_staging.XlsxStagingTests.test_duplicate_identical_rows_and_contradictory_locations_or_apps_block_all tests.test_xlsx_staging.XlsxStagingTests.test_cross_workbook_duplicate_and_conflicting_assets_block_full_scope tests.test_xlsx_staging.XlsxStagingTests.test_absent_location_is_not_explicit_blank tests.test_xlsx_staging.XlsxStagingTests.test_rejection_survives_unrelated_row_changes_and_blocks_all_rows tests.test_xlsx_staging.XlsxStagingTests.test_rejection_follows_substantive_assertion_when_row_moves -v
```

## Git verification

Final read-only HEAD remains **`c301020`** (`fix: preserve human queue rejections across irrelevant changes`). Exact status:

```text
 M Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
?? Grundschutz-AI/docs/tasks/TASK-0072-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/xlsx_staging.py
?? Grundschutz-AI/tests/test_xlsx_staging.py
```

Nothing staged or committed. `git diff --check` passed with only Git's configured LF-to-CRLF checkout notice. Direct strict UTF-8/trailing-whitespace/final-newline checks and balanced Markdown fences passed for all four files, including the untracked files that Git's diff check does not cover. A read-only `git diff --exit-code` confirmed no changes to DOCX staging/tests, either OOXML reader/safety module, domain, inventory, storage, extraction, support or validation. No matching XLSX-staging or DOCX-staging-fixture temporary directories remained. Read-only Git ran in the repository owner's context without Git configuration or security-setting changes.

```powershell
Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --stat
```
