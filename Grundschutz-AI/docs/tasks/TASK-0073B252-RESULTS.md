# TASK-007.3B.2.5.2: Verified native evidence read contract

2026-11-11. **READY FOR CONTRACT REVIEW. Contract/design only.**
Required and observed starting HEAD:
`3bf64021ce2dc1d532c27c59b62bcb0b5961bccc` (`3bf6402`), branch master.
Starting worktree was clean. No production Python API was added or modified.

## Deliverables and boundary

Created only:

- [ADR-0014](../decisions/0014-schema3-verified-native-evidence-read.md),
  **PROPOSED**, containing the precise proposed API, immutable result, same-snapshot
  algorithm, eligibility/error/concurrency matrices, exact provenance bindings,
  resource analysis, future adversarial tests and implementation blockers.
- [tests/test_v3_evidence_read_contract.py](../../tests/test_v3_evidence_read_contract.py),
  six prerequisite tests using disposable synthetic stores, authentic frozen
  vectors and real pinned native extraction. No mock of an unimplemented consumer.
- This results report.

The baseline review covered AGENTS/GOALS/PLANS, ADR-0008 through ADR-0013,
TASK-0073B23/B240/B241/B250/B251 and the R1 budget correction, existing A0/native
proof contracts and the requested schema-3 source/test modules. The R1 writer
retains one VerificationBudget and uses exhaustion_budget_name separately.
Existing _verify already yields verified LedgerState and Replay.blobs **inside
its caller's transaction**. Existing _read/load_ledger closes that transaction;
it cannot establish currentness for BLOBs later fetched from a second connection.

The proposed read accepts only exact SourceRef, LedgerHead, RegistryState and
source-head tokens, all mandatory. Tokens detect staleness; complete replay
supplies authority. It returns owned immutable native/integration bytes only
for a snapshot-current VALID, active-policy, unexhausted highest-started source.
Every other registration state refuses, including superseded VALID when a newer
head is PENDING/FAILED. Every historical VALID still gets freshly re-extracted.

The result carries the existing derivation-ref/v2, exact verified snapshot and
terminal identities, immutable selection and bytes; no new hash preimage/event/
status/table. DOCX retains null native manifest and full integration structure;
XLSX retains exact native/integration JSON, nested JSON string, empty kinds and
all-sheet coverage. Original binaries are omitted from the proposed result;
current LedgerState.original_blobs exposure is accurately documented unchanged.

One read-only transaction spans replay, currentness, token comparisons, binding
and owned materialization. BEGIN alone is deferred; its first actual read sets
the snapshot. After closing, an object describes its old head, not a lease or
independently authenticated freshness. Later consequential use must reverify in
its own authorized transaction. Historical evidence exposure remains a distinct,
unimplemented future capability with unresolved authority requirements.

Limits preserve cumulative 60 seconds and 10 seconds/document context, including
extra selection/copy work in the **same** VerificationBudget. V historical VALID
means V real bridge calls and 2V worker parses for a single replay, not O(1).
The proposed 24-MiB result/16-KiB metadata admission bounds can only tighten the
existing ceilings. No partial results or durable failure/exhaustion events on
read failure. Controlled native temporary transport remains permitted; this is
not a temp-I/O-free operation or an OS-enforced hostile native sandbox.

## Executable prerequisite evidence

| New test | Observed prerequisite, not consumer acceptance |
|---|---|
| test_docx_exact_bytes_in_live_readonly_snapshot | Deleted original; exact DOCX coverage text/reference/integration in live verified transaction; null native manifest; one real bridge/two workers; mode=ro/query_only blocks write probe; rows and file bytes unchanged. |
| test_xlsx_exact_bytes_and_nested_manifest_in_live_snapshot | Same verification for XLSX all-sheet coverage and exact native/embedded JSON string; no reserialization. |
| test_deferred_begin_does_not_establish_snapshot_before_first_read | Real writer commits newer PENDING after reader BEGIN but before first read; subsequent verification sees newer head and old VALID is ineligible. |
| test_writer_cannot_commit_while_verified_reader_holds_snapshot | Real ordinary writer reaches COMMIT, fails BUSY and rolls back while reader holds SHARED snapshot; all persistent rows unchanged. |
| test_closed_snapshot_has_no_later_currentness_or_two_connection_lease | Old frozen state remains true at H, but new snapshot H+1 rejects old applicability after newer PENDING; old exact bytes still exist, demonstrating why a second fetch is insufficient. |
| test_full_replay_reextracts_superseded_and_current_valid | V=2 (one superseded, one current): two real bridge calls/four pinned workers; PENDING remains untouched, all rows unchanged. |

