# ADR-0010: Historical implementation compatibility and verified replay

**Status:** Contract proposed in documentation-only TASK-007.3B.0, 2026-11-10, inspected baseline **2ee9bc7cf309727e5a9f10e2982791dbc991c464**. TASK-007.3B.1 implements only the Gate A read-only compatibility subset described in section 10; Gates B/C/D and the wider design remain proposed/disabled. Human release review remains required.

Predecessors: [ADR-0008](0008-document-proposal-boundary.md), [ADR-0009](0009-structural-evidence-and-sqlite-v2.md). Verification: [TASK-0073B0-RESULTS](../tasks/TASK-0073B0-RESULTS.md).

## 1. Actual A-stage compatibility boundary

`v2_ledger._local_spec(kind)` hashes the exact on-disk bytes of all ten statically allowlisted modules below, sorted by module name, for **both** DOCX and XLSX. The descriptor includes family, method, serialization version, type and runtime: exact Python major.minor.patch, `sqlite3.sqlite_version`, and literal platform profile `windows-fixed-ntfs-refs/v1`. It contains no Git commit. Raw CRLF/LF differences change identity.

This checkout uses **Python 3.12.6, SQLite 3.45.3**; all ten modules have LF endings and zero CRLF pairs. Name this exact packaging/runtime profile **A0**. A commit alone does not identify all possible runtime/checkout combinations.

| Module | SHA-256 of exact module bytes |
|---|---|
| `docx_ingestion.py` | `a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b` |
| `docx_staging.py` | `af01b5e5b09b9551ef3388a53ab433a693cb72369578f760004e0c7ac2a4849a` |
| `ooxml_safety.py` | `35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6` |
| `support.py` | `c48ac29efae541c9c3a34acb65c32e151e5d0aef4c74b54ad7df1bf800c56dcb` |
| `v2_codec.py` | `577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3` |
| `v2_ledger.py` | `a66d5106fcf7b153088eff24ce0cecf0d9fba9ef0167cf0f40632f5f76b6d2be` |
| `v2_schema.py` | `9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc` |
| `validation.py` | `22d3840b6efbed5b0bfab2f9ddb7d4fe3da49bff8592595be5b9cbb8e8df18b5` |
| `xlsx_ingestion.py` | `8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72` |
| `xlsx_staging.py` | `89978979da572f84d26668e91f2e0a2212e474cbc769e4e682ed84cf108dca06` |

The complete descriptor is reconstructed as a canonical JSON object with `type="implementation-spec/v1"`, `family="docx"` or `"xlsx"`, the ordered `module_hashes=[{"module_name":<name without .py>,"sha256":<table hash>},...]`, `runtime={"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"}`, `serialization_version="canonical-json/v1"`, and `method_version="docx-plain/v1"` or `"xlsx-literal/v1"` respectively.

Define C(x) as strict A canonical UTF-8 JSON; S(b) as SHA-256 of bytes; H(t,x)=S(C({"type":t,"value":x})). A Spec's identity removes its `type` member before H. Spec identity and canonical BLOB digest are **different**.

| Frozen identity | DOCX A0 | XLSX A0 |
|---|---|---|
| Implementation Spec | `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c` | `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2` |
| Descriptor BLOB S(C(spec)) | `c61db30620d92e88e8e69ef8b4bdf786c38bedc5b338373676381a471c552af1` | `4e394cd2fe03f2d7e4caef3d2c338fd0b6fa07595fba01005175ef2877e0afee` |
| Default policy Spec | `2359df5e7ddb0a7228214fc29f68dcd2dd864354004fde6f6c02a513705aabeb` | `b7ebd2d0711a5a5e8c52cd32e1b6aa57bda37dda9cfe3bdaa8b20540deab5f93` |
| Existing staging policy fingerprint | `bea69dfeb93e4fd79b0663339cca75150c495758b0b02dd5138dea9442939e8e` | `cab624db7febb44ca1eb31ddaf9f29cbcf86b51cd5bee04777b71581c8deac18` |

### Current SourceLedger.open checks

1. Calls `load_ledger` read-only **before opening a read/write handle**. Checks trusted absolute local Windows path/profile, size and sidecars; a missing file is not created.
2. Builds the catalog from currently installed DOCX/XLSX descriptors. Connects read-only/query-only, enables foreign keys, disables trusted schema and requires DELETE journal mode.
3. In a read transaction checks user_version=2, exact current sqlite_master name/type/SQL map, foreign keys/integrity, bounded BLOB sizes/hashes, exact canonical specs/payloads/envelopes, sequence, chain, singleton transaction groups, audit fields, ownership and legal transitions.
4. Decodes policies through **current** reader-limit/staging-policy classes, including current policy fingerprints. At implementation.registered, stored Spec bytes must equal the current family Spec bytes. Rebuilds all heads/counters/projections and compares persisted tables; extra/orphan data is refused.
5. After successful read-only verification, repeats path/catalog setup, connects read/write without creation and fully verifies again. Errors close the handle. The instance caches this catalog; there is no file-change monitor.

