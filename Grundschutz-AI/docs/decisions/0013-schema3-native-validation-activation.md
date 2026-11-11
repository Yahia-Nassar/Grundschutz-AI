# ADR-0013 — Schema-3 persistent native validation activation contract

**Status: PROPOSED; independent contract review required.** TASK-007.3B.2.5.0,
2026-11-11, baseline `b310430f5be52b5e5790a5a991e1993249f12ccf`. This is a
documentation-only implementation contract. It activates no event, writer,
replayer, persistent derivation, policy command or approval pathway.
Actual verification: [TASK-0073B250-RESULTS](../tasks/TASK-0073B250-RESULTS.md).

Predecessors: [ADR-0008](0008-document-proposal-boundary.md),
[ADR-0009](0009-structural-evidence-and-sqlite-v2.md),
[ADR-0010](0010-historical-implementation-compatibility.md),
[ADR-0011](0011-verified-source-validation-profile.md),
[ADR-0012](0012-schema3-crash-recovery-contract.md).
ADR-0011 owns the existing derivation-ref/v2, source-valid/v1 and meaning of
VALID. This ADR makes their later activation obligations explicit, without
changing their preimages, SQL or approved native identities. ADR-0012 remains
PROPOSED; operational recovery is **NOT_OPERATIONALLY_AUTHORIZED**, independently
of any future native validation capability.

## 1. Existing boundary and release prerequisites

Today v3_codec recognizes source.validated syntax and derivation-ref/v2, but
_v3_capture.Replay rejects source.validated, policy.activated and post-capture
validation failures. SourceLedger has no validate_source method. Its existing
successful captures remain PENDING, including after restart; no reader executes
on capture/load. load_initialized_store remains genesis-only. Empty derivations
tables and valid codec objects convey no processing authority.

The future fixed command allowlist must be separately implemented and accepted
with complete writer/replay tests. An existing native catalog capability
extract_captured_bytes permits native mechanics, not persistent validation by
itself. Do not add a capability, descriptor member, handler, codec tag or schema
flag as an informal activation shortcut. Gate A entries remain read-only only.

| Frozen release contract | Identity |
|---|---|
| Physical profile / schema | sqlite-source-validation/v1 / user_version=3, feature_profile=verified-source/v1 |
| Physical schema fingerprint | `75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c` |
| Native golden fixture | 106,955 exact UTF-8 bytes; `553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b` |
| DOCX native handler | a0-docx-native/v1; `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` |
| DOCX reader Spec | `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c` |
| XLSX native handler | a0-xlsx-native/v1; `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` |
| XLSX reader Spec | `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2` |
| Host / canonical event | Windows fixed-local NTFS/ReFS admission, Python 3.12.6, SQLite 3.45.3, LF artifact pins; canonical-json/v1 / ledger-event/v3 |

Exact catalog descriptors/artifact pins and frozen policy constructors are used,
not recomputed enrollment from whatever code happens to be installed. The four
profiles remain two historical source_ledger_read and two native
extract_captured_bytes entries. All source text stays untrusted. Structural VALID
does not prove inventory assertions, source authenticity, visual completeness,
scope eligibility, human approval or BSI compliance. No automatic Ollama call.

## 2. Exact future command and immutable outcome

The following is a **proposed signature, not a runnable API**:

```python
def validate_source(
    self, ref: SourceRef, *,
    expected: LedgerHead,
    expected_registry: RegistryState,
    expected_source: SourceRef,
    actor_id: str,
) -> ValidationOutcome:
    ...  # Proposed SourceLedger method; not implemented.
```

The receiver already owns a trusted existing schema-3 path and tightening-only
LedgerLimits. No path creation, document path, caller observations, parser
result, hash, policy override, selection override, timestamp, executable/module
name, failure code or cached derivation is accepted by this command. actor_id is
required bounded audit text, not authenticated identity or human approval. New
validation requires explicit invocation, including after capture/restart. There
is no generic append-event API, startup validation or recovery validation.

Require exact typed tokens, including complete registry counters/epoch/exhaustion
and active policy, not just registry ID. expected_source must be the nonnull
highest-started head for ref.source_id and may be newer than ref. Verify ownership,
exact SourceRef, no terminal row, completed source.captured event and BLOB with
recomputed SHA/length, PENDING state, unexhausted registry, enrolled exact native
handler/reader availability and registration policy still active. Resolve the
effective policy and DOCX-null/XLSX-exact selection solely from verified events.
The source.captured event itself never confers VALID.

Proposed ValidationOutcome is frozen/slotted, with exact validated fields:

| Field | Type and meaning |
|---|---|
| head | LedgerHead of the one committed terminal event; never a speculative head. |
| registration | Exact target SourceRef. |
| capture_event_sequence | Positive integer, verified existing capture of this target. |
| terminal_event_sequence, terminal_event_sha256, transaction_id | Positive integer equal to head.sequence; exact head hash; lowercase 32-hex singleton transaction identity. |
| state | Typed closed enum: VALID (`valid`) or FAILED (`failed`); never a free string or review state. |
| derivation | Exact immutable v3_codec.DerivationRef for VALID; null for FAILED. |
| failure_phase, issue_codes | VALID: null and empty tuple. FAILED here: `validation` and nonempty bounded tuple of permitted known codes from section 7. |
| source_head_at_completion | Highest-started SourceRef at commit, including a newer registration; not a replacement source head. |
| registry | Complete committed RegistryState including terminal epoch/accounting. |

