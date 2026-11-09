# TASK-007.0: Trusted document-to-proposal integration architecture

Date: 2026-11-09 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`. Read-only Git confirmed clean initial HEAD **`3c476ac`** (`feat: add bounded synthetic PDF ingestion`).

## Outcome and deliverables

Completed documentation/design only. Created:

- `docs/decisions/0008-document-proposal-boundary.md`
- `docs/tasks/TASK-0070-RESULTS.md`

No application/test code, existing documentation, package, model, SQLite schema/data, security setting or BSI baseline was changed. No company documents, network access, automatic commits, actual integration, PDF evidence promotion or TASK-007.1 implementation. All test fixtures exercised by the existing suite are synthetic.

ADR-0008 contains the A–G component/trust-boundary diagram and matrix; existing API inventory; proposed typed staging/queue/source contracts; whole-document/scope gates; DOCX/XLSX mapping examples; PDF exclusion; versioned migration/reload plan; proposed 007.1 tests; implementation order and open questions. Proposed interfaces/tables are labeled unimplemented and are not existing APIs.

## Main findings from current APIs

| Finding | Design consequence |
|---|---|
| DOCX has exact bytes/text/segments but no native manifest property | Propose a separate canonical integration manifest preserving all segments/locators and original binary identity; do not invent a `DocxExtraction.manifest_sha256` API. |
| XLSX native manifest omits original binary digest | Bind both native manifest and original workbook hash in the integration source contract. Preserve sheet/row/cell identity and blank/empty/missing distinctions. |
| Extraction Candidate is only shallowly frozen, uses text hashes and string states | Freeze typed snapshots and rerun validation; its mutable dictionaries/status cannot authorize a proposal or reviewer. No automatic call to `extract_inventory`, which would invoke Ollama. |
| Extraction JSON validation and domain affirmative support have different grammars | DOCX requires their intersection and the full original source. Additional context never gets removed to satisfy one parser. |
| Current Evidence hashes exact UTF-8 text and assesses a full affirmative sentence | Binary document hashes/structural locators cannot be substituted. Cell adjacency or generated German prose cannot establish original XLSX evidence. |
| Current Inventory only knows registered text Evidence, not document heads/scopes | A future context-aware approved-view gate is necessary; a failed newer source registration must invalidate old eligibility even when no valid Evidence can be created. |
| Schema v1 accepts only exact legacy domain events and UTF-8 sources | Document registrations/manifests, candidate history, structural support and migration need an explicit v2 design/codec; no extra tables or hidden JSON/base64 payloads in v1. |
| PDF is diagnostic-only and unrendered | Exclude PDF result/quote/bytes/manifest and declared PDF-derived intermediates before evidence/queue/domain approval; no override or plain-text fallback. |

Current ReviewState and ReviewRecord meanings remain unchanged. A staging QueueDecision is a proposed new type because a ReviewRecord targets an existing domain object. Queue states may be proposed, rejected or needs_clarification, never approved. Later positive inventory decisions still require explicit human ReviewRecords for actual object revisions and approved dependencies.

A read-only synthetic API probe (no adapter, model, Evidence or storage creation) confirmed the 92-character DOCX example passes both existing validators and gives field spans `[11,18)`, `[36,57)`, `[85,91)`. The appended administrator update failed extraction coverage and returned no affirmative support. A bare-city `im Berlin` sentence passed extraction validation but returned no domain affirmative support. This supports the documented intersection requirement; it is not a new integration test or implemented boundary.

## Recommended workflow

Register a trusted logical source/version and capture exact untrusted bytes; revalidate supported structure against them; inspect complete document and declared scope; stage deterministic or explicitly requested local-AI candidates; validate exact values/quotes/nulls/roles/predicates and all conflicts; offer only eligible proposed items for human review. No extracted segment is an approved fact. Machine findings are validation observations, not fabricated human decisions.

Every binding/candidate includes current registration, original binary digest, complete integration manifest, reader/limits, mapping/support policy and scope/context fingerprints. Registration/review times are timezone-aware events outside new deterministic content manifests. Preserve established legacy domain fingerprint semantics, including existing Provenance fields. New registrations/reverts, unchanged quotes with changed context, source-scope changes and policy changes require fresh validation and review; old decisions never reactivate merely because bytes return to an earlier digest.

DOCX proposal: exactly one supported top-level paragraph, optional surrounding whitespace, no additional paragraphs/tables/headers/instructions. Use the unchanged full text with existing validation plus full-assertion support. The fictitious SRV-001/Rostock/ERP-01 example preserves the full location and exact paragraph offsets. A missing location is real null, without invented location evidence. An appended contradictory administrator update blocks the entire document.

XLSX proposal: an explicitly selected sole worksheet `IT-Systeme`, exact A1/B1/C1 headers `System-ID`/`Standort`/`Anwendung`, bounded contiguous data rows and no unaccounted cells/sheets. Conditional on a separately reviewed synthetic mapping policy, each complete row stages intended hosts/located_at claims with cell/header and whole-workbook context. BLANK location maps to explicit null; missing cell/empty TEXT/placeholders remain clarification-required in this initial policy. Bare `Berlin` remains literal reader output and is not invented into `Rechenzentrum Berlin`. Duplicate/conflicting rows block scope; no partial eligible-row import.

XLSX staging is **not** yet representable as relationship-supporting current Evidence. A reviewed structural support/type/binding and compatible fingerprint/replay contract is required before materialization. Even DOCX text compatible with Evidence cannot bypass document-currentness/source retention gates into schema v1. These are explicit feasibility gates, not implemented adapters or silent changes to existing semantics.

## Persistence and human review plan

Propose an explicit migration to a separate schema v2 database, retaining the original v1 store and verified historic payloads/sources/decisions. New immutable source registrations/blobs/manifests, scope/context, candidate revisions, queue decisions and domain bindings/events need atomic writes and global action order. Preserve v1 historical support-policy replay rather than reinterpreting old fingerprints under a new policy; never label old text approvals as proven document evidence.

Reload must verify original bytes, re-extract compatible complete manifests, recompute context/candidate/predicate support and replay history in order, then derive present approved eligibility using current source heads. Missing/corrupt/unsupported data blocks use with no cached approved fallback. The existing `Inventory.approved_records()` remains its actual domain-only API; it does not currently provide this document-currentness projection. No migration SQL, new tables/store or approval/export adapter was implemented.

The small proposed sequence is 007.1 nonpersistent DOCX staging and PDF exclusion, then 007.2 nonpersistent XLSX staging. Before 007.3 coding, review structural evidence/currentness and event/codec/fingerprint versions; split a small additional design task if needed. Then implement separately authorized verified persistence/migration. Domain materialization and current-context-aware human approval/export remain a later scoped integration step. PDF promotion is absent from the plan while its visual gate remains unresolved.

## Remaining risks and open decisions

Whole-scope coverage prevents omitted known source content; it does not discover unknown documents or interpret arbitrary German contradictions. The operator must declare the complete relevant synthetic scope and register changes. Accepted DOCX/XLSX structures do not prove visual correspondence, author identity or factual truth. PDF visual verification remains unavailable and cannot be waived through this queue.

Source/reviewer authentication, protected source retention/backup, honest lineage, local attacker/file-race protection, tamper-resistant history and larger-history replay budgets remain unresolved. Hashes/frozen dataclasses/SQLite triggers do not provide these properties. The exact row mapping, null policy, identity/duplicate handling, scope supersession and v2 structural evidence contract require review. The proposed staged budgets and later tests are designs, not implemented enforcement or measured integration performance.

No production readiness, completed integration or IT-Grundschutz certification compliance is claimed. Recommended next action is human review of ADR-0008 and its design gates; TASK-007.1 has not begun.

## Existing offline suite

Executed from the application directory:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion
```

**Observed: 279 tests in 12.405 seconds; OK; zero failures and errors.** These are the unchanged existing offline tests, including real bounded PDF worker tests. No new integration tests or fixtures were added, and the future 007.1 matrix in ADR-0008 was not executed as implemented integration. Optional live Ollama classes were not selected. No source/model network call was made.

## Reproduction commands

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion -v

Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --name-only
git diff --exit-code -- Grundschutz-AI/grundschutz_ai Grundschutz-AI/tests
```

Git checks are read-only in the normal user context; no safe.directory, ownership or security/configuration changes are needed or performed. Direct UTF-8/trailing-whitespace/final-newline checks also cover the new untracked files, which `git diff --check` alone does not inspect.

## Final Git verification

HEAD remains **`3c476ac`**. Final read-only status:

```text
?? Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
?? Grundschutz-AI/docs/tasks/TASK-0070-RESULTS.md
```

`git diff --name-only` and the explicit application/test-code diff were empty. `git diff --check` passed. Both new documentation files passed direct strict UTF-8, trailing-whitespace, final-newline and balanced-code-fence checks. No existing tracked file was modified; exactly the two requested documentation files are new/untracked. Git ran read-only as the normal user without ownership/configuration/security changes. Nothing staged or committed.