Changed hashed code or runtime can therefore block an old registered implementation even when document format tags remain unchanged. The exact Spec mismatch currently raises CodecError wrapped as **CorruptLedgerError**, not a dedicated historical-incompatibility error. Missing local artifacts raise UnsupportedLedgerError. Relaxing Spec comparison alone would leave current policy constructors/fingerprints, exact DDL and current codec decoders as independent barriers.

| Difference | Interpretation |
|---|---|
| Reader grammar, manifest or locator change | Potential source-format/semantic incompatibility; requires explicitly compatible historical semantics. |
| Ledger, schema, codec, stager, validation/support or other-format module change | Broad implementation-code identity changes; this alone does not prove a document-format change. Still rejected today. |
| Python/SQLite patch or line-ending change | Different installed identity; equivalence requires review, never assumption. |
| Extra tables/triggers or event/canonical codec | Independent storage/codec incompatibility. |
| Matching descriptor | Artifact identity only; does not prove correct document validation, source truth or human approval. |

### Already frozen versions

- Schema/user_version **2**, metadata/genesis feature_profile **staging_only**, serialization **canonical-json/v1**, envelope **ledger-event/v2**, Spec tags **implementation-spec/v1**, **policy-spec/v1**.
- Exact A `v2_schema.expected_objects()`: 12 STRICT tables (store_metadata, content_blobs, implementation_specs, policy_specs, registries, policy_activations, logical_sources, registrations, registration_observations, source_heads, registry_state, events) and 18 UPDATE/DELETE immutability triggers. No future tables, even empty reservations.
- Documentation schema vector: H("a-schema-objects/v1", sorted array of {"name":name,"kind":type,"sql":exact_sql}) = **092b2d5aed6e07ddb99b3a4299d01b05c0f6cc5845b75bec6aa968aaa0fefa32**. This is not a stored A field; actual A verification compares the full map.
- Canonical JSON: sorted keys, compact separators, literal Unicode/UTF-8 without BOM, exact re-encoding. No duplicate keys, floats/nonfinite numbers, lone surrogates, out-of-range integers, unknown fields or boolean-as-integer coercion.
- Policies **docx-single-assertion/v1**, **synthetic-it-table/v1**; support **inventory-affirmative/v1**; remediation **docx-assertion-remediation/v1**, **xlsx-assertion-remediation/v1**; integration **docx-integration/v1**, **xlsx-integration/v1**. Preserve their distinct preimages.

| Only accepted A event kind | Payload codec |
|---|---|
| store.initialized | store-init/v1 |
| implementation.registered | implementation-register/v1 |
| registry.created | registry-create/v1 |
| policy.activated | policy-activate/v1 |
| source.started | source-start/v1 |
| source.captured | source-capture/v1 |
| source.failed | source-fail/v1 |
| registry.exhausted | registry-exhaust/v1 |

Exact payload members remain A `v2_codec._SHAPES`. Envelope members are codec, store_uuid, sequence, event_id, transaction_id, transaction_index, transaction_count, kind, payload_codec, payload_sha256, previous_event_sha256, event_sha256, occurred_at, actor_id. Payload digest=S(C(payload)); event digest=H("ledger-event/v2", envelope without event_sha256). Sequence orders events, not timestamps. Index=count=1. source.validated/source-valid/v1 and scope/candidate/queue/domain/export/import tags remain refused.

## 2. Proposed trusted catalog

Ship an immutable application-owned **historical-catalog/v1**, never a database-enrolled list. Exact lookup includes stored Spec identity **and canonical descriptor bytes**, schema profile, codecs and policy semantic version; no prefixes, ranges or newest-reader default.

Each entry specifies:

- Exact descriptor/BLOB hashes and bytes, provenance commit/release, packaging/runtime tuple, exact schema allowlist and codec/policy versions with all configuration fields and hard ceilings.
- Application-assigned entry ID and **static handler ID**. Separate capabilities cover ledger replay/policy decoding, canonical hashes, native reader and integration/candidate/remediation semantics. Verify local handler artifact hashes; these do not replace historical implementation identities.
- Explicit tested producer-runtime/host-runtime combinations. Copying old runtime strings into a descriptor does not establish old execution semantics.
- Release-owned human/security approval: reviewer, aware timestamp, reason, reviewed source/bundle reference and frozen vectors. Diagnostics report catalog/entry/handler versions.
- Lifecycle: active for named capabilities, read-only retired, or revoked. Retirement stops new captures; retain safe reviewed historical read handlers. Revoked/absent required handlers refuse complete trusted replay. Never rewrite historical events to current identities.

Only static trusted local code supplies handlers. SQLite module names, paths and strings remain data: no import, eval, executable loading, path resolution, subprocess, download or installation selected by DB metadata. A reviewed compatibility shim may reproduce old semantics without importing old Python files, but requires its own pinned artifact identity and old-vector equivalence evidence. Code resemblance and equal version labels are insufficient.

**Recognized metadata is not an available executable implementation.** Diagnostic recognition alone cannot return verified state. All capabilities required by the exact requested schema/event profile must be available and artifact-verified. Initially use a conservative complete-bundle rule, including the historical reader artifact even for A metadata replay that does not execute it: matching descriptor plus missing reader refuses trusted replay. No partial trusted state and no fallback.

