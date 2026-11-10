# TASK-007.3B.1: Trusted historical ledger compatibility, Gate A only

Date: 2026-11-10 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`.

## Result

**Gate A technical implementation complete; READY FOR REVIEW.** An authentic A-stage database created by unchanged **2ee9bc7** code was verified by the changed B.1 application through a separate read-only API. Every literal payload/event hash, complete returned state/projection manifest and original byte digest matched. No historical writer or later feature gate was enabled. Human release acceptance remains separate.

Starting/ending HEAD: **78485a90dcdea6f62a4c985489b1bea9b506112d**, `docs: define historical ledger compatibility and replay gates`. Starting tree clean. No automatic commit or staging.

Read the requested instructions/charter/plan, ADR-0008/0009/0010, both predecessor reports, actual v2 codec/schema/ledger and their tests before implementation. AGENTS.md is in the application directory.

## Authentic A0 oracle, established before production edits

The isolated checkout was an exact Git archive of commit **2ee9bc7cf309727e5a9f10e2982791dbc991c464**, exported with **per-command** `git -c core.autocrlf=false archive`. No repository configuration or security setting changed. A direct temporary worktree attempt could not create its .git file in the owner-separated temporary directory; it left no registered extra worktree. The archive checkout supplied the same exact committed source without worktree administration.

The first default archive used CRLF and the harness refused it before database creation. A fresh LF export passed all ten module hashes, Python **3.12.6**, SQLite **3.45.3**, real Windows fixed-local NTFS/ReFS check, both descriptors/default policies, and exact A schema identity **092b2d5aed6e07ddb99b3a4299d01b05c0f6cc5845b75bec6aa968aaa0fefa32**. Hashed source files were not edited or normalized to manufacture identity. The harness verifies its imported module path belongs to that checkout.

`tests/a0_oracle.py` then used only unchanged A public commands, UUID(int=1..n) and fixed UTC time mocks in the test harness, to create the ADR-0010 **13-event** history. The A implementation itself reopened and verified all projections, literal hashes, heads and original captures. This happened before creating the production compatibility modules or changing the current writer docstring.

Original A fixture retained for review outside Git:

```text
C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite
```

| Artifact | SHA-256 |
|---|---|
| Actual original A SQLite file bytes | `5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537` |
| Canonical complete A state/projection manifest | `3b01d810cadc1058be89b4c9aebcdaf8b0ec4058375b134c4a8336c98b193c15` |
| A-produced SQL text transport, 54,444 bytes | `a89ea981a57ffbe1328ed8aee7ff9e916099ee2196aa4c055d7d81af133b8d61` |
| Final immutable event, sequence 13, store UUID=U(1) | `e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09` |
| Original DOCX-labelled 27-byte capture | `0ff38ccf4f11a70bac7ac86d85d2dbe772c24858d4bc42d2927bc2415f0b1937` |
| Original XLSX-labelled 27-byte capture | `b17a108c5ef9447e9308ffad6bb817990930f4869aee29c9949af00c45a41f2f` |

The complete literal 13 payload/event vector pairs and deterministic commands are retained in [ADR-0010](../decisions/0010-historical-implementation-compatibility.md), the independent A harness and catalog. They were not replaced with B-derived expectations. Two additional tightened-policy fingerprint/Spec vectors were obtained by importing unchanged A code from the isolated checkout; ADR section 10 and tests record exact limits and literals.

No binary SQLite fixture is in Git. The plain SQL fixture is a literal export of the real A-produced database, used only by offline tests; it is never executed by the production loader. It permits standalone regressions without Git, a runtime checkout or the original temporary database. The separate cross-version proof uses the **original A-created DB**, not a B writer or SQL reconstruction.

## Exact catalog and public API

| Entry | Historical implementation Spec identity | Capability |
|---|---|---|
| a0-docx/v1 | `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c` | source_ledger_read |
| a0-xlsx/v1 | `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2` | source_ledger_read |

Both use **historical-catalog/v1**, source-lf/v1 packaging, exact Python/SQLite/Windows runtime tuple, schema 2/staging_only, canonical-json/v1, ledger-event/v2 and the eight original A payload codecs. Their complete descriptors, separate BLOB digests, policy version/ceilings, handler identity, manifest anchor and literal event vectors are immutable application-owned entries. Exactly two are supported; a hard ceiling of four cannot be relaxed through configuration and no enrollment API exists.

Trusted handler ID: **a0-source-ledger-read/v1**. Complete adapter file SHA-256: **a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd**. Its bundle also requires the other nine exact A module artifacts, including both readers/stagers; stored names/paths never select code. The old descriptor's v2_ledger identity remains unchanged and is serviced by this explicitly pinned bridge. New/unknown/forged descriptors, unavailable artifacts, unsupported hosts and changed bundle files refuse complete loading. Recognition metadata alone does not prove executable availability.

New public API in `grundschutz_ai.v2_compat`:

- `historical_catalog()`: immutable metadata entries, no runtime enrollment.
- `load_historical_ledger(path, *, limits=HistoricalLedgerLimits())`: complete read-only verification.
- `HistoricalLedgerLimits`, `HistoricalLedgerState`: frozen historical types; current writer limits are intentionally not interchangeable.
- `HistoricalLedgerError`: static fail-closed loader error, no partial trusted state/source-text logging.

The handler's DTOs, filesystem guards, schema checking, event/state machine, projections and limit definitions were checked **AST-identical** against isolated A. Only frozen policy parsing, the strictly read-only connection/transaction and private read entry differ. The pure policy bridge preserves exact original field sets/ceilings and staging fingerprint preimages, including DOCX support policy. It never instantiates current staging policies. The unchanged original codec/schema remain hash-pinned. All malformed/inconsistent inputs must pass the same complete A replay and projection comparison.

Connections use internally constructed `mode=ro`, `query_only=ON`, foreign keys, trusted_schema=OFF and a read transaction. Even the private connection helper refuses write mode. No writer class is copied/exported. Current SourceLedger.open gained no historical fallback: only its module docstring changed, which also intentionally changes its already code-bound current descriptor. The current writer therefore refuses A0 registered implementations; its operational code is untouched.

## Observed A-to-B replay

The original A-created file was loaded after the B.1 code changes. Its byte digest remained **5f218c87...c84d537** before and after; all 13 events and canonical returned state matched the separately written A manifest. The literal SQL regression also compared complete stored projections plus state against the full A manifest digest.

Expected and observed heads:

| Source | Current result | Retained history |
|---|---|---|
| synthetic:compat-a0-docx | revision 2/U(17), PENDING, no captured hash | revision 1/U(10) FAILED/operator_failed, exact DOCX-labelled bytes retained |
| synthetic:compat-a0-xlsx | revision 1/U(26), captured **PENDING**, exact hash | no inferred VALID state |
| synthetic:compat-a0-missing | revision 1/U(31), FAILED/capture_failed, no raw digest | no invented bytes or hash |

Two registries, three logical sources, four registrations and two original BLOBs matched. Captures deliberately are not Office ZIPs: A quarantine can verify their history but cannot validate them as documents. No parser was called, no source became VALID, no old head became eligible, and no staging/domain data was created.

## Refusals and safety coverage

New regressions cover exact catalog identity/immutability; unknown/forged descriptors with coherently rebuilt minimal histories; missing handler/reader files; unreviewed changed code; wrong Python/SQLite/OS/filesystem; changed policy specs/all original hard caps; A-derived tightened fingerprints; unknown schemas/extra tables/codecs/future tags; corrupted originals; missing/reordered/rewritten events; false current heads/capacity; and coherently rehashed false lengths, revisions and ownership.

Coherent attacks rehash the entire following chain and remove obsolete payload BLOBs, so rejection does not rely on an orphan leftover. Every negative loader test checks refusal and unchanged DB bytes. Limits cover catalog entries, event count, aggregate metadata/original bytes, replay time and nonrelaxable typed ceilings. Side-effect guards cover network/model transport, readers/stagers, legacy storage and domain construction; trace checks permit only read statements/transaction control and ensure query-only mode.

Existing conservative A limits remain: 256 MiB DB, 10,000 events with control reserve, four registries, 32 MiB aggregate originals, 128 MiB metadata and sixty-second cooperative replay deadline. Exact historical reader/source/history limits are checked without reader execution. No new schema, event codec, process worker or later-gate resource mechanism was introduced.

## Actual tests

Final full run, with the original-A oracle explicitly supplied and optional model integration disabled:

```text
Ran 550 tests in 28.984s

