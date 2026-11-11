# TASK-007.3B.2.5.0 — Persistent native validation activation contract

## Result and boundary

**READY FOR CONTRACT REVIEW.** [ADR-0013](../decisions/0013-schema3-native-validation-activation.md)
is **PROPOSED**, pending independent review. This documentation-only task does
not activate persistent native validation. It does not imply production readiness,
Sprint 0 acceptance or approval of the BSI normative baseline.

Required and actual clean starting HEAD, unchanged final HEAD:
`b310430f5be52b5e5790a5a991e1993249f12ccf`.
Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`.
No dependencies, downloads, network/model calls, company documents, security/Git
configuration changes, staging or commits. Test artifacts are owned disposable
synthetic fixtures outside Git.

Exactly two new documentation files:

- [ADR-0013](../decisions/0013-schema3-native-validation-activation.md): exact
  future command/outcome, byte/hash contracts, transaction/replay algorithms,
  state/currentness, failure/rollback, resource and threat/acceptance matrices.
- This report: findings, actual verification, identities, blockers and reproduction.

No optional test module was necessary: existing inert-codec vectors, seven native
goldens, worker forgery/deadline tests and capture-only activation-refusal tests
already verify the fixed contracts. No existing Python, test, historical fixture,
schema, codec, catalog, handler or ADR was modified. **No new executable tests**
were added; the detailed persistent activation cases in ADR-0013 are future work,
explicitly distinguished from currently executable component evidence.

## Contract decisions and implementation gaps

The proposed fixed command is validate_source(ref, *, expected,
expected_registry, expected_source, actor_id) on an already opened SourceLedger.
It accepts exact global/registry/highest-started tokens; the target must already
have a verified immutable source.captured event and be captured PENDING,
nonterminal, under its still-active compatible policy/handler. The command takes
no document path, caller observations, derivation hash, policy/selection override
or database-selected code. It uses only original SQLite capture bytes, including
after restart. No automatic validation occurs on capture, normal load or startup.

The immutable proposed outcome identifies the one committed VALID or permitted
FAILED transaction, reference, capture, head and registry/source context. A
control-only exhaustion commit is separately reported; an ambiguous commit outcome
requires explicit reconciliation and conveys no claimed durable state.

Derivation and event contracts are reused verbatim: derivation-ref/v2,
source-valid/v1 and ledger-event/v3, with separate tagged derivation identity and
canonical reference-BLOB digest. Native text is exact UTF-8; DOCX native manifest
stays null/absent; XLSX native and both integration manifests retain exact pinned
serialization. The XLSX nested native_manifest_json stays a JSON string. Equal
content can deduplicate only after exact-byte equality; registration-bound
derivations cannot be reused across distinct SourceRefs.

The transaction performs complete RO replay, fresh expected-token checks and
initial native processing, then BEGIN IMMEDIATE, fresh complete replay/checks,
atomic BLOB/derivation/terminal/event/projection writes, full mirror-building
replay and final complete precommit replay. Exactly one singleton event commits.
No stale retry, partial trusted prefix, independently trusted cached observation
or error-triggered second failure transaction is permitted.

Review findings made explicit in the proposed ADR:

1. **Recognition is not activation.** The current codec recognizes VALIDATED,
   but the capture-only replayer rejects it; no public validate_source method
   exists. Current FAILED replay also disallows a retained capture, so post-capture
   validation failures need their own strictly bounded future transition.
2. **Write-lock/native cost is material.** Preserving the current mirror rebuild
   discipline gives 4V+3 native bridge calls for a successful new VALID with V
   historical VALIDs, 3V+2 calls under the lock. Each call performs two worker
   parses. Even the first VALID therefore needs six worker passes, four locked.
   All repeated work shares command and document budgets; no claim that parsing
   occurs entirely outside the write lock.
3. **Failure classification is not currently sufficient for every A outcome.**
   The pinned worker returns exit 2 for parser and other errors; worker_failed
   does not prove invalid_source/unsupported_structure. Under the existing pins,
   these cases conservatively refuse without a failure event and preserve PENDING.
   A future trusted classification mechanism would require separate review of
   protocol/artifacts, not fabricated identities or an unpinned parent parser.
   Initial target worker_timeout may justify a narrowly verified parse_timeout
   FAILED attempt if sufficient fresh replay/commit budget remains. Replay or
   protocol failures never turn existing VALID into FAILED.
4. **Policy activation beyond revision 1 is still unsupported.** Historical policy
   semantics and transition/currentness tests are defined, not implemented. An
   older registration may complete with explicitly refreshed tokens while a newer
   source head stays current, only if its own policy is still active. Historical
   VALID never substitutes for a newer PENDING/FAILED head or gains current
   applicability under a changed active policy.
5. **Capture-only BLOB-count admission needs a reviewed role-based replacement.**
   The current 2*events+8 heuristic assumes no derivations. The future safe
   bound is derived from payload/descriptor/policy/raw/derivation roles and followed
   by exact replayed reference closure. The fixed byte/event/schema/codec limits
   are not raised. Native text/manifests/reference/spec accounting is all-history
   and role-aware, with exact dedup equality.
6. **Relative bridge deadlines are not integrated persistent replay budgets.**
   The proposed orchestration retains the 10-second native and 60-second cumulative
   ceilings, conservatively sharing document time across repeated passes; it must
   account for preflight/transport/serialization/cleanup and refuse late results.
   Integer remaining-time rounding must tighten, never round up. Cleanup/rollback
   may finish after admission timeout; no hard RSS/disk/wall-clock guarantee is
   claimed. Full-history/lock/RAM performance needs later measurement.

The ADR separates A (fully verified permitted source.failed), B (no-write refusal)
and C (verified durable registry.exhausted only when reserve/capacity permits).
Unknown worker failures, SQL errors and uncommitted control attempts never
manufacture durable failure/invalidation. Text/manifest aggregate control uses
existing policy_capacity, not invented budget_name values.

## Actual verification

Complete offline suite on Python 3.12.6 / SQLite 3.45.3:

**912 tests run in 242.783 seconds; 907 passed, 0 failures, 0 errors, 5 skipped**;
exit code 0. All existing offline tests passed. **Historical skips: 0.**

Both authentic original historical proofs executed and passed:

- HistoricalLedgerTests.test_original_A_created_database_cross_version_readonly_proof.
- NativeGoldenTests.test_original_historical_producer_reproduces_literal_vectors.

All seven BridgeTests native goldens passed: docx_complete, docx_coverage,
xlsx_complete, xlsx_blank, xlsx_missing, xlsx_empty_text and xlsx_coverage.
They use the unchanged literal fixture and exact original producer contracts.

Activation remains refused: TamperTests.test_syntactically_valid_source_validated_still_refused,
test_policy_activation_is_outside_this_minimal_profile and
test_validation_phase_failed_refused all passed. Codec tests preserve the exact
derivation/payload shape and independent tagged/BLOB vectors. Current public
validate_source availability was independently inspected: **False**. These are
actual checks; no proposed persistent VALID success/restart/forgery/concurrency
case is reported as passed.

Every skip is an existing optional live Ollama integration test, with the exact
reason **Optional localhost integration disabled** because
GRUNDSCHUTZ_RUN_INTEGRATION='0':

| Class | Skipped method |
|---|---|
| LocalIntegrationTests | test_complete |
| LocalIntegrationTests | test_missing_location |
| LocalIntegrationTests | test_prompt_injection |
| LocalSafetyIntegrationTests | test_injection_is_rejected |
| LocalSafetyIntegrationTests | test_contradictory_location_update_is_rejected |

No additional historical, runtime or platform skip was accepted. git diff checks
confirm all tracked content unchanged; new documentation gets separate UTF-8,
whitespace and local-link checks because ordinary diff omits untracked files.

## Runtime, schema and frozen artifact identities

Observed Python **3.12.6**, SQLite **3.45.3**, Windows 11, fixed-local C: temporary
fixtures on NTFS. Existing application NTFS/ReFS admission stays unchanged;
this run does not independently qualify ReFS recovery or power-loss durability.
The forensic identity check verifies the actual loaded sqlite3.dll path and hashes:

| Artifact / contract | SHA-256 |
|---|---|
| C:/Python312/python.exe | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| C:/Python312/DLLs/_sqlite3.pyd | `fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e` |
| C:/Python312/DLLs/sqlite3.dll | `054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3` |
| Physical schema-3 fingerprint, recomputed | `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c` |
| Native golden fixture, 106,955 bytes | `553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b` |
| DOCX handler a0-docx-native/v1 | `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` |
| XLSX handler a0-xlsx-native/v1 | `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` |

SQLite source ID:

```text
2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355
```

Both native catalog profiles passed verify_available, including every literal
artifact pin. No handler/hash/ceiling was auto-enrolled or replaced. The catalog
still has only two historical read and two native mechanics profiles.

## Reproduction commands

PowerShell, from the application directory with the independently retained
historical artifacts verified present for this run:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = '0'
$env:GRUNDSCHUTZ_A0_ORACLE = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite'
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI'
py -3.12 -m unittest discover -s tests -v
```