No raw text/manifests, proposal, Evidence, Inventory, ReviewRecord or approved
view is returned. The result reports committed processing metadata; it is not
an authentication capability. A control-only exhaustion commit raises the existing
RegistryExhaustedError (reload required); it never returns a fake VALID/FAILED
outcome. Errors and uncertain acknowledgements follow sections 7–8.

## 3. Derivation and exact byte representations

Let C be unchanged canonical-json/v1, S exact-byte SHA-256, and
H(t,v)=S(C({"type":t,"value":v})). Use exactly the existing complete reference:

```text
type = "derivation-ref/v2"
store_uuid, registry_id
registration = {source_id, revision, registration_id}
kind = "docx" | "xlsx"
capture_event_sequence
binary_sha256, byte_length
reader_spec_hash, handler_spec_hash
policy_revision, policy_spec_hash, policy_fingerprint
reader_limits_sha256
reader_method, reader_implementation_sha256
native_text_sha256
native_manifest_sha256
integration_manifest_sha256
```

Required members stay present, with DOCX native_manifest_sha256=null. No additional
member or new version. IDs/hashes/integers/nulls use the existing strict codec.
derivation_sha256 is H("derivation-ref/v2", complete object **without type**).
derivation_blob_sha256 is S(C(complete object **with type**)); these are distinct
identities. reader_limits_sha256 is H("reader-limits/v1", complete historical
reader-limits dictionary). Policy Spec identity and frozen A0 staging fingerprint
remain distinct. reader_implementation_sha256 is the pinned reader_stamp hash of
the historical Python/reader/OOXML preimage, not handler_spec_hash.

| Content BLOB / relationship | Exact required representation |
|---|---|
| Original | Already committed immutable capture bytes; compare hash/length and exact dedup equality. Never overwrite, reopen an original path or reconstruct an original from text. |
| Native text | Exact native.text encoded strict UTF-8, no BOM, normalization, trimming, case folding, newline addition or repair. Address by S(bytes). Retain empty text as a real empty BLOB when emitted. |
| DOCX native manifest | Hash/reference **and BLOB absent/null**; no fabricated `{}`, empty manifest or new native-manifest format. |
| XLSX native manifest | Exact pinned native.manifest_json.encode('utf-8') bytes, S(bytes). All worksheets/rows/cells retained. |
| Integration | Exact pinned manifests()/wire_dump output bytes, S(bytes), docx-integration/v1 or xlsx-integration/v1. No reserialization through ledger payload codecs. |
| XLSX nested manifest | xlsx-integration/v1 native_manifest_json remains a JSON **string**, including exact escaping. Do not turn it into an object or double-normalize it. |
| Reference | C(full derivation-ref/v2) BLOB, addressed by derivation_blob_sha256; SQL columns exactly agree with it and all parent/event bindings. |

Reference/payload codecs retain their current 1-MiB string cap. Manifests are
bounded opaque bytes, compared to freshly reconstructed pinned output; do not
decode multi-MiB nested manifest strings using the ledger decoder or enlarge it.
Repeated content shares a BLOB only after recomputed digest, length and exact-byte
equality. Each registration has a distinct derivation reference because its
SourceRef/capture identity is included, even for identical bytes. Source/store/
registry identities cannot be transplanted. Binary repackaging with the same
native text still changes binary and integration bindings and the derivation.

## 4. Fixed event and transaction algorithm

Use only source.validated with exact source-valid/v1 fields:

```text
payload_codec = "source-valid/v1"
registration
capture_event_sequence
derivation_sha256
derivation_blob_sha256
source_head_at_validation
observed_at
```

observed_at is trusted-command UTC YYYY-MM-DDTHH:MM:SS.ffffffZ, equal to envelope
occurred_at. source_head_at_validation is the exact highest-started SourceRef at
this event's historical position, **not necessarily registration**. Envelope uses
unchanged ledger-event/v3 hashing, unique event/transaction IDs, contiguous sequence
and transaction_index=transaction_count=1. The command supplies actor_id; existing
codec allowance of null machine actors does not add an unauthenticated command.

Proposed ordered operation, with one absolute command deadline from entry:

1. Under the existing instance lock, check liveness/path/file identity, sidecar
   refusal, reviewed host/artifacts, exact schema/FKs/integrity and complete
   read-only replay in a consistent snapshot. Verify every prior VALID from raw
   captured bytes as described in section 5; no trusted partial prefix.
2. Compare all three caller tokens. Check target eligibility/ownership, capture,
   handler, selection and active policy. Verify captured raw bytes/hash/length.
3. Close the RO snapshot. Invoke only the pinned extract_captured_bytes bridge on
   these verified bytes with registration source ID, exact handler/reader, stored
   policy, expected capture digest/length and stored selection. No original path.
   Use the remaining shared limits/deadlines. Worker derive/verify passes plus
   parent reconstruction must finish; a constructed DTO alone is not proof.
4. Privately build native UTF-8/manifests/reference from that verified observation.
   It remains speculative and cannot be returned/cached as authoritative. A known
   permitted target failure may instead prepare the narrowly defined A outcome;
   ambiguous worker/environment failures take B, without opening a write handle.
