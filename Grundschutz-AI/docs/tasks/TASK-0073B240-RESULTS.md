# TASK-007.3B.2.4.0 — Crash recovery contract and synthetic forensic proof

## Result

**Contract and controlled synthetic proof complete; READY FOR CONTRACT REVIEW.**
[ADR-0012](../decisions/0012-schema3-crash-recovery-contract.md) is **PROPOSED**, not
accepted for operational recovery. No production recovery, repair, journal cleanup,
adoption or trusted-loader change was implemented.

Required/actual clean starting HEAD and final HEAD:
**b70ed93bff0237dae3dd3e1f3106658d0c7641cd**. Repository `Y:/Grundschutz-AI`;
application `Y:/Grundschutz-AI/Grundschutz-AI`. Only synthetic owned fixtures were
accessed. No dependencies, downloads, network/model/company-document access,
security/Git setting changes, staging or commits.

## Deliverables and unchanged boundaries

Exactly three new files:

- [ADR-0012](../decisions/0012-schema3-crash-recovery-contract.md): proposed operator
  authority, custody, copy-only engine operations, decision/interruption matrix,
  full replay, human adoption gate and explicit blockers.
- [test_v3_recovery_forensics.py](../../tests/test_v3_recovery_forensics.py): isolated
  test-only fixture producer, exclusive read acquisition, independent copies,
  diagnostic probes and 27 focused regressions. Not imported by application code,
  not an operator CLI, and not a generic recovery API.
- This report: exact observations, identities, checks and reproduction.

No tracked file changed. Existing production modules, current ledger/store tests,
native handler modules/catalog/artifact hashes, frozen schema-2 handler/oracle and
all historical goldens remain unchanged. The existing application still refuses
`-journal`, `-wal` and `-shm` before opening a SQLite connection. The old
initialized-only API remains genesis-only; the capture ledger remains PENDING/
capture-FAILED only. No source.validated, VALID, derivation, candidate, inventory,
queue, review, approval, export or migration feature was added.

Schema fingerprint remains exactly:
`75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c`.

## Reviewed local runtime and filesystem

Python **3.12.6**, Windows 11, SQLite **3.45.3**; actual temporary fixture volume
**C: / NTFS**, fixed local storage. Existing application NTFS/ReFS admission was
not changed, but **ReFS recovery was not demonstrated**.

Observed SQLite source identity, queried from the loaded engine:

```text
2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355
```

| Loaded runtime artifact | SHA-256 |
|---|---|
| `C:/Python312/python.exe` | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| `C:/Python312/DLLs/_sqlite3.pyd` | `fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e` |
| `C:/Python312/DLLs/sqlite3.dll` | `054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3` |

The test queries the actual loaded `sqlite3.dll` path with Windows
GetModuleHandleW/GetModuleFileNameW, checks the source ID and these literal hashes,
and refuses another runtime. This is not complete OS/stdlib authentication.
Page size was **4,096 bytes**; default cache setting **-2000** (SQLite's negative
KiB cache setting). Test-only hot cases set cache_size=2 and cache_spill=ON on
their disposable writer connection. Existing DELETE/FULL discipline remains.
Observed journal header sector field was **512 bytes**, not a claim about disk
physical-sector or power-loss atomicity.

## Controlled fixture and evidence acquisition

Each case is generated through the unchanged public schema-3 APIs in a fresh
`grundschutz-v3-recovery-forensics-*` local temporary directory outside Git.
There is one known producer process, deterministic UUID/time inputs and no native
reader or external service. Before the injected interruption, each public command
has closed its SQLite handles. A quiescent checkpoint copy is independently
verified by the application; it is the expected committed history, not a claimed
acquisition of an arbitrary live operational database.

Baseline sequence 8 contains an earlier **captured PENDING revision 1** and a
separate genuinely **FAILED capture** without invented bytes. Capture experiments
first commit a new main-source revision 2/start at sequence 9. Its capture would
be sequence 10. These retained states let the tests prove that recovery never
promotes PENDING, resets FAILED or falls back from the latest committed start.

After `os._exit`, the known producer has exited and is reaped. Before reading any
artifact, the harness acquires deny-sharing **read-only** Windows handles to all
recognized members. It checks local path ancestry, regular-file/single-link type,
reparse flags, identities, lengths and unchanged directory inventory. A live
SQLite writer and an ordinary existing reader both prevented acquisition in
tests; partial acquisition released already-held handles. No process is killed
to obtain access and no ACL or security setting is changed.

