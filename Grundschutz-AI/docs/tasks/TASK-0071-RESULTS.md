# TASK-007.1: Nonpersistent DOCX proposal staging

Original TASK-007.1 date: 2026-11-09 (Europe/Bucharest). Repository: `Y:/Grundschutz-AI`; application: `Y:/Grundschutz-AI/Grundschutz-AI`. Read-only Git confirmed original initial clean HEAD **`60cb360`** (`docs: define document-to-proposal trust boundaries`). TASK-007.1a security remediation on **2026-11-10** started from clean **`a021f0c`** (`feat: add nonpersistent DOCX proposal staging`), which contains the prior task. The attachment described the earlier uncommitted baseline; this records the actual checkpoint without changing Git history.

**Current verification:** TASK-007.1a passes **348 offline tests (339 previous + 9 new)**, including both human-rejection reactivation regressions and resource-limit relaxation. The original 339-test result and demonstration fingerprints below are historical TASK-007.1 observations; see the security-remediation section for the current rules and results.

## Outcome and exact files

Implemented synthetic DOCX registration, complete-scope validation, deterministic typed proposal staging and non-approving human queue triage. No inventory materialization, evidence creation, persistence, inference, PDF evidence use or XLSX staging was implemented.

| File | Change |
|---|---|
| `grundschutz_ai/docx_staging.py` | New bounded in-memory coordinator, immutable records, captured-byte revalidation, integration manifests, currentness/conflict/fingerprint checks and queue history. |
| `tests/test_docx_staging.py` | 60 new synthetic offline regressions; all fixture documents are temporary and outside the repository. |
| `docs/tasks/TASK-0071-RESULTS.md` | This report and reproduction commands. |
| `docs/decisions/0008-document-proposal-boundary.md` | Clarify actual implemented names, conservative scope/session rules, retention budgets and staging-only boundaries; preserve future architecture gates. |

Legacy readers, extraction/validation/support, domain, Evidence, Inventory and SQLite code/semantics remain unchanged. No new packages, installations/downloads, network, model/GPU/security-setting changes, company documents, automatic commits or BSI baseline changes. TASK-007.2 was not started. The test-only DOCX fixture writer is existing standard-library scaffolding, not an application document-generation feature.

## Public staging APIs

```python
session = DocxStaging(policy=StagingPolicy())
event = session.register_docx(source_id, trusted_path)
# Or explicitly observe invalidation before capture:
ref = session.begin_registration(source_id)
event = session.finish_registration(ref, trusted_path)

head = session.current_head(source_id)
snapshot = session.snapshot(event.ref)  # only for structurally valid registrations
scope = session.create_scope((source_id,))
context = session.assess(scope)
report = session.stage(scope)
eligible_now = session.is_eligible(report.proposals[0])  # only when present

decision = session.triage(
    candidate.id,
    state=ReviewState.REJECTED,  # or PROPOSED / NEEDS_CLARIFICATION; never APPROVED
    reviewer_id=explicit_reviewer,
    timestamp=aware_timestamp,
    reason=explicit_reason,
    candidate_fingerprint=candidate.fingerprint,
    context_fingerprint=candidate.context_fingerprint,
)
```

Imports are `DocxStaging, StagingPolicy` from `grundschutz_ai.docx_staging`, and the unchanged `ReviewState` from `grundschutz_ai.domain`. `registration_history(source_id)`, `candidate_history(source_id)`, `scope_history()`, `policy_history()` and `decision_history()` return immutable historical tuples. `set_policy(typed_policy)` activates a changed bounded policy and invalidates old scope bindings. A same-policy/no-op scope/stage call does not reset revisions or review blocks.

`register_docx`/`finish_registration` also accept optional `claimed_extraction` for full comparison with a fresh reader result, and `declared_lineage`, which must be the empty tuple in this direct-DOCX-only task. No generic text/dictionary/reader-artifact-only intake, visual override, to_evidence, approved export or domain-writing API exists.

Records include RegistrationRef/Event/Status, PolicyRevision, DocumentSnapshot/Binding, ReviewScope/ContextAssessment, DocxQuote, MissingObservation, FieldValue, IntendedClaim, StagedCandidate, ValidatedProposal, StageReport and QueueDecision. These are new staging-owned types; existing reader/domain fields were not redefined. Candidate UUIDs and asset names are not internal SYS/APP/LOC IDs.

## Registration, capture and manifests