If these temporary historical artifacts have expired, rebuild only from the
unchanged original `2ee9bc7cf309727e5a9f10e2982791dbc991c464` checkout using
[TASK-0073B20's exact reproduction](TASK-0073B20-RESULTS.md#exact-reproduction).
Do not substitute a current-writer DB or generate expected goldens from current
code. Equivalent acceptance must execute both original proofs, not skip them.

Optional focused reproduction (already covered by the full run; not an extra
executed suite in this task):

```powershell
py -3.12 -m unittest tests.test_v3_codec tests.test_v3_native tests.test_v3_native_worker -v
py -3.12 -m unittest tests.test_v3_ledger.TamperTests.test_syntactically_valid_source_validated_still_refused -v
```

Identity and disabled-API verification (read-only):

```powershell
@'
from pathlib import Path
import hashlib
from grundschutz_ai import v3_schema as schema, v3_native_catalog as catalog
from grundschutz_ai.v3_ledger import SourceLedger
from tests.test_v3_recovery_forensics import runtime_identity
print(runtime_identity())
print(schema.schema_fingerprint())
raw = Path('tests/fixtures/b0-native-goldens.json').read_bytes()
print(len(raw), hashlib.sha256(raw).hexdigest())
for profile in catalog.native_catalog():
    catalog.verify_available(profile)
    print(profile.spec.data()['handler_id'], profile.spec.sha256)
print('validate_source available:', hasattr(SourceLedger, 'validate_source'))
'@ | py -3.12 -
Get-FileHash -Algorithm SHA256 -LiteralPath docs/decisions/0013-schema3-native-validation-activation.md,docs/tasks/TASK-0073B250-RESULTS.md
Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --exit-code
git diff --cached --exit-code
git diff --check
```

## Remaining blockers and next action

Independent review must accept/revise ADR-0013 before implementation. Persistent
VALID writer/replayer/immutable metadata, captured-failure transition, role-based
admission/accounting, policy-transition replay, shared deadline orchestration,
COMMIT-uncertainty handling and the full persistent threat matrix are unimplemented.
Precise invalid-document classification remains blocked under the current pinned
worker error channel; safe refusal is specified until separately reviewed.
Native/full-history write-lock, memory and replay throughput limits remain unmeasured.

ADR-0012 remains **PROPOSED**. Operational recovery remains
**NOT_OPERATIONALLY_AUTHORIZED**: real operator authentication, independent
checkpoint/custody/audit, maintenance interlocks, confined worker, target-volume
qualification and adoption/restart protocol remain missing. Public synthetic
credentials do not establish those controls. Source validation does not bypass
them or authorize repair.

For this schema-3 document-validation path, domain/proposal/inventory creation,
human approvals, queue persistence, PDF promotion, export and migration remain
disabled. No production/Sprint 0/BSI claim.
Next step is human contract review only; no subsequent task was started.

## Artifact hashes and Git status

| New artifact | SHA-256 |
|---|---|
| ADR-0013 | `d8f85f96afc75234b8128a7284588fb4e9e7c5da6c70b5126a591fa00d07cd64` |

This report's final SHA-256 is supplied in the completion response and reproducible
with Get-FileHash above; embedding its own digest would be self-referential.

Final HEAD is `b310430f5be52b5e5790a5a991e1993249f12ccf`. No files staged/committed;
no tracked file changed. Exactly two untracked deliverables:

```text
?? Grundschutz-AI/docs/decisions/0013-schema3-native-validation-activation.md
?? Grundschutz-AI/docs/tasks/TASK-0073B250-RESULTS.md
```
