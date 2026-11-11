# ADR-0012 — Schema-3 crash recovery contract

**Status: PROPOSED, not accepted for production/operator use.** TASK-007.3B.2.4.0,
baseline `b70ed93bff0237dae3dd3e1f3106658d0c7641cd`. This document and the isolated
synthetic experiments add **no application recovery capability**. Actual results,
runtime/artifact identities and reproduction are in
[TASK-0073B240-RESULTS](../tasks/TASK-0073B240-RESULTS.md).

Predecessors: [ADR-0008](0008-document-proposal-boundary.md),
[ADR-0009](0009-structural-evidence-and-sqlite-v2.md),
[ADR-0010](0010-historical-implementation-compatibility.md),
[ADR-0011](0011-verified-source-validation-profile.md).

## Decision and exclusions

Propose a separately authorized, offline operator workflow: acquire an unchanged
evidence bundle after stopping writers, experiment only on independent copies,
require complete application replay and external history reconciliation, then
await an explicit human adoption decision. Do not modify the original store or
its sidecars, even if SQLite appears able to open it.

Ordinary loaders remain unchanged: any `-journal`, `-wal` or `-shm` blocks loading
before an application SQLite connection. No automatic rollback, journal deletion,
rename/truncation, SQL repair, migration, new event, missing-BLOB reconstruction,
policy/handler change or source-status promotion. The initialized-only loader
still refuses source history; the capture-only loader still refuses VALID,
derivations and later events. Schema fingerprint remains
`75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c`.

This is not a general SQLite recovery algorithm. The demonstrated profile is a
single schema-3 database, DELETE journaling, FULL synchronization, exact reviewed
SQLite/Python binaries and synthetic data on the tested local Windows NTFS volume.
No ATTACH, super-journal/multi-database transaction, WAL recovery, remote volume,
unknown journal provenance, encryption or damaged-file salvage is supported.
ReFS is allowed by existing application path rules but was **not tested here**;
it needs separate forensic validation. No production code or historical handler
is changed to widen these rules.

## Three distinct checks

1. **SQLite rollback:** the engine restores pages from a genuine applicable
   rollback journal on a disposable copy. This is physical transaction recovery,
   not application trust or proof that a journal belongs to a particular store.
2. **SQLite integrity:** `PRAGMA integrity_check` checks SQLite structural
   consistency. It does not establish the event chain, original-BLOB digests,
   correct projections, required committed suffix, or source authenticity.
3. **Application replay plus external reconciliation:** exact schema, codecs,
   event/BLOB/foreign-key/mirror/counter/head verification using the unchanged
   applicable loader, followed by comparison to independently retained committed
   heads/command evidence. Only this can qualify a diagnostic candidate within
   the known case; it still grants no operational adoption or inventory approval.

The experiments demonstrate genuine hot journals by **combined observations**:
an actual interrupted SQLite producer with no surviving producer handle; changed
uncommitted main-file pages; observed journal header; a read-only engine probe on
a copy failing with `SQLITE_READONLY_ROLLBACK` (776); and successful engine rollback
of another allowed working view to the complete independently verified checkpoint.
A filename, nonzero size, magic bytes or read-only success alone is insufficient.
No standalone general-purpose journal classifier is implemented.

## Operator authority and acquisition prerequisites

Before a future implementation touches evidence:

- An identified authorized operator declares a maintenance/recovery case, reason,
  scope, expected store identity, known outstanding commands and available last
  acknowledged committed head(s). Operator identity strings are not authentication;
  real authorization and custody must come from a separately approved control.
- Stop the application and every known writer/service, account for worker exits
  and close database handles. Maintain an interlock against restart throughout
  acquisition and any later adoption. Merely finding no PID, obtaining a SQLite
  lock once, or seeing a journal does not prove that no writer can reappear.
- Require an explicitly provided absolute local supported path outside Git,
  ordinary single-link regular files, no aliases/UNC/URI/ADS/reserved names,
  symlinks, junctions/reparse points or unexpected directory entries. A recovery
  workspace must be unused, operator-controlled and isolated from operational
  configuration. Do not create/delete other users' files or change ACL settings.
- Acquire deny-sharing **read-only Windows file handles for all known members**
  before reading any bytes. Failure must release all handles and stop, without
  killing a process or altering a file. Verify file identities/lengths and the
  member inventory while handles are held. These OS sharing controls help block
  ordinary concurrent access; they do not defeat raw disk access, a privileged
  attacker, every parent-directory race or a compromised kernel.

The synthetic harness proves rejection while a live SQLite writer holds a
transaction, as well as rejection of an existing reader and cleanup after partial
handle acquisition. Its known sole producer is reaped before acquisition. That
is evidence for this controlled fixture, not a universal proof that every service
on a real machine has stopped. A production maintenance interlock remains missing.

### Reuse of filesystem checks

