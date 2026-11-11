# TASK-007.3B.2.1: SQLite schema 3 and event codec v3 foundation

Date: **2026-11-11**, Europe/Bucharest. Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`.

## Result and boundary

**Inert physical foundation complete; READY FOR REVIEW.** Only fresh initialization and complete read-only verification of a **genesis-only** schema-3 store are enabled. Strict v3 codec recognition of future events is not permission to append/apply them.

Baseline/final HEAD: **84353f7d4a5393295f700f819f840b2fbe9935a0**, `docs: freeze native reader goldens and Gate B schema contract`. Initial tree clean. No automatic Git staging/commit, dependency/download, network/model call or company document. No normative BSI/Sprint 0 approval.

Read the requested instructions/charter/plan, ADR-0008/0009/0010/0011 and predecessor results, actual v2 codecs/schema/current and historical ledger/catalog and their tests/goldens before selecting the separate v3 modules. [ADR-0011 section 11](../decisions/0011-verified-source-validation-profile.md) records only necessary foundation/fingerprint clarifications; the wider native-validation design remains unimplemented.

**No source registration/capture/failure/validation, policy activation, handler registration, reader execution, persistent candidates/queue, Evidence/Inventory/ReviewRecord, approval, export, PDF promotion or migration was implemented.**

## Frozen physical layout

- PRAGMA user_version **3**, metadata schema_version **3**.
- feature_profile **verified-source/v1**, physical profile **sqlite-source-validation/v1**.
- serialization **canonical-json/v1**, envelope **ledger-event/v3**, initialization payload **store-init/v2**.
- **15 STRICT tables**, **24 UPDATE/DELETE immutability guards** for twelve immutable tables.
- **36 SQLite-generated PK/UNIQUE indexes**, no separate user CREATE INDEX statements.
- **75 exact sqlite_master objects** checked, including internal autoindex names/null SQL. Unknown internal/user tables, indexes and triggers are rejected.

Tables: store_metadata, content_blobs, implementation_specs, reader_handler_specs, policy_specs, registries, policy_activations, logical_sources, registrations, source_captures, derivations, source_terminals, source_heads, registry_state, events. No candidate/queue/domain/migration tables and no old registration_observations table. Only store_metadata/source_heads/registry_state are mutable projections.

Schema identity:

```text
75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c
```

This is H("sqlite-schema/v3", preimage), where H(t,v)=SHA256(canonical({"type":t,"value":v})). preimage contains physical_profile, user_version, encoding=UTF-8, sorted exact {name,kind,sql} objects and sorted index {table,name,unique,origin,partial,columns,collations,descending} records. Full tagged canonical input: **31,123 bytes**. .NET SHA-256 independently confirmed the literal digest. Actual SQLite objects/indexes are compared against the fixed statements/index contracts; imported schema data cannot enroll new definitions.

All IDs/hashes/counters have typed/CHECK bounds; required/composite FKs and UNIQUE keys are fixed. Narrow ADR clarifications: metadata binds sequence/hash through a composite events FK; derivations bind exact registration registry/policy/reader/handler dependencies through a composite FK and its required UNIQUE key. Source ID/revision/store identity are normalized through parents. SQL terminal checks enforce exclusive null/empty/phase/byte rules; canonical known issue-code semantics are enforced by the codec, without requiring a SQLite JSON extension.

The physical profile name is bound by the exact fingerprint and returned metadata, not an extra mutable DB column or an unreviewed genesis field. Existing schema-2 SQL was not altered.

## Strict inert codec and literal vectors

`v3_codec.py` defines frozen Payload, Envelope, Event and DerivationRef records. It reuses unchanged canonical-json/v1 primitives and the exact original SourceRef class/preimages from v2_codec. It does not mutate the old constants, tag maps, policies or fingerprints.

Exactly ten wire contracts: store.initialized/store-init/v2, implementation.registered/implementation-register/v1, reader.handler_registered/reader-handler-register/v1, registry.created/registry-create/v1, policy.activated/policy-activate/v1, source.started/source-start/v2, source.captured/source-capture/v1, source.failed/source-fail/v2, source.validated/source-valid/v1, registry.exhausted/registry-exhaust/v1.

Checks include strict canonical bytes/UTF-8/types and bounded allocation, exact fields/tags, IDs/hashes, no bool counters, exact source references, singleton transaction groups, genesis/chain shape and event/payload pairing. The pair checks payload hash/kind/version, genesis store UUID, audit timestamp equality and capture-before-validation sequence claims. These are syntactic/internal checks, not proof of source history/native support or handler authority. No event applier or generic writer exists.

DOCX derivation-ref/v2 requires native_manifest_sha256=null; XLSX requires its digest. Actual native handlers/handler-spec enrollment and source-policy/provenance replay remain future work.

Independent literal preimages were hashed with **.NET SHA-256**, not v3 factories:

| Literal vector | SHA-256 |
|---|---|
| Exact genesis payload bytes | `f7fc5a269b8554c2be78810fe3aeb889fdc2e2357fe1de3f792d0d5961cfccce` |
| Tagged genesis envelope | `be5aa16f76c6634fdb14c4bb1238d638ee8ec890923d63d3a95cef702b64252a` |
| Exact original SourceRef bytes | `daa5c8f29826418829af7b9d60aba4511521d215945ea08a23dc99d125b73da3` |
| Literal derivation-ref/v2 canonical BLOB | `020ed9f91fd81ba3ce8af47197b74ce336b239eca64d9ffb45492ed7a3d5af43` |
| Same derivation tagged identity | `d09be1fa9973c4f4f693ac4550fa1a4c5539fc727aa68814a053d01a0af0e190` |

Genesis uses store UUID=32 zeroes, event ID=32 ones, transaction ID=32 twos, sequence/index/count=1, previous=null, actor=synthetic:human, time=2026-11-11T12:00:00.000000Z. Literal payload:

```json
{"feature_profile":"verified-source/v1","payload_codec":"store-init/v2","schema_version":3,"serialization_version":"canonical-json/v1","store_uuid":"00000000000000000000000000000000"}
```

Original SourceRef uses source_id=synthetic:source, revision=2, registration_id=32 ones. Complete literal derivation inputs are in tests/test_v3_codec.py; shared canonical Unicode/tagged-hash vectors from prior tests are also checked, unchanged. Expected digests are frozen literals rather than recomputed through the factories under test.

## Minimal public store API

```python
from grundschutz_ai.v3_store import (
    StoreLimits, create_initialized_store, load_initialized_store,
)