Every attempt gets a new unique registration identity and increasing logical-source revision. Beginning it immediately invalidates earlier proposals. Frozen pending/captured/terminal events retain history, aware observation times and exact captured bytes/digest where capture succeeded. A failed capture does not invent bytes or a digest. Failed reader attempts retain bounded rejected bytes as diagnostics only. `valid` means reader structural conformance; it does not imply staging eligibility, factual truth or approval. A late older completion never replaces the highest-revision head.

The original file is opened/captured once with regular-file/size bounds. The existing reader operates on a separately closed private temporary copy outside Git; returned bytes must exactly match. The copy is removed on success/error. A TEMP root inside the repository is refused before creating a copy. Changing the original path after capture does not change the trusted captured version. An optional claimed DocxExtraction must match the fresh result completely, including values, hashes and locators.

The deterministic staging integration manifest binds trusted source ID, binary SHA-256, reader method, effective limits, actual reader/ooxml implementation digest plus Python version, native UTF-8 text SHA-256 and complete ordered segment text/hash/locator records. It contains no registration UUID/revision or time. It is `DocumentSnapshot.manifest_sha256`, not an invented native DocxExtraction property. Identical bytes/configuration/source ID retain the same manifest while new registrations remain distinct; revalidation always occurs before immutable native results can be shared.

## Scope, candidate and queue fingerprints

One session owns one active scope. Explicit scope membership must cover every logical source known to that session; omission, unknown declared input, pending/failed source, unsupported shape/assertion, changed reader policy, resource exhaustion or conflicts block all eligible proposals. No source is silently excluded. Scope IDs are canonically ordered; document segment order and literal values are preserved. A new registration or policy activation makes old scopes stale, even if the quote/text or binary bytes later revert.

DocumentBinding fingerprints bind registration identity/revision, complete integration manifest, scope fingerprint and active policy. Context fingerprints bind the whole scope, document bindings, content/policy checks and bounded issue codes. Candidate fingerprints additionally bind owned candidate ID/revision, exact typed values, full quotes/locators, intended predicate roles and validation issues. Registration/policy/review timestamps are outside these content fingerprints; operational registration/scope/policy identities are deliberately included in currentness bindings.

A separate **`docx-assertion-remediation/v1`** fingerprint now binds the logical source ID, exact grammar-supported field values (including null) and intended predicate/endpoint roles, independently of policy-limited field emission. It excludes whole-context/resource-policy changes, other sources, registration IDs, original ZIP bytes, run layout, surrounding whitespace, quote coordinates and clocks. This identity only matches human blocks; full proposal validation remains independently mandatory. The original whole-context remediation hash was unsafe and is superseded by TASK-007.1a. Human rejection/clarification of unchanged substantive assertions survives these irrelevant changes. Corrected assertion values/roles require fresh full validation; returning to old rejected values restores their block. Queue history is append-only, uses only non-approved ReviewState values, and requires explicit identity/reason/aware time and current fingerprints. Automated findings never create reviewer decisions or domain ReviewRecords. Policy-only human reconsideration is not implemented.

Immutable reports/proposals are historical snapshots. **Always call `session.is_eligible(proposal)` against the live owning session**; proposed state or a matching old quote alone is insufficient. This read-only query creates no candidate revision and checks owned current candidates, full context and queue blocks. It is not a transaction granting future materialization rights: source state can change afterward. There is no materialization/export path in this task.

## Successful synthetic demonstration

A temporary DOCX containing exactly this single paragraph was registered and staged through the public API:

```text
Der Server SRV-001 befindet sich im Rechenzentrum Rostock und betreibt die Anwendung ERP-01.
```

Observed registration: revision **1**, status **valid**. The candidate state was **proposed**, with live eligibility **true**:

| Field | Exact value |
|---|---|
| system_id | SRV-001 |
| standort | Rechenzentrum Rostock |
| anwendung_id | ERP-01 |

Intended claims: `SRV-001 hosts ERP-01` and `SRV-001 located_at Rechenzentrum Rostock`. Each field and claim retains the full original sentence quote, part `word/document.xml`, segment ordinal 1, body_index=1, paragraph_index=1, table/row/cell=null and segment-local Unicode character span **[0,92)**. The complete source text and native UTF-8 hash are unchanged. Surrounding-whitespace tests preserve the entire source for hashing and adjust quote offsets; no source trimming occurs. Quotes describe original text, not rendered pages or semantic truth.

Observed exact original DOCX binary SHA-256:

