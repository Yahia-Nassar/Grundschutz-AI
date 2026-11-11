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

## PROPOSED addendum: TASK-007.3B.2.4.1 trust prerequisites

**Status remains PROPOSED for operational use. No production recovery operation
can currently be justified.** The following is a review contract and a test-only
model, not an authentication implementation or extension of the capture ledger.
It grants no recovery, adoption, publication, source validation or inventory
authority. Diagnostic labels below are neither database states nor permissions.

### Independently acknowledged history

A database SHA-256, journal filename/header/checksum, self-consistent replay or
hash stored next to a database proves neither origin nor completeness. A writer
or attacker controlling those artifacts can substitute an older valid prefix.
Require an independent authority that observes committed history, retains its
acknowledgements outside the database/sidecar/case writer's control, authenticates
its own identity and answers a fresh examiner challenge about its latest head.
No such operational authority, key, operator or service has been established.

The bounded **synthetic-committed-head/v1** proposal uses canonical-json/v1 UTF-8
without BOM/newline, duplicate keys, floats or noncanonical encodings. It reuses
the unchanged inert codec primitives, not a new ledger codec. Exact key sets,
strict types (bool is not integer), and bounds apply: 32 KiB/record, depth 16,
4,096 tree nodes, 64 array/object members, 2,048 UTF-8 bytes/string. The 64-record
test chain limit fails closed; it never silently prunes an earlier checkpoint.
Larger stores/history need a separately reviewed checkpoint protocol.

