# TASK-007.3B.2.4.1 — Recovery trust prerequisites and external checkpoint proof

## Result and scope

**READY FOR CONTRACT REVIEW; NOT_OPERATIONALLY_AUTHORIZED for every production
recovery request.** [ADR-0012's proposed addendum](../decisions/0012-schema3-crash-recovery-contract.md#proposed-addendum-task-0073b241-trust-prerequisites)
defines the exact checkpoint, custody, maintenance prerequisite and decision
matrices. ADR-0012 remains **PROPOSED**. No production recovery, checkpoint writer,
authentication, adoption or new approval pathway was implemented.

**R1 correction:** the original custody decision compared the joint byte manifest
but omitted comparisons of acquired file IDs, store UUID and committed checkpoint
head. Its original positive result did not establish those bindings. The
TASK-007.3B.2.4.1-R1 section below records the correction and current acceptance
run; the original execution results are retained as historical observations.

Required/actual clean starting HEAD and final HEAD:
**d40d7b19aff3781dc19dcd8733c4b081c5f85a30**. Repository `Y:/Grundschutz-AI`;
application `Y:/Grundschutz-AI/Grundschutz-AI`. Only owned disposable synthetic
fixtures outside Git were examined. No network, dependency/model installation,
company documents, ACL/security/Git configuration changes, staging or commits.

Changed files:

- ADR-0012: appended explicitly proposed contract; original contract retained.
- [tests/test_v3_recovery_trust.py](../../tests/test_v3_recovery_trust.py): test-only
  public-credential checkpoint/witness/custody/grant prototypes and 32 regressions
  (26 original plus six R1 regressions).
  No application import, operator CLI, public recovery interface or secret file.
- This report.

All production modules, frozen v2/A0 code, existing tests, historical fixtures,
native bridge/handler identities, physical schema, canonical event codecs and
capture-only semantics remain unchanged. Existing application loaders still
refuse journal/WAL/SHM before connecting. PENDING/FAILED remain the only capture
states; no source.validated, replacement event, fabricated missing BLOB,
inventory, review, export, migration or later Gate B work was introduced.

## Independent history experiment

The external checkpoint binds exact store/schema/profile, sequence/event hash,
event/transaction ID, registry/policy epochs, current SourceRefs, retained capture
references and BLOB digests/lengths, UTC observation/recording metadata, issuer,
authorization context and authority epoch. Exact types/fields/canonical bounds
are specified in the ADR. It deliberately does **not** substitute a database-file
hash for an independently acknowledged committed head.

The test observer retains checkpoints separately in test-process memory, outside
the fixture SQLite files and evidence directories. An ordinal/hash-linked chain
and separately challenge-bound latest-head witness detect missing/stale records.
This separation is a **test assumption**, not an independently controlled security
domain. Public HMAC keys (bytes 0..31 and 32..63) exercise binding/refusal only;
anyone can forge them. No actual key, operator, trust root or service was invented.
Operational authenticity, custody, revocation and freshness remain BLOCKED.
Timestamps are audit metadata; freshness requires the independent authority's
current response to a new examiner challenge. Static literal-test challenges
must never be reused as real examination nonces.

| Actual synthetic experiment | Observed diagnostic result |
|---|---|
| Clean committed copy and independently retained matching head | TRUST_PREREQUISITES_VERIFIED for history only. Full unchanged replay matches. |
| Genuine interrupted hot capture, copy-only SQLite rollback | Uncommitted capture/event/BLOB absent; committed STARTED head retained; original earlier PENDING capture bytes preserved. Exact checkpoint matches. |
| Capture commit succeeded but client acknowledgement lost | Candidate has 10 events versus externally observed 9: INCOMPLETE_EVIDENCE. Separate exact command intent identifies the committed capture; no checkpoint/client acknowledgement or database mutation is generated. Wrong BLOB intent refuses. |
| Independent observer separately observes the complete commit | 10-event ledger matches exact second checkpoint; captured bytes remain PENDING. This is an explicit test observation, never an automatic response to mismatch. |
| Self-consistent 9-event predecessor against current 10-event checkpoint | CONFLICTING_EVIDENCE: missing committed suffix, despite successful internal replay. No partial-prefix acceptance. |
| Two valid forks with same store UUID and sequence, different events | CONFLICTING_EVIDENCE. No branch selected automatically. |
| Altered checkpoint, valid outsider MAC, changed transaction/head/capture/source reference | CONFLICTING_EVIDENCE. Internally valid syntax/hashes cannot enroll an authority. |
| Missing checkpoint/witness, ordinal gap, stale chain against current witness, old challenge | INCOMPLETE_EVIDENCE. Unknown authority epoch conflicts. |
| Forged future timestamp / authenticated future timestamp without witness | Invalid MAC conflicts; authentic audit time alone remains INCOMPLETE_EVIDENCE. Neither proves freshness. |
| Identical source bytes captured under different registrations | Same BLOB digest, distinct SourceRefs/events. No identity substitution. |
| Newer uncaptured STARTED revision after captured PENDING revision | Newest SourceRef remains current; older captured candidate conflicts with newer checkpoint and cannot be used as fallback. |

In the deterministic post-commit fixture, the acknowledged earlier head is
sequence **9**, event hash
`5574fc047c06bbf118824837aaa941c0465daa3097c1aef46050abb49de97097`;
the complete commit is sequence **10**, event hash
`51ebd38912eb7c092097e1282c3e15a84caaac271b4d712c8dabc7a28b8197dd`.
Old captured bytes are **42** bytes, SHA-256
`a1abab51aa326d76d1431e636a5ff3d4b5b99dce8fa77763986fbfb2f97bffff`;
new captured bytes are **528,384** bytes, SHA-256
`6def82774045b76e4ff723d04be1f996d115f65e6df78e96279f04eb3850f8f6`.
No observed capture becomes VALID or approved. Mismatch/reconciliation functions
are pure diagnostics; lost-ack tests also compare unchanged candidate bytes,
full state and checkpoint collection. Every fixture test rechecks original and
sealed bundle equality in teardown, including negative cases.

## Literal vectors and independent calculation

The test file contains complete literal canonical UTF-8 bytes `LITERAL_9` and
`LITERAL_10`, not expectations generated during the assertions. They are frozen
from the deterministic genuine committed histories and tested against a new
replay. PowerShell/.NET separately computes SHA-256 and public-test HMAC over
those literal bytes without importing the checkpoint factory/serializer/signing
helper. A second unit test verifies the two literals with the factory disabled.
These calculations verify representation/binding, not external authenticity.

| Literal | Bytes | SHA-256 |
|---|---:|---|
| LITERAL_9 | 1,670 | `3d1e6d0cee2496c1e7cd5dfd7884202065d19bb2147ebc0082d1a373b07c5d89` |
| LITERAL_10 | 1,981 | `fe723bd92d71c0492e80946caa12c8bedb23e5ac8ee9d96d091dc18b21606e2f` |

HMAC-SHA256 preimage is ASCII `checkpoint`, one NUL byte, then the literal bytes;
public key is byte values 0..31. Independently observed MACs:

```text
LITERAL_9  c5686427f8d5aec58cdc09d0294f3b46e75b371a20c468cbd0f104ccf81d851b
LITERAL_10 19bab497dd32ee7327e0ee8b618fa65cbf34c20c56f79bc0cbc115042e219fb6
```

## Operator, custody and association evidence

| Adversarial proof | Actual enforcement / remaining assumption |
|---|---|
| Missing/bad operator grant, wrong store/action/role/challenge | Refused before acquisition. Public-test grant only; no real identity or authorization infrastructure. |
| Missing/revoked maintenance flag | Refused. Flag is a simulated application policy service, not an OS-enforced maintenance lease. |
| Live SQLite BEGIN IMMEDIATE writer | Exclusive read acquisition refused by Windows. Writer is an owned fixture connection. |
| Separate owned process holding incompatible file handle | Acquisition refused; child released/reaped under bounded waits. No unrelated process stopped. |
| Second member unavailable after first acquired | Entire acquisition refused; test confirms first handle released. No partial bundle returned. |
| Writer process attempts restart while acquisition handle held | Windows denies SQLite opening/writing; no change. Denial ends when handle closes and does not implement persistent restart inhibition. |
| Equal-byte journal replacement during acquisition | Existing before-open/held-file identity comparison refuses before returning a bundle. Only a disposable acquisition copy is replaced. |
| Unexpected member or hard-linked alias | Acquisition refused. No ignored member or silently followed alias. |
| Missing/truncated/transplanted/stale journal versus independently retained exact bundle | CONFLICTING_EVIDENCE; no SQLite probe called. Original/sealed artifacts retained unchanged. |
| No independent producer trace, even with plausible/signed local manifest | QUARANTINED_UNKNOWN. SHA/header/checksum/name is not provenance. |
| Known association but missing custody proof | INCOMPLETE_EVIDENCE. |
| Trace permits ATTACH/super-journal, unknown producer mode or WAL | QUARANTINED_UNKNOWN before journal interpretation. No hostile journal parser added. |
| All positive synthetic prerequisites, request for production recovery | NOT_OPERATIONALLY_AUTHORIZED unconditionally. Diagnostic success is not a permission. |

The custody prototype binds exact joint bundle/member hashes, original file IDs,
case/store/checkpoint identity, known controlled producer code/exit trace, DELETE
journal mode/no ATTACH, and pinned SQLite source ID. Its independently retained
expected trace is an assumption outside attacker-supplied files. A self-signed
manifest or authenticated statement by an untrusted producer cannot establish
association. The tests neither enumerate all Windows writers nor implement
continuous custody or a hostile-worker sandbox. Unknown physical cases never
reach a new SQLite engine pathway.

## Runtime and unchanged identities

Observed Windows 11 / Python **3.12.6** / SQLite **3.45.3**, fixed local **C: / NTFS**
temp fixtures (GetVolumeInformationW rechecked). The reused harness checks exact runtime and loaded sqlite3.dll path,
not merely an arbitrary DLL found on disk. SQLite source ID:

```text
2024-04-15 13:34:05 8653b758870e6ef0c98d46b3ace27849054af85da891eb121e9aaa537f1e8355
```

| Artifact | SHA-256 |
|---|---|
| C:/Python312/python.exe | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| C:/Python312/DLLs/_sqlite3.pyd | `fdeacc2aff71fe21d7a0de0603388299fa203c2692fdbdb3709f1bc4cc9cdc0e` |
| C:/Python312/DLLs/sqlite3.dll | `054a7b736de7afbd447b07ee5e72df2febcaa06758f7a028873771567e8735d3` |
| Physical schema-3 fingerprint | `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c` |
| a0-docx-native/v1 handler Spec | `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` |
| a0-xlsx-native/v1 handler Spec | `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` |
| Native literal golden fixture | `553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b` |
| Original historical A-created SQLite oracle | `5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537` |

## Original execution verification results (before R1)

Complete Python 3.12.6 offline suite: **906 tests run in 231.038 seconds;
901 passed, 5 existing optional Ollama tests skipped, 0 failures/errors**.
All **875 previous offline passes** and **26 new regressions** pass. The original
A-created database cross-version proof and the original historical native
producer proof were both enabled and passed; all seven native golden cases
passed. The five skips are model integration opt-ins, not historical proofs.

First development run: 24 tests, 23 passed and one error. The identity-change
proof expected the outer diagnostic refusal, but the unchanged existing forensic
guard detected replacement earlier and raised its own Blocked exception. The
assertion was corrected to require that earlier refusal; it was not changed to
accept replacement. Targeted verification of that test and both newly frozen
literal-vector tests: **3 passed in 4.537 seconds**. The final full run above
includes all 26 new tests successfully. No unresolved test failures remain.

Independent .NET vector calculations returned the exact lengths/SHA/MAC values
listed above. Runtime/schema/handler/oracle identities were rechecked unchanged.
`git diff --exit-code -- Grundschutz-AI/grundschutz_ai Grundschutz-AI/tests/fixtures`
passes, confirming no production/fixture edits. `git diff --check` passes; new
UTF-8/LF files are separately checked for syntax/whitespace/link validity.
Git emits its existing LF-to-CRLF informational warning for the Markdown ADR;
no Git setting or hashed production source was changed.

## TASK-007.3B.2.4.1-R1 — Synthetic custody binding correction

R1 began at the same HEAD `d40d7b19aff3781dc19dcd8733c4b081c5f85a30` with the
three original task deliverables already uncommitted (one modified ADR, this
untracked report and the untracked test module). Only those permitted files were
edited. The clean-start statement above describes the original task, not R1.

Root cause: the original provenance() verified syntactic UUID/digest fields and
the signed byte manifest, but ignored file_ids and never compared store_uuid or
checkpoint_head_sha256 with independently verified history. Its acquisition
wrapper returned only a Bundle and accepted caller-supplied expected IDs. Thus
equal-byte copies and valid synthetic records for the wrong store/head could
pass the custody-only decision. This was a gap in the synthetic proof, not a
production recovery feature.

Only this test module, ADR-0012 and this report changed for R1:

- acquire_diagnostic() now observes exact member name/device/inode/length from
  os.fstat on the same protected Windows share=0 read handles used by the unchanged
  forensic acquisition. It returns immutable AcquiredEvidence with bundle and
  observed file IDs, and compares internal pre/held/post identities and member
  inventories. Caller-provided identity tuples are no longer an input. All
  existing Windows path/file/size/exclusivity checks remain in force.
- custody_record() records identities through that protected acquisition too.
- provenance() requires protected observations plus separately retained expected
  custody, verifies checkpoint chain/current witness and reconciles the replayed
  store, then compares custody file_ids, store_uuid and checkpoint_head_sha256
  against the acquired identities, verified checkpoint and actual replayed head.
  Existing producer, manifest, hash and unsupported-structure checks remain.
- Six regressions cover equal-byte/different-ID acquisition, valid synthetic
  records for another store and another genuinely committed head, changed/missing
  observed IDs, actual member disappearance after the protected read, and refusal
  of bytes/caller identity tuples/local signatures without independent custody
  and verified checkpoint evidence. Existing replacement-during-acquisition and
  writer/partial-acquisition/restart tests retain their refusal expectations.

The synthetic custody/observer roles and their independently retained expected
records remain **assumptions** within one test process. Public test HMACs and
AcquiredEvidence instances are not real credentials or independent authority.
Matching a locally created signature/manifest/identity tuple alone supplies no
such authority. No operational independent checkpoint/custodian, protected audit,
authentication or continuous custody is implemented; all six production blockers
below remain. **Production recovery is NOT_OPERATIONALLY_AUTHORIZED**, including
after a positive synthetic result. ADR-0012 remains **PROPOSED**.

R1 focused run: **32 tests passed in 66.597 seconds; no failures/errors/skips**.
This includes all 26 original trust regressions and six new correction tests.

| New R1 regression | Observed result |
|---|---|
| Original versus protected-acquired equal-byte copy | Original matches; copy has different OS file identities and yields CONFLICTING_EVIDENCE. |
| Valid public-test custody record naming another store UUID | CONFLICTING_EVIDENCE despite valid synthetic MAC and otherwise matching bytes/IDs. |
| Valid custody record naming the preceding genuinely committed event head | CONFLICTING_EVIDENCE against independently verified current checkpoint/head. |
| Changed or missing acquired member identity tuples | CONFLICTING_EVIDENCE; no partial set qualifies. |
| Journal moved out of an owned acquisition copy after protected read, before post-check | Acquisition refuses with CONFLICTING_EVIDENCE; original/sealed evidence untouched. |
| Local signature/bytes/caller identity tuple without required independent context | Missing retained trace yields QUARANTINED_UNKNOWN; raw bundle/tuples or missing verified checkpoint/witness yield INCOMPLETE_EVIDENCE. |

R1 full Python 3.12.6 offline acceptance: **912 tests run in 245.350 seconds;
907 passed, 5 optional Ollama skips, 0 failures/errors**, exit code 0. All **901
previous offline passes plus six new regressions** pass. **Historical skips: 0**;
both original historical proofs were enabled and passed. All seven native golden
cases passed. No unresolved test failures remain.

The unchanged Windows forensic acquisition, original/sealed bundle comparisons,
schema/codec/native/history tests and production refusal all remain exercised.
`git diff --check` and the production/fixture/forensic-harness diff checks pass.
Final Git HEAD remains `d40d7b19aff3781dc19dcd8733c4b081c5f85a30`; the exact
three-file status is listed below. No files staged or committed. Artifact
SHA-256 values below are updated for R1; this report's final digest is supplied
separately in the completion response to avoid a self-referential digest.

## Reproduction commands

PowerShell, existing reviewed runtime and independently retained original
historical artifacts (both paths verified present for this run):

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = '0'
$env:GRUNDSCHUTZ_A0_ORACLE = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite'
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = 'C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI'
py -3.12 -m unittest tests.test_v3_recovery_trust -v
py -3.12 -m unittest discover -s tests -v
```

If historical temporary artifacts have expired, use the unchanged exact
`2ee9bc7cf309727e5a9f10e2982791dbc991c464` Git-archive/original-producer commands
in [TASK-0073B20-RESULTS](TASK-0073B20-RESULTS.md#exact-reproduction).
Never manufacture a current-writer replacement oracle. The two independent
proofs must execute, not skip, for equivalent acceptance.

Independent .NET calculation, no prototype imports:

```powershell
$lines = Get-Content tests/test_v3_recovery_trust.py
foreach ($line in $lines) {
    if ($line -match "^LITERAL_(9|10) = b'(.*)'$") {
        $number = $Matches[1]
        $raw = [Text.Encoding]::UTF8.GetBytes($Matches[2])
        $sha = [Security.Cryptography.SHA256]::Create()
        $mac = New-Object Security.Cryptography.HMACSHA256
        try {
            $mac.Key = [byte[]](0..31)
            $preimage = [Text.Encoding]::ASCII.GetBytes("checkpoint" + [char]0) + $raw
            $digest = [BitConverter]::ToString($sha.ComputeHash($raw)).Replace('-','').ToLowerInvariant()
            $tag = [BitConverter]::ToString($mac.ComputeHash($preimage)).Replace('-','').ToLowerInvariant()
            Write-Output "$number $($raw.Length) $digest $tag"
        } finally { $sha.Dispose(); $mac.Dispose() }
    }
}

Get-FileHash -Algorithm SHA256 -LiteralPath tests/test_v3_recovery_trust.py,docs/decisions/0012-schema3-crash-recovery-contract.md,docs/tasks/TASK-0073B241-RESULTS.md
Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai Grundschutz-AI/tests/fixtures
```

## Exact continued blockers

1. No real independent authenticated checkpoint issuer/custodian, enrolled trust
   root, nonrollbackable latest-head service, challenge/epoch/key lifecycle or
   independently retained authenticated command/audit record.
2. No authenticated/authorized operator infrastructure or durable, independently
   audited maintenance/restart interlock covering all writers/services.
3. No production initial provenance/association proof or continuous protected
   namespace/file custody through acquisition, experiments and future adoption.
4. No confined resource-bounded hostile-journal worker or super-journal/path
   handling. WAL/SHM, unknown/missing association, unsupported physical cases and
   runtime changes remain quarantined; no general recovery parser was created.
5. No reviewed human adoption, no-overwrite publication, identity recheck,
   rollback-retention and restart protocol. Production recovery still cannot be
   invoked through an application API.
6. Process-exit tests on fixed local NTFS do not qualify ReFS, arbitrary volumes,
   power loss, torn writes/controller caches or privileged filesystem attackers.

No prerequisite alone is sufficient. Even all synthetic positives leave these
blockers intact. Stop at this contract/proof task; human contract review is the
next step, with no subsequent implementation started.

## Artifact identities and Git status

| Reviewed artifact bytes | SHA-256 |
|---|---|
| tests/test_v3_recovery_trust.py (R1) | `59b35840f610149fa568f0be966cf5122c3e136b3e385c846c0e6d6e2408ef58` |
| ADR-0012 including proposed addendum and R1 correction | `7ff3c1d5455537288cd4ca7f843abc07daf29bd89d7ab3e23f1a4a981c8ab88c` |

This report's final SHA-256 is supplied in the completion response and can be
recomputed above; it cannot embed its own final digest. No binary evidence or
credential file is added to Git.

```text
 M Grundschutz-AI/docs/decisions/0012-schema3-crash-recovery-contract.md
?? Grundschutz-AI/docs/tasks/TASK-0073B241-RESULTS.md
?? Grundschutz-AI/tests/test_v3_recovery_trust.py
```
