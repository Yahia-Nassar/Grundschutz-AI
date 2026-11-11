# ADR-0014: Schema-3 verified native evidence read

**Status: PROPOSED; independent contract review required.**
TASK-007.3B.2.5.2, 2026-11-11. Design only, based on Git `3bf6402`.
No production consumer is implemented or exposed by this task.

This contract builds on [ADR-0011](0011-verified-source-validation-profile.md)
and [ADR-0013](0013-schema3-native-validation-activation.md), including the
accepted shared VerificationBudget R1 correction. [ADR-0012](0012-schema3-crash-recovery-contract.md)
remains **PROPOSED**. Production recovery remains **NOT_OPERATIONALLY_AUTHORIZED**.
It does not supersede the proposal boundary in [ADR-0008](0008-document-proposal-boundary.md),
the persistence model in [ADR-0009](0009-structural-evidence-and-sqlite-v2.md),
or the historical trust boundary in [ADR-0010](0010-historical-implementation-compatibility.md).

## 1. Authority and applicability

Structural VALID means that a complete verified replay freshly reproduces the
pinned native derivation from the exact captured original bytes. It proves no
authorship, real-world inventory truth, human approval, model-input suitability
or independently authenticated freshness. A self-consistent hash chain alone
is insufficient. SourceStatus is not the domain ReviewState.

For a completely verified LedgerState S, resolve registration R by exact
SourceRef in S, registry G by R.registry_id, and its event-owned active policy P.
Current applicability is exactly:

1. R.status is SourceStatus.VALID, with its verified capture and terminal;
2. S.source_head(R.ref.source_id) == R.ref (highest **started**, not completed);
3. G.exhausted is False;
4. R.policy_revision == G.policy_revision, with the exact policy Spec and
   fingerprint already bound by replay to that immutable revision;
5. the entire snapshot, all history, native derivations, BLOB closure and mirrors
   verify successfully under the trusted runtime and limits.

This is the existing S.is_current_valid predicate after complete verification,
with its prerequisite trust conditions made explicit. Caller tokens, terminal
SQL rows and cached projections cannot supply any of these conditions.

| Case | Verified state | Current-read eligibility |
|---|---|---|
| A | Captured PENDING | Refuse; capture is not validation. |
| B | Uncaptured PENDING | Refuse; no evidence to validate. |
| C | Terminal FAILED, with or without capture | Refuse; no fallback. |
| D | Historical VALID, superseded by a higher start | Refuse; retain historical record unchanged. |
| E | VALID, highest-started head, active policy, unexhausted registry | Eligible at this verified snapshot head only. |
| F | Newer PENDING after older VALID | Both ineligible: new is PENDING, old is historical. |
| G | Newer FAILED after older VALID | Both ineligible; never use last known good. |
| H | Older registration completes VALID after newer start | Old completion is historical; it cannot move the source head. |
| I | VALID but registry exhausted | Refuse even if no newer source start exists. |
| J | VALID under obsolete policy revision | Refuse; never upgrade/reinterpret its policy in place. |

Post-initial policy activation is presently unsupported by Replay and therefore
refuses the whole load, rather than returning an old-policy result. J is also a
required future eligibility invariant if policy transitions are separately
authorized. This task does not activate them.

## 2. Exact proposed API and tokens

Proposed future method, **not an implemented API**:

```python
def read_current_native_evidence(
    self,
    ref: SourceRef,
    *,
    expected: LedgerHead,
    expected_registry: RegistryState,
    expected_source: SourceRef,
) -> VerifiedNativeEvidence:
    ...
```

All four arguments are mandatory, nonnull exact types (no subclasses, dicts,
strings, bool substitutes or coercion). SourceRef is v3_codec.SourceRef;
LedgerHead and RegistryState are the existing v3_ledger exports. This method
uses the SourceLedger's already approved path, file identity and tightening-only
LedgerLimits. A closed SourceLedger refuses; there is no auto-open or retry.

Comparisons against the same replayed S are exact value equality:

- expected == S.head: store_uuid, sequence and event_sha256;
- expected_registry == S.registry(R.registry_id): **every** RegistryState field,
  including session_id, kind, policy_revision, epoch, exhaustion and retained
  history/byte/text/manifest/derivation counters;