Initial catalog cap: **four exact descriptors total**, enough for the two A0 families plus at most two separately reviewed B profiles. This is not enrollment or approval. Additional runtime/CRLF/release variants consume entries and require review; raising the hard cap requires a separate reviewed contract change.

## 3. Frozen A-stage fixture contract

### Existing golden vectors

Preserve the literal vectors in tests/test_v2_codec.py; do not regenerate expected values through B:

| Preimage/vector | Expected SHA-256 |
|---|---|
| Canonical UTF-8 `{"a":1,"text":"Ä\\r\\n","z":[null,true,-2]}`, JSON escapes, no final newline | `0149df147f33e29c3279b9791c21bc3f2760869d0a7259ef5d6f61341c7ac396` |
| H("golden/v1", {"a":1}) | `cfe2b97340217e4a08d67cb3142e6e9ca2139bed0f5f7a81c2aec1af5fe552a4` |
| Genesis payload: store_uuid=32 zeroes, schema=2, staging_only, store-init/v1, canonical-json/v1 | `aad5dbcce9890ed6355f6b34b059023908cddc7139c90e5e745c35820a66bd82` |
| Envelope for that genesis: sequence=1, event_id=32 ones, transaction_id=32 twos, index=count=1, previous=null, time=2026-11-10T12:00:00.000000Z, actor=synthetic:human | `1309df5825470401c924ed11f3ebebabad13baf6fb90f67702f4976e2c4db36d` |

Existing A tests document independent .NET hashing of literal preimages. The **new A0 fixture-reference vectors below** were calculated read-only with json/hashlib over explicit JSON preimages using the observed descriptors/policies, without creating a DB. They still require comparison with a future A-only fixture builder and independent review. They are not a successful historical replay test.

### Deterministic A0 ledger fixture

U(n)=n encoded in exactly 32 lowercase hexadecimal digits. Store=U(1), actor=`synthetic:compat-reviewer`, every audit time=`2026-11-10T12:00:00.000000Z`. A future test-only harness patches `v2_ledger.uuid4` to UUID(int=1), UUID(int=2), ... and `v2_codec.utc_now` to this timestamp; no production changes.

D1=(source_id synthetic:compat-a0-docx, revision 1, registration U(10)); D2=(same source, revision 2, U(17)); X1=(synthetic:compat-a0-xlsx, revision 1, U(26)); Y1=(synthetic:compat-a0-missing, revision 1, U(31)).

- DOCX-labelled exact bytes: ASCII `FICTITIOUS A0 DOCX CAPTURE` plus one LF, 27 bytes, SHA-256 **0ff38ccf4f11a70bac7ac86d85d2dbe772c24858d4bc42d2927bc2415f0b1937**.
- XLSX-labelled exact bytes: ASCII `FICTITIOUS A0 XLSX CAPTURE` plus one LF, 27 bytes, SHA-256 **b17a108c5ef9447e9308ffad6bb817990930f4869aee29c9949af00c45a41f2f**.

These fictitious bytes intentionally are **not Office ZIP documents**. A permits quarantine capture without parsing. B must preserve A history without blessing them as valid documents. Positive reader fixtures are separate below.

DOCX registry=U(6), session=U(7); XLSX registry=U(22), session=U(23). Initial epoch=1, history=0. Default policy Specs are frozen in section 7; policy revision=1 throughout. source.started uses empty lineage, exact family implementation hash, predecessor=null except D2 predecessor=U(10). DOCX selection=null; XLSX selection={"name":"IT-Systeme","ordinal":1,"sheet_id":1,"relationship_id":"rId1","part":"xl/worksheets/sheet1.xml"}.

| Sequence | Event/command meaning | Event ID / transaction ID |
|---|---|---|
| 1 | create store; store.initialized | U(2) / U(3) |
| 2 | register DOCX A0 implementation | U(4) / U(5) |
| 3 | create DOCX registry/default policy | U(8) / U(9) |
| 4 | begin D1 | U(11) / U(12) |
| 5 | capture DOCX-labelled bytes for D1 | U(13) / U(14) |
| 6 | fail D1; phase=environment, issue_codes=["operator_failed"] | U(15) / U(16) |
| 7 | begin D2; leave uncaptured | U(18) / U(19) |
| 8 | register XLSX A0 implementation | U(20) / U(21) |
| 9 | create XLSX registry/default policy | U(24) / U(25) |
| 10 | begin X1 | U(27) / U(28) |
| 11 | capture XLSX-labelled bytes for X1; leave PENDING | U(29) / U(30) |
| 12 | begin Y1 | U(32) / U(33) |
| 13 | capture nonexistent local .xlsx path: source.failed, phase=capture, issue_codes=["capture_failed"] | U(34) / U(35) |

Implementation events bind both section 1 identities. Registry payloads use initial_policy_revision=1, baseline_registry_epoch=1, baseline_history_units=0. Captures bind byte_length=27 and the exact original hash. Observed/activated/envelope times use the fixed timestamp; singleton envelope predecessor is null only at genesis.