OK (skipped=5)
```

**545 passed; 0 failures; 0 errors; 5 existing optional Ollama tests skipped.** All **502 previous offline tests** remain passing, plus **43 new tests**. The cross-version original-A test ran and passed.

The initial focused 42-test suite passed in 2.204s; after strengthening coherent attack construction it passed again in 2.073s. Review then removed the private historical write-mode branch and added its regression, giving 43 new tests in the final full suite. No validation expectation was weakened. No unresolved test failure remains.

Without GRUNDSCHUTZ_A0_ORACLE, the original-file proof is explicitly skipped; ordinary regressions still verify the hash-pinned A SQL export. That default result is not a fresh independent A-to-B proof. All acceptance commands below supply the real A oracle.

Additional checks: handler-versus-A AST comparison, exact artifact/manifest/fixture digests, unchanged original modules/schema/v1 storage, read-only Git diff/status, UTF-8/trailing-whitespace/final-newline, Markdown/local-link checks. Temporary negative-test databases were cleaned by their tests; the original oracle/isolated checkout are retained outside Git for human review.

## Files and rationale

| File | Change |
|---|---|
| grundschutz_ai/v2_compat.py | New bounded exact catalog, pinned bundle/host checks and explicit read-only public API. |
| grundschutz_ai/v2_a0.py | New frozen A-only DTO/replay/projection/path handler and pure historical policy bridge; no writer. Intentional frozen duplication avoids interpreting old history with changed live semantics. |
| grundschutz_ai/v2_ledger.py | Module docstring only; points to separate historical API and changes current descriptor so A0 cannot obtain current writer authority. |
| tests/a0_oracle.py | Independent, strict A checkout verifier/public-API fixture producer and immutable manifest/export harness. |
| tests/fixtures/a0-ledger.sql | Literal synthetic A-produced SQL transport; no binary DB. |
| tests/test_v2_compat.py | 43 new offline/security/cross-version tests. |
| docs/decisions/0010-historical-implementation-compatibility.md | Minimal status/section-10 clarification of actual Gate A bridge and proof; other gates unchanged. |
| docs/tasks/TASK-0073B1-RESULTS.md | This report. |

No modifications to v1 storage, domain, extraction, support, validation, readers/stagers, v2 codec/schema or existing tests. No dependencies, installations/downloads, network/model calls, company documents, BSI baseline changes, migrations or automatic Git commit.

Final captured repository-root short status:

```text
 M Grundschutz-AI/docs/decisions/0010-historical-implementation-compatibility.md
 M Grundschutz-AI/grundschutz_ai/v2_ledger.py