5. Open the checked existing DB with DELETE/FULL, foreign_keys=ON,
   trusted_schema=OFF, zero busy retry; BEGIN IMMEDIATE. Recheck file/store identity
   and perform **fresh complete replay**, then compare all original expected
   tokens again. Any intervening event, even unrelated, can make them stale.
6. Recheck target/capture unchanged, current policy/handler/head, unexhausted
   registry, counters, content role sets, available reserved capacity and deadline.
   Do not silently retry/rebase or reuse a stale parse in another command.
7. Before writes choose exactly one prospective event: VALID, an eligible known
   validation FAILED, or verified registry.exhausted when a permitted aggregate
   capacity check fails. C replaces the requested operation; never append both.
8. For VALID, atomically insert exact deduplicated new text/native/integration/
   reference and payload BLOBs, derivations row, valid source_terminals row and
   event. Preserve source_captures/originals and all past rows. Deferred FKs allow
   insertion order; only the three mutable projections may be rebuilt.
9. Preserve the existing mirror rebuild discipline: full replay with mirror
   comparison disabled reconstructs expected rows (including **fresh native
   re-extraction**), then apply exact allowed mirror additions/projections. Perform
   another full replay with every stored mirror compared before commit. Check
   BLOB closure, capacity, DB page/size and time bounds after actual SQL writes.
10. COMMIT once, close transaction resources and return the verified committed
    outcome. On any precommit failure ROLLBACK/close and return no trusted result.
    If commit acknowledgement is uncertain, follow section 8; no repair event.

Precommit obligations include exact reference/event/BLOB/terminal correspondence,
all native coverage/manifests rederived, complete historical policy/handler
interpretation, highest-started projection, no orphan/unknown rows or BLOBs,
reserved event/metadata capacity, role-based counters and unchanged trust/runtime.
No duplicate completion, implicit source failure, local cache, hash chain alone
or SQL CHECK alone satisfies them.

**Write-lock cost:** with V historical VALID registrations and a successful new
VALID, this algorithm makes V native bridge calls in initial RO replay, one target
call before BEGIN, V in fresh locked replay, V+1 in mirror-building replay and
V+1 in final precommit replay: **4V+3 bridge calls total, 3V+2 under the lock**.
Each bridge call has two pinned worker parses. Even V=0 therefore has six worker
passes, four under the write lock. No cross-pass native cache is independently
trusted. Failure/control paths do not parse a new VALID but still verify existing
history. Do not layer the current _write's extra RO preflight on top and silently
omit its cost: a later private orchestrator must implement this exact sequence,
or separately account for/review additional full passes. Any optimization avoiding
these verifications requires a separate private-proof design and acceptance.

## 5. Complete replay and compatibility

A future trusted load uses one consistent RO snapshot, one shared deadline and
the unchanged filesystem/sidecar/DDL/codec checks. Process all events in global
order; verify unique singleton transaction identities, payload/envelope/chain
hashes, store UUID, registered Specs/handler availability, historical policies,
starts, captures, terminals, counters and exact SQL mirrors. Recompute every
referenced BLOB's digest/length, require exact byte equality on reuse and reject
orphan/unknown rows/BLOBs. Do not return a verified prefix on any failure.

At **every source.validated event**, require a captured PENDING/nonterminal target,
earlier exact capture event, then-active matching policy, enrolled exact handler
and source_head_at_validation equal to the highest start seen **at that event**.
Re-extract its exact captured bytes using that historical policy/reader/handler
and selection on every complete trusted load. Reconstruct exact native text,
all observations, reader stamp, native/integration bytes and complete reference;
compare all SQL columns/references/BLOB bytes. Native worker observations are never
an independently trusted stored cache. Terminal FAILED is a recorded bounded
attempt outcome, not a promise that a timeout will reproduce on every load.
For this proposed first activation, the additional failure transition is only
captured PENDING -> FAILED with phase=validation and issue_codes=[parse_timeout],
under section 7's conditions; preserve the existing pre-capture failure rules.
The current capture-only check requiring no capture on every FAILED must not be
reused for this new transition. Other recognized failure phases/codes remain
inert until their named workflow/classification is independently accepted.

Rebuild source_heads from source.started only; completion never updates its
last_event to the terminal event. Retain older VALID as historical state, with
explicit applicability blocks. A verified PENDING/FAILED/policy-blocked/exhausted
history may be returned as blocked, but an unverifiable VALID refuses the whole
trusted load. No automatic validation of PENDING or fallback to old VALID.

Preserve genesis-only load_initialized_store and full schema-3 genesis/capture
compatibility. Preserve schema-2 verification via frozen v2_compat/A0; never
execute current native validation for historical A0 captures. No migration,
SQL/schema rewrite, catalog expansion or changed source identity/preimage.
Current source.validated rejection remains until a separately accepted release.

## 6. State/currentness and coverage matrices

Here historical VALID means a committed structural validation verified under its
historical interpretation. Currently applicable VALID additionally requires the
target is the highest-started head, exact active policy revision/Spec/fingerprint
still matches, registry is unexhausted and complete current verification succeeds.
It still supplies no proposal/inventory/review/export authority.

