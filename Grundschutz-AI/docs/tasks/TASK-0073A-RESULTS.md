# TASK-007.3A: Versioned SQLite v2 source and event ledger

Date: 2026-11-10 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`. Initial Git: clean **`24add8c`**, `docs: design structural evidence and SQLite v2 persistence`.

## Result and boundaries

Implemented only the A-stage source/event persistence foundation. Verified immutable source history is **not** proposal replay, evidence, inventory or approved export. Captured sources remain PENDING; explicit failures become FAILED. **source.validated is rejected** until B supplies complete compatible derivation/manifest verification. No queue history, scope/candidate replay, v1 importer/migration, domain construction, approval, export or PDF promotion is implemented. TASK-007.3B was not started.

No new dependencies, downloads/network, model calls, company documents, workstation-security changes, normative BSI changes or automatic commits. Existing InventoryStore/schema v1, staging/reader/domain/validation code and all existing tests remain unchanged.

## Exact files

| File | Change |
|---|---|
| `grundschutz_ai/v2_codec.py` | New strict bounded canonical JSON, typed SourceRef/Payload/Spec/Envelope, allowed A event tags and tagged hashes. |
| `grundschutz_ai/v2_ledger.py` | New isolated SourceLedger, read-only verified loader, immutable state, trusted local descriptors/policies, registration/capture/failure/current-head transitions and bounded atomic writes. |
| `grundschutz_ai/v2_schema.py` | Small fixed schema/trigger module; keeps exact DDL reviewable separately from command/replay logic. |
| `tests/test_v2_codec.py` | 20 new codec regressions, including four fixed independent serialization/hash vectors verified using .NET SHA-256 over literal UTF-8 preimages. |
| `tests/test_v2_ledger.py` | 65 new synthetic offline tests, temporary DBs/source bytes outside Git, independent SQL corruption/fault/concurrency/process-exit checks. |
| `docs/tasks/TASK-0073A-RESULTS.md` | This report and reproduction commands. |
| `docs/decisions/0009-structural-evidence-and-sqlite-v2.md` | Required A/B boundary clarification first; actual A API/schema/filesystem/control-budget clarifications. Wider design remains proposed. |

## Actual public interfaces

```python
from grundschutz_ai.v2_ledger import SourceLedger, load_ledger, LedgerLimits
from grundschutz_ai.docx_staging import StagingPolicy as DocxPolicy

# Paths must be unused/explicit and outside Git on an accepted local volume.
with SourceLedger.create(trusted_db_path, actor_id="synthetic:operator") as store:
    implementation_hash = store.register_implementation(
        "docx", expected=store.load().head, actor_id="synthetic:operator")
    registry_id = store.create_registry(
        "docx", DocxPolicy(), expected=store.load().head,
        actor_id="synthetic:operator")
    ref = store.begin_registration(
        registry_id, "synthetic:source", expected=store.load().head,
        expected_source=None, actor_id="synthetic:operator")
    state = store.capture_source(
        ref, trusted_synthetic_docx_path, expected=store.load().head,
        actor_id="synthetic:operator")
    assert state.registration(ref).status.value == "pending"

snapshot = load_ledger(trusted_db_path)  # read-only connection, verified all-or-nothing
with SourceLedger.open(trusted_db_path) as store:
    failed = store.fail_source(ref, expected=store.load().head,
        actor_id="synthetic:operator", reason_code="abandoned")
