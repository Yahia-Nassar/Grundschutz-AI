# TASK-007.3B.2.5.1 — Schema-3 persistent native validation implementation

## Result and scope

**READY FOR R1 IMPLEMENTATION REVIEW.** The explicit writer, complete trusted VALID
replay and persistent derivation verification are implemented and tested together.
All 81 original focused tests and their offline acceptance run pass as recorded below.
**R1 correction:** those tests missed budget-variable shadowing in ordinary writes
after VALID history. The R1 section below supersedes their cumulative-budget claim
for that path and records the correction and expanded acceptance evidence.
This is **not production deployment authorization** or approval of Sprint 0,
source authenticity, human inventory assertions or the normative BSI baseline.

Required/actual starting HEAD and unchanged final HEAD:
`b673129217fbf6ce918612b6b1e1a10829508edd`, initially clean. Repository
`Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`.
Only disposable synthetic stores/documents were used outside Git. No dependency
installation, model/download, network/cloud call, real company document,
security/Git configuration change, staging or commit.

## Changed files and boundaries

| File | Change |
|---|---|
| [v3_ledger.py](../../grundschutz_ai/v3_ledger.py) | Fixed explicit validate_source, operation-owned validation transaction, shared replay budget, role-derived BLOB admission and commit/rollback classification. |
| [_v3_capture.py](../../grundschutz_ai/_v3_capture.py) | Immutable VALID metadata/outcome, fresh native derivation replay, captured timeout-FAILED transition, role counters and current-native query. |
| [_v3_validation.py](../../grundschutz_ai/_v3_validation.py) | One new private helper for the frozen native bridge, cumulative deadlines, exact reference/BLOB construction, row mapping and role retention. No SQL or original-path API. |
| [test_v3_validation.py](../../tests/test_v3_validation.py) | 81 new executable persistent/security regressions, genuine pinned native workers, original literal goldens, SQL/clock/process faults and complete-row comparisons. |
| [test_v3_recovery_trust.py](../../tests/test_v3_recovery_trust.py) | Only the closed source-state enum assertion/comment changes: native VALID now joins PENDING/FAILED. Recovery/authorization refusal and every custody check remain unchanged. |
| [ADR-0013](../decisions/0013-schema3-native-validation-activation.md#task-0073b251-clarification-known-commit-versus-late-response) | Minimal reviewable clarification of known committed late/close errors versus genuinely indeterminate COMMIT. No event/schema/state additions. ADR remains PROPOSED. |
| This report | Implementation evidence, exact verification, hashes and reproduction. |

All forbidden production modules, physical schema, canonical codecs, native
bridge/catalog/contracts/workers, reader/artifact pins, frozen v2/A0 and literal
goldens remain unchanged. The original incomplete-source.validated regression
still refuses the forged history; no original test was changed to accept it.
The enum assertion update reflects the newly authorized processing state and
does not convert diagnostic recovery labels into database states or approvals.

ADR-0012 is unchanged and **PROPOSED**. Operational recovery remains
**NOT_OPERATIONALLY_AUTHORIZED**. Policy activation, PDF promotion, proposals,
domain/inventory/review/approval/export/migration and model inference are not
enabled by this schema-3 operation. The separate genesis-only store API remains
genesis-only; schema-2 A0 uses its unchanged read-only compatibility path.

## Public API and immutable metadata

```python
SourceLedger.validate_source(
    ref, *, expected, expected_registry, expected_source, actor_id
) -> ValidationOutcome
```

Requires exact typed SourceRef, LedgerHead, complete RegistryState and nonnull
highest-started source-head token. The target must be captured PENDING,
nonterminal, owned by that registry/source, with an exact earlier capture and
still-active enrolled handler/reader/policy. No path, parsed observations,
selection/policy override, derivation hash or database-controlled executable is
accepted. Captured bytes come only from fully verified SQLite original BLOBs.

ValidationOutcome is frozen/slotted and strictly validates head, target,
capture/event sequence, event hash, transaction ID, terminal SourceStatus,
DerivationRef or validation failure tuple, source_head_at_completion and complete
registry state. Only VALID or FAILED are permitted outcomes; PENDING and arbitrary
state strings are refused. A known exhaustion commit raises RegistryExhaustedError
instead of returning a false source terminal.

SourceRegistration retains an immutable derivation, terminal event sequence and
failure phase when applicable. LedgerState.is_current_valid(ref) is a native
structural applicability query, not an approval capability: highest-started head,
VALID terminal, matching active policy and unexhausted registry are required in
a completely verified state. New PENDING/FAILED heads block old VALID fallback.
Explicitly reissued old completion with fresh tokens can be historical VALID;
its event binds the newer highest-started source head and never replaces it.

CommitOutcomeUnknownError carries a frozen **intent**, not a committed result:
prior expected head, target, capture sequence/binary hash, intended transaction ID,
event hash/kind and optional intended derivation identity. It has no claimed new
head/outcome. Actor strings remain audit metadata, not authenticated human identity.

## Transaction, replay and byte verification

One validation command performs this exact sequence:

1. Read-only full trusted replay under one command budget; compare all expected
   tokens and target/capture/handler/policy eligibility.
2. Retrieve exact retained capture bytes and run the pinned two-worker native
   bridge before opening a writer. Derive speculative exact text/manifests/reference.
3. Recheck instance/file trust, open the verified existing DB with zero busy retry,
   BEGIN IMMEDIATE, and replay the complete history fresh under the same budget.
4. Compare the original expected tokens again; recheck target, active policy,
   handler, highest-started source head and prospective capacity. No stale retry.
5. Choose one VALID, narrowly permitted validation FAILED or reserved exhaustion
   event. Insert immutable BLOBs with digest/length/**exact-byte** dedup equality;
   for VALID insert the derivation row and VALID terminal, then the singleton event.
6. Full native re-extraction with mirror comparison disabled reconstructs expected
   rows; exact mirror additions/projections follow. A final complete replay compares
   every SQL row, BLOB, counter, head and native/reference byte binding.
7. Check actual page/byte/event/time budgets and COMMIT once. Return only a verified
   committed outcome after resource closure. Established precommit failure rolls
   back all new content, terminal/reference/event rows and projections.

Every complete trusted load re-extracts **each** historical VALID from captured
bytes through the pinned bridge. No stored native object, hash claim or decoded
manifest cache is authority. Exact fresh reference/native text/native manifest/
integration bytes must match all stored BLOBs and relational columns. Global
events/hash/transaction identities, ownership, historical policy/handler, capture,
terminals, highest-started source heads and all role counters must fully replay.
Unknown/orphan BLOBs, extra/missing/forged rows and incomplete VALID closure refuse
the whole load; no partial trusted prefix or cache fallback.

Existing derivation-ref/v2, source-valid/v1 and ledger-event/v3 bytes/preimages are
unchanged. Native text is exact UTF-8 without normalization or added newline.
DOCX native manifest remains null with no fabricated BLOB. XLSX retains exact
native/integration serialization; native_manifest_json remains a nested **string**.
Every registration has its own reference even when raw/text content deduplicates.

Opening/loading/capturing a PENDING source never validates it automatically.
Opening or writing a history that already contains VALID does necessarily
**reverify those existing VALID observations**; that is trusted replay, not a new
validation event. Original mutable document paths are never reopened by validation
or VALID replay. Tests delete/replace those paths and still verify retained bytes.

## A/B/C failure evidence and commit distinctions

| Scenario actually exercised | Result |
|---|---|
| Real sleeping child worker, initial target, pinned bridge kills/reaps and cleans transport; remaining global budget sufficient | A: exactly one source.failed, phase=validation, issue_codes=[parse_timeout]. Captured bytes retained, no derivation, immutable FAILED. Focused elapsed 10.172 s includes timeout handling and failure transaction. |
| Malformed DOCX / generic worker_failed, protocol/native_refused/cleanup error, arbitrary initial exception | B: no source.failed/validated, no partial rows, capture stays PENDING. No invented invalid-document classification. |
| Trusted handler/artifact unavailable | B: typed unsupported-environment refusal; no terminal event. |
| Timeout/corruption in existing VALID replay or locked re-extraction | B: full verification refused; no rewrite of old VALID into FAILED, no new source failure. |
| Missing capture, duplicate terminal, wrong ownership or typed/stale token | B: refusal, no target completion; historical verification still occurs where required. |
| SQL insertion/projection/precommit failure, lock contention, confirmed rollback of failed COMMIT | B: exact prior logical table/BLOB/event/head/counter state retained; no repair/failure/control transaction appended. |
| Verified aggregate text/manifests/metadata/events over normal capacity, reserved control fits | C: one existing registry.exhausted, target remains PENDING, prior captures/terminals/derivations preserved. policy_capacity covers text/manifests; no new enum value. |
| Reserved control insertion denied | No durable exhaustion claim; RegistryExhaustedError is not raised for the failed SQL attempt. |
| COMMIT succeeds internally then exception hides acknowledgement | CommitOutcomeUnknownError with non-durable intent; reload shows one complete VALID closure, duplicate completion refuses. No automatic retry or synthetic acknowledgement. |
| COMMIT returns successfully after admission deadline | Explicit known-committed LedgerLimitError; no late success/fictional rollback/unknown outcome. Reload verifies the existing terminal. |
| COMMIT succeeded, subsequent close errors | Explicit known-committed LedgerError; no indeterminate-commit claim. |

The last two cases resolve a real contract ambiguity in the minimal ADR-0013
addendum: a synchronous SQLite COMMIT cannot safely be preempted by a Python
deadline. Deadline admission is checked before and after; known completed commit
is not undone or hidden. Cleanup/rollback/reaping are not a hard cancellation,
wall-clock, disk quota or arbitrary hardware-I/O durability guarantee.

## Capacity, shared deadlines and observed performance

Fixed ceilings remain 256 MiB DB, 2 MiB/source, 32 MiB unique originals, 10,000
events, four registries/16 sources each, 128 MiB global metadata, independent
8 MiB manifest caps, 32 MiB retained manifests and 1,000,000 text codepoints per
registry. Existing codec, reader, native wire and terminal control reserves remain.

The capture-only count heuristic is replaced by the ADR-0013 role-derived upper
bound before BLOB allocation, then exact replayed reference closure. Global
metadata is the distinct union of metadata/reference/text/manifest/spec/payload
BLOBs plus **all envelope bytes**. Raw and metadata roles are charged separately
even when physical bytes share a BLOB. Per-registry text/native/integration sets
retain all history; Unicode codepoints differ from UTF-8 bytes. A mixed-role
persistent test makes one document's native text equal another's integration
manifest: one physical BLOB, independently charged role retention.

Executable boundary tests cover exact/one-over metadata, event, per-document
manifest, aggregate manifest and text budgets; reserved control success/failure;
DB page-growth rollback; dedup with distinct references; binary repackaging; empty
native text with its real empty digest. Large XLSX native manifest **1,117,574
bytes** exceeds the ledger decoder's 1 MiB string cap but is correctly retained
and verified as opaque native bytes. It remained VALID with nested JSON-string
semantics, taking **4.125 s including a fresh trusted load** in the focused run.

One absolute monotonic 60-second-or-tighter deadline spans complete load/command.
A budget object tracks up to ten native seconds per persistent document context
across every repeated bridge pass; only timings, **never observations**, are
retained. Tightened integer ExecutionLimits use floor of remaining document and
command allowances; less than one second refuses, never rounds upward. Late
successful results are refused. Worker cleanup exceptions cannot masquerade as
the permitted timeout. Repeated SQL/native passes never reset allowances.

| Focused persistent golden | Result | Validation elapsed | Bridge calls / locked calls / worker parses |
|---|---|---:|---|
| docx_complete | VALID; exact literal text/integration | 1.734 s | 3 / 2 / 6 |
| docx_coverage | VALID; ordered tables/empty/Unicode locators | 1.797 s | 3 / 2 / 6 |
| xlsx_complete | VALID; exact sheet and all cells | 1.797 s | 3 / 2 / 6 |
| xlsx_blank | VALID; physical BLANK retained | 1.813 s | 3 / 2 / 6 |
| xlsx_missing | VALID; missing record remains absent | 1.844 s | 3 / 2 / 6 |
| xlsx_empty_text | VALID; TEXT empty distinct | 1.781 s | 3 / 2 / 6 |
| xlsx_coverage | VALID; empty/unselected sheets retained | 1.797 s | 3 / 2 / 6 |

With one historical VALID, the test observed exactly **seven bridge invocations,
five under the write lock**, matching 4V+3 and 3V+2. Each historical context is
re-extracted on every pass. Near-deadline/forced-slow tests prove cumulative
document refusal, no rounding up, late-result rollback, locked replay refusal
and no partial history when cumulative time expires after initial progress.
Parsing is explicitly **not entirely outside the write lock**.

These measurements establish small synthetic feasibility, not throughput at
10,000 events or maximum historical content. Histories that cannot be completely
verified within accepted budgets refuse; no cache/eviction/limit increase is used.
Process/RSS/disk quotas and hostile-native-code isolation remain unimplemented.

## Crash, SQL fault and adversarial coverage

| New executable group | Tests | Actual coverage |
|---|---:|---|
| PersistentGoldenTests | 7 | All seven immutable native vectors persisted and reopened, byte-exact manifests, worker/lock call counts, no original-path dependence, immutable metadata. |
| EligibilityTests | 9 | Captured/uncaptured PENDING, duplicate VALID/FAILED, currentness, newer PENDING/FAILED blocking fallback, late older completion, exact tokens, distinct references/dedup. |
| ForgeryTests | 25 | Wrong source/store/registry/capture/policy/reader/handler/stamp/limits/binary; coherently rehashed text/native/integration manifests; empty coverage/sheets/kinds/selection/cell moves; terminal/mirror/BLOB closure; incomplete event refusal. |
| FailureAndTransactionTests | 21 | A/B classification, actual timeout cleanup, replay and cumulative deadlines, SQL faults, concurrency/stale race, confirmed rollback, commit ambiguity, known committed late/close cases. |
| ResourceTests | 15 | Exact/one-over role/resource limits, reserved control, original/text/manifest dedup, binary repackaging, actual DB page growth, Unicode codepoints, empty text and >1 MiB opaque native manifest. |
| CrashAndBoundaryTests | 4 | Process exits before/after COMMIT; preserved evidence/private copy investigation; no model/network/domain/review/export/recovery/policy/PDF side effects. |

SQL authorizer faults execute at content_blobs, derivations, source_terminals,
events, store_metadata projection deletion and registry_state insertion. A final
fully executed precommit replay is separately forced to fail. Complete table
snapshots and trusted replay check event hashes/counts, captured originals,
terminal/derivation rows, counters and highest-started heads after every rollback.

Real owned process exits occur immediately before COMMIT (exit 83) and after
COMMIT succeeds (exit 84). Before commit, ordinary trusted loading refuses the
residual journal. Exact original/sealed evidence bundles are acquired exclusively
and retained unchanged; only a new bounded working copy from the known synthetic
producer is examined through the existing forensic harness/SQLite backup. Full
candidate replay equals the independently retained prior captured-PENDING state
and every prior table row. No manual journal deletion or original-file recovery.
After commit, normal replay re-extracts the complete one-event VALID closure;
old tokens/duplicate completion cannot issue another terminal.

This is a controlled synthetic forensic test, not a production recovery API or
proof of power-loss durability, arbitrary journal provenance or independent
authentication. The existing recovery custody and refusal tests remain in force.

## Original TASK-007.3B.2.5.1 test results (before R1)

Final focused suite: **81 tests passed in 343.012 seconds; 0 failures/errors/skips**.
The existing capture suite also ran independently: **96 passed in 70.958 seconds**.
Development groups (38, 14, 14, 7 and 8 tests) each passed before the final focused
run. No failed test expectation was relaxed to accept forged/incomplete data.

Complete offline suite: **993 tests run in 588.973 seconds; 988 passed,
0 failures, 0 errors, 5 skipped**, exit code 0. This preserves all **907 previous
offline passes** and adds **81 new passes**. **Historical skips: 0.** Both authentic
independent proof tests executed and passed:

- HistoricalLedgerTests.test_original_A_created_database_cross_version_readonly_proof.
- NativeGoldenTests.test_original_historical_producer_reproduces_literal_vectors.

All seven original BridgeTests goldens and all seven new persistent golden cases
passed. The original incomplete source.validated/policy activation/unsupported
validation failure tests still refuse their malformed or disabled histories.
Recovery/quarantine/custody and production-refusal tests also pass unchanged
apart from the documented source enum assertion.

Every skipped test is an existing optional live Ollama test, disabled by
GRUNDSCHUTZ_RUN_INTEGRATION='0', with reason **Optional localhost integration disabled**:

| Class | Skipped method |
|---|---|
| LocalIntegrationTests | test_complete |
| LocalIntegrationTests | test_missing_location |
| LocalIntegrationTests | test_prompt_injection |
| LocalSafetyIntegrationTests | test_injection_is_rejected |
| LocalSafetyIntegrationTests | test_contradictory_location_update_is_rejected |

Full-run persistent golden timings were 1.750 s DOCX complete, 1.765 s DOCX
coverage, 1.829 s XLSX complete, 1.797 s XLSX BLANK, 1.781 s XLSX missing,
1.797 s XLSX empty TEXT and 1.797 s XLSX coverage. The real worker-timeout/failure
transaction took 10.187 s. Large XLSX validation plus a fresh load took 4.109 s.
No unresolved test failures/errors remain; no later planned policy/recovery/
production qualification test is represented as passed.

git diff --check, Python AST, UTF-8/LF, trailing whitespace and local documentation
link checks pass. The forbidden-module/fixture diff and staged diff are empty.
Existing Git LF-to-CRLF informational warnings were observed; no configuration or
frozen source bytes were changed to suppress them.

## TASK-007.3B.2.5.1-R1 — Preserve shared verification budgets

R1 started at the required unchanged HEAD
`b673129217fbf6ce918612b6b1e1a10829508edd`, with the original seven uncommitted
implementation deliverables already present. Only v3_ledger.py,
test_v3_validation.py and this report were edited for R1. No Git baseline,
validate_source(), frozen component, recovery logic or other existing deliverable
was changed during this correction.

The independently reported defect was confirmed: _write() initialized/received
VerificationBudget and passed it into initial RO and locked replay, but then
assigned `budget = None` for event/metadata exhaustion classification. Later
mirror-building/final replay received None and created new document allowances.
The exhaustion branch instead passed a string, which caused AttributeError when
historical VALID needed native extraction. The common absolute 60-second
deadline did not preserve the separate ten-second document allowance.

The production fix is only a local variable rename within _write(): retain
`budget` unchanged and use `exhaustion_budget_name` for None / events /
metadata_bytes and the _exhaust() argument. Event, BLOB, reserve, SQL, rollback,
result and existing control-event selection rules are unchanged. The same
verification object now flows through all four _write() replays. capture_source()
also preserves that object from its extra outer read into those four stages.

Five new SharedWriteBudgetTests use an authentic, persistently validated golden
DOCX. Instrumentation wraps the real _verify, pinned native bridge and both
real workers; their results are never replaced by cached/fabricated observations.

| Regression | Required evidence and observed corrected behavior |
|---|---|
| begin_registration normal | Exact same VerificationBudget identity and absolute deadline at [RO, locked, mirror-building, final], mirror flags [true,true,false,true]; four fresh bridge calls/eight actual worker passes; one normal start commits, prior VALID/capture/derivation/terminal intact. |
| begin_registration accumulated time | Deterministic bridge elapsed times [2,2,2,5] seconds; integer limits [10,8,6,4]. Same context charges 11 seconds, LedgerLimitError, >40 seconds global time still available. Complete all-table snapshot and full trusted replay match before the failed command. |
| capture_source normal | Exact same object through its outer RO plus all four _write stages, flags [true,true,true,false,true]; five fresh bridge calls/ten worker passes; one capture commits, old VALID remains intact. |
| capture_source accumulated time | Elapsed [2,2,2,2,5], limits [10,8,6,4,2], same context charges 13 seconds; atomic LedgerLimitError with >40 global seconds remaining. All event/BLOB/derivation/terminal/head/counter/projection rows unchanged. |
| ordinary event exhaustion | With existing VALID and tightened normal event ceiling, all four replay stages retain the shared object. Exactly one events registry.exhausted control commits; no target registration/capture/derivation/terminal or source-head changes. |

The deterministic monotonic simulation is frozen outside bridge work, advances
with actual wall time while the real pinned bridge/workers execute (so worker
deadlines still operate), then advances to a prescribed elapsed duration after
the genuine verified result. It refuses a test environment whose real processing
already exceeds the prescribed interval, never moves time backwards and never
changes native observations. Production replay/derivation/byte checks and worker
derive/verify passes execute normally. Time simulation is only in these tests;
production clock/budget implementation is unchanged.

### Demonstrated failure before the fix

Before any production edit, original TASK-251 v3_ledger.py SHA-256 was
`51213c3cd67a1bb5e1f47672845dd002127872b1c6c4669c1004222cd38a4c80`.
The five regressions ran in **34.477 seconds: 0 passed, 4 failed, 1 errored,
0 skipped**. Both accumulated-time tests reported LedgerLimitError not raised;
both identity tests found the budget was not shared. The control test raised
AttributeError because a string reached budget.extract(). These were actual
reproductions against the original uncommitted implementation, not the older
capture-only Git baseline.

After the rename: **5 passed in 38.294 seconds; 0 failures/errors/skips**.
An additional in-memory original-behavior replay confirms the same counterexample
without editing/stashing/replacing any source file or Git history; reproduction
below renames the classifier variable back only in an isolated process's compiled
_write function and checks expected failures plus unchanged file digest.
The final live-module-instrumented negative control ran in **34.640 seconds**,
again with **4 expected failures and 1 expected error**, and its enclosing proof
script exited 0 only after checking those exact outcomes and unchanged source
bytes. This negative control is not included in passing acceptance totals.
An exact inverse identifier replacement also reproduces the original whole-module
SHA-256, proving validate_source() and every other production byte were untouched
by R1. The other four prior implementation artifacts retain their recorded hashes.

Expanded focused acceptance: **86 tests passed in 384.195 seconds; 0 failures,
0 errors, 0 skips**, exit code 0. This includes the 81 original persistent
validation cases and all five R1 regressions.

Full R1 offline acceptance: **998 tests run in 614.621 seconds; 993 passed,
0 failures, 0 errors, 5 skipped**, exit code 0. All 988 prior offline passes and
five new R1 regressions pass. **Historical skips: 0**; both authentic original
A0 proofs executed and passed. All seven original native bridge goldens and all
seven persistent native golden cases passed. The five skips are exactly the
same five optional Ollama tests named in the original results table, each with
reason **Optional localhost integration disabled**, GRUNDSCHUTZ_RUN_INTEGRATION='0'.
There are no unresolved acceptance failures/errors; intentional original-defect
negative controls are separate from these passing totals.

The schema/codec/native catalog/handler/golden/runtime identities in the frozen
identity table were rechecked unchanged, including both native verify_available
checks and authentic A0 oracle digest. The forbidden-component diff and staged
diff are empty. Final HEAD remains b673129217fbf6ce918612b6b1e1a10829508edd;
git status --short --branch, git diff --check and git diff --stat confirm only
the same seven existing implementation deliverables listed below. No staging or
commit, and no further change to test_v3_recovery_trust.py, ADR-0013,
_v3_capture.py or _v3_validation.py during R1.

Original results above are historical evidence, not proof that the shadowed
ordinary-write path previously met the contract. Production recovery remains
NOT_OPERATIONALLY_AUTHORIZED and ADR-0012 remains PROPOSED; this correction adds
no operation or approval pathway.

### R1 reproduction commands

Normal acceptance uses the existing environment and authentic historical artifact
paths in the Reproduction section below:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = '0'
py -3.12 -m unittest -v tests.test_v3_validation.SharedWriteBudgetTests
py -3.12 -m unittest -v tests.test_v3_validation
py -3.12 -m unittest discover -s tests -v
```

Optional reproducible original-defect proof, **test-process memory only**, with
an expected failing unittest result as the successful negative control:

```powershell
@'
import ast, hashlib, inspect, textwrap, unittest
from pathlib import Path
from unittest.mock import patch
from grundschutz_ai import v3_ledger as ledger
from tests.test_v3_validation import SharedWriteBudgetTests
path = Path(ledger.__file__)
before = hashlib.sha256(path.read_bytes()).hexdigest()
tree = ast.parse(textwrap.dedent(inspect.getsource(ledger.SourceLedger._write)))
class OriginalShadowing(ast.NodeTransformer):
    def visit_Name(self, node):
        if node.id == 'exhaustion_budget_name': node.id = 'budget'
        return node
tree = ast.fix_missing_locations(OriginalShadowing().visit(tree))
namespace = {}
exec(compile(tree, '<test-only-original-budget-shadowing>', 'exec'), vars(ledger), namespace)
assert namespace['_write'].__globals__ is vars(ledger)
with patch.object(ledger.SourceLedger, '_write', namespace['_write']):
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SharedWriteBudgetTests))
assert result.testsRun == 5 and len(result.failures) == 4 and len(result.errors) == 1
assert hashlib.sha256(path.read_bytes()).hexdigest() == before
print('EXPECTED ORIGINAL DEFECT: 5 run, 4 failures, 1 error; files unchanged', before)
'@ | py -3.12 -
```

## Runtime and unchanged frozen identities

Python **3.12.6**, SQLite **3.45.3**, Windows 11 fixed-local profile; synthetic
temporary artifacts on C:/NTFS. Exact source ID:

```text
2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355
```

| Frozen identity | SHA-256 |
|---|---|
| Physical schema fingerprint | `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c` |
| Original native goldens, 106,955 bytes | `553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b` |
| Original A0 oracle.sqlite, 188,416 bytes | `5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537` |
| a0-docx-native/v1 handler | `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` |
| a0-xlsx-native/v1 handler | `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` |
| v3_schema.py source | `076f539c004b462b51b0020b6fd58a0b6af263252f6e018ba49a42434669ece8` |
| v3_codec.py | `6440d0215ec96e6a179b792173e5ca0453b80b63cd997c85c95e10149d976e5d` |
| v3_store.py | `f67ab2cb9887ba8785d9154032982c185a9b09610e1b66791bb06facb9afc031` |
| v3_native.py | `73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926` |
| v3_native_catalog.py | `1b3d65085681f8b9112cf1b0f5a6374edbc54d0603431c25339abf5aa02a46b9` |
| v3_native_contract.py | `9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2` |
| v3_native_worker.py | `454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319` |
| C:/Python312/python.exe | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| C:/Python312/DLLs/_sqlite3.pyd | `fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e` |
| Actual loaded C:/Python312/DLLs/sqlite3.dll | `054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3` |

Both native profiles pass verify_available with every pinned artifact, and the
schema fingerprint is independently recomputed. The four-profile catalog and
all historical fixture bytes are unchanged.

## Reproduction

From PowerShell, using the authentic independent artifacts verified present for
this run (never a current-writer substitute):

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = '0'
$env:GRUNDSCHUTZ_A0_ORACLE = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite'
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI'
py -3.12 -m unittest -v tests.test_v3_validation
py -3.12 -m unittest discover -s tests -v
```

If those independent temporary artifacts have expired, rebuild only from exact
original commit `2ee9bc7cf309727e5a9f10e2982791dbc991c464` using
[TASK-0073B20's original-producer commands](TASK-0073B20-RESULTS.md#exact-reproduction).
Equivalent acceptance must execute both original historical proofs, not skip
or regenerate their expected values from current code.

Read-only identity checks:

```powershell
@'
from pathlib import Path
import hashlib
from grundschutz_ai import v3_schema as schema, v3_native_catalog as catalog
from tests.test_v3_recovery_forensics import runtime_identity
print(runtime_identity())
print(schema.schema_fingerprint())
raw = Path('tests/fixtures/b0-native-goldens.json').read_bytes()
print(len(raw), hashlib.sha256(raw).hexdigest())
for profile in catalog.native_catalog():
    catalog.verify_available(profile)
    print(profile.spec.data()['handler_id'], profile.spec.sha256)
'@ | py -3.12 -
Get-FileHash -Algorithm SHA256 -LiteralPath grundschutz_ai/v3_ledger.py,grundschutz_ai/_v3_capture.py,grundschutz_ai/_v3_validation.py,tests/test_v3_validation.py,tests/test_v3_recovery_trust.py,docs/decisions/0013-schema3-native-validation-activation.md,docs/tasks/TASK-0073B251-RESULTS.md
git status --short --branch
git diff --check
git diff --stat
Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git diff --cached --exit-code
git diff --exit-code -- Grundschutz-AI/grundschutz_ai/v3_schema.py Grundschutz-AI/grundschutz_ai/v3_codec.py Grundschutz-AI/grundschutz_ai/v3_store.py Grundschutz-AI/grundschutz_ai/v3_native.py Grundschutz-AI/grundschutz_ai/v3_native_catalog.py Grundschutz-AI/grundschutz_ai/v3_native_contract.py Grundschutz-AI/grundschutz_ai/v3_native_worker.py Grundschutz-AI/grundschutz_ai/v2_a0.py Grundschutz-AI/grundschutz_ai/v2_codec.py Grundschutz-AI/grundschutz_ai/v2_schema.py Grundschutz-AI/grundschutz_ai/v2_compat.py Grundschutz-AI/grundschutz_ai/v2_ledger.py Grundschutz-AI/tests/fixtures
```

## Limitations and review requirements

Generic worker_failed cannot reliably distinguish invalid source from worker/
environment failure under the frozen protocol; this activation safely implements
B, not an invented invalid_source classifier. Only the specified trustworthy
initial timeout can produce A. Policy activation beyond revision 1 stays rejected;
future policy transition/currentness tests remain future work, not claimed here.

Repeated pinned parses are executions of the **same implementation**, not
independently developed semantic parsers. They do not prove document truth,
authentic authorship, visual completeness or general Office compatibility.
The successful boundary/large-manifest tests are not exhaustive fuzzing or maximum
history/near-memory/power-loss qualification. A constrained complete load may
refuse well below theoretical storage ceilings; no history is skipped to pass.

The existing filesystem/runtime trust model does not defend against privileged
whole-corpus replacement or forge actor identities into authenticated operators.
No OS Job Object/RSS/disk sandbox, durable maintenance interlock, independent
checkpoint/custody/audit service or publication/adoption protocol was added.
ADR-0012 remains PROPOSED; production recovery NOT_OPERATIONALLY_AUTHORIZED.

Independent review must assess the complete writer/replayer/helper/tests together,
including the narrow post-COMMIT clarification. Structural VALID grants no
proposal/inventory/review/approval/export authority. No subsequent task began.

## Changed artifact SHA-256 and Git status

| Changed artifact | SHA-256 |
|---|---|
| grundschutz_ai/v3_ledger.py (R1 replacement) | `eb4862711cd8635564d0945553ea38ef8b3b78c71da9e764d39a79ae8644a1b5` |
| grundschutz_ai/_v3_capture.py | `a119a23ff9b9eb33e9c3fbf9b87912eb5d52289781ad12db97de1f31d83a068f` |
| grundschutz_ai/_v3_validation.py | `a0d3e1ec4eb2710174fd411fb04bc33da37ba69396b5602966c5e933132e5e99` |
| tests/test_v3_validation.py (R1 replacement) | `71cbd28921a833ede06bc6e1725dc661bbba6d47b604ae17abbaf4fd40541943` |
| tests/test_v3_recovery_trust.py | `99a70d93feaf7ee72fbd415ee1f496c5dada8f2d92bc2dde1a55a87e35e06c2a` |
| ADR-0013 with minimal clarification | `fbaa93ff4fa5cb55ed4888a11ffa10b76f08179812dbd31c5db57ce844bfb516` |

This report's final digest is supplied in the completion response and recomputed
above; it cannot contain its own final hash. No binary DB/document/journal,
secret or model artifact was added to Git.

HEAD remains `b673129217fbf6ce918612b6b1e1a10829508edd`. No staging/commit.

```text
 M Grundschutz-AI/docs/decisions/0013-schema3-native-validation-activation.md
 M Grundschutz-AI/grundschutz_ai/_v3_capture.py
 M Grundschutz-AI/grundschutz_ai/v3_ledger.py
 M Grundschutz-AI/tests/test_v3_recovery_trust.py
?? Grundschutz-AI/docs/tasks/TASK-0073B251-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/_v3_validation.py
?? Grundschutz-AI/tests/test_v3_validation.py
```