| Required member | Exact type / binding |
|---|---|
| checkpoint_version, encoding | Strings `synthetic-committed-head/v1`, `canonical-json/v1`. |
| checkpoint_id, ordinal, previous_sha256 | Lowercase 32-hex identity, positive signed-64-bit integer, null only for ordinal 1 otherwise lowercase 64-hex hash of previous canonical checkpoint payload. Contiguous ordinals; no reset/implicit bootstrap. |
| store_uuid | Exact physical store's lowercase 32-hex identity. Not an inferred path or logical source ID. |
| schema_version, physical_profile, feature_profile, schema_fingerprint, event_codec | Integer 3; `sqlite-source-validation/v1`; `verified-source/v1`; `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c`; `ledger-event/v3`. Unknown profiles refuse. |
| head | Exact object: sequence (positive integer), event_sha256 (64-hex), event_id and transaction_id (32-hex), transaction_index and transaction_count (integers exactly 1), kind (recognized event-kind string). Binds exact committed transaction, not only a count. Recognition never enables source.validated. |
| registry_heads | Sorted unique registry_id array; each exact object has registry_id/session_id (32-hex), kind (`docx` or `xlsx`), policy_revision/epoch (positive integers). Relevant policy epoch is not inferred from a current filesystem path. |
| source_heads | Sorted unique source_id array; exact SourceRef objects: source_id (nonempty bounded string), revision (positive integer), registration_id (32-hex). Includes latest STARTED head even if uncaptured/FAILED. |
| captures | Sorted unique registration_id array for **all retained captured registrations**: registration (exact SourceRef), event_sequence (positive integer <= checkpoint head), binary_sha256 (64-hex), byte_length (nonnegative integer). These are observed committed captures, not VALID states or permission to recapture. |
| observed_at, recorded_at | Valid UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`; recorded_at >= observed_at. Audit metadata only; never establishes freshness. |
| producer | Exact object: producer_id, key_id, authorization_context (bounded nonempty strings) and authority_epoch (positive integer); must match independently enrolled issuer/context/epoch. Test literals are `synthetic:observer-A`, `PUBLIC-TEST-ONLY-A`, `synthetic:independent-observation/v1`, 1. No database-selected key/path/code. |
| acknowledgement_basis | String `client_commit_receipt` or `independent_commit_observation`; records how the independent observer learned of the commit. Does not fabricate a lost client receipt. |

In tests, immutable SignedDiagnostic carries payload bytes plus a lowercase
64-hex HMAC-SHA256 tag. Domain-separated preimages are ASCII purpose, NUL, then
canonical payload. Purposes are `checkpoint`, `witness`, `grant`, `custody`.
**All test keys are public constants:** bytes 0..31 for checkpoint/witness and
32..63 for grant/custody. They are deliberately forgeable by anyone and cannot
authenticate a real actor. They are not secret storage or a recommended production
credential design. Literal checkpoint bytes and independently calculated .NET
SHA/MAC vectors are in tests/test_v3_recovery_trust.py; the results report records
their exact identities. Tests establish binding and refusal logic under explicit
trusted-observer assumptions, not real organizational separation.

The synthetic freshness witness has exact members: witness_version
(`synthetic-freshness/v1`), challenge (32-hex), store_uuid (32-hex), ordinal
(positive integer), authority_epoch (positive integer), checkpoint_sha256
(64-hex). The verifier's challenge must be new and independently generated for
each real examination, and the authenticated authority must answer from its
nonrollbackable latest retained record. Fixed challenges in literal tests are
**not** operational nonces. Neither a signed timestamp nor a replayed witness
proves currency. Missing authority access/current witness means INCOMPLETE_EVIDENCE.
Same-process memory and public test credentials do not implement custody,
nonrollbackable storage, revocation, secure clocks, independent audit or nonce
management. Key rotation, authority replacement and new trust anchors require a
reviewed external continuity process; unknown epochs/issuers cannot bootstrap it.

| History observation | Required diagnostic response; no repair/acknowledgement |
|---|---|
| Exact committed head, transaction, heads, captures and current external witness | May satisfy the **synthetic** history prerequisite after full unchanged replay. |
| Missing checkpoint/witness, ordinal gap, unavailable latest record, replayed challenge | INCOMPLETE_EVIDENCE. Obtain independently authenticated missing evidence; never select the newest locally readable prefix. |
| Candidate older than independently acknowledged head / missing committed suffix | CONFLICTING_EVIDENCE even when candidate replay is fully valid. Preserve both artifacts. |
| Same sequence with different hash/transaction, fork, changed store/heads/BLOB references or invalid MAC | CONFLICTING_EVIDENCE. No automatic fork selection or repair. |
| Candidate has valid committed tail beyond last external acknowledgement | INCOMPLETE_EVIDENCE. Reconcile separately retained command intent, exact registration/transaction, predecessor and BLOB hash/length. Never acknowledge merely because bytes are readable. |
| Commit succeeded, client receipt lost | A pure observation may identify the one matching committed capture and retained PENDING bytes. It neither issues a client receipt nor appends a checkpoint/event. Independent later acknowledgement requires separate evidence/authority. Conflicting or missing intent blocks. |
| Same bytes, different registration IDs | Distinct registrations/events, possibly one deduplicated BLOB. A digest cannot substitute for registration identity or source-currentness. |
| Newer committed STARTED head | Supersedes older capture immediately, even while uncaptured PENDING. Never substitute the older captured revision. |

The test reconciler verifies every acknowledged event head against the candidate
chain and compares exact tip heads/captures. It performs no SQL write and has no
acknowledgement callback. An externally acknowledged intermediate checkpoint
assumes the independent observer actually verified that committed state; the
test helper accepting a LedgerState is not proof of that external role. No
mismatch creates source.failed/source.validated, replacement events, BLOBs or
acknowledgements. Existing loader/replay rules remain authoritative.

### Maintenance, acquisition and custody prerequisites

| Prerequisite / required evidence | What the tests demonstrate | Assumption / missing implementation; sufficiency and continued refusal |
|---|---|---|
| Authenticated authorized operator, explicit reason/case/store/action scope | Public-test grant binds grant_version, case_id, store_uuid, operator_id, role, reason, action, interlock_id, challenge. Missing grant stops before acquisition; invalid signature/role/store/action/challenge refuses. | Synthetic equality/MAC checks are application policy, not organizational identity. Production IAM, role enrollment/revocation, approval and independent audit are absent. Never sufficient for a production command. |
| Maintenance/restart interlock, identified and stopped writers/services | Test service flag must remain active before/after acquisition; missing/revoked flag refuses. Owned writer/restart processes are exercised. | Flag is a simulation/procedural attestation. No service manager, durable maintenance lease, restart inhibit or exhaustive handle enumeration exists. PID/account names alone prove nothing about other writers. Refuse until real controls are reviewed. |
| OS-enforced read-only acquisition of **all** exact members | Windows CreateFileW GENERIC_READ/share=0/OPEN_EXISTING/OPEN_REPARSE_POINT, before reading any member. A live SQLite transaction or incompatible handle blocks; partial acquisition releases previous handles; restart fails while handles are held. | Denial is OS-enforced for those handles only, not global quiescence or durable interlock after release. A privileged actor/storage change remains outside the proof. Unknown open handles/writers block acquisition, never trigger process termination. |
| Exact member inventory and identities, no aliases/extra members | Fixed main/-journal/-wal/-shm names, regular single-link nonreparse leaves, volume/ancestry guards, pre-open/held file IDs and lengths, pre/post inventory; equal-byte replacement and unexpected/hard-linked members refuse. | Joint observation is bounded to controlled temp files. Future custody must retain actual volume/file identities, authorized paths and parent-directory protection through every handoff; no production ACL/namespace protection is implemented. |
| Joint hashes and uninterrupted exclusive custody | Original/sealed bundles compared after every test, copies separate; signed public-test custody record binds bundle manifest, original file IDs and known producer trace. | An external trusted custodian must independently retain case/store/checkpoint binding, times, member inventory/IDs/hashes, acquisition result, all transfers and decisions. Test handles close after acquisition. No continuous operational custody or independent audit store exists. |
| Qualified committed-history checkpoint | Literal vectors, altered/untrusted records, stale witness/time, missing prefix/suffix and fork tests. | Authenticity/freshness/custody of the external observer are assumptions. No real trust root. Verified test bytes cannot authorize production recovery. |
| Qualified physical/runtime profile and isolated copy worker | Reuses pinned Windows/Python/SQLite harness and known DELETE-mode producer, copies only. | Not a hostile-journal sandbox or target-volume/power-loss qualification. No resource-isolated production worker, adoption, atomic publication or restart protocol exists. |

The public synthetic acquisition grant uses exact fixed action
`acquire_diagnostic_copy`; it cannot grant engine recovery, adoption or restart.
Even its positive test must never be interpreted as permission. A future protocol
must preserve interlock and authenticated custody from initial acquisition through
copy experiments, replay and separately approved adoption, with identity rechecks
at each boundary and independent decision audit. Releasing a handle and later
reopening a path requires new qualified acquisition; stale file IDs or manifests
are insufficient. No ACL changes or unrelated process termination is performed.

### Journal association and refusal boundary

Association requires **all** of: exact jointly acquired main/sidecar file IDs and
bytes; unchanged externally retained joint manifest; independently known producer
identity and operation trace for this interruption; expected DELETE journal mode,
no ATTACH/super-journal/path references, pinned loaded SQLite runtime; independently
acknowledged committed history; and controlled quiescence/custody with no TOCTOU
gap. Matching filename, plausible header, checksum or hash alone is insufficient.
The test custody payload binds custody_version (`synthetic-known-producer/v1`),
case_id, store_uuid, bundle_sha256, members (name/length/hash tuples), file_ids
(name/device/inode/length tuples), mode, producer_exit, producer_sha256,
sqlite_source_id, journal_mode, attached_databases and checkpoint_head_sha256.
The independently retained expected trace/manifest is a trusted test input, not
a claim recovered from the suspicious directory. Matching a self-supplied signed
manifest cannot supply the missing independent producer observation.

#### R1 correction: compare custody to protected observations and verified history

TASK-007.3B.2.4.1-R1 corrects the original test-only provenance decision: its
custody record carried file_ids/store_uuid/checkpoint_head_sha256, but the
decision did not compare those fields to the acquired identities and independently
verified history. The original passing tests therefore did not establish these
bindings. This correction adds no operational authority; **PROPOSED** status and
every production blocker remain unchanged.

The test-only acquisition now returns immutable AcquiredEvidence containing the
joint byte bundle and member identities obtained with os.fstat from the **exact
Windows deny-sharing read handles used by the unchanged forensic harness**.
All handles must still be acquired before any bytes are read; the existing
ancestry/volume, regular-file, single-link, nonreparse, size, pre-open/held-ID and
complete-inventory checks remain intact. The wrapper compares its own pre-open,
held and post-read inventories and refuses changed/disappearing members. It no
longer accepts caller-provided expected identity tuples. An equal-byte copy is a
different acquired file set and cannot inherit the original custody record.

The provenance decision requires the protected acquisition result, separately
retained expected custody trace, and successful checkpoint-chain/fresh-witness
verification **and** full-state reconciliation. It compares custody file_ids to
the exact acquired tuples (name/device/inode/length), custody store_uuid to both
verified checkpoint and replayed store UUID, and checkpoint_head_sha256 to both
verified committed checkpoint head and replayed head. Missing observations,
different IDs/member sets, another store, or another committed head refuse.
Hash/manifest checks continue in addition to these comparisons.

AcquiredEvidence is a data carrier, **not an authentication capability**. Public
HMACs, arbitrary caller-created records/identity tuples and equal bytes cannot
establish independent provenance. Separately retained custody/observer roles are
still explicit trusted synthetic assumptions in one test process, not properties
created by a local signature or DTO type. Handles close after acquisition; this
does not implement continuous custody or authorize a later reopening/adoption.
No copy re-anchoring, production authentication or recovery pathway is introduced.

| Physical evidence condition | Decision and permitted work |
|---|---|
| Exact known synthetic producer/trace, joint bundle, checkpoint and custody | Synthetic diagnostic prerequisite only. Existing bounded fixture-copy engine experiment may be exercised in tests, never against originals. |
| Known expected journal missing/truncated, altered or transplanted; identity/hash mismatch | CONFLICTING_EVIDENCE; preserve everything, no engine call or automatic journal deletion. Even stale journal bytes from another genuine test case fail association. |
| Missing initial journal/producer history, unknown origin, stale association not independently disproved | QUARANTINED_UNKNOWN. Cannot infer clean commit or journal absence from current directory alone. |
| WAL/SHM, possible super-journal/ATTACH or external path references, unsupported runtime/physical case | QUARANTINED_UNKNOWN. No general journal/path parser or unrestricted SQLite worker is introduced. Test unsupported trace flags are refused before parsing. |
| Missing custody/checkpoint/maintenance proof but otherwise known case | INCOMPLETE_EVIDENCE; no operational action until independently supplied and verified. |
| Concurrent writer, incompatible handle, changed member or revoked interlock | Acquisition refused; retain diagnostic evidence and re-establish case under reviewed controls. A successfully closed process is not proof that it was the only writer. |

### Readiness outcome matrix

| Diagnostic outcome | Necessary condition | Sufficient for a production command? |
|---|---|---|
| TRUST_PREREQUISITES_VERIFIED | Controlled **synthetic case only**; exact independently retained checkpoint/fresh witness, known-producer custody and simulated writer-control evidence all pass. | **No**. Public credentials and assumed independent roles are not operational controls. |
| INCOMPLETE_EVIDENCE | Missing checkpoint/custody/writer proof, gap, stale witness, or unacknowledged valid tail. | **No**. Refuse; do not synthesize missing history or acknowledgement. |
| CONFLICTING_EVIDENCE | Inconsistent histories/transactions/commands/file IDs/hashes/authority claims. | **No**. Preserve both sides, investigate independently. |
| QUARANTINED_UNKNOWN | Uncertain provenance or unsupported physical/journal case. | **No**. Preserve evidence; no engine interpretation. |
| NOT_OPERATIONALLY_AUTHORIZED | A production request, including one accompanied by all positive synthetic proofs. | **No**. Real operator authority, independent checkpoint/custody/audit, interlock, isolated worker, target-volume qualification and adoption/restart controls are still absent. |

Multiple failure reasons must be retained for human review; a first diagnostic
label is not a complete operational decision engine. The small test aggregator
demonstrates only the listed precedence (production always refuses, otherwise
custody/history/writer prerequisites); it is not an authorization API. No source
review state, source-currentness rule, schema fingerprint, native handler identity,
frozen A0 proof, event codec or capture-only semantics changes. Do not begin
production recovery or later Gate B features based on this proposed addendum.
