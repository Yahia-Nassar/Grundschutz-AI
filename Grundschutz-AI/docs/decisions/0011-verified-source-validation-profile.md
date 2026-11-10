# ADR-0011: Verified source validation physical profile

**Status:** Proposed contract, TASK-007.3B.2.0, 2026-11-11. Baseline **0a8af67cf36dc6df742b88380cdde0115947172d**. Only synthetic golden fixtures/tests and this design are delivered. No production Python, schema, codec or ledger is changed; no proposed B DDL is executed. Gate B remains disabled pending a separate implementation task and review.

Predecessors: [ADR-0008](0008-document-proposal-boundary.md), [ADR-0009](0009-structural-evidence-and-sqlite-v2.md), [ADR-0010](0010-historical-implementation-compatibility.md). Actual checks: [TASK-0073B20-RESULTS](../tasks/TASK-0073B20-RESULTS.md).

## 1. Authentic native contract and immutable vectors

The independent producer runs only unchanged commit **2ee9bc7cf309727e5a9f10e2982791dbc991c464**, LF packaging, Windows fixed local NTFS/ReFS, Python **3.12.6**, SQLite **3.45.3**. It verifies all ten original module hashes, both implementation/default-policy identities and four historical test-helper hashes before constructing fixtures. No current application code produces expectations.

Retain the exact synthetic bytes as base64 text in [b0-native-goldens.json](../../tests/fixtures/b0-native-goldens.json), **106,955 UTF-8 bytes**, SHA-256 **553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b**. Base64 preserves original bytes; it is not reconstructed from extracted text. ZIP members retain historical insertion order, ZIP_STORED and fixed fictitious timestamp 2020-01-01 00:00:00. Every member's exact content hash/size is recorded.

| Requested reference | Original binary SHA-256 | Native UTF-8 text SHA-256 |
|---|---|---|
| docx_complete | `d8c0bfdc1b10927bc0a5e2e8833038c80c497d8bec5efd27af2fecba0f9d4299` | `cfe8ce9a7794a4582b89f9cd6df145cc3f5b4b83f2f2f837414b4a0bd81b531d` |
| xlsx_complete | `d12084673da49c9cf78630e1a217af3d00a9178ea03b6508c15af95422fd7345` | `13361eadb0f700c06a08264073c85a979a3fdd788b5b026f3f63e9b80f526adf` |

DOCX complete: existing synthetic_parts(paragraph(COMPLETE)), source **synthetic:task-0071**, 1,381 original bytes, 92 Unicode characters, one segment. Native manifest/hash are **null**, because no DOCX native manifest exists. Reader stamp **c4d61c972ec670cdf00b18de62cae0dc88df4a62d0745fe79d5d0681a762af12**; integration SHA-256 **08c66fb331418bdf1ef164cf2d57f167f0eb2c15b7e05c75d4d7ba14934d0e96**.

XLSX complete: existing fictional_parts(), source **synthetic:task-0072**, 2,747 original bytes, six cells/65 text characters; headers System-ID/Standort/Anwendung and data SRV-001/Rechenzentrum Rostock/ERP-01. Selection is exactly **{"name":"IT-Systeme","ordinal":1,"sheet_id":1,"relationship_id":"rId1","part":"xl/worksheets/sheet1.xml"}**. Native manifest SHA-256 **5a0b36a32b5728627e094166e9899b5206b88f6563d2b5efb958de774af72660**; reader stamp **4198a751148d1dbce974b06f449443ea954beb186d5a56798eac8be1e1131cb0**; integration SHA-256 **668ff566ba1e321fe4c5516603e4c8baf13746f828bd232a65d6053f2b1f69c7**.

The fixture also freezes DOCX paragraphs/table cells/empty paragraphs and decomposed Unicode/whitespace, XLSX extra empty-sheet coverage, and explicit BLANK, physically missing B2 and TEXT "" variants. Blank and empty TEXT have identical native text hash but distinct native manifests; missing B2 is another observation. No conversion to null is performed by this reader task. Mapping explicit blank to missing inventory location belongs to later structural proposal rules.