| Sequence | Reference payload SHA-256 | Reference event SHA-256 |
|---|---|---|
| 1 | `e1a9ccac9447d298a7ad5c361232a7d7d5a03e09b48d46b1e35c8f53c921688a` | `593006a5553fcda703f840562bd52722a0826da67d2b15caccbbd186a28656f3` |
| 2 | `e5d5949d7ae4e4195d53d3695b79ef1aae812ff4fbe6385407eb2670beca67f8` | `bf7d243e89cbc76c7fac3894ee3c8a9350a4778e1dbebb85832f3e27d22df7ff` |
| 3 | `819356cdc16eb61bbab04fc5950d2a3f22711c79e7972973bc7f41592cbe8ae7` | `3b359f36843f00a39ded0a9ac8142cef771626aa033684899a5ba321fcd60172` |
| 4 | `1a4ffd74a078b1c51a67e4a35ac152fd14d73e97a1adf8082bc0449512616c87` | `7dc76bd9de8a4621e3f2f43040001c393b5e98e0b0ec38e3d27988d97ddb0fb7` |
| 5 | `8471b484c4013b522904dc9ea291db99277b97e0d3fb2c32aed04927d30f00e1` | `657fda49506e500d823ad9070bf978aad6caebc5f1f803d90d47b4aa8eca211a` |
| 6 | `48c5ad667a4b2f4a06d1e606cce1702bca910f821aba81a3ed027346f4e8becf` | `17675a2242068dcd8c6f0fa6108de869253001553287f5d99ccb7769b1a9d969` |
| 7 | `7e3d3f577c1f9553387b1a19bfb7fbc3c04e06e6592f36a97fcdc684fe90a44a` | `a637f40bf84571cd0a118d6b5c7f05be8bc31b7dc4959a50ab33af9476cea184` |
| 8 | `df5756ed1ffb6c9368d746ce8729669c88502488297a3cc4586ebbe8e3a0b9b5` | `6586d65b9ba8509a8386d90ba529ea421dc2707903640cdca653f3b5dd31b158` |
| 9 | `e800031646e5fb1d424150f831222e07fa50659b854987e4f9aa3fbc8b5ed80c` | `e8f947c8c407b12850461b601874a5d114d3f63454546a0a3d161916c8d881e4` |
| 10 | `d2f62536f3198775a08193fd5b3613c9e02e11c41340c4fd8ae77566dc0a928e` | `cd174093e7d525ba627ffc4f47016df30743b383876057abacac2d8dd98d5f29` |
| 11 | `717c1a84fadf7c79de4379eb7a8ab703267780493d4605116c39ce45c379551b` | `77730a8763d4645bc771b83aa45ab032cdbce9c400e6e4f613eea0b621cdd4c2` |
| 12 | `21f3f11cbc00cf0bf48d2b01f0aaab1c43b67cb4524b9bb6f5410c52b0189aed` | `40ab7acb208f43b8ffb61beafe59be9020fb2f8c12670f9b2bf918183ecebfd2` |
| 13 | `bd85b230efb9d227d81174d32a0a6aa3edb9fa346b0c6029550efe8263a10832` | `e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09` |

Final head=(store U(1), sequence **13**, event hash **e54703aeb3fa75f06680f4bbf83ea2e413a4e9e00759d1f02e691bd3f1430f09**). D2 is current PENDING without bytes/hash; old D1 remains FAILED with bytes/hash. X1 is current PENDING with captured bytes/hash. Y1 is current FAILED without invented digest. Totals: 2 registries, 3 logical sources, 4 registrations, 2 original BLOBs; no VALID source, scope, candidate, queue or approved fact.

### Future fixture creation and two-version proof

1. Archive a reviewed immutable A checkout at 2ee9bc7 with exact LF artifacts and the frozen runtime. Verify section 1/7 module, descriptor, schema and policy identities before creating anything.
2. In a future approved harness use new temporary fixed-local NTFS/ReFS paths outside Git: unused DB, the two exact synthetic source files and a guaranteed nonexistent .xlsx. No user DB or binary fixture is added to Git.
3. Apply only the UUID/time harness mocks. Use A's public SourceLedger commands in table order. Pass fresh expected LedgerHead for every command and the exact predecessor SourceRef for D2. Do not build event rows through SQL or import staging snapshots.
4. Close and reopen/read with A. Compare all canonical descriptors/policies, 13 payloads/envelopes, observations, projections and current heads to these literal expectations. Archive a separately reviewed logical fixture manifest, artifact digest and source bytes outside Git. Do not let B calculate its own expected values.
5. Give the unchanged A DB to changed B code with reviewed exact handlers. Historical **read-only** verification must reproduce all blocked heads/history. Check DB bytes before/after load. Writable open is a separate test requiring an explicitly supported unchanged schema; no implicit upgrade or event on open.
6. Isolated unknown/forged descriptor, runtime, schema, codec and missing-handler variants must refuse without writes, repair or partial trusted state.
7. Separately freeze valid A-native DOCX/XLSX goldens **before B changes**: baseline tests/test_docx_staging.py synthetic_parts(paragraph(COMPLETE)), and tests/test_xlsx_staging.py fictional_parts() with default row/headers/SELECTION. Existing writers use ZIP_STORED/fixed 2020 timestamps. Record exact source bytes, native text/hash/manifest where present, integration manifest, all locators, limits and implementation stamps. Independently review literal golden values under A. This positive-reader corpus is a Gate B prerequisite; not created or demonstrated here.