state = create_initialized_store(trusted_unused_local_path, actor_id="synthetic:operator")
same = load_initialized_store(trusted_unused_local_path)
assert same == state
```

Both functions close every SQLite handle before returning frozen InitializedStoreMetadata (head, exact genesis pair and verified schema/profile metadata). No writable handle/context or append/reopen-for-writing interface is returned. Even the private connection helper refuses writable access to a published target.

The loader accepts one and only one initialization event, one canonical payload BLOB, one metadata row and no rows in all twelve other tables. It verifies exact schema/indexes, integrity/FKs, profile, canonical payload/envelope and hashes, contiguous single genesis/head and exact initial projections. Recognized but nonapplicable source.validated data or any future state causes whole-load refusal.

Filesystem checks reuse the unchanged, hash-pinned A0 path guard: fixed local Windows NTFS/ReFS, absolute explicit path outside Git, no UNC/URI/mapped remote volume, ADS, links/reparse points, hard-linked DB or unsupported sidecars. Exact Python **3.12.6** and SQLite **3.45.3** are required. Frozen shared v2_codec/v2_a0/v2_schema bytes remain pinned; no old trust requirement was relaxed. This foundation does not enroll a native implementation or use current staging semantics.

### Atomic initialization/publication

1. Reject an existing target before any SQLite open. Allocate an exclusive private staging file in the same verified local parent.
2. Configure DELETE journaling, synchronous=FULL, foreign_keys=ON and trusted_schema=OFF. BEGIN IMMEDIATE; execute fixed DDL, PRAGMA user_version and only the three genesis/BLOB/metadata inserts.
3. Fully verify within the transaction, COMMIT, close, then independently verify read-only. Enforce cumulative deadline and file/page/metadata budgets.
4. Recheck paths and unused target; publish using Windows no-overwrite os.rename. No fallible verification or connection close remains after publication. Return immutable state.

The case-insensitive filename prefix **.grundschutz-schema3-init-** is reserved and not publicly loadable. A failed creation before publication leaves the caller target absent and removes only the owned staging file when possible. A racing existing file is preserved. No directory sweep, overwrite, upgrade, repair or automatic orphan recovery occurs.

Publication is the externally visible commit point. Abrupt exit before SQL commit or after private commit leaves no target; a private orphan can remain but cannot be loaded through the public API. Exit after publication leaves a complete readable genesis DB even if no success acknowledgement reached the caller. These are process-exit observations, **not arbitrary power-loss durability**. Trusted-parent/local access assumptions and unsigned-corpus authenticity limits remain.

A deterministic synthetic demonstration observed a **241,664-byte** DB, **740 metadata bytes** (payload+canonical envelope) and binary SHA-256 **78c3e1f6f3693036127de70b7e47a7d3de0f5dba802e26fcb02ecd945e472aa0**, unchanged across read-only load. Physical file bytes are an environment-specific observation, not a portable SQLite fixture; no binary DB is added to Git.

StoreLimits only tighten existing ceilings: 256 MiB DB, 10,000 events, 128 MiB metadata, 32 MiB originals, sixty-second cumulative operation deadline. Only one event/no originals is currently applicable. Exact metadata accounting includes envelope bytes. Limits are checked before publication; they are not OS disk/RSS quotas. Future registry reserves, native worker limits and source budgets cannot be inferred as active capabilities.

## Tests and failures actually observed

Final complete suite with optional Ollama disabled and both authentic historical proofs enabled:

```text
Ran 671 tests in 36.124s