Full literal native/integration JSON, limits, ordered observations, exact locators and cell-local spans are retained. DOCX locators are one-based body/paragraph/table/row/cell indices and zero-based half-open **segment-local Unicode codepoint offsets**. XLSX spans are cell-local; coordinate/row/column and full actual sheet identity are required. Flattened text joins native segments/cells with their existing LF separators. These are extracted-text positions, not XML-byte positions or invented pages. No Unicode normalization, whitespace trimming, case folding or line-ending repair is added.

[tests/native_golden_oracle.py](../../tests/native_golden_oracle.py) is a reproducible, test-only A checkout verifier/producer. [tests/test_v2_reader_goldens.py](../../tests/test_v2_reader_goldens.py) compares current native-profile output with frozen literals, detects altered/incomplete artifacts, and separately re-executes the unchanged historical producer in an isolated subprocess. Current snapshot tests are explicitly **current profile conformance**, not historical compatibility dispatch. They never generate expected values or authorize old ledgers; Gate A tests/handler/catalog remain untouched. Future changed current semantics cannot rewrite these A vectors.

## 2. Concrete physical choice: new schema 3, new files only

Propose **user_version=3**, metadata schema_version=3, feature_profile **verified-source/v1**, serialization **canonical-json/v1**, envelope **ledger-event/v3** and genesis payload **store-init/v2**. The separate physical profile name is **sqlite-source-validation/v1**. This supersedes the earlier open B write-format choice; it does not reinterpret A.

Rationale: A requires the exact schema-2 SQL map, eight event tags, ledger-event/v2 and pending/failed states. A stored profile flag cannot enable new columns or events. A new schema number and envelope namespace make mutual refusal explicit and keep old hashes immutable. Project terminology “SQLite v2 architecture” is not a promise to keep physical PRAGMA user_version=2 forever.

- Fresh B creation must use an unused trusted local path, exclusive creation, exact reviewed DDL/profile, DELETE journaling/FULL synchronization. It is not an upgrade or copy of an A file.
- Frozen schema-2 A files remain read-only through existing v2_compat.load_historical_ledger. Existing A writer/codec/handler are unchanged and must refuse schema 3.
- A future B reader/writer accepts only exact schema-3/profile/version/DDL combinations. It must refuse A files for writable use before a read/write handle, and refuse unknown/extra tables, triggers, indexes, codecs or future tags.
- No migration, automatic event conversion, history import, cross-store registration reuse or legacy v1 import is authorized. Any later explicit transfer needs separate design/lineage review; it cannot rewrite old UUIDs/hashes to pretend continuity.
- Only ten event kinds listed below may exist in B. No reserved candidate/queue/domain tables or placeholder activation fields.

No physical schema-3 database, production DDL module or new codec is created in this task. The following exact relational contract must become reviewed, fixed SQL and an exact schema fingerprint in the future implementation; no SQL fingerprint is invented here.

## 3. Typed/hash contracts

C is canonical-json/v1 encoding: strict UTF-8, sorted keys, compact separators, no BOM, duplicate keys, floats/NaN/infinity or lone surrogates. Exact typed contracts additionally reject unknown/missing members and bool-as-integer counters. S is SHA-256 of exact bytes; H(t,v)=S(C({"type":t,"value":v})). Existing Spec/native/staging preimages remain unchanged. IDs are opaque 32-lowercase-hex, hashes 64-lowercase-hex, counters positive signed-SQLite-range integers except explicitly nonnegative lengths. Nullable fields remain present.

Existing document registration reference stays exactly {source_id,revision,registration_id}. Its source ID is trusted operator identity, not a filename; store UUID scopes the surrounding new contracts. Do not alter an existing reference/fingerprint preimage.

### Reader and execution identity

An implementation-spec/v1 retains the exact reviewed A0 reader descriptor, including its historical broad module list, even though those historical ledger semantics are not used as the B writer. A future independently reviewed native compatibility bridge is required to execute the same reader/integration semantics. Existing Gate A entries grant **source_ledger_read only**; they cannot authorize validation.

Propose **reader-handler-spec/v1** with all required members:
type, handler_id, reader_spec_hash, family, reader_method, artifact_hashes, host_runtime, policy_versions, serialization_version, native_manifest_version, integration_manifest_version, golden_fixture_sha256.