These tests inspect existing private replay machinery solely to prove its
transaction prerequisites. They do not implement a production consumer and do
not satisfy the later DTO/token/egress/deadline-copy/side-effect acceptance gates.
The test explicitly confirms SourceLedger has no read_current_native_evidence
method. No newly exposed entry point or changed existing API is implied.

Focused final run: **6 run, 6 passed, 0 failures, 0 errors, 0 skips**, 42.544s.
An initial development run had six helper AttributeErrors (limits instead of
the existing private _limits); corrected in the new test module before the
successful run. No production code or expected native bytes changed to fix it.

Current full offline run: **1,004 run, 999 passed, 0 failures, 0 errors,
5 skips**, **660.471s**, exit code 0. This is the previous 998 tests plus six
new prerequisites. Both authentic historical proofs and all seven native and
persistent golden cases executed successfully. No historical skips. Previous
checkpoint results were not substituted.

The log's `INITIAL_TIMEOUT: FAILED parse_timeout` is the expected synthetic
source terminal from a passing controlled real-worker-timeout test, not a suite
failure. The large-XLSX test also passed with a 1,117,574-byte native manifest.
Local run log (temporary, outside Git):
`C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-b252-full-bdcc4b0f5b354e0582ad5cb2edc59d5f.log`.

Authentic historical proofs observed executing (not skipped):

- test_v2_compat.HistoricalLedgerTests.test_original_A_created_database_cross_version_readonly_proof.
- test_v2_reader_goldens.NativeGoldenTests.test_original_historical_producer_reproduces_literal_vectors.

The seven frozen BridgeTests golden cases have also passed in this current run:
docx_complete, docx_coverage, xlsx_complete, xlsx_blank, xlsx_missing,
xlsx_empty_text, xlsx_coverage. The literal fixture SHA-256 remains unchanged.

The five intentional skips, all with reason `Optional localhost integration disabled`:

- test_extraction.LocalIntegrationTests.test_complete.
- test_extraction.LocalIntegrationTests.test_missing_location.
- test_extraction.LocalIntegrationTests.test_prompt_injection.
- test_extraction.LocalSafetyIntegrationTests.test_contradictory_location_update_is_rejected.
- test_extraction.LocalSafetyIntegrationTests.test_injection_is_rejected.

These skips avoid Ollama/model calls in this offline contract task. No historical
skip has occurred. The native proof work executes locally without inference.

## Runtime and frozen identities

Reviewed Windows 11 fixed-local profile: Python **3.12.6**, SQLite **3.45.3**,
temporary artifacts on **C:/NTFS**. Runtime pin checks succeed. SQLite source ID:

```text
2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355
```

| Identity verified in this task | SHA-256 |
|---|---|
| Schema fingerprint, recomputed | `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c` |
| Original seven native goldens, 106,955 bytes | `553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b` |
| Authentic A0 oracle.sqlite, 188,416 bytes | `5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537` |
| a0-docx-native/v1 handler | `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` |
| a0-xlsx-native/v1 handler | `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` |
| DOCX reader Spec | `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c` |
| XLSX reader Spec | `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2` |
| v3_schema.py | `076f539c004b462b51b0020b6fd58a0b6af263252f6e018ba49a42434669ece8` |
| v3_codec.py | `6440d0215ec96e6a179b792173e5ca0453b80b63cd997c85c95e10149d976e5d` |
| v3_store.py | `f67ab2cb9887ba8785d9154032982c185a9b09610e1b66791bb06facb9afc031` |
| v3_ledger.py, including unchanged R1 | `eb4862711cd8635564d0945553ea38ef8b3b78c71da9e764d39a79ae8644a1b5` |
| _v3_capture.py | `a119a23ff9b9eb33e9c3fbf9b87912eb5d52289781ad12db97de1f31d83a068f` |
| _v3_validation.py | `a0d3e1ec4eb2710174fd411fb04bc33da37ba69396b5602966c5e933132e5e99` |
| v3_native.py | `73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926` |
| v3_native_catalog.py | `1b3d65085681f8b9112cf1b0f5a6374edbc54d0603431c25339abf5aa02a46b9` |
| v3_native_contract.py | `9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2` |
| v3_native_worker.py | `454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319` |
| C:/Python312/python.exe | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| C:/Python312/DLLs/_sqlite3.pyd | `fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e` |
| Actual loaded C:/Python312/DLLs/sqlite3.dll | `054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3` |