OK (skipped=5)
```

**666 passed, 0 failures, 0 errors, 5 existing optional Ollama tests skipped.** All **575 previously passing tests** remain passing. New tests: **24 codec + 15 schema + 52 store = 91**.

Coverage includes all ten inert contracts, independent literal hashes, exact fields/types/limits, actual 15-table/24-guard/36-index identities, all guards exercised against SQL dummy rows, FK/CHECK/uniqueness enforcement, fresh genesis/read-only byte identity and real Windows handle release, existing-file/no-overwrite races, wrong versions/DDL/profile/codecs/hashes/sequence/FKs/projections, coherent false metadata, transaction rollback, postcommit-verification failure, private-name case handling, source.validated refusal and no native/network/domain effects.

Three real subprocess exits were tested: exit code 71 before private SQL commit, 72 after private commit/before publication, and 73 after publication. The first two produced no trusted public target; the third reopened as exactly one complete genesis event. No repair or claimed power-loss test.

Initial codec run: 24 passed. Schema run: 15 passed. First 51-store run: **50 passed, 1 test-fixture error** because SQLite concatenation returned TEXT for a STRICT BLOB column. The fixture was corrected with an explicit BLOB cast, preserving the intended byte/hash attack. Combined 90-test run passed in 4.277s; the added case-insensitive-prefix regression passed separately in 0.018s and in the final 91-new-test full suite. No expectation was weakened and no unresolved failure remains.

## Preserved compatibility and fixtures

- v1 storage and all v2 codec/schema/ledger/A0/catalog production modules are untouched.
- Existing A writer/codec/historical loader refuse schema 3; new creation never overwrites/reinterprets schema 2 and new read-only loading refuses it.
- Authentic A0 original-file proof ran and passed; no SQL transport was substituted for that proof.
- Historical native producer proof ran and passed; all seven old DOCX/XLSX cases remain byte-identical.
- A0 SQL text fixture: **a89ea981a57ffbe1328ed8aee7ff9e916099ee2196aa4c055d7d81af133b8d61**.
- Native golden text, 106,955 bytes: **553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b**.
- Frozen v2_a0.py: **a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd**.
- Frozen v2_codec.py: **577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3**.

No historical code/fixtures or existing tests were changed to make the new tests pass. Without the two proof environment variables, those original-file/producer tests are explicitly skipped; that is not equivalent to this acceptance run.

## Changed files and Git status

| File | Change |
|---|---|
| grundschutz_ai/v3_codec.py | New independent v3 inert contracts and consistent typed event/reference serialization. |
| grundschutz_ai/v3_schema.py | New fixed schema SQL, immutability guards, implicit index manifest and frozen fingerprint. |
| grundschutz_ai/v3_store.py | New genesis-only creation/publication and strict read-only load, with immutable metadata and conservative bounds. |
| tests/test_v3_codec.py | 24 new codec/vector/negative tests. |
| tests/test_v3_schema.py | 15 new actual-SQL/schema/guard/index/constraint tests. |
| tests/test_v3_store.py | 52 new store/boundary/rollback/corruption/process-exit tests. |
| docs/decisions/0011-verified-source-validation-profile.md | Narrow foundation status, exact fingerprint and concrete integrity/publication clarifications. |
| docs/tasks/TASK-0073B21-RESULTS.md | This report. |

Final repository-root short status:

```text
 M Grundschutz-AI/docs/decisions/0011-verified-source-validation-profile.md