```text
d8c0bfdc1b10927bc0a5e2e8833038c80c497d8bec5efd27af2fecba0f9d4299
```

Native extracted text/segment SHA-256:

```text
cfe8ce9a7794a4582b89f9cd6df145cc3f5b4b83f2f2f837414b4a0bd81b531d
```

Staging integration manifest SHA-256:

```text
d44190a050792e7ccec10233f4d35580797a651a65f5be8317adf493e657f4b9
```

Observed reader implementation digest:

```text
c4d61c972ec670cdf00b18de62cae0dc88df4a62d0745fe79d5d0681a762af12
```

Observed binding/context/candidate fingerprints for that session:

```text
binding:   b5545b6a5a66d5910b3d9c149c62f175f08b6fa6496026fea34919e44d38d589
context:   41395d19114cedba9b79bd7c4b2c3b28706e4e310e52dd69ea2fa3ed5a0b2689
candidate: b9f8ef0011d4a161fdce864e5ff68972354248a6de9d35b29623d6ea8683850a
```

Operational fingerprints change across new sessions/registrations because identities are unique; they are not portable constant expected hashes. Manifest reproducibility assumes identical source ID, exact ZIP/XML bytes, reader code bytes, Python version and limits. A checkout with different source-code line endings legitimately changes the implementation/manifest digest. Hashes identify data/configuration; they do not authenticate its origin.

## Blocked demonstrations

After `begin_registration` for revision **2**, the old proposal's live eligibility immediately became **false**, before parsing. Revision 2 then received a renamed PDF-like input `%PDF-1.4...` under `.docx`: registration **failed**, old eligibility stayed **false**, eligible proposals **0**, issue `source_failed`. No PDF reader or evidence conversion was called.

Revision **3** contained the valid initial sentence followed by:

```text
Änderung vom Administrator: Der Standort von SRV-001 wurde nach Berlin verlegt.
```

The DOCX structure was **valid**, but staging returned **0 proposals**, candidate state **needs_clarification**, issue `unsupported_assertion`. An exact initial quote did not hide the contradictory appended context. The temporary demonstration source was removed.

Regressions also demonstrate a valid changed location and reversion to original bytes: new registrations/candidate revisions require fresh validation and old proposals never regain eligibility. Missing location remains actual null with an explicit MissingObservation, no positive location quote and no located_at claim. Duplicate/conflicting source assets, extra paragraphs (including empty ones), tables, negations, injected instructions, unsupported city wording and forged native hashes/text/locators all block rather than truncate or coerce.

## Tests and verification

Final complete offline command:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging
```

**Original TASK-007.1 observed result: 339 tests in 12.304 seconds; OK; 0 failures, 0 errors.** This preserved **all 279 existing offline tests** and added **60 staging regressions**. This historical suite did not cover the subsequently reproduced human-rejection bypasses. TASK-007.1a results below supersede it. Optional live Ollama classes were not selected, and no model/network request was made.

The first isolated staging run exposed one failed assertion and one test error: a shared test helper placed two line breaks before the sentence, and mocked domain constructors interfered with a dependent module's import metadata. The helper/import order were corrected without weakening production validation. Subsequent staging and full runs passed; the final count above includes added resource/TEMP/scope/queue hardening. No unresolved test failure remains.

Tests cover exact fields/claims/quotes, missing/null values, split runs and whitespace; all required malformed/unsupported/contradictory inputs; native-result spoofing; captured-byte/path/temp lifecycle; immutable histories; same-byte/changed/failed/reverted registrations and late older completion; scope omission/missing/pending/failed/conflict/currentness; policy history/revalidation; rejected/stale/approved queue attempts and replay bypasses; PDF exclusion; immutable typed records and resource boundaries. A side-effect regression patches all six forbidden domain constructors, inventory mutations/reviews, store commit, SQLite connect, extraction/model/network calls and print; none is called while registering, staging, querying eligibility and recording a non-approving queue decision.

## Resource and security limits

Default budgets: 16 logical sources; 32 MiB retained unique binary bytes; 1,000,000 retained parsed-text characters; 32 MiB retained manifests; 512 history units; 1,000,000 current scope characters; 2,000 characters per complete source paragraph; 64-character asset/application IDs; 256-character locations; 16 KiB deterministic field envelopes; 8 MiB individual integration manifests. Existing reader defaults are inherited, with only tightening permitted. Per-attempt history reserves three units. Capacity failure closes eligibility for the session; it never silently drops a source/history entry or serves an old proposal. No hard RSS, process sandbox or parse deadline is claimed beyond existing bounded reader mechanics.

Only direct synthetic DOCX files in the deliberately narrow reader/profile are supported. Most ordinary Word files remain unsupported. The registry cannot determine whether data is synthetic, authenticate source/reviewer identities or detect undeclared PDF ancestry in text copied by a dishonest trusted caller. All declared derived lineage is rejected. Frozen dataclasses/hashes do not resist malicious code mutating the trusted process or coherently rewriting its state. There is no filesystem monitoring, global inter-session identity catalog, discovery of unknown documents or general German contradiction parser.

History is intentionally nonpersistent and lost when the session is discarded; it is not a durable audit log. Registration valid, queue proposed and live proposal eligibility do not establish factual or visual truth. No PDF visual override, XLSX mapping, Evidence/Inventory adapter, human approval, approved export, database migration or certification claim is provided. Human/domain review and persistence require later separately authorized contracts. Recommended next action is review of this bounded implementation and its limitations, not automatic continuation to TASK-007.2.

## PowerShell reproduction

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging -v
py -3.12 -m unittest tests.test_docx_staging -v
```

