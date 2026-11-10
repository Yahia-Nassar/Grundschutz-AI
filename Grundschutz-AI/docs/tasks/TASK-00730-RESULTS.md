# TASK-007.3.0: Structural evidence and SQLite v2 persistence design

Date: 2026-11-10 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`. Initial read-only Git: clean **`480fadf`** (`fix: enforce aggregate XLSX staging scope limit`), matching the requested baseline.

## Outcome and exact files

Completed the documentation-only design. **Schema v2, document persistence, migration, structural Evidence, materialization and document-backed approval remain unimplemented.** No Python/test code, existing user database, dependency, model, network, real company document, security setting or BSI normative baseline was changed. No automatic commit.

Design for review: [ADR-0009](../decisions/0009-structural-evidence-and-sqlite-v2.md).

| File | Change |
|---|---|
| `docs/decisions/0009-structural-evidence-and-sqlite-v2.md` | New proposed architecture: typed/versioned structural evidence and compatibility contracts; trust diagram; source/currentness state machine; queue/relational/event model; transactions/concurrency; migration; verified replay/budgets; threat/test matrices; future task gates and residual risks. |
| `docs/tasks/TASK-00730-RESULTS.md` | This report and reproduction commands. |
| `docs/decisions/0008-document-proposal-boundary.md` | Only correct the outdated introductory implementation-status paragraph and add the necessary ADR-0009 cross-reference. |

Inspected the requested domain/storage/staging/reader interfaces, decisions/results, goals/quality requirements and regression contracts. Important actual names/semantics are documented in ADR-0009 section 2: InventoryStore.commit accepts tuple[Write,...]; schema/event format remains 1; Evidence.source_text is an InitVar and source_sha256 identifies exact UTF-8 text; native DOCX has no manifest attribute; XLSX native/integration manifests differ; RegistrationRef uses revision; QueueDecision is distinct from ReviewRecord. The corrected aggregate XLSX eligibility limit is 100, independently of the 100-row workbook cap.

## Recommended design decisions requiring review

1. **Add a new versioned structural evidence type.** Prefer StructuralEvidenceV1 over a support sidecar pretending to satisfy legacy text Evidence. Recompute actual predicate support from retained raw workbook bytes, complete manifests, exact sheet/header/cell quotes, explicit BLANK/null semantics and the full current scope. No stored boolean or invented German sentence grants support. Keep inventory-affirmative/v1 and historic Evidence/hash semantics unchanged.
2. **Use an explicit additive document/v2 domain boundary later.** New evidence references, source bindings, revision digests and document review codecs are distinguishable from legacy/v1 records. Existing Inventory/storage constructors must continue rejecting new payload types. Future legacy DOCX Evidence reviews require both the unchanged legacy checks and explicit document-currentness review; historical approvals cannot be silently promoted. This is a contract recommendation, not a code change.
3. **Keep exact original BLOBs in the same future SQLite database.** This permits atomic BLOB/reference commits without promising consistency across unrelated filesystem files. Separate native text, binary, native-manifest and integration-manifest hashes; pin explicit resource configurations and trusted local implementation artifacts, not informal version strings alone.
4. **Commit pending registration before capture/parsing.** A failed/crashed replacement keeps an invalidating pending/failed head even when no new proposal exists. Terminal observations do not roll source heads backward. Current views are recomputed separately from immutable historical approvals/decisions.
5. **Capture durable commands in global order.** Current separate in-memory histories cannot recover complete chronology. Future replay must hydrate validated recorded UUIDs/revisions/policies/epochs, not call public register/stage APIs that allocate new identities. Persistent logical source ownership and substantive blocking keys prevent restart, relocation, unrelated changes or policy changes from silently clearing rejections.
6. **Use explicit offline copy/import migration.** Original v1 remains intact; verify a consistent backup, build a separate v2 output outside Git, preserve exact source/payload bytes, original legacy event order and review fingerprints, and compare independent replay before an operator switches databases. No startup upgrade or invented DOCX/XLSX originals. Legacy approvals stay legacy-only unless separately reviewed document binding actions occur later.

ADR-0009 gives concrete payload field sets, version/hash inputs, primary/composite foreign keys and uniqueness, global event ordering, separate transaction boundaries, failure classifications, compatibility dispatch and explicit future feature gates. It distinguishes valid blocked context from database corruption and states that a failed invalidating write cannot be claimed as a committed durable head. All proposed authority remains in trusted validators, never stored status projections or approval caches.

## Unresolved acceptance and rollout gates

| Gate | Status / required evidence |
|---|---|
| ADR-0009 contracts accepted by project owner/reviewer | **Pending review.** New type/domain boundary, codec/schema, migration and transaction choices are proposed. |
| Trusted compatible reader/stager/v1 implementation catalog | **Pending implementation/verification.** Unknown/unavailable old semantics must refuse replay, not silently substitute current rules. |
| Replay/storage budgets and target filesystem | **Pending measurements.** Proposed bounded synthetic budgets and deadlines need validation on Windows/available RAM and a reliable local SQLite volume. Repository Y:/ does not establish database filesystem guarantees. |
| A/B/C persistence, verified replay and migration | **Unimplemented.** No migration success or durable document/queue history claimed. |
| D structural/domain integration and E current approval/export guard | **Unimplemented and gated separately.** Persistence alone cannot activate either. |
| Mixed DOCX/XLSX scope, PDF evidence | **Excluded.** No combined coordinator or independent PDF visual verification exists. |
| Source/reviewer authentication, durable protected audit, source custody | **Unresolved for real data.** Current identity strings/hashes are not authentication or tamper-resistant infrastructure. |
| Applicable normative BSI baseline | **Still pending authoritative confirmation.** No certification or production claim. |

The architecture specifies how these gates must fail closed; it does not report them as implemented passes. In-memory staging remains session-only today. The first persistence design retains all historical blocks and the aggregate 100-row eligibility limit, with full over-limit diagnostics rather than truncation.

## Future decomposition and recommended next task

After design review and a new explicit implementation request:

- **A — versioned persistence codecs and source/event storage:** first; raw BLOBs, immutable events, source pending/capture/terminal transactions and strict feature/version refusal. No trusted queue/domain/approval projection yet.
- **B — verified DOCX/XLSX manifests and queue replay:** depends on A; source identity hydration, full scopes/locators, candidates, historic decisions and remediation replay.
- **C — explicit offline v1-to-v2 migration tool:** depends on A+B plus pinned v1 compatibility validation; source/snapshot/target comparisons and interruption tests.
- **D — structural evidence and unapproved domain integration:** depends on B and accepted structural/domain contracts; C additionally where imported legacy history is involved. No implicit approval.
- **E — current-context domain approval/export guard:** depends on B+D (and C for migrated data); fresh dependency-bound explicit reviews and stale-publication refusal.

**Recommended next implementation task: A, only after ADR-0009 review.** Nothing in TASK-007.3 implementation was begun by this documentation task.

## Tests actually executed

Full existing Python 3.12 offline suite, unchanged:

```text
Ran 417 tests in 16.181s
OK
```

**417 passed, 0 failures, 0 errors; 0 new tests.** All existing domain, SQLite v1, extraction mocks, DOCX/XLSX/PDF diagnostic readers, DOCX queue-rejection hardening and XLSX aggregate-limit regressions remain included. Optional live Ollama classes were excluded; no model/network calls. The existing SQLite tests used only their temporary synthetic fixtures outside Git and removed them normally; no user database was opened, migrated or modified. This suite checks unchanged current behavior, not implementation of the proposed v2 design. ADR-0009's new persistence/replay/migration test matrix is prospective, not executed test coverage.

## Exact PowerShell reproduction

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging tests.test_xlsx_staging
Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai Grundschutz-AI/tests
git diff -- Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
```

## Final Git/document checks

Final read-only HEAD remains **`480fadf`** (`fix: enforce aggregate XLSX staging scope limit`). Exact status:

```text
 M Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
?? Grundschutz-AI/docs/decisions/0009-structural-evidence-and-sqlite-v2.md
?? Grundschutz-AI/docs/tasks/TASK-00730-RESULTS.md
```

Only the three intended documentation files changed: one modified tracked ADR and two new/untracked documents. Nothing staged or committed. `git diff --exit-code -- Grundschutz-AI/grundschutz_ai Grundschutz-AI/tests` passed with no differences. The ADR-0008 diff contains only the introductory implementation-status correction and cross-reference. `git diff --check` passed with only Git's configured LF-to-CRLF notice; direct strict UTF-8, trailing-whitespace, final-newline, balanced Markdown-fence and local-link checks passed for all three files, including untracked documents. Read-only Git ran in the repository owner's context without configuration or security-setting changes. No permanent database/fixture or additional files were created by this task.
