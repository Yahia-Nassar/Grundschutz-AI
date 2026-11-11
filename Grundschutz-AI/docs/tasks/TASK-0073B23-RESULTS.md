# TASK-007.3B.2.3 — Trusted schema-3 bootstrap, registration and capture

## Result and scope

**READY FOR REVIEW for trusted enrollment and capture-only persistence.**
Baseline and final HEAD: **ed3f06186ff621d7a8d1747a8a6d6a27c97c9897**, initially
clean. Repository `Y:/Grundschutz-AI`; application
`Y:/Grundschutz-AI/Grundschutz-AI`. Reviewed Windows fixed-local NTFS/ReFS,
Python **3.12.6**, SQLite **3.45.3**. Synthetic data only.

A fresh initialized store can now enroll the two approved native identities,
create typed registries, start increasing source revisions and capture immutable
original bytes. **Every successful capture remains PENDING.** Genuine failures
of original-file capture may produce terminal FAILED without inventing bytes or
a digest. Neither result is a review state or human decision.

No source.validated, VALID terminal, native parsing during capture/replay,
derivation, candidate, queue, Evidence, Inventory, approval, export, PDF promotion
or migration is implemented. No dependencies, network/model calls, company
documents, security/Git configuration changes, automatic staging or commits.
This is not completion of the wider Gate B source-validation design, Sprint 0
acceptance, source authentication, production readiness or BSI verification.

## Changed files

| New file | Responsibility |
|---|---|
| [v3_ledger.py](../../grundschutz_ai/v3_ledger.py) | Narrow public commands, operation-owned SQLite handles, verified read-only preflight, fresh write replay, one-use capture authority, resource admission and atomic commit/rollback. |
| [_v3_capture.py](../../grundschutz_ai/_v3_capture.py) | Private immutable capture-only records and pure event-to-state reconstruction, separated from writable connections and original-file I/O. This small private boundary prevents writable command logic from becoming replay authority. |
| [test_v3_ledger.py](../../tests/test_v3_ledger.py) | 96 synthetic offline regressions, including actual SQLite faults, competing writers and process exits. |
| This report | Contracts, exact results, reproduction and limitations. |

**No tracked file changed.** In particular, v2/v3 canonical codecs, physical
schema/fingerprint, initialized-only store, native bridge/catalog/artifact pins,
handler descriptors, frozen A0 handler/oracle and historical goldens are unchanged.

## Trusted bootstrap and authority

Enrollment selects only the two release-owned native profiles from the unchanged
static catalog. The public API accepts a supported family or exact native
handler hash; it does not accept descriptor bytes, executable/module paths or
database-defined implementations. Stored descriptor bytes must equal the exact
catalog bytes, with independently verified content digest/length and identity.
All required native artifacts and the exact host runtime are checked on each
operation/load, even though no native reader executes here.

The existing four-profile ceiling remains: two A0 `source_ledger_read` profiles
plus two native `extract_captured_bytes` profiles. Native handler hashes remain:

- DOCX: `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5`.
- XLSX: `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2`.

There is **no new catalog capability or descriptor member**. Existing native
capability equality is an availability/identity prerequisite for enrollment,
not permission to validate a persistent source. Capture authority is supplied
by this task's explicitly authorized, fixed ledger-command allowlist; no parser
is dispatched. Gate A ledger-read entries cannot enroll as native handlers.
Source validation would require a separately reviewed operation/authority
contract; it cannot be inferred from this bootstrap or existing capabilities.

Exact order for each family, after the unchanged genesis event:

1. `implementation.registered` / `implementation-register/v1`, storing the exact
   historical reader Spec and descriptor BLOB.
2. `reader.handler_registered` / `reader-handler-register/v1`, requiring its
   implementation already registered and storing the exact native handler Spec.
3. `registry.created` / `registry-create/v1`, requiring compatible enrolled reader
   and handler, explicit unique session ID and complete same-family policy Spec.
   It owns initial policy activation revision 1/fingerprint, epoch 1/history 0.

Each command commits exactly one singleton event transaction. The two families
may enroll in either order. Repeated family registries reuse the same enrolled
implementation/handler and policy bytes; identities/session uniqueness remain
separate. No multi-event bootstrap command, bulk append or registry flag activates
later features. Policy activation after revision 1 is unnecessary for this
minimal workflow and remains unsupported, including on load. To use another
approved tightened initial policy, create a separate registry; logical source
ownership cannot move between registries.