| Situation | Future command / replay effect | Current applicability |
|---|---|---|
| Uncaptured PENDING | validate refuses InvalidCommandError before target reader; no event/hash invented. | Blocked; reopening never restores original-path capture authority. |
| Captured PENDING | Explicit validation may commit one VALID or eligible A/C; load alone leaves PENDING. | Blocked until complete valid commit and applicable context. |
| VALID at current head under same active policy | Immutable historical VALID; every complete load re-extracts. | Native applicability only, no human approval. |
| VALID or FAILED target receives duplicate completion | InvalidCommandError; zero writes/reader work for target. | Terminal state not overwritten. New registration required. |
| Newer PENDING starts after older VALID | Head immediately newer; old historical VALID retained. | No fallback, including when new source is uncaptured. |
| Newer FAILED head after older VALID | Failed latest head retained. | No fallback to old VALID. |
| Older completion after newer start | Old stale invocation refuses atomically. Explicit fresh-token reissue may complete old ref if its policy still active; payload binds newer source head. | Newer remains head, including PENDING/FAILED; old result historical only. |
| Policy changes during target processing | Changed global/registry tokens cause StaleWriteError; no terminal event. | Capture remains PENDING. No automatic retry. |
| Fresh-token reissue for target registered under obsolete policy | InvalidCommandError, even if two revisions share config/hash; active revision must match. | Explicit new registration/capture under active policy required. |
| Policy changes after a VALID | Historical validation replays with its then-active policy, not new limits/defaults. | Blocked if active revision/Spec/fingerprint differs. |
| Identical original bytes / later return to earlier bytes | New SourceRef/capture/derivation required, equality-checked BLOB dedup only. | No old validation/token reuse. |
| Registry exhausted | Terminal block; history still fully verified, new completion refused. | Blocked; no counter reclamation/reset. |

Policy activation beyond revision 1 is **not currently implemented**. This matrix
defines the ADR-0011 semantics for later verified transition replay and tests;
it does not add a policy API or permit forged test SQL as an application writer.
Policy transition activation/fixtures need separate trusted implementation/review
before claiming these cases have executable persistent proof.

| Format | Complete retained native coverage / anti-forgery check |
|---|---|
| DOCX | Ordered body paragraphs and table-cell paragraphs, all emitted empty paragraphs/cells, exact text/hash and full part/body_index/paragraph_index/table_index/row_index/cell_index/char_start/char_end locators. One-based structural indices; zero-based half-open segment-local Unicode codepoints. Empty spans retained; no PDF page numbers or XML-byte offsets invented. Unsupported/tracked/alternate content fails under the pinned reader. |
| XLSX | Trusted full selection tuple name/ordinal/sheet_id/relationship_id/part must match exactly one actual native sheet. Retain all ordered sheets, row_indices, cells, coordinates/row/column/kind/text/hash, including empty/unselected sheets. Cell-local offsets derive from exact native cell text and pinned locator semantics, not added JSON fields. Native manifest and nested integration string stay exact. |
| BLANK/missing/TEXT empty | Absent cell is no record; physically BLANK has its BLANK record; TEXT "" remains TEXT. Equal text hash does not make native manifests equal. No null conversion or staging table-header restriction is added to Gate B. |
| Coherent forged artifacts | Every full replay re-extracts raw bytes and compares complete observations/serialization/reference, not merely claimed hashes. Detect moved locators/cells, dropped empty structure/sheets, altered reader stamps, false selection and coherently rehashed manifests/mirrors. |
| Repackaged binary | Native text/native XLSX manifest may match; binary/capture and integration/reference must bind the new exact bytes. |

Two workers and repeated loads share the same pinned parser implementation. They
are independent executions, **not independently developed semantic parsers**.
Neither golden equality nor re-extraction proves real-world document truth,
authentic authorship, unrestricted Office compatibility or visual completeness.

## 7. Failure, refusal and control-event matrix

A = explicit fully verified source.failed/validation transaction, with one terminal
FAILED row, known issue tuple, preserved existing capture and no derivation.
B = refusal without terminal/event/BLOB/projection effects; captured PENDING stays
PENDING (or existing terminal remains unchanged). C = verified durable one-event
registry.exhausted transaction in existing reserved capacity; no target terminal,
capture stays PENDING but registry becomes blocked. No event is durable until its
actual commit is known to have succeeded.