- expected_source == S.source_head(ref.source_id): source_id, revision and
  registration_id. For success this also equals ref.

SourceRef has no store UUID. Its namespace is the verified store, bound by the
mandatory global token. A foreign store token is stale; a same-looking ref
without an exact matching local registration grants nothing. Tokens are
observations for stale detection, never authority overriding S. Wrong registry
ownership is an invalid command, not a request to read another registry.

No document paths/bytes, caller derivations, text/observations, selection override,
claimed VALID flag, policy override, executable/module names, arbitrary SQL,
callbacks or event appends are accepted. No fast/cache/history mode is offered.

## 3. Immutable return value

Proposed exact field structure (documentation, not a runtime declaration):

```python
@dataclass(frozen=True, slots=True)
class VerifiedNativeEvidence:
    snapshot_head: LedgerHead
    snapshot_registry: RegistryState
    snapshot_source_head: SourceRef
    terminal_event_sequence: int
    terminal_event_sha256: str
    derivation: DerivationRef
    selection: SheetSelection | None
    native_text_utf8: bytes
    native_manifest_utf8: bytes | None
    integration_manifest_utf8: bytes

    @property
    def applicability(self) -> str:
        return "snapshot_current"
```

Existing DerivationRef is immutable and retains its exact canonical bytes.
It is the **single authority** for store_uuid, registry_id, registration, kind,
capture sequence, original digest/length, reader/handler, policy, limits,
method/implementation and content identities. Optional convenience properties
must compute these from derivation, not retain independent mutable dictionaries.
DerivationRef.sha256 and .blob_sha256 retain their distinct existing meanings.
selection is the exact frozen SheetSelection reconstructed from verified
selection_json and cross-checked by pinned replay; DOCX selection is None.
The global snapshot head is not necessarily the earlier terminal event head.

Future construction must enforce exact field types and cross-check:

- derivation.store_uuid equals snapshot_head.store_uuid;
- registry, kind and policy revision agree with snapshot_registry;
- derivation.registration equals snapshot_source_head (the eligible target);
- 0 < capture_event_sequence < terminal_event_sequence <= snapshot_head.sequence;
- terminal event at that sequence is the replayed source.validated for this
  reference and exact derivation; terminal_event_sha256 is its envelope hash;
- the canonical derivation BLOB and all content bytes have their exact bound
  identities; manifest nullability and selection follow kind and pinned policy;
- no writable buffer, mutable nested container, handle, cursor, generator,
  temporary path or original binary bytes enter this object.

Fully materialize **independently owned** exact bytes before closing the snapshot;
use bounded copying from replay BLOBs, not a live SQLite buffer or deferred fetch.
Immutable zero-length byte objects may naturally share the singleton. Each other
record is an existing immutable value. No caller-mutable view backs the result.
Construction/type validation alone is not proof that the application actually
performed verification; a manually constructed DTO is not a capability token.

The default result omits original binary bytes. This does **not** change or hide
the current API: LedgerState.original_blobs already exposes captured originals
as immutable Blob values. That is not a current-evidence authorization pathway.

## 4. Byte and provenance binding

Keep canonical-json/v1, ledger-event/v3 and derivation-ref/v2 unchanged. In existing
notation, C is strict canonical UTF-8 JSON, S is SHA-256 of exact bytes, and
H(t,v) = S(C({"type": t, "value": v})). No new preimage, signature, digest domain,
event, source status, table or evidence identifier is introduced.