Do not bypass/modify `v3_store._checked_path`, `v3_ledger` or frozen `v2_a0` to make
ordinary loading accept sidecars. The test harness reuses the unchanged A0
parent/volume/ancestry guard on a fixed absent sentinel in an owned temp directory,
then independently checks the fixed artifact leaves, links, file identities and
exclusive handles. This permits evidence retention of a WAL/SHM filename without
claiming that the corresponding database is loadable or recoverable.

A future operator tool needs its **own reviewed forensic path boundary** using
these same restrictions, without importing a historical writer or relaxing a
historical handler. The test's private-temp-name restriction is only a fixture
safety guard, not authentication of operational data or a production path API.

## Proposed procedure and decision states

### 1. EXAMINATION_BLOCKED or ACQUIRED_UNCHANGED

Inventory the exact main filename and possible exact `-journal`, `-wal`, `-shm`
companions. Unknown files, super-journal names, links, aliases, busy handles,
unsupported volume/runtime, incomplete custody or uncertain writer shutdown stop
the workflow. Preserve artifacts; do not silently discard, sweep or select a
subset to obtain a readable database. WAL/SHM are retainable forensic evidence
but explicitly unsupported for recovery in this profile.

Once quiescence and exclusive acquisition are established, copy the main file and
all relevant sidecars **together**, preserving their required relative basenames.
Record exact raw lengths and SHA-256, member list, file identities and the bundle
manifest. Use independent files, never hard links to the originals. Verify every
copy byte for byte and retain a sealed acquisition copy separate from working
copies. Recheck source inventory/identities/bytes; inconsistent acquisition blocks.

Proposed conservative admission limits, subject to separate implementation review:
at most four recognized members, 256 MiB/member and 512 MiB/bundle; all existing
application replay budgets remain in force. Over-limit or unexpected artifacts
require manual investigation, never truncation. Streaming acquisition, worker
deadlines/disk/RSS limits and failure audit durability need implementation review;
these limits do not assert a hard OS resource sandbox.

### 2. QUARANTINED_UNKNOWN or CONTROLLED_COPY_EXPERIMENT

The test's controlled single-producer trace and independently verified checkpoint
establish its case qualification. For an operational bundle, plausible headers
and consistent SHA-256 values are not equivalent provenance. Rollback journals
do not carry an authenticated application store UUID or committed event head.
Their random seed/checksums are not a cryptographic database association.

A missing, truncated, altered, transplanted, stale or unrelated journal is blocked
when detected from custody/producer/checkpoint evidence. If such evidence is
absent, **unknown remains blocked** even if SQLite ignores the journal or the
database passes integrity/replay. A missing journal cannot always be diagnosed
from the main file alone. Do not construct zero headers, splice records, substitute
a similar journal, force modes that ignore journals, or choose an older prefix.

In particular, untrusted rollback journals may contain super-journal/path
references. A broadly privileged SQLite process must not interpret unknown
journals before single-database provenance/path confinement has been established.
The controlled producer never uses ATTACH; no general hostile-journal parser or
super-journal exclusion mechanism is supplied here. This is a blocker for a
generic future recovery command, not a tested universal path-safety guarantee.

### 3. ENGINE_COPY_ROLLBACK or READ_ONLY_COPY_BACKUP

Only for a separately qualified case, use the exact reviewed local runtime on a
fresh working copy. The tested engine probe uses `mode=ro` first, zero busy timeout,
trusted_schema=OFF, query_only=ON and a read transaction with integrity checking.
Verify that the read-only probe leaves every working artifact unchanged.

- If SQLite reports recovery is required (`SQLITE_READONLY_ROLLBACK` in the tested
  hot cases), explicitly authorize a disposable-copy `mode=rw` open, retaining
  query_only=ON and issuing only the same read transaction. SQLite itself performs
  page rollback and may remove **that working copy's** journal. No user SQL UPDATE,
  DDL or event insert is used for recovery. Any error, residual unknown sidecar,
  unexpected file effect, timeout or integrity failure quarantines the working copy.
- For the qualified tested non-hot case, a read-only integrity pass leaves the
  residual journal intact and the ordinary loader still refuses that copy. Do
  not clear it by writing or deleting. A read-only SQLite connection and the
  SQLite backup API can create a **separate fresh candidate** of the engine's
  logical database view. This preserves the working journal and sealed/original
  artifacts. It is not physical rollback and does not make an unknown journal safe.
- Without a sidecar, make no repair. Examine/replay a diagnostic copy and reconcile
  the command outcome; absence alone is not a universal proof of a clean crash.

Unknown inputs are never routed to these engine operations. A future worker must
be independently reviewed for fixed commands/runtime, extension/attachment/path
confinement, bounded time/output/resources and privileges. The current harness
executes only small known fixtures and is not a hostile native-code sandbox.

### 4. REPLAY_REJECTED or REPLAY_VERIFIED_DIAGNOSTIC