| Condition | Exact proposed outcome and error / event |
|---|---|
| Known invalid_source / unsupported_structure observation under trusted bounded validation | A permitted by ADR-0011 only if classification is actually verified. **Current pinned bridge collapses parser and other child errors to exit 2 / worker_failed; this alone is insufficient. With today's error channel choose B, UnsupportedLedgerError with static diagnostic, preserve PENDING.** Precise authenticated bounded classification is an unresolved later review dependency; no parent parser bypass or invented worker protocol/pin here. |
| Explicit initial target worker_timeout with otherwise verified environment/context and sufficient total budget | A may commit `phase=validation, issue_codes=[parse_timeout]` after fresh tokens/full prestate verification and failure precommit replay. It records a bounded attempt, not proof the document is invalid. No A if timeout classification or cleanup/worker termination is uncertain. |
| Timeout/failure while replaying existing VALID, or new VALID precommit re-extraction disagrees/fails | B: entire load/command refused, no rewrite of VALID into FAILED. CorruptLedgerError for inconsistent verified bytes; UnsupportedLedgerError for unavailable trusted execution; LedgerLimitError for cumulative budget exhaustion. |
| Worker protocol/ack error, generic worker_failed/native_refused, transport/cleanup error, unknown exception | B: UnsupportedLedgerError/static native diagnostic; no fabricated invalid_source/source.failed. Known host/artifact/handler mismatch likewise refuses before native dispatch. |
| Missing capture, already VALID/FAILED, wrong ref/ownership, fresh request under inactive registration policy | B: InvalidCommandError; no target parse/completion. |
| Stale global/registry/source token, intervening policy event | B: StaleWriteError; rollback all speculative work, no automatic retry. |
| Corrupt BLOB, manifest, reference, mirror, impossible history or missing registered dependency | B: CorruptLedgerError; whole trusted replay refused, no failure event masking corruption. |
| SQLite BUSY/LOCKED, or SQL/write/FK/page-size failure with confirmed rollback | B: LedgerBusyError for contention, otherwise typed ledger refusal; no durable event, source remains PENDING. No second failure/control transaction as error handling. |
| Fully verified new derivation would exceed global metadata/events or registry aggregate text/manifests | C only if fresh active context, exact prospective accounting and control reserve fit. budget_name is existing `events`, `metadata_bytes` or `policy_capacity` for text/manifests. Otherwise B/LedgerLimitError. Never introduce `text_chars`/`manifest_bytes` codec enum values. |
| Per-document output/reader/serialization limit fails before fully verified candidate, or no time to verify all history/control | B: LedgerLimitError or static unsupported native refusal as appropriate; do not infer durable registry exhaustion from unverified observations. |
| Registry already exhausted | B: RegistryExhaustedError; reload confirms prior durable block, no new event. |
| Reserved control write fails, or control would exceed its own hard DB/event/metadata limits | B/LedgerLimitError or SQL refusal; original registry not claimed exhausted by this attempt. |
| Explicit abandonment/environment/capacity issue strings submitted by caller | Not an argument to validate_source. Other source-fail/v2 phases/codes remain syntactic contracts, not a new failure API. |

Successful A returns the FAILED ValidationOutcome, not an exception concealing a
committed failure. Successful C raises RegistryExhaustedError with reload required.
For C, registry epoch increments once, exhausted becomes true, history reservations
are not reclaimed; no derivation count/text charge. For A, registry epoch increments
once, capture/history reservation and bytes remain, no derivation count increase.
Neither a parser exception nor SQL exception automatically commits A or C. Every
chosen path still needs full prestate/token/capacity and precommit verification.

## 8. Crash, rollback and acknowledgement reconciliation

Before COMMIT, interruptions expose only the prior committed capture/PENDING
state after separately qualified copy-only investigation. Never synthesize a
FAILED/VALID, missing BLOB or replacement event to reconcile a rollback. Ordinary
startup/load still refuses sidecars; no recovery is invoked by validation.

If COMMIT returned successfully but the response is lost, the exact one terminal
event and its complete derivation must survive together. Reload must re-extract
VALID. Reconcile separately retained command intent against store UUID, prior
head, target SourceRef, capture hash/sequence and intended derivation/transaction;
never resend old tokens or recapture automatically. A fresh duplicate completion
still refuses rather than creating a second terminal.

If COMMIT/connection-close outcome cannot establish whether commit succeeded,
the future API must raise proposed CommitOutcomeUnknownError (a LedgerError,
**not implemented today**) carrying only bounded exact command intent/reference
metadata, never a claimed committed head/state. Do not assert rollback merely
because the client saw an exception. Close resources, prohibit automatic retry
and require verified reconciliation. Local readable history does not authenticate
freshness: missing suffix/forks and independent custody/checkpoints remain the
ADR-0012 blockers. No synthetic acknowledgement or operational recovery is added.

## 9. Resource and execution budget contract

| Resource | Hard ceiling and proposed enforcement |
|---|---|
| Main database | 256 MiB, trusted tightening only; initial file/page checks and precommit actual page_count × page_size bound. Roll back an oversized prospective write; do not assume journal/temp/disk allocation is bounded by main DB size. |
| Original bytes | 2 MiB/source, 32 MiB global all-history unique raw bytes; preserve already captured originals. Validation adds no original read or raw bytes. Per-registry retained raw policy applies too. |
| Events / registries / sources | 10,000 events, 4 registries, 16 logical sources/registry. Normal event ceiling max_events−max_registries (9,996 defaults); reserve one event plus 1 KiB per configured registry for terminal control. No new registry/source from validation. |
| Metadata | 128 MiB global cumulative unique metadata/reference/text/manifest/spec/payload BLOBs **plus every canonical envelope's bytes**. Keep 1 KiB/registry control reserve for normal writes. No orphan BLOB inserted for an abandoned derivation. |
| Native / integration manifest | Separately <=8 MiB each, additionally tightened policy max_manifest_bytes. Pinned wire output cap 32 MiB and existing wire/reader string/node limits may refuse earlier; never raise them to reach a ceiling. |
| Registry retention | <=32 MiB retained manifests, <=1,000,000 native text Unicode codepoints, all-history unique per content role; old revisions never evicted. |
| History / epoch | source.started already reserves 3 units for start/capture/one terminal; validation adds no new reservation or reclaimed credit. VALID increments epoch/derivation_count once plus distinct text/manifest charges. Policy activation has its separate existing epoch/history rule. |
| Canonical codec | Unchanged 8 MiB input, depth 64, 100,000 nodes, 10,000 members, 1 MiB/string. Manifest bytes use pinned bounded serializers, not relaxed ledger decoding. |
| Native wire | Existing 64 KiB metadata, 2 MiB input, 32 MiB output, 4 KiB stderr; depth 32, 500,000 nodes, 20,000 members, 8 MiB/string. Two worker passes share the same remaining bridge deadline. |
| Native processing | <=10 seconds/document context. Conservatively share this allowance across repeated passes of the same (store,registration,capture,handler,policy) in one command/load, rather than granting another 10 seconds on each replay. This tightens, never raises, ADR-0011's ceiling; performance acceptance must measure it. |
| Complete command/load | <=60 seconds cumulative admission deadline from entry, including trust checks, SQL/full replay, each native pass, serialization, transport and commit checks. No new 60-second allowance per pass or event. Refuse full load if complete history cannot fit. |