| Existing derivation-ref/v2 field | Required source of verification |
|---|---|
| store_uuid, registry_id | Verified genesis and event-owned registration. |
| registration: source_id/revision/registration_id | Exact source.started identity and ownership. |
| kind, capture_event_sequence | Registration and its single verified source.captured. |
| binary_sha256, byte_length | Exact retained captured original bytes, S(raw) and len(raw). |
| reader_spec_hash, handler_spec_hash | Event-enrolled descriptors, fixed catalog pins and registration. |
| policy_revision, policy_spec_hash, policy_fingerprint | Exact historical activation/Spec, also active for eligible target. |
| reader_limits_sha256 | Existing H("reader-limits/v1", complete frozen limits). |
| reader_method, reader_implementation_sha256 | Pinned native result and implementation stamp. |
| native_text_sha256 | S(exact native.text.encode("utf-8", errors="strict")). |
| native_manifest_sha256 | DOCX null; XLSX S(exact retained native-manifest UTF-8 bytes). |
| integration_manifest_sha256 | S(exact retained integration-manifest UTF-8 bytes). |
| DerivationRef.sha256 | Existing H("derivation-ref/v2", reference value excluding its type). |
| DerivationRef.blob_sha256 and canonical | S(entire canonical reference), and byte-for-byte equality to the retained reference BLOB. |

Full replay already rebuilds this reference using fresh pinned extraction and
compares exact derived content with stored BLOBs. The consumer selects those
verified retained bytes; it must not call derive to create a replacement or
choose a newer implementation/worksheet.

No trimming, NFC normalization, newline insertion, semantic parsing, inferred
sheet selection, cell reinterpretation or alternative serialization is allowed.
DOCX integration manifest preserves empty paragraphs/cells, body/table ordering,
native structural locators and Unicode codepoint offsets, not invented pages.
XLSX preserves every sheet's coverage, exact selected-sheet identity (name,
ordinal, sheet_id, relationship_id, part), coordinates and kinds. A missing cell,
BLANK cell and TEXT containing "" remain distinct even when visible text matches.
XLSX integration's native_manifest_json remains a nested **JSON string** containing
the exact native JSON, not an object reconstructed/reformatted by the ledger.
DOCX native_manifest_utf8 is None; there is no invented native-manifest BLOB.

Native text and manifests are exact extraction representations, not authentic
facts. Any later decoded convenience view must be lossless, derived from these
bytes and discardable; it cannot replace their authority. Opaque manifests are
not forced through the event codec's smaller JSON-string limit.

## 5. One-snapshot transaction algorithm

The future method must perform this sequence, without a public callback or SQL
escape hatch. The implementation does not exist in this task.

1. Start one monotonic absolute deadline using LedgerLimits.max_replay_seconds
   (at most 60); allocate one VerificationBudget. Acquire the ledger lock within
   remaining time; check before/after acquisition. Strictly check arguments,
   closed state, pinned runtime/handler availability, approved fixed-local
   Windows NTFS/ReFS path,
   file identity and no journal/WAL/SHM sidecars using the existing trust checks.
2. Open exactly one operation-owned mode=ro connection using _connect(readonly=True),
   timeout=0, query_only=ON, foreign_keys=ON, trusted_schema=OFF; require DELETE
   journal mode. Do not recover, convert or delete sidecars.
3. Execute BEGIN. **BEGIN is deferred and alone establishes no snapshot.**
   Perform the first actual schema/data read in this transaction; _verify's
   schema checks establish the read snapshot. All subsequent trusted reads use
   this same connection and active transaction.
4. Call complete _verify(connection, limits, deadline, budget=that_same_object),
   mirrors=True. Verify exact schema/physical profile, integrity/FKs, every
   envelope/payload, all event ordering/identities/ownership, all captured BLOB
   hashes/lengths, policies, all historical VALID via fresh pinned extraction,
   complete BLOB reference closure and every SQL mirror. A mismatch anywhere
   refuses everything, even if unrelated to the requested target. No SQL-only
   terminal check or stored-cache shortcut can substitute.
5. Record a monotonic selection start immediately after complete verification.
   From this S and Replay, resolve the target and compute applicability. Compare
   all mandatory expected tokens as specified below; require current applicability.
   Do not seek the latest completed VALID or silently retry a newer snapshot.
6. Resolve the target derivation through its exact replayed terminal and canonical
   BLOB, and all target bytes through Replay.blobs, **while this same transaction
   remains open**. Check all section 4 bindings, kind/nullability, stored selection,
   size bounds and terminal identity. No second connection, original source path
   or freshly supplied content participates.