SQLite physical layout/digest is an artifact check, not the semantic compatibility oracle. Exact logical history, descriptors, source bytes and locators must match. A purported A fixture generated by B does not prove compatibility.

## 4. Future verified DOCX/XLSX replay

The complete requested operation must verify or return bounded errors with **no partial trusted result**.

1. Select an exact supported schema/event profile and trusted catalog handler bundle. Apply count/size limits before allocation; verify integrity, canonical records, all chain/transaction/reference/projection invariants and historical policy transitions. DB names never choose code.
2. Retrieve original bytes only from captured immutable content BLOBs; recompute size and SHA-256 against source.captured. Any future external store must be trusted local, hash-addressed, immutable/read-verified and bounded. Never reread a mutable import path.
3. Reconstruct full ordered registrations and highest-started heads, retaining pending, failed and old captured revisions, registry ownership, policy-at-registration and exact explicit sheet selection. A newer blocked head must never fall back to an older valid head.
4. Future source.validated requires preceding exact captured registration, pinned reader/policy/runtime and full re-extraction. Retain original binary and native UTF-8 Unicode-text hashes separately. Matching stored hashes does not excuse a parse failure.
5. DOCX: recompute native ordered segments/text hash and docx-integration/v1 over complete text/locators. **No native DOCX manifest exists today**; do not invent one. Preserve exact part/paragraph/table/row/cell/paragraph positions and segment-local offsets, never pages.
6. XLSX: recompute native text/native-manifest hashes and full ordered sheet/cell structure, explicit selected sheet identity, blanks versus empty TEXT, row/column/coordinate/text/offsets; compare xlsx-integration/v1 in full. No omitted cells or first-sheet fallback.
7. Integration manifests bind binary identity, source, native structure, limits and the **existing** reader implementation stamp (Python version plus reader/OOXML byte hashes). This differs from the broader ledger Spec identity. Historical handlers reproduce both, never substitute current stamps.
8. Verify every future source.validated derivation field: exact SourceRef/raw hash, reader/policy identity, native hashes where defined, integration hash and immutable derivation reference. Recompute, do not trust status/support flags. Unknown, duplicate or impossible transitions refuse. A FAILED terminal ref cannot become VALID; begin a new registration.
9. Under Gate C reconstruct complete declared same-format scopes and contemporaneous/current heads; cover every segment/sheet/row/cell. No mixed-format coordinator, skipped workbook, row truncation or imported session snapshot. Recompute values/nulls/quotes/predicates, conflicts, bindings and candidate/context fingerprints. XLSX 101 rows blocks the whole scope.
10. Replay candidate IDs/revisions/history through a dedicated deterministic adapter preserving IDs/timestamps, not live staging calls that allocate UUIDs or create scopes. Compare recomputed data to persisted derivatives. Historical reports are not live eligibility.
11. Under Gate D replay globally ordered, identified human decisions with exact original candidate/context fingerprints and permitted states. Reapply **all** REJECTED/NEEDS_CLARIFICATION blocks to existing source-bound remediation/v1 identities. Repackaging, row moves, unrelated revisions and policy tightening/restoration cannot clear them. Reversion restores the old block; corrected content is a new unapproved revision. No policy-only override.
12. Recheck exact store head, SourceRefs, active policy, complete scope and candidate/context fingerprints before any new command, under the write transaction. Stale tokens fail without automatic retry; no approval results.

**A checks available now:** source/event/BLOB integrity, exact existing implementation/policy identities, revisions/ownership, PENDING/FAILED heads, counters/projections. A stores no native derivations, integration manifests, scopes, candidates or queue decisions, so cannot prove them. Reading A captured bytes does not create validation authority. Reopened uncaptured PENDING ref has no old capture authority; explicitly fail it or begin a new revision. Existing captured PENDING and terminal FAILED states remain blocked on load.

## 5. Independent feature activation gates

| Gate | Required independent review/test evidence | Still disabled |
|---|---|---|
| A: historical recognition/read | Exact reviewed catalog/bundles/host tuple, frozen A schema/policy/codec adapter; A-created fixture reopened by changed B code, unknown/missing-handler refusal, unchanged history | All later event families and domain/export |
| B: verified source.validated | Gate A; valid/hostile native/integration/locator corpus; exact-byte replay, timeout/crash tests; explicit validation payload/state machine and exact B write-schema/profile | Persistent scopes/candidates and human queue; domain/export |
| C: persistent scope/candidate replay | Gates A/B; deterministic identity-preserving adapter, complete context/conflict/100-row/stale-token/history tests | Durable human queue; domain/export |
| D: durable human queue | Gates A–C; original decision binding, human identity/timestamp validation, substantive block/reversion history and bounded exhaustion | Domain Evidence/Inventory/ReviewRecord, approval/export, PDF promotion and v1 migration |