Successful/blocked public-API demonstration from the same directory:

```powershell
@'
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.docx_staging import DocxStaging
from tests.test_docx_ingestion import paragraph, synthetic_parts, write_synthetic_docx

source_id = 'synthetic:task-0071-demo'
sentence = 'Der Server SRV-001 befindet sich im Rechenzentrum Rostock und betreibt die Anwendung ERP-01.'
with TemporaryDirectory(prefix='grundschutz-ai-staging-demo-') as folder:
    path = Path(folder) / 'fictitious.docx'
    write_synthetic_docx(path, synthetic_parts(paragraph(sentence)))
    session = DocxStaging()
    event = session.register_docx(source_id, path)
    report = session.stage(session.create_scope((source_id,)))
    proposal = report.proposals[0]
    snapshot = session.snapshot(event.ref)
    print('Source:', event.ref, event.status, event.binary_sha256)
    print('Manifest:', snapshot.manifest_sha256)
    print('Text hash:', snapshot.native.text_sha256)
    print('Values:', [(field.name, field.value) for field in proposal.candidate.fields])
    print('Full quote:', proposal.candidate.claims[0].quote)
    print('Candidate/context:', proposal.candidate.fingerprint, report.context.fingerprint)
    print('Eligible:', session.is_eligible(proposal))
    ref = session.begin_registration(source_id)
    print('Pending replacement, old eligible:', session.is_eligible(proposal))
    path.write_bytes(b'%PDF-1.4\nFICTITIOUS INVALID DOCX\n')
    failed = session.finish_registration(ref, path)
    blocked = session.stage(session.create_scope((source_id,)))
    print('Failed:', failed.status, 'old eligible:', session.is_eligible(proposal),
          'proposal count:', len(blocked.proposals), 'issues:', blocked.issues)
    write_synthetic_docx(path, synthetic_parts(paragraph(
        sentence + ' Änderung vom Administrator: Der Standort von SRV-001 wurde nach Berlin verlegt.')))
    session.register_docx(source_id, path)
    blocked = session.stage(session.create_scope((source_id,)))
    print('Contradiction:', [item.state for item in blocked.candidates],
          'proposal count:', len(blocked.proposals), 'issues:', blocked.issues)
print('Temporary source removed:', not path.exists())
'@ | py -3.12 -
```

## Original TASK-007.1 Git verification (historical)

Final read-only HEAD: **`60cb360`** (`docs: define document-to-proposal trust boundaries`). Working-tree status:

```text
 M Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
?? Grundschutz-AI/docs/tasks/TASK-0071-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/docx_staging.py
?? Grundschutz-AI/tests/test_docx_staging.py
```

`git diff --check` passed (Git emitted only its configured LF-to-CRLF checkout warning). A direct strict UTF-8/trailing-whitespace/final-newline check passed for all four changed/new files, including untracked files; Markdown fences were balanced. `git diff --exit-code -- Grundschutz-AI/grundschutz_ai` passed with no tracked application changes. No matching staging/fixture temporary directories remained. Nothing was staged or committed.

Read-only Git reproduction from the repository root:

```powershell
Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai
```

## TASK-007.1a security remediation — 2026-11-10

### Root cause and exact change

