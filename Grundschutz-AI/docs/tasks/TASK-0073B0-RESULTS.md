# TASK-007.3B.0: Historical compatibility and verified replay contract

Date: 2026-11-10 (Europe/Bucharest). Repository: `Y:/Grundschutz-AI`; application: `Y:/Grundschutz-AI/Grundschutz-AI`.

## Result and boundary

**Documentation deliverable complete; READY FOR ARCHITECTURE REVIEW. Historical compatibility/replay is neither implemented nor demonstrated.** TASK-007.3B implementation has not begun. The new [ADR-0010](../decisions/0010-historical-implementation-compatibility.md) defines the proposed contract and outstanding implementation/review gates.

Exact HEAD before and after: **2ee9bc7cf309727e5a9f10e2982791dbc991c464**, `feat: add verified SQLite v2 source event ledger`. Initial working tree was clean.

Read AGENTS.md, GOALS.md, PLANS.md, ADR-0008, ADR-0009, TASK-0073A-RESULTS.md; inspected the current v2_codec/v2_schema/v2_ledger modules, both DOCX/XLSX readers and stagers, and both v2 test modules. Existing architecture/quality boundaries remain in force. Root instructions are in the application directory; there is no repository-root AGENTS.md.

## Historical compatibility problem

Current trusted implementation identity hashes **all ten** allowlisted modules for either format: docx_ingestion, xlsx_ingestion, ooxml_safety, docx_staging, xlsx_staging, support, validation, v2_codec, v2_ledger, v2_schema. It also includes exact Python/SQLite runtime, fixed Windows filesystem profile, family/method and canonical serialization version. Raw file bytes, including line endings, matter; Git commit is not a descriptor field.

SourceLedger.open first verifies read-only using the current descriptor catalog and exact current schema. It then opens read/write without creation and fully verifies again. At implementation.registered, stored Spec bytes must equal the installed family Spec. Code/runtime changes therefore can prevent opening an old ledger even when its source-format tags remain unchanged. The mismatch currently maps to **CorruptLedgerError**; missing local artifacts map to UnsupportedLedgerError. Current policy reconstruction/fingerprints, strict codec tags and exact SQL allowlist are additional compatibility barriers, so allowing an old hash alone would be insufficient.

The exact local A0 profile is frozen in ADR-0010: LF module bytes, Python **3.12.6**, SQLite **3.45.3**, platform **windows-fixed-ntfs-refs/v1**. Its implementation Spec identities are:

- DOCX: `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c`.
- XLSX: `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2`.

ADR-0010 also records all module hashes, separate descriptor BLOB digests, full default policy Specs/fingerprints, exact schema identity, eight A event codecs and existing four independent golden vectors. A matching descriptor identifies reviewed artifacts; it does not prove document validation or truth.

## Proposed catalog and replay design

The proposed historical-catalog/v1 is application-owned and exact-match only, initially capped at four implementation descriptors. Each entry binds immutable old descriptor bytes, schema/codec/policy/runtime combinations, pinned static handler artifacts, approved capabilities and explicit human review/retirement metadata. No SQLite-driven imports, executable paths/code, downloads, unknown acceptance, newest-reader fallback or rewritten historical identities.

Recognition is distinct from executable availability. Under the initial conservative complete-bundle rule, a known descriptor with an unavailable required reader still refuses trusted replay. No partial trusted output.

Future replay must retrieve exact captured bytes, recompute binary/native/integration identities and exact locators through pinned historical handlers, reconstruct highest-started source heads and complete same-format scopes, then replay immutable candidate and human queue history. Existing substantive remediation identities preserve rejection/clarification through repackaging, unrelated revisions, policy changes and reversion; current action tokens remain bound to exact current fingerprints. No status flag or stored support claim substitutes for recomputation.

## Compatibility fixtures and proposed tests

ADR-0010 fixes a **future** synthetic A0 ledger procedure using the public A commands, exact default policies, deterministic UUIDs/timestamps and 13 immutable events. Expected current heads: DOCX revision 2 PENDING without capture, captured XLSX PENDING, and a missing XLSX FAILED. Older captured DOCX revision 1 remains FAILED; no VALID sources or proposals. Its deliberately non-Office capture bytes demonstrate that A quarantine is not format validation.

New payload/event reference vectors were calculated **read-only** from explicit JSON preimages using json/hashlib and the observed A descriptors/policies. Reference final head: sequence 13, hash `e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09`. This calculation did not create/open a historical fixture DB and does not prove that a future builder or B replay matches it. Independent vector review and A-builder verification remain required.

Before Gate B, separately freeze valid A-native DOCX/XLSX fixtures with exact bytes, native/integration hashes and every locator using existing baseline synthetic helpers. B cannot generate its own alleged A oracle. The ADR specifies A-to-B reopening, reviewed/unknown/forged/missing-handler/code-change cases, corrupt bytes/policies, identical-content repackaging, reverted human blocks, unrelated changes, crash heads, coherently rehashed false metadata, unknown schemas/codecs and every replay budget.

No binary compatibility fixtures were added or created in this task. No future compatibility tests were added or run.

## Activation gates and exact blockers