Artifacts are read together, hashed, retained as exact bytes in a sealed copy,
then copied to fresh independent working files with original relative basenames.
Copies are verified byte for byte and have different NTFS file identities; they
are not hard links. Original/sealed bytes and SHA-256 are rechecked after engine
operations and rejection cases. Unknown extra files stop acquisition; WAL/SHM
bytes may be retained as evidence but block this recovery profile.

No original database or journal is opened writable by the recovery experiments.
The live-writer rejection test deliberately establishes a competing read/write
transaction with **no data changes** before attempting acquisition; that is a
controlled concurrency fixture, not a recovery write. Intentional corruption
tests alter only separate diagnostic copies. Temporary synthetic artifacts are
removed at test teardown; the experiment does not implement long-term forensic
custody/retention for operational stores. No binary fixture enters Git.

## Observed interruption matrix

| Case / child exit | Main changed from its own checkpoint? | Sidecar observation | Ordinary load | Qualified copy result |
|---|---|---|---|---|
| Before BEGIN / 61 | No | No journal | Accepted by full replay | Exact sequence 8; no new intent. |
| Empty open transaction / 62 | No | No journal | Accepted by full replay | Exact sequence 8; no new registration. |
| During registration / 63 | No | Residual journal, first magic bytes zero, first record count 0 | Refused | Read-only backup candidate, exact sequence 8. |
| During capture without spill / 64 | No | Residual journal, first magic bytes zero, first record count 0 | Refused | Read-only backup candidate, exact sequence 9; newest start uncaptured PENDING. |
| After uncommitted page spill / 65 | Yes | Genuine rollback-required journal | Refused | Engine rollback on working copy, exact sequence 9. |
| During capture with spill / 66 | Yes | Genuine rollback-required journal | Refused | Event/raw BLOB/mirror changes rolled back together; exact sequence 9. |
| COMMIT succeeded, caller acknowledgement lost / 67 | Yes | No residual journal | Accepted by full replay | Complete sequence 10, exact new captured bytes, still PENDING. |

The no-sidecar cases demonstrate that ordinary loading is not universally blocked
after an exit. When a sidecar exists, both ordinary loaders refuse before their
SQLite connection factory, without attempting rollback or deleting anything.
Every copy outcome requires full replay and comparison with the independently
verified expected committed checkpoint/known producer outcome. Process exit is
an observation; it is **not a simulated power cut**.

### Genuine hot-journal evidence

Both spilled cases were created by actual SQLite page-cache spill, not hand-built
journal bytes. Their main files changed before COMMIT. First journal magic was
`d9d505f920a163d7`; first segment record count **2**, original page count **65**,
sector field **512**, page size **4096**. More than one journal header/segment may
exist; the test records the first header, not a complete hostile-journal parse.

A `mode=ro` engine read on a working copy returned extended error **776 /
SQLITE_READONLY_ROLLBACK**, leaving the copy unchanged. An explicitly requested
`mode=rw` read transaction on that qualified disposable copy, with query_only=ON
and trusted_schema=OFF, allowed **SQLite itself** to perform rollback and remove
only that working copy's journal. No recovery UPDATE, DDL or replacement event
was issued. Integrity then passed and full application replay exactly reproduced
sequence 9, all source states/counters/heads and retained original bytes.

Classification follows the known producer, spill, absent live writer, engine
error and exact rollback outcome together. Magic, filename or nonzero size alone
never classifies an arbitrary journal as hot, applicable or safe.

### Non-hot residual evidence

For the two non-spilled uncommitted cases, the main file was byte-identical to
its own committed checkpoint. A read-only SQLite integrity check succeeded and
left the residual journal byte-identical. The application correctly continued
to refuse that journal-bearing view.

On a **qualified copy only**, the SQLite backup API read its database through a
mode=ro/query_only source and wrote to a separate fresh, exclusively created
candidate. It did not clear/write/delete the source journal. Full application
replay of the sidecar-free candidate matched the checkpoint exactly. This is a
logical backup candidate, not rollback of a non-hot journal and not proof that
an unknown/stale journal can be ignored. No UPDATE designed to dirty a page and
clear a journal was used. The previous TASK-0073B23 fixture helper remains
unchanged historical test code; it is expressly **not this proposed procedure**.

## Exact pre-recovery artifact observations

The following are exact measurements from one complete seven-case run. Each
experiment seals/rechecks its **own** bytes, lengths and hashes. SQLite journal
seeds are random; physical database layout can also differ despite identical
logical history (including process-dependent row insertion order). These are
recorded evidence identities, **not expected fixed golden hashes across runs**.
Reproduction regenerates new disposable cases and checks their own exact custody.