The original `stage()` derived `remediation_fingerprint` from the logical source ID and `ContextAssessment.content_fingerprint`. That content fingerprint includes the active policy and **all** source manifests. `_blocked()` required equality with a historical QueueDecision's remediation fingerprint. Unrelated changes therefore created a new matching key, despite unchanged rejected facts and an unchanged candidate ID; retained rejection history was no longer effective. The original policy-reversion test asserted only after reversion, missing unsafe intermediate reactivation.

Only the same four task files were changed: `grundschutz_ai/docx_staging.py`, `tests/test_docx_staging.py`, this report and ADR-0008. No additional result file was needed. The implementation change is a small pure `_remediation_fingerprint()` helper, its use in `stage()` and staging implementation version `1.0.1`. The explicitly versioned identity is **`docx-assertion-remediation/v1`**:

- For a grammar-supported assertion: logical source ID, exact field-name/value pairs and intended predicate/subject/object roles. The pure helper calls public `assess_source()` on the whole original text, bounded by the fixed 2,000-character hard cap and independent of active field/resource limits. Null remains distinct from an absent/unsupported assertion. No quotes, binding hashes or mutable candidate state are used to decide substantive identity.
- For unsupported or over-hard-cap text: logical source ID and native extracted-text SHA-256 form a diagnostic-only fallback. All validation/currentness/conflict failures still block proposals; this fallback cannot create eligible data.
- Resource limits, unrelated documents, registration UUIDs/revisions, ZIP packaging, run boundaries, surrounding whitespace, quote offsets and time are excluded from this matching identity. Exact original text, quotes, locators, hashes and histories remain preserved in their original records.

`_blocked()` still enforces every historical human rejection/clarification matching the stable source-owned candidate ID and substantive identity. `_blocked()`, triage's current candidate/context checks, whole-context content fingerprints and `is_eligible()` were not bypassed or relaxed. The helper only matches blocks and neither emits fields nor grants support/eligibility; `_derive()` and both full public validation contracts remain mandatory for proposals. Full operational fingerprints still change after policy, scope, source or evidence revisions, so stale decision tokens remain invalid even when the remediation identity stays equal. A genuinely changed validated assertion may yield a new proposed revision, never an approval. Reverting to an old rejected assertion reinstates its block. Complete-scope all-or-nothing output remains enforced.

This conservative identity treats accepted syntactic variants with identical field values/roles as the same assertion. It is not a general German semantic-equivalence parser. Policy-only/context-only reconsideration of unchanged human-blocked facts needs a future separately reviewed explicit human action; no override or new authority was invented. The version tag is part of the hash preimage and must not be changed to reset blocks. There is no persistent queue migration or hot-reload/replay contract.

### Executed before/after demonstrations

The two new executable regression tests were first run against the unchanged implementation: **2 tests in 0.038 seconds; 2 failures, 0 errors**. A separate synthetic public-API exercise confirmed actual eligibility, not just fingerprint differences:

| Scenario | Before fix | After fix |
|---|---|---|
| A: reject SRV-001, then max_id_chars 64 to 63 | Candidate proposed; 1 proposal; eligibility `[True]`; rejection still in history. | Candidate rejected; 0 proposals; old eligibility false; forcing a proposed snapshot still yields `[False]`; same remediation identity; history intact. |
| B: reject source A/SRV-001, then add valid source B/SRV-002 | Candidate A proposed; 2 proposals; eligibility `[True, True]`; rejection still in history. | Candidate A rejected; 0 proposals for entire scope; forcing proposed snapshots for both candidates still yields `[False, False]`; old eligibility false; same remediation identity; history intact. |

Both scenarios now pass as `test_rejected_assertion_survives_unrelated_id_limit_change` and `test_rejection_survives_adding_unrelated_source_and_blocks_whole_scope`. After-fix API observations were also executed independently and matched this table. No fabricated source facts or approved objects were created for either demonstration.

### Regression coverage and actual results

Added nine tests:

1. Rejection survives the exact max_id_chars 64-to-63 change; new candidate/context fingerprints coexist with the same blocking identity.
2. Human NEEDS_CLARIFICATION survives an unrelated location resource-limit change.
3. Adding an unrelated valid source preserves rejection and blocks every proposal in the scope, including eligibility checks on state-altered snapshots.
4. Revising an unrelated document preserves the block and invalidates all old proposals.
5. ZIP_STORED-to-ZIP_DEFLATED repackaging changes binary/manifest fingerprints but preserves assertion identity and rejection.
6. Surrounding-whitespace and split-run changes preserve rejection while retaining correct full quotes/offsets.
7. Old candidate or context fingerprints cannot authorize decisions against a new current revision, despite unchanged remediation identity.
8. A Rostock-to-Schwerin assertion correction calls both validators, produces a new validated revision and retains immutable queue history; reverting to Rostock restores the original rejection.
9. Human REJECTED and NEEDS_CLARIFICATION decisions survive relaxing each of four limits (ID, complete-source length, field-envelope bytes, location length) that initially prevented any fields from being emitted. The matching identity is unchanged; state-altered proposal snapshots are still ineligible.

Strengthened the existing policy-change/reversion test to check the intermediate policy as well. Expanded the existing no-side-effects regression through rejection, unrelated policy/source changes, complete-scope blocking and a corrected-source workflow. All six forbidden domain constructors, Inventory mutations/reviews, store commit, SQLite connection, extraction/Ollama/network calls and print remain mocked and uncalled. Existing same-byte replay, APPROVED/string-state rejection, stale context, scope conflict and history tests continue to pass; none was weakened to accept reactivation.

An initial post-fix staging run had **68 tests, 1 error, 0 failures**: the new split-run fixture omitted `xml:space="preserve"` on trailing whitespace, correctly causing reader rejection and hence no candidate. Only the fixture XML was corrected. The subsequent staging run passed **68 tests in 0.878 seconds**. After expanding side-effect coverage, an intermediate full suite passed **347 tests in 12.474 seconds**. Final review then exposed a further boundary in that initial helper: deriving identity from emitted fields let relaxation of a field/resource limit turn a fallback identity into a positive identity for unchanged human-blocked text. The ninth test reproduced **8 failing subtests (2 human blocking states times 4 limits), 0 errors, in 0.083 seconds** before correction. The helper now derives its bounded matching identity independently of policy-limited emission, without changing eligibility validation.

**Final full Python 3.12 offline suite: 348 tests in 12.567 seconds; OK; 0 failures, 0 errors**: all **339 previous tests plus 9 new** (279 legacy tests and 69 staging tests). No unresolved regression failure remains. Live model tests were excluded; no network or inference was requested.

### Reproduction and remaining limits

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
# Executable demonstrations for both previously failing scenarios:
py -3.12 -m unittest tests.test_docx_staging.DocxStagingTests.test_rejected_assertion_survives_unrelated_id_limit_change tests.test_docx_staging.DocxStagingTests.test_rejection_survives_adding_unrelated_source_and_blocks_whole_scope -v
# All staging security/currentness regressions:
py -3.12 -m unittest tests.test_docx_staging -v
# Entire offline suite, excluding optional live-Ollama classes:
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging
```

History remains session-local, bounded, unauthenticated and nonpersistent. Source-ID reassignment or a fresh session is not protected by a durable identity catalog or reviewer authentication. Hashes cannot establish factual truth, authentic lineage or visual equivalence. Changed assertion values qualify only for a fresh proposed revision under the narrow grammar, never approval; remaining source/queue/domain review is still necessary. A post-query mutation can invalidate eligibility. No policy-only override, persistence, PDF evidence promotion, XLSX staging, automatic model call or approval pathway was added. No dependencies, legacy reader/domain changes or Git commit; TASK-007.2 remains unstarted. Recommended next action: human review of this security fix before further integration.

### TASK-007.1a Git verification

Final HEAD remains **`a021f0c`** (`feat: add nonpersistent DOCX proposal staging`). All four changes are unstaged tracked modifications; no untracked files and no automatic commit:

```text
 M Grundschutz-AI/docs/decisions/0008-document-proposal-boundary.md
 M Grundschutz-AI/docs/tasks/TASK-0071-RESULTS.md
 M Grundschutz-AI/grundschutz_ai/docx_staging.py
 M Grundschutz-AI/tests/test_docx_staging.py
```

`git diff --check` passed, with only Git's existing LF-to-CRLF checkout notices. A read-only `git diff --exit-code` for all legacy domain, inventory, storage, extraction, validation, support and DOCX/XLSX/PDF/OOXML modules passed with no differences. Strict UTF-8/trailing-whitespace/final-newline checks and balanced Markdown fences passed for the four files. No matching task temporary directories remained. Git's normal sandbox identity hit repository ownership checking; read-only Git checks then succeeded in the owner's context without changing safe.directory, permissions or security settings.

```powershell
Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --stat
```