Global raw and metadata sets are distinct **roles**: a shared physical BLOB counts
against each applicable role budget. Within global metadata union count identical
content once, plus envelope bytes separately. Per registry count unique raw and
unique native-text digests separately; native and integration manifest role sets
are each distinct, so a cross-role reuse must satisfy both role charges even if
physical bytes coincide. Same content reused in another registry counts in that
registry too. derivation_count counts registrations, not unique text. Always verify
exact bytes before dedup; content-address equality alone does not grant reuse.

The current capture-only SQL admission heuristic `blob_count <= 2*events+8`
assumes no derived content and is not a valid general bound after activation.
A later verifier must derive a safe admission count from the unchanged event
roles: at most E payload BLOBs, one additional descriptor/policy/raw BLOB per
implementation/handler/registry/policy/capture event, and at most four additional
BLOBs (reference, text, native, integration) per VALID event. Thus use the
role-derived upper bound n_event+n_impl+n_handler+n_registry+n_policy+n_capture+4*n_valid
before allocation, followed by exact
replayed reference closure; dedup can only reduce this count. Untrusted SQL kind
counts are admission hints, never event authority. This replaces an inapplicable
capture-only heuristic, **not** the fixed byte/event/schema/codec ceilings; it
requires explicit later tests/review and no change in this task. The current
8-MiB largest-BLOB admission cap remains sufficient for all permitted roles.

Freeze complete historical reader limits (no current-default substitution):

| Common fields | Exact ceiling |
|---|---|
| max_file_bytes, max_uncompressed_bytes, max_ratio | 2,097,152; 8,388,608; 100 |
| max_xml_bytes, max_xml_chars | 2,097,152 each |
| max_xml_depth, max_xml_nodes, max_xml_attributes | 32; 20,000; 16 |
| max_attribute_chars, max_namespaces, max_text_chars | 4,096; 32; 1,000,000 |
| DOCX-specific | max_entries=16, max_segment_chars=16,384, max_segments=4,096, max_table_rows=1,000, max_table_columns=128 |
| XLSX-specific | max_entries=64, max_cell_chars=16,384, max_cells=10,000, max_shared_strings=10,000, max_shared_text_chars=1,000,000, max_worksheets=16 |

Future orchestration must maintain one absolute command deadline and remaining
per-document allowances across **all** repeated bridge calls. The existing pinned
ExecutionLimits.max_seconds is an integer and each bridge starts a relative timer
after some preflight work. Pass floor(min(remaining allowances,10)); refuse when
less than one second remains, charge complete elapsed work and check again after
the bridge/cleanup returns. Never round up or accept a late result. Existing
two-second child reaping grace and short thread joins are cleanup only, not extra
result-admission time. Rollback/cleanup may finish after an admission deadline;
these mechanisms are not a hard wall-clock/RSS/disk/process sandbox guarantee.
New deadline propagation/performance tests are required before activation.

History size ceilings do not guarantee throughput: 4V+3 repeated bridge calls and
3V+2 locked calls can exceed budgets far below 10,000 events. No skip-old-VALID,
unverified cache or increased ceiling is allowed. Under low available RAM, resource
isolation, transport peak allocations, lock latency and complete replay viability
remain measured implementation gates.

## 10. Later implementation and acceptance matrix

Proposed later changes are limited to a private validated-derivation verifier and
immutable read metadata, role-derived BLOB admission, gated Replay transitions/role accounting/mirrors,
the single fixed validation orchestrator/result, and focused adversarial tests.
Keep capture-only behavior until writer and complete replayer are accepted
together. Do not make the existing pure capture replayer invoke a reader unless
an applicable VALID event actually requires it. Add no SQL DDL, codec, handler,
current staging/domain, proposal, approval or export implementation here.

In the following matrix **E** means an executable component test exists today;
**P** means the persistent activation/transaction/replay test must be implemented
later. Existing component success never means the proposed persistent test passed.
For B, the exact return is whole-command/load refusal with no trusted prefix;
errors follow section 7. All cases use owned synthetic fixtures.