| Case | Main bytes / SHA-256 | Journal bytes / SHA-256 |
|---|---|---|
| before-begin | 258048 / `d2ec653be641480c17c327f59e706108133ead7dfc7323904e53095200e7f642` | absent |
| open-transaction | 258048 / `8edfe7e42a312ad68642de63bc5e264aed55d8e747799d0c9de123ce65817116` | absent |
| registration-uncommitted | 258048 / `d2ec653be641480c17c327f59e706108133ead7dfc7323904e53095200e7f642` | 66176 / `15cd6a54e82a51d4c74c2049faac849a19acbb42395e91daeaea2a363e59c054` |
| capture-uncommitted | 266240 / `54234eb63bb6e369fb70e0d511f96cd7408583bd6563c6d2d4d0bc0a90cec6fc` | 57968 / `57d5fb629fba21cfa7542808c16d817c7ec9e1f87aab0bc64b514c4bda8ba9c9` |
| page-spill | 786432 / `94aa325e4923efc218406dd9f120bf39155874c658cbbd759d9c3f44791870d6` | 13832 / `bb92e14a05f0eb1d1e8a07398a81cdd609b30fd155d20838e678126b04e26b0b` |
| hot-capture | 794624 / `4117a582e9249f3b788713b6ad591d69c740d2a434cf7c7394fff6843ea78d6f` | 60960 / `2a320e989d0c0e790fee1a291df8c914c372c1af0eb57553985616b137cf8525` |
| post-commit | 794624 / `c655105d8333fef4f8bcbf4e0477107d395fbca0c66bbd6b9883944350891b7b` | absent |

The test's bundle SHA-256 covers the exact JSON array of sorted
`[name,length,sha256]` triples, compact UTF-8, no final newline. This is diagnostic
custody metadata, not a new ledger codec or authenticated signature.

| Case | Bundle SHA-256 |
|---|---|
| before-begin | `91304c4eb1475949690a81e0bb6cdf9ec1b83e15ca40e2291757e1e3c5739ea5` |
| open-transaction | `94af616d2a350fb53e8841ecf0cc53086a00128b01e536cf542f450773bda651` |
| registration-uncommitted | `342e81f3de800d02e1dde184e844d192a0f47f03cee8b2336ed0d936e191d20f` |
| capture-uncommitted | `2e82f64a20e8bf6d1d0ceee842a225abe27c2882ec1c3b2145a2559a505000e2` |
| page-spill | `ed6344404f3b47de122c3a6b050d03a9a3c6e6b92038189b9bb37fb3612b5f3a` |
| hot-capture | `ee8dc6018856ce4a95326c5db8d82ee46081caa4cfbcf9a1f7a6e6dbc05c5b3a` |
| post-commit | `0be99c3e276ed0e47e5d88946f493e20a817fa32b286c9d51566bba396754f1b` |

Replayed event-head hashes were stable logical outcomes for the fixed synthetic
UUID/time trace:

- Sequence 8: `2c668ab8c303f10878a46ab253a68ce02ea42b96c8a95d511a0112f1318657e7`.
- Sequence 9: `5574fc047c06bbf118824837aaa941c0465daa3097c1aef46050abb49de97097`.
- Sequence 10: `51ebd38912eb7c092097e1282c3e15a84caaac271b4d712c8dabc7a28b8197dd`.

Retained original-BLOB SHA-256:
`a1abab51aa326d76d1431e636a5ff3d4b5b99dce8fa77763986fbfb2f97bffff`.
Only the postcommit case retained the additional 524,288-byte capture,
`6def82774045b76e4ff723d04be1f996d115f65e6df78e96279f04eb3850f8f6`.
The tests compare exact bytes, not just these digests. No PENDING source became
VALID and the earlier FAILED capture remained FAILED without a binary hash.

## Negative findings and fail-closed outcomes

- Missing/truncated header or body, changed and transplanted journals were blocked
  before engine interpretation when they disagreed with the independent sealed
  fixture/producer evidence. This is **not** a general journal-to-database binding
  parser. An initially corrupt bundle without such evidence is unknown and blocked.
- WAL/SHM bytes were preserved and rejected for recovery; unknown extra files
  stopped acquisition. No ignored sidecar or implicit mode conversion.
- A live SQLite writer or reader prevented exclusive acquisition. Hard links,
  relative/unsafe workspace paths and original-path engine targets were rejected.
- Copies with a forged registry projection, same-length corrupt original BLOB or
  missing committed event each returned `integrity_check = ok` but were rejected
  by full application replay. No repair/event/BLOB synthesis was attempted.
- A complete older checkpoint could pass full replay yet was the wrong known
  postcommit result. External head/command evidence detected the lost suffix;
  unauthenticated hash chains cannot independently establish freshness.