```

`create/open/load_ledger` accept optional typed LedgerLimits. `activate_policy(registry_id, typed_policy, *, expected, actor_id)` appends a changed explicit configuration; same-policy activation is refused. `begin_registration` requires exact expected source reference (None for first registration); XLSX additionally requires the existing trusted `xlsx_staging.SheetSelection`. Its subsequent capture path must have the declared extension. These selections are metadata only, not verified workbook identity until B.

`fail_source` permits only explicit abandoned/operator_failed reason codes; after capture it retains the raw digest. `close` and context-manager lifecycle are supported. No generic append-event, parser, validate_source, staging/queue or approved-record API exists. New LedgerHead and `v2_codec.SourceRef` are exact frozen typed tokens; they do not substitute for staging-owned references. SourceStatus has only PENDING/FAILED.

LedgerState contains head, immutable events/implementations/policy activations/registries/registration history/current source references/original BLOBs. `registration(ref)` and `source_head(source_id)` are lookup helpers, not eligibility methods. Payload/Spec/Envelope hold validated immutable canonical bytes; `data()` returns a detached dictionary whose mutation changes no stored/snapshot state. No DB text is deserialized into executable classes/modules.

Errors are explicit: LedgerBusyError, StaleWriteError, LedgerLimitError, InvalidCommandError, UnsafePathError, UnsupportedLedgerError and CorruptLedgerError under LedgerError. CodecError reports invalid typed/JSON values. No source text is logged/interpolated into diagnostics.

## Versions, schema and strict codecs

Versions: **schema/user_version 2**, **ledger-event/v2**, **canonical-json/v1**, **implementation-spec/v1**, **policy-spec/v1**, and exactly the eight A payload tags specified in ADR-0009. Metadata/genesis retain feature_profile staging_only; it grants no staging authority. Events use exact envelopes with store/event/transaction identity, contiguous sequence, singleton complete transaction group, payload codec/hash, predecessor hash, tagged event hash, audit timestamp and actor. Global ordering never comes from timestamps.

Allowed events: store.initialized, implementation.registered, registry.created, policy.activated, source.started, source.captured, source.failed, registry.exhausted. source.validated and every B–E/import/approval/export event are unsupported at both codec and loader boundaries. Each A command is one complete event transaction; no public multi-event batch is offered yet.

The exact 12 tables are store_metadata, content_blobs, implementation_specs, policy_specs, registries, policy_activations, logical_sources, registrations, registration_observations, source_heads, registry_state and events. There are **no empty reserved future tables**. Exact SQLite DDL/trigger checks, STRICT tables, foreign-key enforcement/integrity checking, unique IDs/revisions and immutable-history UPDATE/DELETE guards apply. Only metadata and head/registry projections are mutable and are independently compared with event replay. Unknown extra tables/indexes/triggers fail opening; their presence cannot enable a feature.

JSON uses strict UTF-8, sorted keys, compact encoding, no normalization, and exact tagged field sets. Duplicate keys, noncanonical wire encodings, unknown/missing fields, invalid integers/bool-as-counter, floats/NaN/infinity, invalid UTF-8/surrogates and arbitrary Python objects are rejected. Preflight bounds wire size, lexical depth/token counts and separators before JSON allocation; decoded strings/arrays/depth/nodes are also bounded. Defaults: 8 MiB payload, depth 64, 100,000 nodes, array/object cardinality 10,000 and 1 MiB per decoded string. New hashes follow ADR's tagged `{type,value}` canonical SHA-256 rule; binary hashes remain hashes of exact bytes. V1 fingerprint algorithms are unchanged.

Implementation registration selects only a fixed installed local DOCX/XLSX descriptor, covering a static allowlist of code-file hashes and exact Python/SQLite/runtime-profile metadata. No caller/DB path or executable module is loaded. Policy specs contain every explicit original staging/reader configuration field; independently reconstructing those known policy dataclasses enforces their existing hard caps, including XLSX max_scope_rows=100. A database descriptor must match the trusted current local artifact exactly. A historical compatibility catalog/code migration is not implemented; code/runtime/line-ending changes can intentionally make an older ledger unavailable pending separately reviewed compatibility support.

## Pending/capture/failure and concurrency contracts

1. Begin registration obtains BEGIN IMMEDIATE, verifies the full committed ledger and exact expected global/source heads, reserves source/history capacity, assigns a new ID and increasing source revision, appends source.started and updates the current-head projection. Success returns **only after commit**, before any source file I/O. Source ownership is immutable and store-wide.
2. Capture verifies a fresh expected head and a live creating-writer capture authority. It removes that one-use authority before reading, bounds the original regular file once under the registration's recorded source policy, and holds no SQLite write lock during that read. No reader/ZIP/XML/model is invoked. A declared DOCX/XLSX extension can still contain malformed or renamed bytes: all are untrusted quarantine while PENDING, never verified format/evidence.
3. The capture write replays fresh state under BEGIN IMMEDIATE and checks the exact expected head. Raw bytes/hash/length, source.captured, normalized rows and projections commit together or roll back together. Binary deduplication compares/reuses exact bytes; every registration and capture observation remains distinct. Capture leaves PENDING.
4. Genuine capture failure commits source.failed with bounded phase/code and no invented raw hash. Explicit failure after capture preserves the exact raw BLOB. FAILED is terminal for that registration. A SQL/stale-write error after reading leaves the committed registration PENDING, publishes no raw/event/projection partial state, and cannot silently recapture that same mutable path/ref. Fail it or start a new revision; reopened uncaptured refs have no live capture authority.
5. Completing an older pending registration with a fresh token may append its historical capture/failure but cannot replace a newer head. Head selection uses highest started revision, never completion time/mtime. Identical bytes and reversion still require new IDs/revisions/events. Actor strings/timestamps establish no authenticated identity.

Writes use parameterized SQL, one connection per thread, timeout=0, BEGIN IMMEDIATE, foreign_keys ON, trusted_schema OFF, synchronous FULL and DELETE journaling. Busy locks produce LedgerBusyError without a partial commit; stale store/source tokens produce StaleWriteError. No automatic retry reuses an outdated token. Codec/replay work is bounded; each replay has a 60-second deadline checked through SQLite progress handling and between bounded events. This is not a hard whole-command/RSS/OS timeout.

Resource defaults: 256 MiB database, 10,000 total events, 4 registries, 32 MiB unique raw bytes, 128 MiB metadata bytes, existing per-registry 16-source and DOCX 512/XLSX 2,048 history-unit policies and original 2 MiB source-file cap (all only tighten). One event and 1 KiB metadata per allowed registry are reserved for terminal exhaustion. Normal admission cannot consume that reserve. Source/history/raw/policy/event/metadata exhaustion commits registry.exhausted before raising the terminal outcome. No history is truncated or reset on restart, and increasing other limits cannot clear that recorded exhausted state. An uncommittable invalidation cannot be claimed durable; unavailable loads expose no cached trusted fallback.

## Verified reopening coverage

`load_ledger` uses a new read-only SQLite connection/query_only mode and a consistent read transaction. It verifies schema/profile/versions, FK/integrity, bounded counts/bytes, every referenced BLOB length/hash and canonical descriptor/payload; reconstructs the global hash chain and transaction groups, immutable source ownership, policy history, epochs/reserved units, source registrations, capture/failure status and highest-revision heads; then compares all normalized row mirrors, current-head/registry projections and metadata with replayed state. Orphan/missing data, hashes, unknown versions/events, impossible order, altered descriptors or projection mismatches refuse the entire trusted load. PENDING/FAILED/exhausted states are legitimate verified blockers, not corrupt data by themselves.

The loader returns only immutable A source/event state. It performs **no document re-extraction, native/integration manifest verification, full-scope/candidate support validation, human QueueDecision replay, substantive block reconstruction, legacy import/domain replay, model regeneration or approval/export eligibility**. Those remain B–E work. Missing compatible trusted code fails closed rather than retrieving/loading code from database/network.

## Independent demonstrations actually executed

A separate public-API script created real fictional DOCX/XLSX ZIP fixtures and a temporary ledger, closed/reopened it read-only, then deliberately corrupted only a current-head projection using an independent SQLite connection:

| Observation | Actual result |
|---|---|
| DOCX raw binary SHA-256 | `4fe07855a4783a67eaacddd40e2ac6dfd267d9644b024f03b5d23373f03895e3` |
| DOCX capture / read-only reopen | PENDING; snapshot equality true; retained original bytes exactly equal fixture bytes. |
| Same DOCX registered/captured again | 2 registrations at revisions 1/2, one deduplicated raw BLOB. |
| Explicit failure of captured revision 2 | FAILED, original digest/bytes retained. |
| New uncaptured revision 3 | Latest DOCX head PENDING, superseding the earlier failed/captured revision. |
| XLSX raw binary SHA-256 | `d12084673da49c9cf78630e1a217af3d00a9178ea03b6508c15af95422fd7345` |
| XLSX capture / final ledger | PENDING; final global sequence 13, two distinct raw BLOBs. No source.validated occurred. |
| Source-head projection manually changed to older valid FK target | CorruptLedgerError; no trusted partial load. |
| Temporary demonstration directory | Removed after all connections closed. |

The regression suite independently changes a source-capture byte_length while recomputing a valid canonical payload hash, event hash/envelope and metadata hash. Replay still rejects it against the actual bytes. Hash-chain consistency alone is not treated as data truth or tamper resistance.

## Tests actually executed

**Final complete offline suite: 502 tests in 26.702 seconds; OK; 0 failures, 0 errors, 0 skips on this Windows environment.** All **417 existing tests** remain unchanged and pass. New tests: **20 codec + 65 ledger = 85**. Includes golden vectors, canonical/error/size cases, source round trips/dedup/status/currentness, actual abrupt child-process exit after pending commit, v1/v2 mutual refusal without file changes, busy/stale writers, forced SQL rollback, one-use capture authority, file/path/budget limits and durable exhaustion, raw/payload/event/projection corruption, unsupported events and side-effect guards. No live Ollama class was selected.

The first 77-test run had **9 cleanup errors and 0 assertion failures**: several test-only SQLite context managers did not close Windows handles, and the new connection helper needed explicit close on setup failure. Both were corrected, including a direct unlink regression for the product error path; no validation expectation was weakened. The next 77-test run passed in 9.893 seconds; 81 tests then passed in 10.337 seconds before the golden/spec/coherently-rehashed corruption checks were added. An intermediate full 500-test run passed in 28.438 seconds. Final review added consistent ledger-error mapping and two fault regressions for create/open connection failures; the 502-test result above includes those changes. Initial failed-run fixture directories were safely removed by exact task names after the process exited; subsequent cleanup passed. No unresolved test failure remains.

## Filesystem and security limitations

The current profile supports only explicit absolute paths on Windows fixed local NTFS/ReFS volumes outside Git. It refuses UNC/mapped remote volumes, user SQLite URIs, memory aliases, alternate streams/reserved filename aliases, relative/missing-parent paths, reparse/link/junction/hard-link database paths and WAL sidecars. New creation is exclusive; existing files are never overwritten, and reopen uses internally encoded mode=ro/rw URIs so a missing file is not silently created. Failed creation may leave an empty/quarantined file at the explicitly chosen unused path; it is not automatically deleted/repaired. Other OS/filesystem profiles are deliberately unsupported.

Path checks are for an operator-controlled local directory, not a defense against a malicious administrator/process racing paths or coherently rewriting a database/runtime. Target-volume SQLite locking, hardware/power-loss durability, disk-full/hot-journal recovery and protected backups still require deployment validation. Hot/unverifiable recovery is refused; no automatic repair or migration is attempted. An abrupt process exit after a committed transaction is tested; it is not a physical power-loss test.

Hash chains/triggers/frozen records provide consistency checks, not tamper-resistant audit, source/reviewer authentication, encryption or real-world truth. Capture is not an atomic filesystem snapshot against concurrent writers. All bytes/metadata remain untrusted and synthetic-only; source IDs are SQL data, never paths. No approved facts can be exported from A state. Trusted compatibility artifact retention, B document/queue replay and later separately gated domain/approval integration remain future work. Recommended next action is review of this A-only implementation, not automatic continuation to B.

## Exact PowerShell reproduction

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
# New infrastructure tests only:
py -3.12 -m unittest tests.test_v2_codec tests.test_v2_ledger -v
# Entire offline suite (no optional live-Ollama classes):
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion tests.test_docx_staging tests.test_xlsx_staging tests.test_v2_codec tests.test_v2_ledger
# Independent round-trip/currentness/corruption and crash regressions:
py -3.12 -m unittest tests.test_v2_ledger.V2LedgerTests.test_original_binary_round_trip_and_capture_stays_pending tests.test_v2_ledger.V2LedgerTests.test_identical_bytes_deduplicate_blob_but_not_source_registrations tests.test_v2_ledger.V2LedgerTests.test_mismatched_valid_older_head_projection_is_refused tests.test_v2_ledger.V2LedgerTests.test_coherently_rehashed_payload_still_cannot_lie_about_source_length tests.test_v2_ledger.V2LedgerTests.test_abrupt_process_exit_after_registration_keeps_committed_pending_head -v
```