| Gate | Current status and outstanding evidence |
|---|---|
| A: historical recognition/read | **Not implemented or accepted.** Approve catalog/host/bundle/retirement rules; implement frozen A schema/policy/codec handlers; build/review the A-only fixture and demonstrate unchanged blocked history under changed B code. |
| B: source.validated | **Disabled.** Gate A plus positive/hostile native/integration/locator goldens, pinned derivation, bounded worker/deadline behavior, typed validation transitions and an independently approved exact B write-schema/profile. |
| C: persistent scopes/candidates | **Disabled.** Gates A/B plus deterministic identity-preserving complete-scope replay, candidate history, stale-token/conflict/aggregate-limit tests. |
| D: durable human queue history | **Disabled.** Gates A–C plus durable exact decision binding, explicit human identity/timestamps, substantive rejection/clarification/reversion tests and bounded history exhaustion. |

Each gate needs independent review; enrolling a descriptor cannot activate later codecs. The exact A layout remains frozen/read-only for historical compatibility. Future B tables/events need an explicitly distinct versioned schema/profile and any upgrade must be separately authorized, never automatic on open. The physical B write-format choice is unresolved.

Evidence, Inventory, ReviewRecord materialization, domain approval/export, PDF promotion, v1 migration/import, automatic model calls and network stay disabled throughout this contract.

Existing conservative event/byte/source/text/manifest/history ceilings are retained. Additional proposed bounds are four catalog descriptors, ten seconds per document within the existing sixty-second total replay limit, 1,600 diagnostic drafts per scope with complete refusal above that allocation budget, and at most 512 durable queue decisions per registry, also charged to existing history/event limits. Unsupported workbooks may contain more than 100 rows; the diagnostic ceiling is a proposed replay budget, not an existing reader guarantee. These new controls are design requirements, not implemented guarantees.

## Actual checks

Unchanged test discovery command, from the application directory:

```powershell
py -3.12 -m unittest discover -s tests
```

Captured result:

```text
Ran 507 tests in 28.917s

OK (skipped=5)
```

**502 passed, 0 failures, 0 errors, 5 skipped optional live-Ollama tests; 507 discovered. New tests: 0.** The executed count matches the 502 offline tests recorded for TASK-007.3A. Optional live integration was not enabled; no model/network call was requested. Existing tests use their already-defined temporary synthetic SQLite/source fixtures outside Git; no task-specific DB write, schema change, migration, user database access or historical fixture creation occurred.

Additional checks: read-only descriptor/default-policy/schema hash calculation and explicit fixture-preimage reference hashing; UTF-8/newline/Markdown/local-link/hash consistency review; read-only Git status and tracked-file diff. No dependency, Python, test, schema or existing ingestion/storage changes. No installation/download, company documents, normative BSI change or automatic commit.

## Changed files and Git status

Only these two new documentation files:

- `docs/decisions/0010-historical-implementation-compatibility.md`.
- `docs/tasks/TASK-0073B0-RESULTS.md`.

ADR-0009 is unchanged; a correction was not needed. Nothing staged or committed. Repository-root status:

```text
?? Grundschutz-AI/docs/decisions/0010-historical-implementation-compatibility.md
?? Grundschutz-AI/docs/tasks/TASK-0073B0-RESULTS.md
```

Tracked-file diff is empty. This leaves the repository functionally unchanged.

## Reproduction commands

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
# Ensure optional localhost tests remain disabled:
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest discover -s tests

# Read-only descriptor, policy and exact-schema identities:
@'
from grundschutz_ai import v2_ledger as ledger, v2_codec as codec, v2_schema as schema
from grundschutz_ai.docx_staging import StagingPolicy as DocxPolicy
from grundschutz_ai.xlsx_staging import StagingPolicy as XlsxPolicy
for kind, policy in (("docx", DocxPolicy()), ("xlsx", XlsxPolicy())):
    spec = ledger._local_spec(kind)
    print(kind, spec.canonical.decode("utf-8"))
    print("spec", spec.sha256, "blob", codec.sha256(spec.canonical))
    print("policy", ledger._policy_spec(kind, policy, spec.sha256).canonical.decode("utf-8"))
    print("policy spec", ledger._policy_spec(kind, policy, spec.sha256).sha256)
    print("staging fingerprint", policy.fingerprint)
objects = [{"name": name, "kind": kind, "sql": sql}
           for name, (kind, sql) in sorted(schema.expected_objects().items())]
print("schema", codec.fingerprint("a-schema-objects/v1", objects))
'@ | py -3.12 -

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --exit-code
git diff --check
```

These hash commands intentionally use inspected private helpers only for read-only reproduction, not as proposed new public APIs. Descriptor results depend on exact checkout bytes/runtime. The future DB creation procedure in ADR-0010 is not a command executed in this task.

## Remaining limitations and next review

The runtime/packaging support matrix, handler packaging and catalog authority/retirement process still need human approval. A-created compatibility fixtures and valid native/integration goldens need implementation and independent review. B write-format/upgrade behavior, validation/queue codecs, deterministic replay adapter and enforced parser timeouts are unresolved implementation gates.

Even correct local replay cannot authenticate an entirely replaced self-consistent unsigned corpus or actor string, establish source completeness, or prove real-world inventory truth. Authenticated sources/reviewers, external integrity checkpoints, backup/access policy and production security remain separate work. No BSI applicability/certification claim follows.

Next action is human review of this contract and explicit selection of the first Gate A implementation milestone. TASK-007.3B has not begun.