?? Grundschutz-AI/docs/tasks/TASK-0073B21-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/v3_codec.py
?? Grundschutz-AI/grundschutz_ai/v3_schema.py
?? Grundschutz-AI/grundschutz_ai/v3_store.py
?? Grundschutz-AI/tests/test_v3_codec.py
?? Grundschutz-AI/tests/test_v3_schema.py
?? Grundschutz-AI/tests/test_v3_store.py
```

HEAD remains **84353f7d4a5393295f700f819f840b2fbe9935a0**. One tracked ADR modified; seven new files; nothing staged/committed. Test/demo DBs are synthetic and outside Git. Existing tracked production/tests/fixtures have no diff. No schema-3 binary fixture is retained in Git.

## Exact reproduction commands

On this exact reviewed Windows/Python/SQLite/LF profile, the 91 foundation tests need no external artifact:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest tests.test_v3_codec tests.test_v3_schema tests.test_v3_store -v

# Complete suite, including both original historical proofs retained this session:
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI"
py -3.12 -m unittest discover -s tests
```

If temporary historical artifacts no longer exist, recreate them using the exact Git-archive/A-public-API instructions in [TASK-0073B20-RESULTS](TASK-0073B20-RESULTS.md), then set the two environment variables to the new paths. Never generate an alleged old oracle using new code or replace golden expectations.

Read-only independent .NET schema-digest reproduction:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$schemaPreimage = @'
import base64
from grundschutz_ai import v3_schema as schema, v3_codec as codec
print(base64.b64encode(codec.canonical_dumps({
    "type": "sqlite-schema/v3", "value": schema.fingerprint_preimage()
})).decode("ascii"))
'@ | py -3.12 -
$schemaBytes = [Convert]::FromBase64String($schemaPreimage)
$schemaHasher = [Security.Cryptography.SHA256]::Create()
try {
    [BitConverter]::ToString($schemaHasher.ComputeHash($schemaBytes)).Replace("-","").ToLowerInvariant()
    $schemaBytes.Length
} finally { $schemaHasher.Dispose() }
# Expected: 75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c, 31123 bytes

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai/v2_codec.py Grundschutz-AI/grundschutz_ai/v2_schema.py Grundschutz-AI/grundschutz_ai/v2_ledger.py Grundschutz-AI/grundschutz_ai/v2_a0.py Grundschutz-AI/grundschutz_ai/v2_compat.py Grundschutz-AI/tests/fixtures
```

All SQLite writes in these checks are explicitly bounded synthetic fixtures; no user/company DB is accessed or migrated.

## Remaining limitations and next boundary

This API verifies initialized metadata only; native original-byte derivation/support, current source/policy semantics, reader-handler spec enrollment, complete future event replay and writer commands remain unimplemented. Empty physical tables and codec-recognized events grant none of those capabilities. Full source validation still requires the outstanding ADR-0011 worker/handler/replay/atomicity/threat-matrix work in a separately authorized task.

Exact shared LF artifacts and Windows/Python/SQLite profile are required; other environments are refused. Staging/publication and cooperative deadlines are not authenticated source handling, a hostile-filesystem sandbox, hard memory/disk quotas or arbitrary power-loss protection. Interrupted private files are not automatically recovered. A self-consistent whole-file replacement/actor forgery cannot be authenticated by hashes alone; metadata is not source truth or human approval.

**Gate B source.validated application/native handlers, persistent candidates, human review queue, approvals, export and migration remain disabled.** No BSI certification or production-readiness claim. Stop at TASK-007.3B.2.1; next action is human review of this inert foundation before authorizing further Gate B work.