7. Materialize and validate the entire immutable result privately. Charge selection,
   binding and copying time since step 5 to the target's same document context
   using that shared budget's charge_derivation, and check the global deadline
   throughout and after completion. Do not allocate a new context or budget.
   No partially populated object escapes on any failure.
8. End the read transaction with COMMIT, close the connection, and check the
   deadline before returning the owned object. On any failure discard it and
   close/roll back only this read transaction. Do not mask refusal with an
   attempted recovery or retry. Return only after successful closure; a late
   result is refused even if its bytes were correct.

Minimal future production changes: add this fixed method plus an immutable DTO
and private result checks, and a narrow private orchestration that keeps the
existing _connect/_verify transaction alive through selection/materialization.
_verify already returns (S, Replay), and Replay.blobs contains exact verified
bytes; frozen schema, codec, bridge, workers and handlers need no modification.
Existing _read/load_ledger closes its connection before returning, so it cannot
be followed by a separate SQL fetch and claimed to satisfy this contract.
Do not expose Replay, a raw connection or an arbitrary live-transaction callback.

The lock and resource checks are result-admission bounds, not proof of hard
kernel preemption: synchronous SQLite/OS cleanup and native process reaping can
finish after a deadline. The caller must receive no late evidence. Read-only
close failure is a refusal, not a CommitOutcomeUnknownError for a write intent.

## 6. Snapshot currentness, concurrency and later use

In the approved DELETE-journal profile, an established read snapshot holds a
SHARED lock. A writer may obtain RESERVED/BEGIN IMMEDIATE and stage changes but
needs EXCLUSIVE to COMMIT; timeout=0 means it can fail BUSY and roll back. The
reader must not release its snapshot early to let that writer commit and then
continue fetching bytes. WAL semantics are outside this profile.

A writer can commit between BEGIN and the reader's first actual read. The reader
then verifies the newer snapshot and rejects stale expected tokens. A writer
that committed before BEGIN behaves likewise. A writer committing after reader
closure does not invalidate the returned object's statement about its **old
snapshot**. It can make the object immediately stale for any later operation.

Snapshot-current means eligible at result.snapshot_head only. Still-current
later is **not guaranteed**. There is no durable applicability lease, authenticated
external checkpoint, independent freshness witness or protection against an
otherwise undetectable whole-file historical replacement from this API. Existing
protected-path/file-ID checks do not solve privileged/raw-disk adversaries.

Any future consequential operation must perform its own complete verification
in its own transaction, compare the exact store/global head, registry/policy,
source head, registration/capture/derivation and dependency identities, and
enforce its independently authorized workflow. Any change requires refusal and
an explicit new verified read/review. Do not trust isinstance, a prior result,
caller hash claims or matching text as a substitute. No such downstream operation
is authorized here, and read eligibility conveys no proposal or approval right.

## 7. Limits and full-replay cost

All existing hard ceilings apply; trusted configuration may only tighten them.

| Resource | Accepted ceiling preserved |
|---|---|
| Operation deadline | 60 seconds cumulative, including trust/snapshot/replay/selection/return admission. |
| Native document context | 10 seconds cumulative per (store, registry, SourceRef, capture sequence, handler hash, policy revision, policy Spec hash). |
| Database / events / registries | 256 MiB / 10,000 / 4. |
| Sources per registry | 16; existing all-history units, no eviction. |
| Captured originals | 2 MiB each; 32 MiB distinct aggregate. |
| Metadata | 128 MiB existing all-history distinct BLOBs plus event envelopes, including role overlap accounting. |
| Native / integration manifests | 8 MiB each per source; retained per-registry manifests 32 MiB with existing separate-role accounting. |
| Native text | 1,000,000 Unicode codepoints retained per registry. |
| Frozen codec and native execution | All existing byte/depth/node/string/array/input/output/transport/reader ceilings unchanged. |

In particular, the event codec retains its 8-MiB value, depth64/node100000/
array10000/string1MiB limits; native transport retains 32MiB/depth32/nodes500000/
array20000/string8MiB, input2MiB, metadata64KiB, stderr4KiB, plus exact frozen
DOCX/XLSX reader limits. No consumer setting can enlarge them.