Default-deny later tags and enable **one independently reviewed milestone at a time**, not all gates together. Catalog enrollment does not enable decoding. No gate passes through this ADR or the existing suite.

**Write-format decision still required:** freeze the A SQL profile permanently; initial historical support is read-only A access. New B tables/events require a distinct explicitly versioned exact schema/profile and decoder. Approve its physical version/profile and any A-to-B upgrade separately before Gate B. Do not silently add tables, reuse A's exact DDL identity, append B tags to an A-only ledger or migrate on open. Historical A read remains required independently of that future write-format choice.

All gates keep Evidence/Inventory/ReviewRecord materialization, domain approval/export, PDF promotion, v1 migration/import, automatic Ollama and network calls disabled.

## 6. Resource limits and refusal

Effective limits are the minimum of application hard ceilings, exact historical policy and current trusted tightened settings. Stricter current policy can block replay; it cannot discard history, change historical parsing or clear human blocks. Apply cumulative limits before allocations and between bounded steps, not anew per event/source.

| Resource | Proposed ceiling (MiB = binary MiB) |
|---|---|
| DB/raw bytes | Existing 256 MiB DB; reader 2 MiB/source; 32 MiB aggregate original BLOBs ledger-wide. |
| Source count | Existing 16 logical sources/registry, 4 registries, at most 64 ledger-wide; complete scope <=16. All revisions also consume byte/history/event limits. |
| Events/metadata | Existing 10,000 events, 128 MiB unique metadata/spec/payload BLOBs. Reserve one event + 1 KiB/allowed registry for exhaustion; default normal event ceiling 9,996. |
| Canonical decoding | Existing 8 MiB/value, depth 64, nodes 100,000, 10,000 items/collection, 1 MiB/string. Strict typed fields remain mandatory. |
| Time | Existing 60 s whole replay; proposed additional 10 s/document under the same total deadline. Future bounded local worker must enforce parser termination before Gate B. |
| OOXML | Existing <=8 MiB uncompressed, 2 MiB/XML part, ratio 100, depth 32, nodes 20,000; DOCX 16 ZIP entries/4,096 segments; XLSX 64 entries/16 sheets/10,000 cells. All other exact reader fields retained. |
| Manifests/text | Existing 8 MiB/integration manifest, 32 MiB retained manifests and 1,000,000 retained native text characters/registry; scope <=1,000,000 characters; DOCX assertion <=2,000. Global metadata cap also applies. |
| Candidates | <=100 eligible assertions/complete scope; XLSX independently <=100 data rows/workbook. Proposed diagnostic allocation ceiling: 1,600 drafts/scope, also bounded by history/metadata. Count complete native rows before allocation; excess refuses the whole operation, retaining original bytes/context references without truncating into eligibility. Unsupported workbooks can contain more than 100 rows, so 1,600 is a proposed replay cap, not an existing reader guarantee. DOCX <=16 single-assertion sources. |
| Queue/history | Proposed <=512 durable queue decisions/registry, also charged to existing 512 DOCX/2,048 XLSX history units and global event/bytes. No eviction or reset of blocks. |
| Historical catalog | Four exact descriptors total initially; bounded codec fields and static lookup table. No database-driven growth. |

A's replay deadline is cooperative, not parser process/RSS isolation. Worker enforcement and new queue/catalog caps are future implementation requirements. No new multi-event transaction support is implied.

Unknown versions/combinations, required reader unavailability, mismatched bytes/manifests/locators, impossible order, incomplete scope or exhaustion refuse the **complete requested trusted replay**. Bounded diagnostic errors contain no source text and confer no authority. No cached eligible subset. Fully verifying a known PENDING/FAILED/exhausted ledger or human-blocked scope may safely return a **blocked** state; that is not a fallback or partial trusted replay.

## 7. Exact A0 default policy inputs

These complete objects freeze fixture inputs; persisted non-default policies still need exact supported decoding and original ceilings. Policy identity is H(type, object without type), not version label/default fingerprint.

DOCX:

```json
{"config":{"max_field_bytes":16384,"max_history_units":512,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_source_chars":2000,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_entries":16,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_segment_chars":16384,"max_segments":4096,"max_table_columns":128,"max_table_rows":1000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c","kind":"docx","semantic_version":"docx-single-assertion/v1","type":"policy-spec/v1"}
```

XLSX:

```json
{"config":{"max_data_rows":100,"max_history_units":2048,"max_id_chars":64,"max_location_chars":256,"max_manifest_bytes":8388608,"max_retained_bytes":33554432,"max_retained_manifest_bytes":33554432,"max_retained_text_chars":1000000,"max_scope_chars":1000000,"max_scope_rows":100,"max_sources":16,"reader_limits":{"max_attribute_chars":4096,"max_cell_chars":16384,"max_cells":10000,"max_entries":64,"max_file_bytes":2097152,"max_namespaces":32,"max_ratio":100,"max_shared_strings":10000,"max_shared_text_chars":1000000,"max_text_chars":1000000,"max_uncompressed_bytes":8388608,"max_worksheets":16,"max_xml_attributes":16,"max_xml_bytes":2097152,"max_xml_chars":2097152,"max_xml_depth":32,"max_xml_nodes":20000}},"implementation_hash":"22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2","kind":"xlsx","semantic_version":"synthetic-it-table/v1","type":"policy-spec/v1"}
```