## Final Git verification

Final read-only HEAD remains **`24add8c`**, `docs: design structural evidence and SQLite v2 persistence`. Exact status:

```text
 M Grundschutz-AI/docs/decisions/0009-structural-evidence-and-sqlite-v2.md
?? Grundschutz-AI/docs/tasks/TASK-0073A-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/v2_codec.py
?? Grundschutz-AI/grundschutz_ai/v2_ledger.py
?? Grundschutz-AI/grundschutz_ai/v2_schema.py
?? Grundschutz-AI/tests/test_v2_codec.py
?? Grundschutz-AI/tests/test_v2_ledger.py
```

One tracked ADR modified and six new/untracked files; nothing staged or committed. Read-only `git diff --exit-code` confirmed no changes to InventoryStore/schema-v1 code, existing readers/stagers/domain/support/validation or their tests. `git diff --check` passed with only Git's configured LF-to-CRLF notice. Strict UTF-8/trailing-whitespace/final-newline checks passed for all seven files, including untracked files not covered by Git diff; Markdown fences and local document links passed. No matching smoke/demo/test temporary directories remained. No permanent database or source fixture was created. Git ran read-only in the repository owner's context without configuration/security changes.

```powershell
Set-Location Y:/Grundschutz-AI
git log -1 --format="%h %s"
git status --short --untracked-files=all
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai/storage.py Grundschutz-AI/grundschutz_ai/docx_staging.py Grundschutz-AI/grundschutz_ai/xlsx_staging.py Grundschutz-AI/tests/test_storage.py Grundschutz-AI/tests/test_docx_staging.py Grundschutz-AI/tests/test_xlsx_staging.py
```