## Registration and one-use capture

`begin_registration` requires explicit registry ID, source ID, kind, exact active
policy revision, reader/handler hashes, DOCX null or typed exact XLSX selection,
empty original-source lineage, actor and three fresh tokens:

- `LedgerHead(store_uuid,sequence,event_sha256)`.
- The complete immutable `RegistryState` returned by verified replay, including
  epoch, active policy, reservations, exhaustion and counters.
- The exact highest-started `SourceRef`, or explicit null for a new source.

Registry tokens reject boolean/integer aliases. The source reference and all
existing canonical preimages are unchanged. The reviewed `source-start/v2`
payload has exactly its existing codec members; kind is checked against immutable
registry/source ownership rather than added as an invented payload member.

A start atomically creates the logical source if new, appends its immutable
registration with exact predecessor, advances the highest-started head immediately,
increments epoch and reserves three history units. Re-registration always creates
a new ID/revision and PENDING without bytes, even if its later bytes match an old
capture. Source ownership and family are store-wide immutable. Source heads'
`last_event` always equals the highest registration's **start** sequence.
Completion of an older revision, with explicitly refreshed tokens, preserves the
newer head. No timestamp, older capture or FAILED state is a currentness fallback.

Only the exact writer instance that committed a start holds its one-use live
capture authority. `capture_source` requires that reference, fresh global,
registry and highest-source tokens, actor and an explicitly supplied trusted
synthetic file path. Read-only preflight verifies all history before I/O. The
live authority is consumed before attempting file capture; I/O, post-read stale,
SQL or capacity failure never grants a reread. An initial stale precondition
does not read the source. Closing/reopening loses uncaptured path authority;
start a new revision instead. Captured PENDING registrations also cannot recapture.

The frozen local-filesystem guard checks absolute fixed-local paths outside Git,
aliases, reparse/link/hard-link restrictions and the trusted extension/family.
One open handle checks regular-file type/link count and size; there is exactly
one bounded `read(maximum+1)`. Oversize/truncated/unreadable results do not produce
partial original bytes. The path is never stored or reopened for that registration.
Changing/deleting the original after the read cannot change the captured bytes.
This does not prove a concurrently modified file represented a coherent external
revision or defeat a privileged filesystem adversary.

On success, exact bytes enter `content_blobs`, with byte length and SHA-256
independently checked. Dedup compares **length and full content equality**, not
only the digest. `source_captures` binds the exact registration, capture sequence,
hash and length. Distinct revisions/capture events remain distinct even when the
BLOB deduplicates. Raw bytes are charged once per role globally and separately
once per registry across all history. A BLOB also used as metadata is charged
to both applicable role budgets. Capture increments epoch, never releases history
reservation and creates **no terminal row**. Status remains PENDING on reopen.

Only genuine capture-phase observations are implemented: `capture_failed`,
`source_limit` or `unsupported_input`, exactly one code and `phase="capture"`,
using the existing `source-fail/v2` contract. Failure writes one immutable FAILED
terminal and increments epoch, with no fabricated capture/hash. No arbitrary
public failure-code API, validation-phase failure or terminal recovery exists.
Reopened uncaptured registrations can be superseded by a new start, not captured
again or automatically abandoned. All committed history remains retained.

## Replay and transaction verification

`load_ledger` is a separate read-only capture-profile loader. The old
`load_initialized_store` still requires exactly one genesis and refuses all later
events; its implementation and tests are unchanged. Schema 1/2 and unknown stores
are refused, without migration or writable initialization.

Before allocating source BLOBs, the new loader checks exact schema/index/trigger
maps, version/encoding, foreign keys/integrity, database pages and bounded event/
BLOB counts/lengths/aggregate sizes. Every BLOB digest/length is recomputed.
Every event has its exact canonical payload/envelope, row mirrors, hash chain,
contiguous sequence, fixed store UUID, unique event/transaction IDs and singleton
transaction group checked. Audit-field consistency is inherited from the unchanged
v3 codec; timestamps do not define currentness.