Member order shown is illustrative; C sorts all keys. Hash the canonical bytes, not Markdown/newline bytes.

## 8. Future test/threat matrix

Required tests below have **not** been implemented or executed here.

| Case | Required outcome |
|---|---|
| A0 DB created by A, opened read-only after B code changes with reviewed bundle | Identical 13 events/head/history/bytes/projections and blocked PENDING/FAILED results; unchanged DB, no validation append. |
| Reviewed historical descriptor/schema/host/policy/handler tuple | Exact recognition and complete verification only for independently enabled capabilities; no document truth claim. |
| Unknown/forged descriptor, runtime change, coherently rehashed unknown identity | Full refusal, no enrollment/import/repair. |
| Matching descriptor, missing historical reader/artifact | Diagnostic recognition possible; trusted replay refused under complete-bundle rule; no newest fallback. |
| Changed trusted ledger/reader/other-format code without declared compatibility | A refuses today; B also refuses unless exact new handler/host compatibility was reviewed. |
| Corrupted document bytes/length/hash | Full refusal. Rehashing stored metadata does not bypass independent derivation checks. |
| Wrong historical policy/config/fingerprint | Refuse; no current-default substitution. Legitimate tighter active settings may reconstruct a verified blocked state. |
| Repackaged identical-content ZIP | New binary/integration binding and stale operational token; substantive human block still applies; no approval. |
| Corrected then reverted rejected/clarification assertion | Preserve revisions; historical substantive block reappears for old content despite new UUID/revision. |
| Unrelated document/row addition/revision, row move, policy tighten/restore | Recompute entire scope/currentness; existing human blocks persist. Missing context blocks full scope. |
| Crash after started before capture | Current PENDING, no invented bytes; no old-head fallback or recovered mutable-path capture authority. |
| Crash after capture before validation | Captured PENDING with verified original bytes; never automatic VALID. |
| Coherently rehashed false status, manifests, locators, candidate support/projections | Recompute and refuse mismatches. A self-consistent forged entire corpus has the authenticity limitation below. |
| Unknown event/payload/manifest/identity codec, schema/version/layout | Full refusal without writes, future-tag skipping or decoder fallback. |
| Impossible sequence/transaction or incomplete source context | Full refusal; only a completely verified known blocked history may be returned. |
| Bytes/count/time/manifest/text/candidate/queue/catalog exhaustion | Bounded refusal or fully verified terminal blocked state; no truncation/eviction/budget reset/partial proposals. |
| DB-supplied code/path, approved queue state, PDF or v1 import tags | Refuse; spies assert no model/network/code execution, domain materialization or read-side SQLite mutation. |
| Valid A-native DOCX/XLSX and hostile variants | Pinned handler reproduces exact native/integration/locator vectors; unsupported sources reject; negative A0 captures never validate. |
| Retired/revoked bundle, absent semantic bridge | Explicit safe reviewed read-only retirement or refusal; never mutate historical identity. |

## 9. Residual risks and unresolved decisions

Exact syntax, hashes and deterministic replay do not establish real-world truth, authenticated provenance, author/reviewer identity or completeness. An attacker who replaces the entire unsigned DB, source corpus and event chain can forge a self-consistent history. Actor strings/timestamps are not authenticated human signatures. Source authentication, local access/backup integrity and an external trusted checkpoint require separate design.

Before Gate A: approve catalog/bundle/host tuples and retirement process; build/review the A-created fixture against these reference vectors; implement/test the frozen A schema/policy/codec handler. Before B: freeze valid A-native/integration vectors; decide explicit B write-format/upgrade boundary, validation codecs/state machine and worker/time enforcement. Before C/D: specify deterministic adapter, event atomicity, candidate and queue codecs and human block replay. None may reset remediation identities or activate all gates together.

Synthetic DOCX/XLSX only. No general Office compatibility, production readiness, BSI baseline confirmation or certification claim.

## 10. TASK-007.3B.1: implemented Gate A subset

Baseline for this implementation: clean **78485a90dcdea6f62a4c985489b1bea9b506112d**. See [TASK-0073B1-RESULTS](../tasks/TASK-0073B1-RESULTS.md) for the authentic oracle, final tests and reproduction. Earlier sections describe A-stage observations and the wider proposed contract; this section records the new, bounded implementation. It does not activate the other gates.

Public read API:

```python
from grundschutz_ai.v2_compat import (
    HistoricalLedgerError, HistoricalLedgerLimits,
    historical_catalog, load_historical_ledger,
)

entries = historical_catalog()  # immutable metadata; not executable availability
state = load_historical_ledger(trusted_synthetic_oracle_path,
                              limits=HistoricalLedgerLimits())
# Immutable source/event metadata only; no eligibility or writer returned.
```