| Case / precondition | Command or forged input | Expected event/SQL effect | Expected replay / exact refusal | Existing evidence vs later test |
|---|---|---|---|---|
| docx_complete captured PENDING | Explicit validate with fresh tokens | One VALID event, reference/text/integration/terminal atomically | Exact frozen DOCX bytes/locators; native manifest null | E: BridgeTests.test_golden_docx_complete; P: persistent success/restart. |
| docx_coverage captured PENDING | Same, with ordered paragraphs/table/empty/decomposed Unicode | One VALID, complete coverage | No omitted empty segment, exact codepoint offsets | E: test_golden_docx_coverage; P: persistent coverage. |
| xlsx_complete captured PENDING | Exact explicit selected-sheet tuple | One VALID, native and integration bytes retained | Actual selection and all cells/sheets match | E: test_golden_xlsx_complete; P: persistent success. |
| xlsx_blank captured PENDING | Validate physical BLANK variant | One structural VALID if profile matches | BLANK preserved, no inventory/null mapping | E: test_golden_xlsx_blank; P: persistent BLANK. |
| xlsx_missing captured PENDING | Validate missing-cell variant | One structural VALID if profile matches | Missing record retained as absence, not fabricated BLANK | E: test_golden_xlsx_missing; P: persistent missing. |
| xlsx_empty_text captured PENDING | Validate TEXT "" variant | One structural VALID if profile matches | TEXT kind retained despite equal empty text hash | E: test_golden_xlsx_empty_text; P: persistent empty TEXT. |
| xlsx_coverage captured PENDING | Validate with empty/unselected sheets | One VALID, all-sheet coverage | No dropped sheet/row/cell | E: test_golden_xlsx_coverage; P: persistent coverage. |
| Invalid/unsupported document | Corrupt ZIP/XML, tracked changes, external content/formulas | Today's ambiguous pinned failure => B, no event; A only with separately verified classification | Captured PENDING retained; UnsupportedLedgerError, no partial derivation | E: reader/bridge malformed tests; P: persistent B and any later reviewed A classification. |
| Existing VALID derivation | Alter reference BLOB or registry/source/capture binding; optionally rehash event chain | No writer action | CorruptLedgerError, full load refuses via raw reconstruction/reference equality | E: codec exact reference tests; P: persisted coherent forgery. |
| Existing VALID manifest | Coherently replace native/integration JSON/hash/reference/mirrors | None | Re-extraction mismatch refuses whole load | E: ObservationTests coherent observation forgeries; P: persisted chain/SQL forgery. |
| Existing VALID text/stamp | Alter text/hash or reader implementation claim | None | Exact native bytes/stamp mismatch, CorruptLedgerError | E: native/golden alteration tests; P: persistent text/stamp attacks. |
| XLSX selection/cell attack | Change sheet part/ID/ordinal; move cell; swap BLANK/missing/TEXT | None on forged load | Exact actual sheet/observations disagree; full load refused | E: native sheet/kind/coherent-omission tests; P: persistent attacks. |
| DOCX/XLSX empty-coverage attack | Drop empty paragraph/cell or unselected/empty worksheet, recompute hashes | None | Fresh extraction detects missing coverage | E: observation/native coverage tests; P: persistent attacks. |
| Same text, repackaged binary | New registration/capture versus transplanted old derivation | Fresh command may VALID only with new binary/integration/reference; transplant none | Wrong capture/binary binding refuses; no old validity reuse | E: historical/native repackaging tests; P: persistent binding. |
| Captured restart, no validation invoked | Open/load, mutable original missing/changed | Zero validation events/derivations | Captured PENDING unchanged, no original read | E: CaptureTests.test_exact_original_bytes_and_hash_remain_pending_after_reopen; P: keep assertion after activation. |
| Complete VALID restart | Load with spies on bridge, then corrupt raw/manifest | Zero new events; every VALID re-extracted | Exact success or complete refusal; no trusted cache/fallback | P: new VALID load and forced re-extraction spies. |
| Known initial target timeout | Verified context, worker_timeout and remaining failure-commit budget | A: one source.failed/validation parse_timeout, preserved capture, no derivation | Terminal FAILED immutable; no repeated failure assertion needed on reload | E: timeout/reaping mechanics only; P: persistent A/rollback. |
| Duplicate completion | Reissue terminal VALID/FAILED with fresh tokens | B: zero events/BLOBs | InvalidCommandError, no overwrite/target parse | E: duplicate capture/FAILED mechanics only; P: VALID duplicate. |
| Older completion after newer start | First use stale tokens, then explicitly fresh tokens under same active policy | Stale B; fresh may append one older historical VALID | source_head_at_validation=newer; source_heads.last_event=newer start, no fallback | E: late capture and inert late-head codec tests; P: VALID/FAILED late completion. |
| Policy changed after VALID | Replay historical VALID then policy.activated | No implicit new validation | Re-extract under old policy; native applicability blocked under new revision | E: codec/frozen policies only; P: trusted activation replay and old-policy applicability. |
| Policy changed during validation | Two controlled writers, policy event between initial parse and lock | B: zero target effects | StaleWriteError; fresh retry of obsolete registration InvalidCommandError | E: capture stale/concurrency mechanisms; P: policy/VALID transaction race. |
| Handler/host unavailable or incompatible | Drift pinned artifact, retire handler, wrong historical policy | B: no write | UnsupportedLedgerError; whole load refused, no latest-reader fallback | E: catalog/bridge identity tests; P: persisted VALID incompatibility. |
| Two writers | Both validate same expected global/registry/head tokens | At most one terminal event; loser no event | StaleWriteError or LedgerBusyError, no retry | E: capture two-writer tests; P: native validation race. |
| SQL/FK/commit failure before durable commit | Inject at BLOB/derivation/terminal/event/mirror/precommit stages | Rollback every new row/BLOB/projection | Prior captured PENDING exact; no fabricated A/C | E: capture atomicity/rollback tests; P: derivation-specific injection points. |
| Crash before commit | Owned process exit during validation SQL/replay | No committed partial terminal/derivation | Sidecars refused normally; qualified diagnostic recovery preserves prior capture/PENDING | E: capture/forensic process exits only; P: VALID-specific exits. |
| Commit succeeds, receipt lost | Exit immediately after validation COMMIT | One complete VALID transaction only | Restart re-extracts; exact intent reconciles; duplicate refuses, no new ack | E: capture lost-ack/custody proofs only; P: VALID-specific process exit. |
| Ambiguous COMMIT outcome | Connection failure obscures transaction result | No assumed durable state or fallback write | CommitOutcomeUnknownError; explicit verified reconciliation | P: future typed error/driver fault classification. |
| Metadata/event/text/manifest retention exhausted | Verified prospective accounting over each role boundary, including dedup/cross-role cases | C only when reserved control event fits; otherwise B | C reload shows exhausted, target PENDING; failed control no durable block claim | E: capture reserve/dedup/limits only; P: role-derived BLOB admission, derivation roles/text/manifests/control. |
| Reader/command/load deadline | Stall initial target versus existing VALID/precommit/repeated pass | Eligible initial timeout A only; shared/corrupt replay timeout B, SQL rollback | No deadline reset, late worker result or skipped old VALID | E: native pair deadline/reaping and capture cumulative deadline; P: all-history/locked-pass shared budgets. |
| Schema-2 original A0 | Frozen original DB/read-only historical producer proofs | No writes, no B parsing of old captures | Exact old state/goldens preserved; B writer refuses schema 2 | E: original_A_created and original_historical_producer proofs; P: run unchanged after activation. |
| No later gates | Try PDF lineage, generic event append, domain/proposal/review/export/model/network effects | None | Unsupported commands/inputs; side-effect spies remain zero | E: current disabled-gate/native side-effect tests; P: new validation boundary spies. |
| Today, before activation | Append syntactically valid source.validated to a disposable fixture | No application activation/write | Capture-only loader rejects it | E: TamperTests.test_syntactically_valid_source_validated_still_refused; must pass throughout this task. |