Both native profiles pass verify_available across all pinned artifacts; the
four-profile catalog, historical fixtures and production source remain unchanged.

## Exact reproduction

PowerShell, with the authentic artifacts confirmed present for this run:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = '0'
$env:GRUNDSCHUTZ_A0_ORACLE = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite'
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI'
py -3.12 -m unittest tests.test_v3_evidence_read_contract -v
py -3.12 -m unittest discover -s tests -v
```

If these independent temporary artifacts expire, use only the original producer
commit `2ee9bc7cf309727e5a9f10e2982791dbc991c464` and
[TASK-0073B20 original-producer instructions](TASK-0073B20-RESULTS.md#exact-reproduction).
Do not generate purported historical evidence using the current implementation.
Both historical tests must execute for this verification gate to be complete.

Read-only identity and scope checks:

```powershell
@'
from pathlib import Path
import hashlib
from grundschutz_ai import v3_schema as schema, v3_native_catalog as catalog
from tests.test_v3_recovery_forensics import runtime_identity
print(runtime_identity())
print(schema.schema_fingerprint())
for profile in catalog.native_catalog():
    catalog.verify_available(profile)
    print(profile.spec.data()['handler_id'], profile.spec.sha256)
raw = Path('tests/fixtures/b0-native-goldens.json').read_bytes()
print(len(raw), hashlib.sha256(raw).hexdigest())
'@ | py -3.12 -
Get-FileHash -Algorithm SHA256 -LiteralPath docs/decisions/0014-schema3-verified-native-evidence-read.md,tests/test_v3_evidence_read_contract.py,docs/tasks/TASK-0073B252-RESULTS.md
git status --short --branch
git diff --check
git diff --stat
git rev-parse HEAD
git diff --cached --exit-code
git diff --exit-code HEAD
```

All task files are new and untracked; ordinary git diff/stat exclude them. To
review their complete contents without staging:

```powershell
Get-Content -Encoding UTF8 -LiteralPath docs/decisions/0014-schema3-verified-native-evidence-read.md
Get-Content -Encoding UTF8 -LiteralPath tests/test_v3_evidence_read_contract.py
Get-Content -Encoding UTF8 -LiteralPath docs/tasks/TASK-0073B252-RESULTS.md
```

## Remaining gates and limitations

No runtime consumer exists. Independent review of ADR-0014, later bounded
implementation and the entire future acceptance matrix remain mandatory before
activation. The new six tests do not prove read-token/DTO/egress/copy-budget/error
semantics of an absent API. Whole-history replay cost may refuse before theoretical
storage ceilings; no cached bypass is proposed. Native temporary I/O and lack
of a hard RSS/Job Object/process sandbox remain documented limitations.

Source authenticity, independent freshness, privileged custody, historical-access
authority and operational recovery remain unresolved. Structural VALID does not
convey truth, approval or permission to send text to a model. No proposal,
inventory, human approval, export or recovery pathway was activated. ADR-0012
stays **PROPOSED**; production recovery **NOT_OPERATIONALLY_AUTHORIZED**.
No BSI baseline change, dependency, model, installation, company document,
network request, staging or Git commit. Stop after this contract task.

## New artifact identities and final Git status

| New artifact | SHA-256 |
|---|---|
| ADR-0014 | `36510621bc3260a281166a1195ea786d9f64bc36232e7ba2ffc907edea831722` |
| tests/test_v3_evidence_read_contract.py | `c77e69c91d13f0352d286c67783d7096707eba1d9d3a2fc73abf7f22523183db` |

The report's final SHA-256 is supplied in the completion response and can be
recomputed above; it cannot contain its own final digest.

Final HEAD remains `3bf64021ce2dc1d532c27c59b62bcb0b5961bccc`.
The only changes are these three **new, untracked** files; nothing is staged:

```text
## master
?? Grundschutz-AI/docs/decisions/0014-schema3-verified-native-evidence-read.md
?? Grundschutz-AI/docs/tasks/TASK-0073B252-RESULTS.md
?? Grundschutz-AI/tests/test_v3_evidence_read_contract.py
```

git diff --check, git diff --stat, git diff --cached --exit-code and
git diff --exit-code HEAD are clean/empty (exit 0); the untracked files were
separately checked for UTF-8, trailing whitespace, Python AST and local links.
All production, frozen-codec/schema/native/golden/historical fixture files match
HEAD. ADR-0014 is ready for independent contract review, not production use or
implementation activation. Stop here; no subsequent task started.