With V historical VALID registrations, one complete replay performs **V fresh
bridge calls and 2V pinned worker parses**, including superseded VALID. PENDING
does not get parsed/validated by the read. Cost includes all events, captured
originals, other BLOBs and mirrors, not just target lookup; it is linear in
bounded history/bytes plus parsing cost, not O(1). Selecting from Replay.blobs
requires no extra native extraction. If a future implementation adds another
pass, it must disclose the extra cost and share the exact same VerificationBudget
and context, never reset 10 seconds or the absolute deadline (the R1 lesson).
No unchecked native observation cache is allowed, including after restart.

Proposed additional read-only egress bound: 24 MiB for the sum of the three
content byte fields (None counts zero), derivation.canonical and metadata bytes.
Metadata is at most 16 KiB, counted using existing C on the exact object with
keys snapshot_head, snapshot_registry, snapshot_source_head,
terminal_event_sequence, terminal_event_sha256, selection, applicability;
values are existing field mappings, SourceRef.data(), exact SheetSelection
field mapping or null, and the constant "snapshot_current". This encoding is
only a size calculation, **not a new persisted identity or hash preimage**.
Both ceilings are fixed tightening-only admission constants in the future
consumer, not new schema/catalog/codec configuration or truncation controls.

Existing text can occupy up to 4,000,000 UTF-8 bytes; two 8-MiB manifests plus
small reference/metadata fit within 24 MiB for supported target records. Retained
aggregate bounds still apply first. Never truncate to pass: any tighter limit
breach refuses the whole return. Full replay already holds all BLOBs; additional
owned copies and native transports add peak memory. These are byte-accounting
limits, not an independently enforced process RSS/Windows Job Object boundary.

## 8. Errors, refusal and retry

Proposed reuse of existing exported LedgerError subclasses; no new persistent
failure state or error payload containing text. Check precedence: strict argument/
closed/path/runtime checks; full snapshot verification; global token equality;
target existence and registry ownership; registry/source token equality;
applicability; exact materialization and final deadline/closure. Compute
applicability from S, but a stale token may be diagnosed before ineligibility.
This ordering cannot bypass full verification or return bytes early.

**For every refusal below: zero evidence bytes/partial DTO returned; zero ledger
events, BLOBs, counters, projections or other persistent modifications by the
reader.** Temporary native-worker I/O may already have occurred. Explicit retry
always requires a completely fresh verified transaction and tokens; no automatic
retry. Permanent integrity/profile failures require separate authorized
remediation, not fallback or retry with validation disabled.