After closing all engine handles, require sidecar-free candidate filesystem
admission and full `v3_ledger.load_ledger` replay with the unchanged limits, exact
schema fingerprint, native identity availability and source/head semantics.
`load_initialized_store` is suitable only for an actually genesis-only store.
Do not replace either loader with `integrity_check`, a SQL row count or a hash
of the candidate file.

Require exact retained original-BLOB bytes/digests and compare history to the
known committed prefix/checkpoints. Any corrupt BLOB, missing event, forged
projection, invalid predecessor/counter, unsupported event or lost committed
suffix stops adoption and preserves all copies as evidence. A self-consistent
older database can pass replay; an external head/checkpoint is necessary to
detect that substitution. Hash chains alone do not authenticate freshness.

No source.failed/source.validated, replacement event or missing BLOB is generated
to make replay succeed. PENDING stays PENDING; existing FAILED stays FAILED.
Recovered uncaptured registrations do not regain mutable-original-path authority.

### 5. AWAITING_HUMAN_ADOPTION

Replay verification produces a diagnostic candidate, **not adoption permission**.
Require a separate explicit, identified human decision against exact pre/post
artifact identities, runtime, replayed head, external checkpoint reconciliation,
limits and outstanding uncertainty. Record decision, reason and audit time outside
the frozen ledger; no new schema/event/review state is invented in recovery.

Any later operational publication/configuration switch needs a separately reviewed
maintenance/adoption protocol with no automatic overwrite of original evidence,
restart interlock, path/identity rechecks, a no-overwrite destination and retained
rollback/custody records. This task never changes an operational path, returns an
approved inventory view or adopts a recovered file automatically.

## Interruption and state matrix

| Point | Required committed result after qualified recovery | Source/head and reconciliation |
|---|---|---|
| Before BEGIN IMMEDIATE | Exact prior committed history. No new intent becomes authoritative. | Prior highest committed start; normal open may succeed if no sidecar exists. |
| Empty uncommitted transaction | Exact prior history. Lock release does not create an event. | No new source revision or FAILED observation. |
| Uncommitted registration | Entire attempted start/logical row/head/counter rolls back. | Prior highest committed start remains. Lost uncommitted intent is not synthesized. |
| Registration COMMIT, acknowledgement lost | Complete new start survives if commit is verified. | New PENDING head immediately blocks fallback; reconcile reference/head before any new command. Existing TASK-0073B23 process test covers this point. |
| Uncommitted capture, including spilled main pages | Committed start survives; attempted capture event/raw BLOB/mirrors/counters roll back together. | Newest committed start remains uncaptured PENDING; older captured revision is not substituted. No fabricated failure. |
| Capture COMMIT, acknowledgement lost | Complete capture, exact original bytes and matching sequence survive. | Captured PENDING, never VALID. Reconcile exact registration/hash/event before considering another command; no recapture. |
| Existing captured PENDING/FAILED before interruption | Exact committed events/bytes remain. | PENDING never becomes VALID; FAILED never resets; all latest-started heads reconstructed from starts. |
| Failed-capture transaction interrupted | Only a genuinely committed source.failed may survive; otherwise original PENDING. | Transaction-rule expectation, not a separately forced process-exit point in this new suite. No invented binary hash. |
| Unknown/missing/mismatched/corrupt sidecar or failed replay | No operational result. Preserve original and working evidence. | Manual investigation; no partial trusted prefix or oldest-readable fallback. |

## Evidence, audit and unresolved gates

An external case record should retain operator authority/maintenance evidence,
case scope, producer/worker identity and exit status, UTC examination times,
exclusive-handle results, exact pre/post member names/lengths/hashes and bundle
manifest, runtime/loaded binary hashes, observed header fields/errors, all
authorized engine operations, candidate/replay head and source-BLOB identities,
checkpoint comparison, failures/quarantine and the separate adoption decision.
Record observations separately from assumptions. Keep source text out of logs;
store evidence locally under approved custody/retention controls. SHA-256 is an
integrity measurement, not a signature or operator/source authentication mechanism.

**Still blocked before any production recovery command:** reviewed operator
authentication and maintenance interlock; trustworthy initial journal/database
association and checkpoint custody; hostile journal/path/super-journal confinement;
bounded isolated worker and resource/failure auditing; explicit adoption/publication
and restart protocol; target-volume qualification beyond this NTFS experiment.
The current filesystem trust model therefore supports this controlled synthetic
proof, **not an unconditional generic repair tool**. If these gates cannot be
established for a real case, retain quarantine and seek specialist investigation.

NTFS/ReFS names, SQLite FULL synchronization and successful process-exit recovery
do not prove arbitrary power-loss durability, sector-write atomicity, controller
flush behavior, torn-file recovery, authenticated history or resistance to a
privileged filesystem adversary. No workstation security setting is changed and
no universal durability/forensic-authentication claim follows from these tests.