artifact_hashes is a sorted unique application-allowlisted array of {artifact_id,sha256}; host_runtime is the exact reviewed {python_version,sqlite_version,platform_profile}; policy_versions is the exact ordered supported semantic-version list. Native version is null for DOCX and **xlsx-literal/v1** for the existing XLSX native encoding (it has no separate version member); integration is docx-integration/v1 or xlsx-integration/v1. Golden digest is the fixture digest in section 1. Identity is H(type, object without type); descriptor BLOB digest is S(C(full object)).

All executable selection is through a static trusted local dispatcher matching exact descriptor bytes/hashes and approved capabilities, never module names, paths or code from SQLite. Preserve the four-profile catalog ceiling: the two existing A0 ledger-read entries plus at most two separately reviewed native handler profiles. No Gate B native capability is enrolled here. Actual future bridge artifact hashes/handler IDs and producer/host compatibility must be reviewed before B activation; this ADR does not invent them or install old code.

### Persistent derivation reference

Use a new **derivation-ref/v2** tag rather than silently broadening ADR-0009's unimplemented v1 sketch. Required complete object:

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
native_manifest_sha256 = null for DOCX, required hash for XLSX
integration_manifest_sha256
```

derivation_sha256=H("derivation-ref/v2", object without type); derivation_blob_sha256=S(C(full object)). reader_limits_sha256=H("reader-limits/v1", exact complete historical reader-limits dictionary). policy_fingerprint retains the exact old staging algorithm, distinct from policy_spec_hash. Reader stamp retains the old Python/reader/OOXML algorithm, distinct from broader reader_spec_hash and new handler_spec_hash. Each registration gets its own derivation even when byte/text hashes match older revisions.

Native text is exact Unicode output encoded UTF-8 without BOM or added newline; native_text_sha256 also addresses its BLOB. XLSX native and both integration manifests are stored as their **exact existing UTF-8 JSON bytes**, not pretty printed, normalized, retagged or wrapped in a new hash domain. DOCX native-manifest BLOB/hash remain null.

Manifest serialization is the pinned native/snapshot serializer, not a call to the ledger payload decoder. In particular xlsx-integration/v1 embeds native_manifest_json as a JSON **string**. Do not convert that string to an object or feed a potentially multi-MiB manifest into a ledger decoder with a 1-MiB string cap. Treat stored manifests as bounded opaque bytes: re-extract, rebuild with a bounded trusted serializer, and compare exact bytes/hash. Never trust decoded stored manifest claims. Reader/output limits bound reconstruction; native and integration manifest limits apply independently, including nested-string escaping. Ledger reference payloads stay small and retain their strict original canonical limits; no decoder cap is silently relaxed.

## 4. Proposed fixed relational layout

All 15 tables are STRICT; IDs use exact BINARY comparison. All listed FKs are enforced and DEFERRABLE INITIALLY DEFERRED where needed for an atomic event transaction. Hash/ID forms and event-role constraints are additionally enforced by the exact typed codec/replay. Byte-length/hash checks remain independent of SQL. No table stores source-controlled executable paths.

| Table | Columns, keys, references and uniqueness |
|---|---|
| store_metadata | singleton PK CHECK=1; store_uuid UNIQUE; schema_version CHECK=3, event_codec=ledger-event/v3, serialization_version=canonical-json/v1, feature_profile=verified-source/v1, last_sequence>=1, last_event_hash. Only verified head projection mutates. |
| content_blobs | sha256 PK, byte_length>=0, content BLOB; CHECK length(content)=byte_length; independently recompute digest. Immutable exact-byte dedup. |
| implementation_specs | implementation_hash PK, descriptor_blob_sha256 FK content_blobs; exact recognized reader Spec. Immutable. |
| reader_handler_specs | handler_spec_hash PK, reader_spec_hash FK implementation_specs, descriptor_blob_sha256 FK content_blobs, registration_event UNIQUE FK events; UNIQUE(handler_spec_hash,reader_spec_hash) for composite registration FK. Catalog equality, capability and family verified independently. |
| policy_specs | policy_spec_hash PK, implementation_hash FK implementation_specs, config_blob_sha256 FK content_blobs; complete policy-spec/v1 bytes. Immutable. |
| registries | registry_id PK, kind docx/xlsx, session_id UNIQUE, created_event UNIQUE FK events. Ownership/family immutable. |
| policy_activations | PK(registry_id,revision); registry_id FK registries, policy_spec_hash FK policy_specs, policy_fingerprint, event_sequence UNIQUE FK events, activated_at. Exact increasing revisions; initial activation owned by registry.created. |
| logical_sources | source_id PK, registry_id FK registries, kind, created_event UNIQUE FK events; UNIQUE(registry_id,source_id). Ownership immutable store-wide. |
| registrations | registration_id PK; source_id,registry_id,revision,predecessor_registration_id,policy_revision,reader_spec_hash,handler_spec_hash,selection_json BLOB,start_event UNIQUE FK events; UNIQUE(source_id,revision), UNIQUE(source_id,revision,registration_id). Composite FK(registry_id,source_id) logical_sources; FK predecessor registrations; FK(registry_id,policy_revision) policy_activations; FK(handler_spec_hash,reader_spec_hash) reader_handler_specs. Predecessor must be exact prior revision/same source; DOCX selection=null, XLSX exact typed sheet identity. |
| source_captures | registration_id PK/FK registrations; capture_event_sequence UNIQUE FK events, binary_sha256 FK content_blobs, byte_length>=0; UNIQUE(registration_id,capture_event_sequence,binary_sha256). Exactly one capture per registration, matching source.captured and actual BLOB length. |
| derivations | derivation_sha256 PK, registration_id UNIQUE FK registrations; all remaining derivation-ref/v2 fields as typed columns (source/store/registry identity bound through registration/metadata); derivation_blob_sha256 FK content_blobs; validated_event_sequence UNIQUE FK events. Composite FK(registration_id,capture_event_sequence,binary_sha256) source_captures; reader_spec_hash FK implementation_specs; handler_spec_hash FK reader_handler_specs; policy_spec_hash FK policy_specs; FK(registry_id,policy_revision) policy_activations. native_text_sha256, integration_manifest_sha256 and nullable native_manifest_sha256 FK content_blobs. UNIQUE(registration_id,derivation_sha256). Every column compared with canonical reference/re-extraction, never independent truth. |
| source_terminals | registration_id PK/FK registrations; terminal_event_sequence UNIQUE FK events; state valid/failed, nullable derivation_sha256, nullable failure_phase, issue_json BLOB. Composite FK(registration_id,derivation_sha256) derivations. CHECK valid implies nonnull derivation/null failure/empty issues; failed implies null derivation/nonempty bounded known issues and known phase. One terminal row total forbids both VALID and FAILED, duplicate completion or in-place recovery. |
| source_heads | source_id PK; revision, registration_id UNIQUE, last_event; composite FK(source_id,revision,registration_id) registrations; last_event FK events equals that registration's **start event**, not completion. Rebuildable highest-started projection. |
| registry_state | registry_id PK FK registries; policy_revision FK(registry_id,policy_revision) policy_activations; epoch>=1, history_units>=0, exhausted in 0/1, retained_bytes>=0, retained_text_chars>=0, retained_manifest_bytes>=0, derivation_count>=0. All rebuilt from global events and distinct role-bound content references. |
| events | Same envelope column names as A: sequence PK>=1,event_id UNIQUE,transaction_id UNIQUE,transaction_index CHECK=1,transaction_count CHECK=1,kind,payload_codec,payload_sha256 FK content_blobs,previous_event_sha256,event_sha256 UNIQUE,occurred_at,actor_id,envelope_json BLOB. Envelope codec is v3; event roles/version/chain/global store identity checked by replay. |

B omits A's registration_observations table: started/capture/terminal history is completely retained in **events**, with one capture/one terminal mirror. It does not copy A rows into a new layout. References, declarations and mirror values must exactly replay; no independent mutable source-status flag.

Counter transitions retain A's conservative reservations: registry creation starts epoch=1/history_units=0; source.started increments epoch and reserves three history units for start/capture/one terminal; capture and each terminal increment epoch without releasing or adding reservation units. Policy activation increments epoch/history by one; registry.exhausted increments epoch and is terminal. VALID additionally increments derivation_count once and charges newly retained text/manifests; capture charges newly retained raw bytes. Distinct all-history content accounting is specified in section 8. No failed/unused reservation is reclaimed to revive an exhausted registry.

Only store_metadata, source_heads and registry_state are mutable projections. The other **12 tables** require both BEFORE UPDATE and BEFORE DELETE abort triggers (**24 guards**) named <table>_no_update / <table>_no_delete. PK/UNIQUE constraints supply exact uniqueness; no extra unchecked indexes/triggers are permitted. All schema SQL strings and checks must be fixed/reviewed before implementation acceptance. Triggers are defense in depth, not authentication against a whole-file replacement.

## 5. Exact event/payload contracts and atomicity

The B envelope has the same exact member names as A, but codec **ledger-event/v3**. payload_sha256=S(C(payload)); event_sha256=H("ledger-event/v3", envelope without event_sha256). Previous hash links the preceding **v3** event; genesis previous=null. Sequence is contiguous, store UUID invariant, event/transaction IDs unique, and timestamps never determine currentness. No rewriting an A v2 chain under a v3 label.

| Only B event kind | Exact payload contract |
|---|---|
| store.initialized | store-init/v2: payload_codec,store_uuid,schema_version=3,serialization_version=canonical-json/v1,feature_profile=verified-source/v1. |
| implementation.registered | Existing implementation-register/v1 exact A shape; only exact reviewed reader Specs. |
| reader.handler_registered | reader-handler-register/v1: payload_codec,handler_spec_hash,descriptor_blob_sha256. References an earlier registered compatible reader implementation; exact local native capability required. |
| registry.created | Existing registry-create/v1 exact A shape; initial policy revision=1, epoch=1/history=0, same-kind registered reader/native handler availability. |
| policy.activated | Existing policy-activate/v1 exact A shape; predecessor/current policy checks, resource constraints and fingerprint recomputation. |
| source.started | source-start/v2: payload_codec,registry_id,registration,predecessor_registration_id,policy_revision,reader_spec_hash,handler_spec_hash,selection,declared_lineage,observed_at. Exact declared_lineage=[] initially; nonempty/PDF lineage refused. |
| source.captured | Existing source-capture/v1 exact A shape; source never becomes VALID from this event. |
| source.failed | source-fail/v2: payload_codec,registration,phase,issue_codes,observed_at. phase is capture/validation/environment/interrupted/capacity. Known issues: capture_failed,source_limit,unsupported_input,invalid_source,unsupported_structure,parse_timeout,operator_failed,abandoned,resource_exhausted. Nonempty unique array of at most four codes; no free-text source material. |
| source.validated | source-valid/v1: payload_codec,registration,capture_event_sequence,derivation_sha256,derivation_blob_sha256,source_head_at_validation,observed_at. Both references and observed_at must match the reconstructed registration/capture/derivation and envelope. source_head_at_validation is the exact highest-started SourceRef when committed, including a newer head for an older completion. |
| registry.exhausted | Existing registry-exhaust/v1 exact A shape; terminal resource block, no reset. |

Inherited shapes are the literal baseline v2_codec._SHAPES fields, not dynamically discovered future defaults. Actor rules retain A except source.validated may be an explicitly identified operator or null for deterministic machine observation; neither is human approval. Audit time is exact aware UTC, observed_at equals envelope time; original source dates/mtime are not validation time.

**One command, one event, one complete transaction group** (index=count=1), retaining A's transaction discipline. Derivation BLOBs, reference/spec mirror, terminal VALID row, registry/head metadata and source.validated event commit atomically. BLOB/table insertion order uses deferred FKs; no orphan uncommitted derivation becomes visible. No multi-event or bulk validation batch, snapshot import or hidden parser event.

Future explicit validation command:

1. Read-only verify complete current store and exact expected global head/source head; require captured PENDING target and available exact pinned handler/policy. Persisted current policy revision must still match that registration for a new completion.
2. Retrieve the immutable captured BLOB; verify hash/length; perform the initial target parse/rebuild outside SQLite's write lock under bounded execution. No mutable source path or database-supplied executable choice.
3. BEGIN IMMEDIATE; replay fresh state and compare exact expected LedgerHead (store/sequence/hash), source_head_at_validation, target capture, handler and active policy. Recheck all limits. No automatic stale-token retry.
4. Atomically append one source.validated plus complete immutable derivation and matching mirrors; reverify the full result before commit. Return only after commit.
5. On stale token, lock/SQL/disk failure, incompatible policy/handler or rollback: no source.validated or partial BLOB/projection remains. Existing capture stays PENDING unless an independently verified failure/exhaustion transaction actually commits.

For this first bounded profile, the fresh in-transaction and precommit complete replays may repeat native verification under the write lock. Do not replace them with an unverified stored cache or pretend all parsing is outside the lock. Accept this serialization cost for the synthetic prototype; a private-proof optimization would need separate design/review. Every pass and target parse shares one cumulative command deadline, rather than restarting sixty seconds per pass. Timeout/busy/verification failure rolls back. Writer lock-hold latency and crash/worker termination behavior must be measured in Gate B acceptance, not assumed safe from these small goldens.

Source invalidity/time-limit failure may explicitly commit source.failed with fresh expected tokens if the whole pre-state verifies and capacity remains. Missing/incompatible trusted replay code or unknown policies refuse the operation, not a fabricated source failure. Capacity can commit bounded registry.exhausted from reserved control space; if even that cannot commit, report an uncommitted error, never claim durable invalidation.

**Actual reader API boundary:** ingest_docx/ingest_xlsx currently take paths, not bytes. Existing private staging _read_captured(raw,source_id,limits) helpers materialize a bounded private temporary file outside Git, invoke the path reader and compare exact returned original_bytes/source_id/limits. The future pinned bridge must supply that reviewed byte-to-reader boundary in its bounded worker, not assume a nonexistent public byte API or delegate to mutable current staging semantics. Only captured SQLite bytes may populate that private transport; never use a stored original import path. Any byte discrepancy or temporary-file failure refuses validation. Temporary transport provides no new provenance or authority.

## 6. Validation state machine and currentness

| State/trigger | Permitted result |
|---|---|
| New source.started | PENDING without capture; highest started revision immediately becomes head. |
| PENDING without capture + live authorized capture | PENDING with immutable bytes; at most one source.captured. Failure may become terminal FAILED without invented digest. |
| PENDING without capture + validate | Refuse. No reader call, no VALID. Reopened uncaptured registration has no old mutable-path capture authority; explicitly fail it or start a new revision. |
| Captured PENDING + explicit verified validation | Terminal VALID only after full re-extraction/manifest/selection/limit verification and atomic source.validated commit. |
| Captured PENDING + known invalid/unsupported source, timeout or explicit abandonment | Terminal FAILED if a fresh failure transaction commits; preserve original capture. |
| FAILED or VALID + any completion/revalidation | Refuse; terminal immutable. Remediation/revalidation requires new registration/revision/capture/derivation, never an UPDATE. |
| Newer registration begins after older VALID | Newer PENDING is head immediately. Never fall back to old VALID when newer head is pending/failed/unsupported. |
| Older completion arrives after newer source.started | With fresh exact global/source tokens and unchanged active policy, may record older historical VALID/FAILED. It cannot replace newer head; terminal source_heads last_event remains the newer start event. Stale requests refuse and must be explicitly reissued. |
| Identical-byte re-registration | New reference/revision/events and derivation identity; raw BLOB may deduplicate only after exact-byte comparison. Native/integration bytes can match for the same source/policy, but status/currentness cannot be reused. |
| ZIP repackaging, same extracted content | New binary identity and integration manifest, new registration/derivation; native text and XLSX native manifest can remain equal. No old binding authorizes it. |
| Reader/runtime/handler incompatibility | Refuse full requested verification; no newest-reader fallback, no automatic VALID or fabricated terminal event. New reviewed handler/profile needed. |
| Policy changes during new validation | Expected policy/head check fails; capture remains PENDING. Explicitly fail/re-register under current policy. No in-place upgrade of FAILED/VALID. |
| Policy changes after a VALID observation | Retain immutable historical VALID/old-policy derivation; current applicability is blocked if active policy differs until a new registration is validated. No old native snapshot gains current authority merely from historical VALID. |
| Resource exhaustion/interruption/restart | Atomically committed history is authoritative. No validation event means captured PENDING, never inferred VALID from leftover cache. Reopened captured PENDING may be explicitly validated from immutable SQLite bytes; loading never validates PENDING automatically. Existing VALID events must still be re-extracted on every complete verified B load. Terminal registry exhaustion remains blocked. |

Status is structural processing state, not any of the four domain review states. VALID means conformance to the bounded native source profile, not affirmative inventory truth, complete proposal coverage or approval. A native multi-paragraph/table DOCX, extra-sheet workbook, changed header, missing cell or empty TEXT can be structurally parseable; Gate B must retain all observations. Later Gate C may reject the entire context. A declared XLSX selection must exactly match one actual native worksheet; all other sheets remain covered. Selecting one sheet never authorizes ignoring another.

## 7. Verified B read/replay

Future trusted loading is read-only and all-or-nothing:

1. Verify exact schema/profile, local handlers and runtime tuple before exposing state. Use a consistent read transaction, path/volume/sidecar rules, strict bounded codecs, FK/integrity checks, event order/hash chain and exact mirror comparisons.
2. Fetch originals only from captured SQLite BLOBs. Verify every referenced BLOB length/hash and no orphan/unknown rows; preserve every revision and raw byte history.
3. Reconstruct starts/captures/terminals/registries/policies in global order and recompute highest-started heads. At each source.validated event require that its policy was then active and source_head_at_validation equals the head at that exact historical position, rather than today's head. Unknown events, impossible transitions, duplicate terminal/capture or inconsistent mirror refuse complete load.
4. For every source.validated, choose only the exact approved compatible native handler, registration-time policy, selection and host combination. Re-extract original bytes under that exact historical interpretation. Do not reinterpret with current staging defaults.
5. Recompute Unicode text/hash, all native observations/locators/limits, native manifest when present, reader stamp, exact integration bytes and derivation-ref/v2. Verify every stored column, reference and BLOB by comparison. DOCX native hash must be null; XLSX cannot omit its native manifest. Stored support/status flags or matching hash chains cannot excuse disagreement.
6. Check complete coverage of all supported body segments/sheets/cells, including empty/missing/blank observations and unselected worksheets. No trimming, normalization, snapshot truncation, default first-sheet selection or invented locators.
7. Reconstruct all terminal and pending heads without implicit recovery or fallback. Return complete immutable source/derivation metadata plus explicit currentness/policy block diagnostics, **no eligible proposals or approval**. Historical VALID with a mismatched active policy is verified historical data but not a current usable derivation.
8. Missing handlers, budget exhaustion, coherent false manifests/locators or incomplete derivation context refuse the whole trusted replay. A fully verified PENDING/FAILED/policy-blocked/exhausted result may be returned as blocked; no verified prefix/cache fallback.

The native/integration golden corpus is an acceptance oracle, not a catalog enrollment or authenticity signature. Entire self-consistent unsigned corpus replacement/forged actor identities remain possible without independent authenticated source/control checkpoints.

## 8. Bounds

Retain existing conservative ceilings; only trusted tightening is allowed. No silent history eviction, discarded worksheet/row, cap relaxation or refreshed budget per source/event.

- Fixed local NTFS/ReFS, 256 MiB DB, 4 registries, 16 logical sources/registry (64 total), 2 MiB/source, 32 MiB aggregate original BLOBs; all registration revisions retained.
- 10,000 events, 128 MiB cumulative unique metadata/derivation/text/manifest/spec BLOBs; one event plus 1 KiB/registry reserved for terminal exhaustion, default normal-event ceiling 9,996. All new events/BLOBs count.
- Existing reader field ceilings, including 8 MiB ZIP uncompressed, ratio 100, XML size/depth/node/attribute limits and full DOCX/XLSX structural caps; pin exact config, do not inherit new defaults.
- 8 MiB each native/integration manifest; 32 MiB retained manifests and 1,000,000 retained native text codepoints per registry. Count retained **all-history unique content** for each role/per registry; global metadata/raw budgets apply additionally. A reused BLOB with multiple roles must satisfy every role's accounting and byte equality.
- Canonical payload/reference codec stays at 8 MiB, depth 64, 100,000 nodes, 10,000 collection items, 1 MiB/string. Manifests are bounded byte-compared native outputs, not an excuse to raise those payload caps.
- Proposed enforceable parser deadline 10 seconds/document within a 60-second total verified-load or command budget shared across all passes. Include re-extraction/serialization and count repeated work; no unbounded recursive retries. A future pinned local worker must terminate on timeout before accepting derivations. This is not implemented or a hard RSS guarantee today.
- At most four reviewed implementation/handler profiles combined; no database-driven enrollment. Gate C's 100 aggregate assertions and Gate D decision/history limits remain disabled contract boundaries, not additional authority supplied by B.

A tightened application memory/file/time budget that cannot verify all history refuses the entire trusted load. Persisted policy transitions preserve their historical interpretation; current applicability can block without rewriting terminal history. Counters, epochs and source/head changes are recomputed, never read as authority.

## 9. Future Gate B threat/acceptance matrix

These are **design tests to implement later**, distinct from this task's 30 native-golden tests.

| Scenario | Required result |
|---|---|
| Authentic complete DOCX/XLSX golden bytes | Explicit captured-PENDING-to-VALID transaction, every native/integration/reference value exact; no proposal/domain approval. |
| Corrupt ZIP/XML, tracked changes, formulas/external references, hidden/unsupported content | Reader/profile rejection; at most explicit terminal FAILED with fresh tokens, preserved bytes, no partial derivation. |
| Forged native/integration hash/JSON/reader stamp, coherent chain rehash | Re-extract; mismatch refuses whole trusted load, even if hashes/projections were coherently rewritten. |
| Wrong sheet identity, moved cell, BLANK versus missing/TEXT "", invalid spans | Compare exact native structure and selected sheet; reject forged derivation. A new structurally valid source may be VALID with observations that later block Gate C. |
| Dropped empty paragraph/table cell/empty or unselected worksheet | Coverage mismatch refuses; identical flattened text is insufficient. |
| Reader/policy/host changed or handler missing | Exact catalog/capability failure, no current-reader/default-policy fallback. Preserve complete known blocked history only where it can actually be verified. |
| Stale global/source/policy token, late older completion | Stale refuses atomically; explicitly reissued old completion cannot replace newer pending/failed head or bypass current-policy rule. |
| Crash before commit / after commit | Before: no event/BLOB/terminal partial state, remains PENDING. After: one complete VALID event/derivation; re-extraction succeeds on restart. Test real process exit; do not claim power-loss durability. |
| Captured restart, uncaptured restart, old FAILED | Explicit immutable-byte validation only for captured PENDING; no mutable-path reread or in-place FAILED revalidation. |
| Identical-byte re-registration / repackaging | New revision/reference; exact old history retained; binary/integration differences accounted; no historical token reuse. |
| Event/byte/time/manifest/text/catalog exhaustion or failed control commit | Whole-operation refusal or verified durable terminal block; no partial trusted state, eviction, fabricated durable invalidation or over-limit acceptance. |
| Schema 2 A0 fixture | Existing read-only Gate A still verifies all 13 events/bytes/projections; new B writer refuses A file and A writer/codec refuse schema 3. No upgrade/migration. |
| Gate C/D/domain/export/PDF/v1 events or DB-driven code | Unsupported and refused; spies ensure no model/network/proposal/queue/Evidence/Inventory/ReviewRecord/export/migration effects. |

## 10. Outstanding implementation gates

Before any Gate B production code is accepted: review this exact schema-3/event-v3 proposal; fix/review literal DDL/check/index/trigger strings and fingerprint; approve exact native handler artifacts/host tuples/capabilities within the catalog ceiling; implement and validate bounded byte/manifest/worker handling; implement atomic state/replay, failure-code and mirror validation; execute the complete threat matrix including stale/crash/forged metadata cases; and preserve the independent A0 proof.

Golden success alone does not enable source.validated. Gates C/D, Evidence, Inventory, ReviewRecord, human approval, export, PDF promotion and migration remain disabled. No normative BSI baseline decision or production/certification readiness is implied.