| Condition/action | Proposed result | Retry qualification |
|---|---|---|
| Unknown registration, malformed/extraneous types, closed ledger | InvalidCommandError. | Correct command/open handle; fresh full read. |
| Foreign store global token | StaleWriteError (existing name also used for stale reads). | Obtain verified tokens for intended store; never transfer authority. |
| Foreign registry or expected_registry does not own target | InvalidCommandError. | Correct ownership, fresh full read. |
| Duplicate/mismatched identity in event history or projections | CorruptLedgerError. | No retry as trusted until authorized integrity investigation. |
| Captured or uncaptured PENDING; terminal FAILED | InvalidCommandError, after token checks. | Separate authorized validation/new registration may change eligibility; read never changes it. |
| Historical VALID, including newer PENDING/FAILED or late old completion | InvalidCommandError. | No older fallback; only a genuinely current VALID can succeed. |
| VALID in exhausted registry | InvalidCommandError. | No clearing exhaustion; separately authorized new scope required. RegistryExhaustedError would falsely imply this read committed an exhaustion event. |
| Obsolete policy, if otherwise supported | InvalidCommandError. | New registration under active policy, not in-place reinterpretation. |
| Presently unsupported policy/event/handler transition | UnsupportedLedgerError. | Separately reviewed implementation/profile required. |
| Wrong expected head, registry value or source-head value | StaleWriteError (ownership mismatch as above). | Explicit fresh full verification and new observations; never substitute new tokens silently. |
| Concurrent source.started commits before snapshot's first read | New snapshot verified; StaleWriteError for old tokens; no old evidence. | Fresh explicit read if newer target becomes eligible. |
| Writer attempts COMMIT during established snapshot | Writer may get BUSY and roll back; reader can complete its consistent old snapshot. | Writer behavior creates no reader write; post-close evidence has no lease. |
| Reader gets SQLite BUSY/LOCKED | LedgerBusyError. | Close failed transaction; fresh full read on explicit retry. |
| Missing/modified/extra/orphan BLOB; missing reference; mismatched mirror | CorruptLedgerError. | Investigate, no trusted partial read. |
| Forged/coherently rehashed text, manifest, reference or changed stamp | CorruptLedgerError when replay identity/bytes mismatch; unsupported trusted code is UnsupportedLedgerError. | No chain-only or cached acceptance. |
| Aliased BLOB identities | Legitimate same exact bytes may deduplicate under existing role rules; wrong-role substitutions/identity or reference mismatches refuse CorruptLedgerError. | No blanket rejection of valid exact-byte deduplication. |
| Native worker timeout/failed cleanup/unsupported environment | UnsupportedLedgerError for NativeBridgeError via existing mapping; LedgerLimitError if shared context/global budget detected exhaustion. | Fresh complete read only after cause resolved; no source.failed emitted. |
| Global/context deadline or return/resource bound exceeded | LedgerLimitError. | No partial return; fresh complete read may still be infeasible under same limits. |
| Result allocation fails or ledger lock cannot be acquired before deadline | LedgerLimitError; discard all partially allocated private buffers. | Fresh complete read only, with the same hard ceilings. |
| Sidecars, unverified filesystem/file-ID change, unknown recovery state | UnsupportedLedgerError. | Stop; no deletion, adoption or recovery. ADR-0012 remains blocked. |
| Original path deleted or modified after capture | Not an error: use retained captured bytes only; success if other gates pass. | Never reopen that path. |
| Previously returned object reused after newer commit | Old object remains exact at old head; it cannot authorize later current use. | Consequential operation must reverify and reject stale tokens. |
| Read transaction/connection cleanup error | Refuse with existing mapped LedgerError; no trusted object escapes. | Fresh full read after cause resolved; no unknown-write reconciliation claim. |

Wrong global tokens take precedence over later unknown-target/currentness errors
after full replay. Foreign registry means mismatched registry_id; same ID with
changed other fields is a stale registry value. Identity ambiguity in persisted
history is never downgraded to an ordinary caller error.
On an existing refusal, cleanup must preserve the original typed refusal while
still closing resources; if cleanup alone fails, map it using the existing
SQLite/OS error rules. Process cancellation may propagate without a result; it
never authorizes partially built evidence or any persistent side effect.

## 9. Read-only capability and historical exposure

All document text and manifest values remain untrusted data, never executable
instructions. Returning owned bytes to the explicit in-process caller authorizes
no export, logging, inference or downstream approval action.

Read opens no writable database connection and emits no events, derivations,
validation/failure/exhaustion terminals, capacity accounting or head changes.
It invokes no model, proposal/inventory/review construction, approval, export,
network, policy activation, migration or recovery. Document/manifest bodies and
text must never enter logs/errors; diagnostics use bounded static codes. Do not
log caller/source identifiers that could contain sensitive text without a
separately authorized logging policy. There are no new worker privileges.

Full verification still uses the pinned bridge's private, bounded temporary
captured-byte file and worker transport outside Git, fixed isolated Python
derive/verify workers, identity comparisons and cleanup. This controlled I/O is
permitted and already required; **the operation is not temp-I/O-free**. It is
not a general hostile native sandbox and supplies no new privileges, external
service, mutable original path or production recovery authority. Both worker
passes execute the same pinned reader, not independently developed semantic
parsers; they do not establish visual completeness or general Office compatibility.

Historical/forensic inspection is a **separate future-only unresolved capability**.
No new historical API is implemented or authorized. Existing load metadata and
original_blobs remain accessible as before and may describe old VALID, but do
not produce an eligible current-evidence object. A later forensic design needs
explicit use cases/authority, old-policy context, access/retention controls and
a distinct result that cannot automatically enter a proposal consumer. No last
known good switch or historical fallback belongs in this method.