?? Grundschutz-AI/docs/tasks/TASK-0073B1-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/v2_a0.py
?? Grundschutz-AI/grundschutz_ai/v2_compat.py
?? Grundschutz-AI/tests/a0_oracle.py
?? Grundschutz-AI/tests/fixtures/a0-ledger.sql
?? Grundschutz-AI/tests/test_v2_compat.py
```

Nothing staged/committed; HEAD unchanged. No registered extra worktree or archive scratch file remains. The path below the temporary root, not a tracked path, holds the authentic DB.

## Exact reproduction

Run from this **LF-packaged** application tree with the exact reviewed runtime. Existing original oracle retained in this session:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
py -3.12 -m unittest tests.test_v2_compat -v
py -3.12 -m unittest discover -s tests
```

To rebuild independently from the immutable A commit when that temporary oracle is unavailable:

```powershell
Set-Location Y:/Grundschutz-AI
$compatRoot = Join-Path $env:TEMP ("grundschutz-ai-a0-review-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $compatRoot | Out-Null
# Scratch export is an unused temporary file; do not overwrite an existing one.
$compatArchive = Join-Path (Get-Location) (".task0073b1-" + [guid]::NewGuid().ToString("N") + ".tar")
git -c core.autocrlf=false archive --format=tar --output=$compatArchive 2ee9bc7
$compatCheckout = Join-Path $compatRoot "checkout"
@'
from pathlib import Path
import sys, tarfile
archive, target = map(Path, sys.argv[1:])
with tarfile.open(archive) as stream:
    stream.extractall(target, filter="data")
archive.unlink()
'@ | py -3.12 - $compatArchive $compatCheckout

Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$compatOutput = Join-Path $compatRoot "fixture"
py -3.12 tests/a0_oracle.py --checkout (Join-Path $compatCheckout "Grundschutz-AI") --output $compatOutput
# Stop here if the strict A0 harness fails; never substitute a B-created DB.
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
$env:GRUNDSCHUTZ_A0_ORACLE = Join-Path $compatOutput "oracle.sqlite"
py -3.12 -m unittest tests.test_v2_compat -v
py -3.12 -m unittest discover -s tests

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai/storage.py Grundschutz-AI/grundschutz_ai/domain.py Grundschutz-AI/grundschutz_ai/v2_codec.py Grundschutz-AI/grundschutz_ai/v2_schema.py
```

The harness refuses mismatched bytes/runtime/schema/policies before creating its DB. Physical DB bytes are a pinned fixture artifact under this exact environment; the complete logical manifest and literal history are the semantic oracle. A different SQLite physical layout is not silently accepted as this original-file proof.

## Remaining limitations and activation boundary

Only the exact two A0 descriptors, LF artifact bundle and exact Windows/Python/SQLite host tuple are supported. Changing any pinned shared file, runtime or packaging refuses loading; compatibility with other versions requires a new explicitly reviewed bridge. The handler intentionally duplicates frozen A read semantics, so future fixes require reviewing/pinning this artifact and rerunning authentic fixtures, not altering old identities.

Replay is cooperative/time-bounded as in A, not a hard CPU/RSS sandbox. Gate A performs no Office parsing or native manifest validation. It cannot authenticate actors/sources, prove corpus completeness/real-world truth, detect a wholly replaced self-consistent unsigned history, or resolve B write-schema and native-reader semantics. The caller must supply a trusted local path; there is no database/network discovery.

**source.validated, persistent candidates/scopes, human queue replay, approvals, Evidence/Inventory/ReviewRecord materialization, approved export, PDF promotion and migration remain disabled.** No schema or event codec was added. Gates B/C/D are not activated by recognition or this technical result.

Next step: human review of Gate A and its authentic oracle. Any Gate B work needs a separate explicit task and the outstanding native-golden/write-profile/state-machine review; this task stops at TASK-007.3B.1.