- Every successful result was diagnostic (`adopted=false`), with original and
  sealed bundles unchanged. No operational configuration/path was changed.
  Reopening a diagnostic PENDING store did not regain mutable-path capture authority.

## Test results

Complete Python 3.12.6 offline suite, with both authentic historical proof variables
present and their paths checked:

```text
Ran 880 tests in 177.656s

OK (skipped=5)
```

**875 passed, five skipped, zero failures/errors**. All 853 previous tests remain
passing (848 pass/five existing optional Ollama skips), plus **27 new passing
forensic tests**: seven real interruption cases, thirteen custody/suspicion tests
and seven replay/authority/runtime tests. The initial focused 26-test run passed
in 51.713s; one additional live-SQLite-writer acquisition test and tightened
test-helper path checks passed in the final full run. No new unresolved test failure.

The original A-created database cross-version proof and fresh historical native
producer proof both ran and passed, not skipped. All seven native goldens, native
artifact identities, schemas/codecs and previous store/capture semantics remain
unchanged. The five skips are only the existing optional Ollama tests; no model
was invoked. New-file syntax/UTF-8/LF/whitespace and documentation links are checked
separately; no existing test expectation was weakened or modified.

## Remaining blockers and guarantees not established

Production recovery remains **NOT READY** until separate review/implementation of:

1. Real operator authorization, maintenance interlock and proof that writers stay
   stopped across acquisition and any adoption. Exclusive Windows handles are a
   demonstrated control, not a complete administrative shutdown mechanism.
2. Trustworthy journal/database association, immutable acquisition custody and
   independent committed-head/command anchors. Initially missing/stale/unrelated
   journals cannot be authenticated from filename/header/checksum/hash chain alone.
3. A constrained, bounded recovery worker and hostile journal/super-journal/path
   threat review. No generic parser/sandbox or arbitrary corrupt-input recovery
   is supplied by this small known-producer test harness.
4. Explicit human adoption, no-overwrite publication/configuration switch, audit,
   evidence retention and restart protocol. No adoption command exists here.
5. Qualification of actual target storage beyond this NTFS process-exit experiment;
   ReFS, power loss, torn writes, hardware flush behavior, disk-full recovery and
   privileged filesystem attacks are unproven.

Observed: process exits, page spill, rollback-required engine error, successful
copy rollback/backup and exact replay/custody checks. Inferred contract
expectations: behavior for untested failure-event crash points and future
operational environments. No arbitrary power-loss durability, full filesystem
adversary resistance, authenticated recovery, production readiness or BSI claim.

## Exact reproduction commands

Run on the reviewed Windows/Python/SQLite/loaded-runtime profile. No dependencies
or external services are required:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest tests.test_v3_recovery_forensics -v

# Complete suite including both authentic historical proofs:
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI"
py -3.12 -m unittest discover -s tests
```

If the temporary historical artifacts expired, use the exact unchanged
Git-archive/A-public-API procedure in
[TASK-0073B20-RESULTS](TASK-0073B20-RESULTS.md). Never substitute a new-code
historical oracle or update old goldens.

Reproduce diagnostic runtime identities and seven-case observations on **new
disposable synthetic fixtures only**, never passing an operational path:

```powershell
@'
import json,tempfile
from pathlib import Path
from tests.test_v3_recovery_forensics import MODES,inspect_case,runtime_identity
with tempfile.TemporaryDirectory(prefix="grundschutz-v3-recovery-forensics-") as directory:
    root=Path(directory).resolve()
    cases=[inspect_case(root,mode) for mode in MODES]
    print(json.dumps({"runtime":runtime_identity(),"cases":cases},sort_keys=True))
'@ | py -3.12 -

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code
```

The diagnostic helper is test-only and deliberately restricted to owned private
temp fixtures. Do not use it as a production recovery instruction. It neither
deletes original journals nor adopts candidates. Production commands remain
unchanged; ADR-0012 must be separately reviewed and accepted before any follow-up.

## Git status

HEAD remains **b70ed93bff0237dae3dd3e1f3106658d0c7641cd**. No tracked changes,
staging or commits; exactly three new files:

```text
?? Grundschutz-AI/docs/decisions/0012-schema3-crash-recovery-contract.md
?? Grundschutz-AI/docs/tasks/TASK-0073B240-RESULTS.md
?? Grundschutz-AI/tests/test_v3_recovery_forensics.py
```

`git diff --exit-code` and `git diff --check` pass. This completes only
TASK-007.3B.2.4.0; next step is contract/security review of ADR-0012 and its
unresolved gates. No production recovery or later task was started.