## 11. Unresolved gates and explicit next review

1. Independent review of this API/outcome, exact transaction/replay sequence,
   failure taxonomy, accounting/currentness and all P tests; none is implemented.
2. Complete immutable validated-source read metadata, terminal/replay/mirror/BLOB
   closure and atomic writer implementation accepted together; no activation via
   codec recognition, table presence or native catalog alone.
3. Safe classification of invalid/unsupported documents through the pinned bridge
   is unresolved: generic worker_failed does not prove source invalidity. A future
   classification change would require separate protocol/artifact/handler review,
   not editing frozen identities or running an unpinned parent parser. Until then
   conservative B is mandatory for these failures.
4. Historical policy transitions beyond revision 1 remain unimplemented and
   rejected today. Trusted transition fixtures/replay must be separately reviewed
   before claiming policy-change behavior. No new policy writer is authorized here.
5. Shared absolute deadlines/per-document accounting, cleanup/rollback outcome,
   COMMIT uncertainty, lock latency and low-RAM/full-history performance require
   executable measurement. Existing relative native limits are not complete
   persistent replay resource integration or hard OS quotas.
6. Real source/actor authentication, custody and independent freshness remain
   unproven. ADR-0012's public synthetic credentials are not operational authority;
   recovery/adoption stays NOT_OPERATIONALLY_AUTHORIZED with its existing blockers.

READY FOR CONTRACT REVIEW is the only requested outcome. No production readiness,
Sprint 0 acceptance, BSI normative baseline change or certification claim follows.
Review this contract before separately authorizing any implementation; stop at
TASK-007.3B.2.5.0.

## TASK-007.3B.2.5.1 clarification: known commit versus late response

**Independent implementation review required; ADR status remains PROPOSED.**
The deadline/COMMIT/cleanup interaction in sections 8–9 needs an explicit
distinction: a COMMIT call that returned successfully establishes a durable
transaction observation even if its I/O finishes after the admission deadline.
Do not return a late success, invent rollback, append a failure, or call that
known commit indeterminate. Raise LedgerLimitError explicitly stating that
COMMIT completed and requiring reload/reconciliation before another command.
The committed terminal/reference stays intact. Likewise a subsequent close
failure reports a LedgerError explicitly stating that validation committed;
it is not CommitOutcomeUnknownError. A known committed registry.exhausted retains
its durable RegistryExhaustedError signal even on late cleanup.

CommitOutcomeUnknownError is reserved for a COMMIT exception where neither
successful commit nor an active transaction followed by confirmed rollback can
be established. Its frozen intent carries intended identifiers, never a claimed
committed head/outcome. No new event/state/schema field is introduced by these
error distinctions. Precommit deadlines still refuse and roll back. A synchronous
SQLite COMMIT cannot be preempted safely by this Python deadline; the bound is
result admission, not a hard cancellation or arbitrary hardware-I/O guarantee.
Focused tests distinguish known rollback, genuinely indeterminate commit,
known-committed late response and known-committed close failure.