## 10. Later implementation acceptance matrix

Every row specifies precondition, action, eligibility, bytes/refusal and effects.
**R** means refusal: no evidence bytes, no partial object, no persistent mutation;
**S** means exact immutable bytes from the same verified snapshot, no persistent
mutation. **N** means no model/domain/proposal/review/approval/export/network/
recovery action; controlled native temp I/O allowed. N applies to every row.
"Prerequisite today" does not claim that a consumer test exists or has passed.
The future method must be tested for every row before activation.

| Precondition | Input/action | Eligibility and bytes | Database/external effects | Executable today vs future gate |
|---|---|---|---|---|
| Current DOCX VALID | Read exact tokens; complete and coverage goldens | E; S text, null native manifest, exact integration. | None; N. | Native/persistent goldens and new live-snapshot prerequisite today; DTO/API future. |
| Current XLSX VALID | Complete/blank/missing/empty_text/coverage goldens | E; S text plus both exact manifests. | None; N. | All five native/persistent golden prerequisites today; consumer future. |
| DOCX empty paragraphs/cells and Unicode | Read coverage; compare exact UTF-8, ordering, locators/offsets, no trim/NFC | E; S includes empty structure. | None; N. | Frozen vectors/live snapshot today; consumer preservation future. |
| XLSX empty kinds and multiple sheets | Compare BLANK/missing/TEXT empty, coordinates, selected identity and all-sheet coverage | E; S preserves differences and nested native JSON string. | None; N. | Frozen vectors/live snapshot today; return checks future. |
| Uncaptured PENDING | Call with fresh tokens | Ineligible; R InvalidCommandError. | No capture/validation; N. | Existing currentness/validation prerequisites; API refusal future. |
| Captured PENDING | Call with fresh tokens | Ineligible; R InvalidCommandError. | No native validation of PENDING; N. | Existing replay prerequisite; API future. |
| FAILED from capture or validation | Call fresh | Ineligible; R InvalidCommandError. | No replacement terminal; N. | Existing state tests; API future. |
| Older VALID, newer PENDING | Read old then new using fresh tokens | Both ineligible; R. | No fallback; N. | Existing/new currentness prerequisites; API future. |
| Older VALID, newer FAILED | Read both fresh | Both ineligible; R. | No fallback; N. | Existing currentness prerequisites; API future. |
| Older completion after newer source.started | Complete old with fresh tokens, then read old | Historical VALID, R; newer head unchanged. | Only explicit setup writer emits terminal; reader none; N. | Existing late-completion tests; consumer future. |
| VALID and registry exhausted | Read fresh | Ineligible, R, no durable exhaustion exception. | No accounting/event changes; N. | Existing exhausted replay tests; consumer future. |
| Historical VALID old policy | Feed unsupported transition today; future supported history with stale policy | Today entire replay refuses UnsupportedLedgerError; future target ineligible/R. | No policy activation by reader; N. | Unsupported transition tests today; supported obsolete-policy history separately blocked/future. |
| Unknown/foreign identity or closed handle | Exact typed but absent ref, foreign store/registry, malformed tokens | R with section 8 precedence. | None; N. | Type/ownership prerequisites; consumer future. |
| Current VALID, stale global token | Change one head field | R StaleWriteError. | None; N. | Writer token prerequisites today; read token tests future. |
| Current VALID, stale registry token | Change each field independently | R StaleWriteError; wrong registry_id InvalidCommandError. | None; N. | Existing tokens today; read tests future. |
| Current VALID, wrong source token | Change source_id/revision/registration_id | R StaleWriteError. | None; N. | Existing tokens today; read tests future. |
| Writer commits after BEGIN, before first read | Start newer revision then establish snapshot | New head, old tokens stale/R. | Only setup writer commits; reader none; N. | New deterministic deferred-BEGIN prerequisite today; consumer future. |
| Established reader snapshot | Real writer attempts COMMIT while reader held | Reader S at held head; writer BUSY/rollback; or reader refuses own error, never mixes heads. | Reader none; failed writer unchanged; N. | New real SQLite contention prerequisite today; consumer future. |
| Observation H then second connection at H+1 | Start new PENDING between reads | Old result only describes H; no current read at H+1 for old ref. | Setup event only; N. | New two-connection/no-lease prerequisite today; consumer must prevent pattern. |
| Returned evidence, later source.started | Later consequential use | Stale old object cannot authorize action; R by fresh downstream verification. | No consequential action from stale object; N. | Snapshot prerequisite today; downstream operation unimplemented. |
| Original path removed/modified | Replay/read after capture | E unchanged if target otherwise current; S captured exact bytes. | No original path access; N. | Existing and new deletion tests today; API future. |
| Coherently rehashed false native text/manifest/ref | Alter disposable store chain and mirrors coherently | R despite chain consistency. | No repair/write by read; N. | Existing adversarial persistent replay tests; consumer refusal future. |
| Missing/extra/wrong-role BLOB or terminal/projection | Alter each disposable field; also test legitimate exact-byte dedup | R for corruption; legitimate dedup S if E. | No mirror rebuild; N. | Existing closure/forgery tests; consumer future. |
| Changed stamp/ownership/incomplete history/unknown event | Alter disposable store | Whole snapshot R, even unrelated to target. | No salvage; N. | Existing replay tests; consumer future. |
| Restarted store with current and historical VALID | Open and read, spy real bridge/workers | V calls/2V parses, every historical VALID; S only for E. | No implicit PENDING validation; N. | Existing restart + new V=2 prerequisite today; consumer future. |
| Native timeout or unavailable pinned handler | Deterministic failure during real replay boundary | R, no partial bytes; typed errors section 8. | No source.failed; N. | Existing replay/budget tests; consumer future. |
| Global 60s/context 10s exhausted | Deterministic accumulated clock, including final copying | R LedgerLimitError, no budget reset. | All rows unchanged; N. | R1 replay tests today; read selection/copy budget gate future. |
| Return, DB, original, metadata/manifest/text/event/registry ceiling | Tighten/oversize each relevant boundary | R, never truncate/evict/skip history. | No exhaustion event on read; N. | Existing resource prerequisites; new return-cap tests future. |
| Read-only transaction | Instrument mode=ro, query_only, authorizer/trace; attempt denied write | S only if E; denied write cannot persist. | Exact rows/file unchanged, no write SQL in real consumer; N. | New mode/query_only/write-refusal prerequisite today; consumer command trace/authorizer gate future. |
| BUSY/LOCKED, sidecar, file identity or cleanup failure | Controlled disposable fault | R, no recovery/sidecar removal. | No reader writes; N. | Existing filesystem/SQL prerequisites; consumer future. |
| Side-effect sentinels around success and every refusal | Spy inference, domain, staging, approval, exports, network and recovery | S or R solely by eligibility; zero sentinel calls. | N with documented worker temp I/O only. | Existing component isolation; consumer sentinels future. |
| Authentic historical A0 artifacts and seven literal vectors | Run original historical producer/readonly proofs; all pinned goldens | Compatibility only, not schema-3 current-evidence authorization. | Disposable tests/readonly historical proof only; N. | Executable today; must remain passing after future changes. |

## 11. Implementation blockers and review gates

Before a later implementation may be accepted: independently review this exact
contract; implement only the bounded read DTO/orchestration; execute every future
matrix row including token precedence, exact bytes, read-only side effects,
selection-copy deadlines/egress cap and cleanup/concurrency faults; retain full
historical/A0/native proof identities; measure full replay/peak-memory cost on
the approved Windows profile. No unchecked cache or wider API may bypass these
gates. The optional tests in this task establish prerequisites, not API readiness.

Production source authenticity, external freshness, privileged filesystem custody,
general hostile-parser isolation, operational recovery and historical exposure
authority remain unresolved beyond this bounded synthetic contract. Proposal
materialization/persistence, inventory, review/approval, inference and export
require their own later authorization and freshness/provenance contracts.
No BSI baseline or certification assertion follows from this design.

Actual test results, artifact SHA-256 identities, baseline/status and exact
reproduction commands are in [TASK-0073B252-RESULTS](../tasks/TASK-0073B252-RESULTS.md).