The private pure replay reconstructs implementation/handler enrollment, policies,
ownership, revisions/predecessors, captures/FAILED observations, source heads,
reservations, epochs, retained role accounting and exhaustion from **events**.
Untrusted policy-row links must resolve to exact validated Specs and match the
event-owned rows. At completion every expected immutable row and mutable
projection is compared with SQLite; the referenced metadata/original BLOB union
must equal the entire BLOB table. Missing, extra/orphaned, duplicate, reordered,
forged or impossible data refuses the whole trusted result. No trusted prefix,
cached status, head fallback, stored source path or parser result is used.

The applicable event allowlist is genesis, implementation, handler, registry,
source start, capture, capture-only failure and exhaustion. `policy.activated`,
syntactically valid `source.validated`, validation/environment/interrupted failure
phases and future/unknown events are refused. `derivations` stays empty; no VALID
or derived native data can be reconstructed as accepted state by this profile.

Every named write performs:

1. Runtime/artifact/filesystem checks and complete **read-only** preflight/token
   comparison before opening `mode=rw`; a missing file is not created.
2. Operation-owned connection with foreign_keys=ON, trusted_schema=OFF, existing
   DELETE journal mode, synchronous=FULL and zero busy timeout.
3. `BEGIN IMMEDIATE`, complete fresh replay and exact global/registry/source
   token comparison. No stale/busy automatic retry.
4. A fixed command plan; exact BLOB equality/dedup; one event; immutable rows
   and rebuilt allowed projections in that same transaction.
5. Complete reconstruction and full mirror/schema/BLOB verification before
   COMMIT. Explicit ROLLBACK on failure; connection closed in all cases. Results
   are exposed only after successful COMMIT. No public writable handle or generic
   append API. Private Python members are not a hostile-code security boundary.

Capture reads outside the write lock after its initial preflight, then refreshes
preflight/in-transaction state with the same deadline. A competing writer may
make that attempt stale after the read: it rolls back, preserves PENDING and
consumes the attempt rather than reopening a mutable path. No required failure
or exhaustion is claimed durable if its transaction failed. As with SQLite
generally, lost acknowledgement after a committed transaction requires reloading;
an error/interrupt is not a promise that a commit never happened.

## Resource admission and exhaustion

Defaults retain ADR-0011's hard ceilings; exact typed trusted settings may only
tighten: 256 MiB database, 10,000 events, four registries, 16 logical sources per
registry (64 total), 2 MiB per original, 32 MiB globally distinct original bytes,
128 MiB metadata and sixty seconds cumulative per operation across all checks,
I/O, replays and commit admission. Initial policy limits/history reservations
retain the frozen A0 interpretation. No history, revision or counter is evicted,
reclaimed or reset. Text/manifest/derivation counters remain zero here.

Normal events stop at 9,996 by default; four event slots and 1 KiB/maximum
registry are reserved for terminal controls. Metadata accounting includes unique
event/spec BLOB bytes **and all canonical envelope bytes**, preserving the
foundation's genesis accounting. Every BLOB with more than one role satisfies
each role's limits/equality. Scope/reader structure limits are not inferred from
capture: no structural parser or proposal scope exists in this task.

A deterministic known source/history/raw/event/metadata capacity failure can
replace the requested registry operation with exactly one `registry.exhausted`
event from reserved control capacity. It increments epoch and permanently blocks
the registry without fabricating a source failure/capture. No attempted start,
original BLOB or partial projection is imported. `RegistryExhaustedError` is raised
**only after that control transaction committed**. Reload returns its preserved
history and new tokens. Four already-created registries can each commit their
reserved terminal event; this is tested with tightened event capacity.

There is no arbitrary public exhaust/reset operation. Bootstrap that cannot
create a registry refuses uncommitted, rather than inventing an owner for a
control event. SQL/disk/deadline/physical-capacity failure can also prevent a
control/failure transaction: it rolls back and reports an error, never durable
invalidation. No disk space is physically preallocated and no OS RSS/CPU/disk
quota or arbitrary power-loss durability is claimed. An exhausted event records
a conservative capacity block; the reviewed payload contains no rejected source
bytes, so replay cannot independently reproduce the uncommitted attempted input.

## Actual acceptance results

Full offline suite: **853 tests in 122.866 seconds; 848 passed, five skipped,
zero failures/errors**. This is all 757 previous tests (752 pass/five optional
Ollama skips) plus **96 new passing tests**:

| New group | Tests |
|---|---:|
| Bootstrap | 15 |
| Registration/currentness | 13 |
| Capture/identity/side effects | 16 |
| Replay/tamper | 20 |
| Atomic writes/concurrency | 8 |
| Capacity/deadline | 13 |
| Actual process exits | 4 |
| Filesystem/lifetime/tokens | 7 |
| Total | 96 |

Both historical proof variables pointed to verified existing original artifacts;
neither historical proof was skipped. The original A-created database read-only
cross-version test and fresh historical native producer test passed. All seven
reader goldens, exact native artifact identities, catalog capabilities and both
older store APIs retain their passing tests and unchanged bytes. Five skips are
the existing optional Ollama tests; this task does not invoke Ollama.

New tests cover both-family bootstrap; duplicate/bad identities, sessions,
families and policies; missing handler/changed policy; three stale tokens;
immutable ownership; monotonic re-registration and late older completion; empty,
exact, missing, oversize, unsupported and changed-after-read originals; content
dedup and multiple roles; no recapture/reopened path authority; all counters and
control reserves; rollback at multi-table writes/COMMIT; actual competing writers;
rehashed reordered events; forged heads/counters/BLOBs/mirrors; unknown and
syntactically valid future events; immutable SQL guards; no reader/model/network/
domain/v1-storage calls; strict path aliases and exactly one original content read.

Four real child exits were observed: code 71 during registration before commit,
72 after registration commit, 73 before capture commit and 74 after capture
commit. Postcommit reopen preserved the complete corresponding PENDING state.
Before commit, no partial state was accepted; previously committed starts/history
were preserved after the explicit disposable-fixture recovery described below.

During development, three fixture issues were corrected without weakening
production contracts: the one-read spy compared short/long Windows path spellings;
the four-registry test initially overcounted repeated family enrollment (the
correct shared enrollment sequence is seven events, not ten); a no-op SQLite
UPDATE did not dirty a page or clear a non-hot journal. Corrected tests retain
the same safety expectations, and all passed in the final full run. No previous
test/expectation or historical vector was modified. No unresolved test failure.

### Capture demonstration and observed latency

The exact historical complete DOCX/XLSX original bytes were written to invented
files in an owned temporary directory outside Git and captured via public
commands, with both families enrolled. No parser was invoked. Reopen exactly
matched the committed returned state; the temporary DB/documents were removed.

| Case | Original bytes | Binary SHA-256 | Capture sequence/state | Command / write-lock duration |
|---|---:|---|---|---|
| DOCX complete | 1,381 | `d8c0bfdc1b10927bc0a5e2e8833038c80c497d8bec5efd27af2fecba0f9d4299` | 6 / PENDING | 169.961 / 87.066 ms |
| XLSX complete | 2,747 | `d12084673da49c9cf78630e1a217af3d00a9178ea03b6508c15af95422fd7345` | 11 / PENDING | 273.706 / 147.617 ms |

Final demo: 11 events, 4,128 distinct original bytes, 18,325 metadata bytes
including envelopes; maximum observed writer lock hold 147.617 ms. The test-only
timer measured from successful BEGIN IMMEDIATE through COMMIT and did not change
product code. These are small synthetic observations, not upper latency bounds
or a scalability/durability benchmark.

Physical schema fingerprint remains exactly:
`75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c`.

## Interruption and remaining limitations

The existing local filesystem contract refuses `-journal`, `-wal` and `-shm`
sidecars before any application connection. That rule is preserved. An abrupt
exit during an open transaction may leave a rollback journal, even when no
uncommitted main-file page was flushed. The application refuses it **without
changing/deleting the DB or journal**. There is no automatic rollback-journal
recovery, repair, retry or sidecar deletion API.

For two disposable crash fixtures only, the test owner explicitly opened SQLite
and performed a reversible projection write in a committed transaction to allow
SQLite's recovery/cleanup; full application replay then proved the exact prior
committed history and absence of partial start/capture/BLOBs. This is test-owner
recovery, not evidence of an implemented application recovery feature or a
recommended production repair command. Non-hot journals were observed; the tests
do not claim arbitrary power-loss recovery, torn-write resilience or a complete
filesystem adversary model. An interrupted production store with a sidecar still
needs a separately reviewed operator recovery procedure before trusted reopen.

Additional limitations:

- Capture proves the exact retained observed bytes, not document validity,
  complete context, source authenticity, actual inventory truth or approval.
  Even non-Office bytes with a trusted .docx/.xlsx label can be quarantined as
  PENDING; that is deliberately not structural ingestion.
- No handler capability/descriptor was expanded. Policy revision 2+, native
  source validation/replay, VALID, derivations and downstream stages remain
  unsupported. All source text/instructions remain untrusted data.
- Complete replay is repeated under the write lock for this small prototype.
  Deadlines/size accounting are application controls, not hard CPU/RSS isolation.
  A tight budget refuses the entire load rather than returning a prefix.
- File identities/path checks reduce accidental alias/replacement problems but
  are not authenticated sources or full adversarial filesystem isolation.
  Unsigned self-consistent whole-store replacement/actor forgery is not solved.
- No durable mutable-path capture authority survives a writer restart or a spent
  attempt. Start a new revision after an uncaptured interruption or failed read/
  stale write; successful existing captures are never reopened from their path.

Stop after TASK-007.3B.2.3. Next step is human review of this capture-only boundary
and its explicit journal limitation; source validation/recovery/later gates need
separate authorization and reviewed contracts.

## Exact reproduction commands

Run on the reviewed Python 3.12.6/SQLite 3.45.3/Windows fixed-local profile with
the exact LF native artifacts. No dependencies or model needed:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest tests.test_v3_ledger -v

# Complete offline suite including both authentic historical proofs:
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI"
py -3.12 -m unittest discover -s tests
```

If those temporary historical artifacts expired, use the exact unchanged
Git-archive/A-public-API procedure in
[TASK-0073B20-RESULTS](TASK-0073B20-RESULTS.md); never generate an alleged old
oracle with the new ledger or substitute updated golden expectations.

Minimal standalone synthetic DOCX-labelled capture demonstration (temporary
directory/DB outside Git; intentionally non-Office bytes, no parsing):

```powershell
@'
import tempfile
from pathlib import Path
from uuid import uuid4
from grundschutz_ai import v3_ledger as l, v3_store as f, v3_codec as c
from grundschutz_ai.v3_native_catalog import native_catalog
with tempfile.TemporaryDirectory(prefix="grundschutz-capture-review-") as root:
    path=Path(root)/"fictitious.sqlite"
    f.create_initialized_store(path,actor_id="synthetic:operator")
    p=next(p for p in native_catalog() if p.spec.data()["family"]=="docx")
    with l.SourceLedger.open(path) as w:
        w.register_implementation("docx",expected=w.load().head,actor_id="synthetic:operator")
        w.register_handler(p.spec.sha256,expected=w.load().head,actor_id="synthetic:operator")
        rid=w.create_registry("docx",session_id=uuid4().hex,policy_spec=c.Spec(p.policy_ceiling),
                              expected=w.load().head,actor_id="synthetic:operator")
        s=w.load()
        ref=w.begin_registration(rid,"synthetic:review",kind="docx",policy_revision=1,
            reader_spec_hash=p.spec.data()["reader_spec_hash"],handler_spec_hash=p.spec.sha256,
            expected=s.head,expected_registry=s.registry(rid),expected_source=None,
            actor_id="synthetic:operator",selection=None)
        original=Path(root)/"fictitious.docx"
        original.write_bytes(b"FICTITIOUS ORIGINAL; NOT A VALIDATED DOCUMENT")
        s=w.load()
        result=w.capture_source(ref,original,expected=s.head,expected_registry=s.registry(rid),
                                expected_source=ref,actor_id="synthetic:operator")
        assert l.load_ledger(path)==result
        print(result.registration(ref).status.value,result.registration(ref).binary_sha256)
'@ | py -3.12 -

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code
```

## Git status

HEAD remains **ed3f06186ff621d7a8d1747a8a6d6a27c97c9897**. No files staged or
committed. No tracked changes; exactly four new task deliverables:

```text
?? Grundschutz-AI/docs/tasks/TASK-0073B23-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/_v3_capture.py
?? Grundschutz-AI/grundschutz_ai/v3_ledger.py
?? Grundschutz-AI/tests/test_v3_ledger.py
```

`git diff --exit-code` and `git diff --check` pass. New Python AST, UTF-8/LF,
whitespace and local report links are checked separately because Git's normal
diff does not include untracked files. All test/demo databases, documents and
crash journals are owned synthetic fixtures outside Git; none is committed.