The application-owned historical-catalog/v1 has exactly **a0-docx/v1** and **a0-xlsx/v1**, with the exact section 1 descriptor bytes/identities, source-lf/v1 packaging, Python 3.12.6, SQLite 3.45.3 and windows-fixed-ntfs-refs/v1. Each entry binds exact A schema/codec versions, complete policy ceilings/version, handler ID **a0-source-ledger-read/v1**, the 13 literal event vectors, and the authentic oracle manifest. Only capability **source_ledger_read** is supported. The hard catalog ceiling remains four; current membership is exactly two, with no runtime enrollment or write/validation capability. Retirement or additional entries require a reviewed application release, never a database action.

The explicitly reviewed bridge replaces the old descriptor's v2_ledger executable role with **v2_a0.py**, SHA-256 **a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd**. Historical descriptors retain their original v2_ledger hash unchanged. The local bundle additionally requires the other nine original A module files with their exact section 1 hashes, including both readers and stagers. No database module name selects a file. The shim does not import the current writer, invoke readers/stagers, or import historical executable code from an archive/database.

DTOs, filesystem/path validation, schema checking, replay state machine, projections and limits are copied from A and checked AST-identical against the isolated A checkout. Deliberate differences are the frozen pure policy bridge, strictly read-only connection/transaction helpers and private read entry. Schema/codec modules remain unchanged and hash-pinned. Current policy constructors are never used. Policy parsing freezes every original field/ceiling and the original staging fingerprint preimage; it supports only the original semantics and valid tightenings. A changed shared artifact refuses loading instead of adopting its new semantics. The connection always uses mode=ro, query_only=ON and a read transaction; even its private helper refuses a write-mode request.

The current v2_ledger writer has only a module-docstring change explaining the separate API. Because A descriptors already include that file's exact bytes, this changes the current local descriptor and makes SourceLedger.open refuse historical A0 registrations without adding a historical fallback. No writer logic, schema or event codec changed.

Before these production edits, tests/a0_oracle.py verified all A0 identities in a separate exact 2ee9bc7 Git-archive checkout and built the 13-event oracle through the **unchanged A public API**, with UUID/time mocks only in the harness. It refused an initial CRLF export; a fresh export using Git's per-command core.autocrlf=false matched the exact LF profile. No hashed production source was edited to forge identity.

Actual oracle artifacts, stored outside Git:

| Artifact | SHA-256 |
|---|---|
| Original A-created SQLite bytes | `5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537` |
| Complete canonical A state/projection manifest | `3b01d810cadc1058be89b4c9aebcdaf8b0ec4058375b134c4a8336c98b193c15` |
| Literal A SQL transport, 54,444 bytes, retained in tests/fixtures/a0-ledger.sql | `a89ea981a57ffbe1328ed8aee7ff9e916099ee2196aa4c055d7d81af133b8d61` |

The SQL text is a trusted synthetic test fixture exported from the real A DB, not a binary database and not production input. Ordinary offline tests reconstruct only its frozen A-written rows without using the B writer. Separately, the cross-version test used the original A-created DB itself, compared the full A state and unchanged binary digest after B.1 read-only replay. The full reconstructed state/projections match the independently generated manifest; all 13 existing literal payload/event vectors match, with the same final head and blocked heads defined in section 3. No source becomes VALID.

Additional policy vectors came from the isolated unchanged A code: DOCX max_sources=8, max_id_chars=32 and reader max_file_bytes=1,048,576 gives policy fingerprint `9f5ad87532f18da33eb62ca525537905ed544c1a77ed99148f277cb81c6e5a03`, Spec `e958f7117992894712f727cb7b9d6501adad40850ea7c5fca5d857caed6eec7a`; XLSX max_scope_rows=50, max_history_units=1,024 and the same reader byte limit gives fingerprint `5e7e836510e405c617c65e7260dddf9fc6e16eec13e37287f540882d8d87ca7f`, Spec `c62783f9c845367ead67d7960e91918cd067f69c15caf70aabf362f5cdb7561e`. All other policy values remain their exact defaults.

Final B.1 verification: **550 tests discovered, 545 passed, 5 existing optional Ollama tests skipped, 0 failures/errors**. This includes all 502 previous offline tests and 43 new tests. The original-A proof runs when GRUNDSCHUTZ_A0_ORACLE names the independently built DB; it was enabled for this acceptance run. Without it, that one proof is explicitly skipped, while the literal A-export offline regressions still run. No B-created DB is substituted for that proof.

The earlier no-implementation statements apply to B.0 and the wider B/C/D design. Gate A now has a technical implementation and demonstrated A-to-B read-only fixture compatibility, pending human release review. **source.validated, persistent scopes/candidates, durable human queue replay, approvals, domain materialization/export, PDF promotion and migration remain disabled.** Native-reader goldens and new write-profile choices remain Gate B work; Gate A never parses the deliberately invalid Office captures.

Limitations remain: this exact LF/runtime/package combination only; no general historical compatibility or semantic bridge for later codec/reader changes; cooperative replay deadline, no parser-worker implementation; unsigned corpus/actor authenticity and source truth are unproven. Fixture hashes are acceptance anchors, not an authenticity guarantee for arbitrary ledgers. Repackaged/CRLF/runtime variants are refused unless independently reviewed in a future release.
