# TASK-007.3B.2.2 — Trusted native reader bridge and handler identity

Completed on the reviewed Windows/Python profile using synthetic data only.
Required and actual starting HEAD: **2ca525161bd756d6868d2998c38b7e6479ca84b1**,
initially clean. Repository: `Y:/Grundschutz-AI`; application:
`Y:/Grundschutz-AI/Grundschutz-AI`. Python **3.12.6**, SQLite **3.45.3**,
Windows fixed-local NTFS/ReFS profile. No installation, download, network call,
model call, security setting change, company document or commit.

## Result and boundary

**READY FOR REVIEW for the nonpersistent bridge only.** All seven immutable A0
goldens are reproduced byte for byte, including the original binary, native
text/observations, limits, native/integration manifest bytes and reader stamps.
The four-profile catalog contains two unchanged read-only A0 ledger profiles
and two native mechanics profiles; it cannot enroll another profile.

No source VALID state, eligibility, persistent derivation reference, SQL writer,
registry bootstrap, source event, Evidence, Inventory, ReviewRecord or approval
is introduced. The schema-3 store remains genesis-only. Persistent source
registration/capture/validation and later Gate B work have not begun.

## Changed files and responsibilities

- [v3_native.py](../../grundschutz_ai/v3_native.py): explicit captured-byte API,
  verified owned temporary transport, fixed worker invocation, bounded pipes,
  cumulative deadline, termination/reaping, complete result verification and cleanup.
- [v3_native_worker.py](../../grundschutz_ai/v3_native_worker.py): fixed isolated
  interpreter entry point, pinned native readers, strict framing, independently
  repeated extraction/comparison and a restrictive Python audit guard.
- [v3_native_contract.py](../../grundschutz_ai/v3_native_contract.py): small
  shared typed contracts, bounded canonical wire format, frozen A0 integration
  encodings and parent reconstruction. Sharing these rules avoids duplicate
  parent/worker serialization logic; this is not a general framework or writer.
- [v3_native_catalog.py](../../grundschutz_ai/v3_native_catalog.py): static
  release-owned identities, literal artifact pins, original reader descriptors,
  policy ceilings, capabilities and exact runtime checks.
- [test_v3_native.py](../../tests/test_v3_native.py) and
  [test_v3_native_worker.py](../../tests/test_v3_native_worker.py): **86 new
  offline tests**, literal historical expectations and hostile boundary checks.
- [ADR-0011](../decisions/0011-verified-source-validation-profile.md): appended
  implementation clarification, precise authority and resource limitations.
- This report. No existing production module, original test or fixture changed.

## Handler identities and trust

The exact twelve-field `reader-handler-spec/v1` shape is unchanged. Capabilities
are immutable catalog-entry metadata outside the descriptor, not a thirteenth
descriptor field. Native entries have only `extract_captured_bytes`; historical
entries retain only `source_ledger_read`. Neither receives source validation
authority. Full reader implementation descriptors come from the unchanged A0
catalog, and their exact tagged hashes are bound below.

| Family | Handler ID | Original reader-spec identity |
|---|---|---|
| DOCX | `a0-docx-native/v1` | `c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c` |
| XLSX | `a0-xlsx-native/v1` | `22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2` |

| Family | H(type, descriptor without type) | S(canonical descriptor BLOB) |
|---|---|---|
| DOCX | `fc9914f4189460d53df1d1559c1cf72004de75192bc9a2cff05e4c7a036923a5` | `196bbb98cce6a56eea7e9c55e186946fa1dcb9b10040e03579c92978c2d0c97d` |
| XLSX | `467a24e02832732d0b93e20b63839f344e6020380bbaaa69c2efaa6ef58df5e2` | `4fb60af3b4a797a71983cad5b3ffdf7195f0ba290fce47c928b4c626034b4552` |

Identities and BLOB digests were independently recomputed using .NET SHA-256
over canonical preimages assembled with standard JSON, without bridge hash
factories. The resulting literal vectors are asserted in tests. The catalog
itself is the trusted application release root, not a self-hashing artifact.
Its code identity is reported separately below. No database/document/source ID
selects an executable, module path or handler implementation. There is no
automatic hash regeneration or current-staging compatibility fallback.

All eleven artifact identities are literal release pins. Files must retain
their exact reviewed LF bytes; line-ending changes also fail closed. Runtime
stdlib/OS DLLs are trusted host dependencies, not a completely authenticated
Python installation. Other Python/SQLite/platform profiles are refused.

| Artifact ID | Exact SHA-256 |
|---|---|
| `canonical-codec` | `577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3` |
| `docx-reader` | `a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b` |
| `historical-catalog` | `0b782ed32aeb8a8e602df916c9d2da1fc0f0f6b97aacdf4e73483737aba0b496` |
| `historical-path-policy` | `a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd` |
| `historical-schema` | `9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc` |
| `native-bridge` | `73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926` |
| `native-contract` | `9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2` |
| `native-worker` | `454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319` |
| `ooxml-safety` | `35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6` |
| `python-executable` | `737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae` |
| `xlsx-reader` | `8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72` |

Trusted release root `v3_native_catalog.py`: `1b3d65085681f8b9112cf1b0f5a6374edbc54d0603431c25339abf5aa02a46b9`.

Both descriptors bind `canonical-json/v1`, the exact runtime
`{python_version:3.12.6,sqlite_version:3.45.3,platform_profile:windows-fixed-ntfs-refs/v1}`
and golden fixture SHA-256
`553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b`.
Policy versions are respectively `docx-single-assertion/v1` and
`synthetic-it-table/v1`; current staging defaults are never used.

Exact compact UTF-8 descriptor bytes (each block's single JSON line, excluding
the surrounding Markdown newline):

```json
{"artifact_hashes":[{"artifact_id":"canonical-codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"artifact_id":"docx-reader","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"artifact_id":"historical-catalog","sha256":"0b782ed32aeb8a8e602df916c9d2da1fc0f0f6b97aacdf4e73483737aba0b496"},{"artifact_id":"historical-path-policy","sha256":"a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd"},{"artifact_id":"historical-schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"artifact_id":"native-bridge","sha256":"73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926"},{"artifact_id":"native-contract","sha256":"9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2"},{"artifact_id":"native-worker","sha256":"454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319"},{"artifact_id":"ooxml-safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"artifact_id":"python-executable","sha256":"737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae"},{"artifact_id":"xlsx-reader","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"}],"family":"docx","golden_fixture_sha256":"553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b","handler_id":"a0-docx-native/v1","host_runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"integration_manifest_version":"docx-integration/v1","native_manifest_version":null,"policy_versions":["docx-single-assertion/v1"],"reader_method":"docx-plain/v1","reader_spec_hash":"c9c8f8d1066a82d296badf396512ea44c68d072f0b5d9cc3e75e936317268a1c","serialization_version":"canonical-json/v1","type":"reader-handler-spec/v1"}
```

```json
{"artifact_hashes":[{"artifact_id":"canonical-codec","sha256":"577c3b6ea0d3a88318f95b2b2c941b2a97d0fe8bcf11bdc478f6ad3aec4513e3"},{"artifact_id":"docx-reader","sha256":"a65c98da1b18c47c9d391ac43a3946c96ab35adb6e6a84938f79a8daedc3689b"},{"artifact_id":"historical-catalog","sha256":"0b782ed32aeb8a8e602df916c9d2da1fc0f0f6b97aacdf4e73483737aba0b496"},{"artifact_id":"historical-path-policy","sha256":"a343231bb8133e701558ac9174ff60411d5e35e4ea0fca454f7ac7c5c976f4dd"},{"artifact_id":"historical-schema","sha256":"9eb6350d0f6775292fd6991d1e0ac87c23974c00214368340f2a69fc2a5c58fc"},{"artifact_id":"native-bridge","sha256":"73965c93b2c26e9bff2c71e7b75c6fd7e34b682124ee254aee8891fba839d926"},{"artifact_id":"native-contract","sha256":"9d3b10d29af6691e9e2e7da1f6d588fc3da2687ced1f7c865f4e636bd874c5b2"},{"artifact_id":"native-worker","sha256":"454c0aae7509f0a81020a46041bbb505c085216e430c3c3d8eb20e560a868319"},{"artifact_id":"ooxml-safety","sha256":"35a90e8c807e4970b813e702f3317625c06983614ea5f4d21b77de9e272283e6"},{"artifact_id":"python-executable","sha256":"737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae"},{"artifact_id":"xlsx-reader","sha256":"8db93a2fd0af394e8b6908197ed5ef73bdd9edde096d99278e0cf62319d03b72"}],"family":"xlsx","golden_fixture_sha256":"553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b","handler_id":"a0-xlsx-native/v1","host_runtime":{"platform_profile":"windows-fixed-ntfs-refs/v1","python_version":"3.12.6","sqlite_version":"3.45.3"},"integration_manifest_version":"xlsx-integration/v1","native_manifest_version":"xlsx-literal/v1","policy_versions":["synthetic-it-table/v1"],"reader_method":"xlsx-literal/v1","reader_spec_hash":"22dbdd6b8be6397e6d215edf51b02546887df92e326fef987c4ec10d5c6198c2","serialization_version":"canonical-json/v1","type":"reader-handler-spec/v1"}
```

## Transport, execution and verification

`extract_captured_bytes` accepts bytes, expected hash/length, source ID, handler
hash, original reader-spec hash, typed complete A0 policy spec, typed execution
limits and exact XLSX selection. DOCX requires null selection. Unknown types,
families, handlers, policies, relaxed limits and structurally invalid selections
are refused before parsing. Actual XLSX selection must match the complete native
sheet identity. Physically present nonselected sheets remain in observations.

Only captured bytes are used. No mutable original source path is accepted.
The parent checks the local OS temp root outside Git, creates an unpredictable
owned directory and exclusively writes `captured.docx` or `captured.xlsx`.
The fixed filename never derives from source ID or workbook metadata. Exact
bytes/length/hash are checked in the parent before and after each worker and in
each worker before and after native parsing. Existing A0 path restrictions
refuse unsafe aliases, reparse points, links and hard-linked reader files.
The directory inherits the account's existing temp ACL; no ACL is changed.

The fixed command is the pinned Python executable, `-I -B`, the application-owned
`v3_native_worker.py`, and parent-owned transport/operation arguments. No shell,
document-selected module, model or database is involved. The child environment
contains only existing SystemRoot/WINDIR/TEMP/TMP variables. Native readers are
the exact unchanged A0 artifacts; the bridge supplies their required path API.

Three phases precede return: derive observations in one child; reconstruct and
check shapes/native invariants/hashes/exact encodings in the parent; independently
re-extract the same bytes in a fresh child and require exact candidate equality.
The final acknowledgement binds the request/context and candidate hash. Missing
or altered observations with coherently recomputed hashes still fail the fresh
extraction comparison. This is repetition through the same pinned parser, not
an independent semantic parser or proof of visual truth.

Wire messages are bounded canonical UTF-8 JSON with strict duplicate-key,
integer/type/shape/version and trailing-data checks. Each frame has an unsigned
eight-byte big-endian length. Input is metadata, original bytes, and only in
verification mode a candidate frame, followed by EOF. Output is exactly one
frame followed by EOF and successful exit. Invalid output yields no partial
result; errors are static codes without source text/parser traces in logs.

| Control | Hard default ceiling (trusted settings may only tighten) |
|---|---|
| Original bytes | 2 MiB; also reader max_file_bytes and per-call policy raw retention |
| Request metadata | 64 KiB |
| Worker output / verification candidate | 32 MiB per frame |
| Native wire tree | depth 32; 500,000 nodes; array 20,000; string 8 MiB UTF-8 |
| Text | native reader ceiling 1,000,000 characters; policy retention also enforced |
| Integration / XLSX native manifest | each at most 8 MiB, tightened by policy |
| stderr | at most 4 KiB retained; any stderr refuses the result |
| Work deadline | one cumulative 10 seconds across transport, reconstruction and both workers |
| Failure cleanup | kill/reap before file cleanup; separate 2-second reap grace, short thread joins |

Native ZIP/XML/entry/decompression/structure bounds remain the complete pinned
reader limits (and are returned with the native result). Ledger codec limits
are unchanged. Proposal row/scope/source-count/history limits retain their
policy identity, but this single-call reader has no scope/session, proposal,
human queue or eligibility API. It does not reinterpret those policy fields as
permission to start staging or source validation.

Parent pipe readers bound allocation before reading the announced body. Parsing
occurs only in the child. A timeout, crash, oversize, malformed frame, trailing
bytes, stderr, forged observations or acknowledgement cannot expose a result.
Termination/reaping is always attempted before deleting transport. Cleanup
checks the exact owned file/directory identities, deletes the known file and
empty directory only, and never recursively deletes unknown contents. Cleanup
failure also prevents return. An unexpected replacement or extra file may leave
an orphan requiring explicit local operator inspection.

Windows process termination is OS-enforced. Size/tree/accounting limits, audit
hooks and the parent's deadline are application-enforced. No Job Object,
restricted token, CPU/RSS/disk quota, complete OS/network sandbox or hostile
filesystem isolation is claimed. Audit tests demonstrate denial of sockets,
SQLite connections, subprocess creation, writes and reads outside the fixed
allowlist. Trusted Python/parser code and native extensions remain part of the
trust boundary; a native-code exploit or privileged local attacker is not covered.

## Actual test results

Final full offline command: **757 tests run in 55.238 seconds; 752 passed,
5 skipped; 0 failures, 0 errors**. This is all **671 previous tests** (666 pass,
5 existing optional Ollama skips) plus **86 new passing tests**. Both authentic
historical proof environment variables were present, their paths verified, and
both proof tests ran and passed rather than skipping:

- `test_original_A_created_database_cross_version_readonly_proof`.
- `test_original_historical_producer_reproduces_literal_vectors`.

The five skips are the existing optional Ollama integration tests; this task
does not invoke Ollama. The focused run before the final four regressions had
82/82 passing; all 86 final regressions passed in the full run.
An earlier tracked-change test initially inserted nothing because it assumed
a different XML namespace prefix. The fixture was corrected to insert an actual
namespaced element; rejection then passed. No expected golden, original test,
parser rule or security rejection was weakened.
After the full run, the hard-link regression's exception assertion was narrowed
to the exact A0 `UnsafePathError`; its targeted rerun passed (1 test, 0.015s).
No production code changed after the full run. New-file UTF-8/LF, Python AST,
whitespace, report/ADR local links, final runtime and literal artifact checks pass.

| Golden | Verified |
|---|---|
| docx_complete | original bytes/hash/length, text/hash, segments/locators/limits, integration bytes/hash, stamp; null native manifest |
| docx_coverage | ordered paragraph/table/empty segments, whitespace, Unicode, locators and exact manifests |
| xlsx_complete | complete sheet identity, row/cell order, coordinates, native and integration bytes/hashes |
| xlsx_blank | explicit BLANK preserved |
| xlsx_missing | physical absence preserved; no invented cell |
| xlsx_empty_text | TEXT with empty string preserved separately from BLANK/absence |
| xlsx_coverage | additional empty worksheet preserved even though flat text is unchanged |

Original reader stamps remain DOCX
`c4d61c972ec670cdf00b18de62cae0dc88df4a62d0745fe79d5d0681a762af12`
and XLSX
`4198a751148d1dbce974b06f449443ea954beb186d5a56798eac8be1e1131cb0`.

Negative tests cover identity/runtime/artifact/policy drift; strict/tightened
input/text/manifest/execution limits; corrupt ZIP/XML and tracked/external
structures; exact selection and traversal metadata; changed capture/transport;
forged/missing/coherently altered observations, blank/empty/missing confusion and
omitted sheets; protocol framing/extra authority/incomplete/oversized/stderr
output; crash, launch failure, timeout, cumulative deadline and reaping;
creation/write/cleanup failures; immutable output and catalog bounds. A synthetic
instruction to call Ollama/network/SQLite or approve data remains ordinary text;
parent side-effect spies and isolated child audit-denial tests pass. No inventory
or review construction code is imported by the bridge. A mutable original file
is altered and deleted after capture; extraction still exactly matches the bytes.

The unchanged schema fingerprint is
`75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c`.
Frozen A0 handler, original SQL oracle, all seven golden vectors, v3 schema,
codec and genesis-only store have no diff. No binary document/database fixture
was added to Git. Synthetic transports are outside Git and removed after tests;
the owned diagnostic transport was also byte/path/identity checked and removed.

## Remaining limitations

- Only the existing bounded synthetic DOCX/XLSX native profiles are supported.
  Unsupported Office constructs fail closed; this is not complete Office support.
- Exact syntactic reproduction does not prove factual truth, authenticated source
  ownership, visible document completeness, or prompt-injection immunity in a
  future model pipeline. Text remains untrusted and never automatically reaches
  Ollama or approved inventory.
- Shared reader bugs survive repeated extraction. Golden evidence covers seven
  approved synthetic vectors, not every possible document. The trusted catalog,
  host interpreter/stdlib/DLLs and local filesystem remain security dependencies.
- No hard memory/CPU/disk quota or full OS sandbox. Interruption/cleanup failure
  may leave an orphan. Results contain untrusted document text and should not be
  logged or treated as an authorization token.
- No persistent registration, registry/handler activation, source validation,
  replay, migration, queue, domain conversion, approval or export. No BSI baseline
  or certification conclusion. Stop after TASK-007.3B.2.2; next step is human
  review of this bridge before separately authorizing persistence work.

## Reproduction commands

On this exact reviewed host and LF artifact profile:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"

# All 86 new tests; no original historical checkout/oracle required:
py -3.12 -m unittest discover -s tests -p 'test_v3_native*.py' -v

# Full suite with both historical proofs enabled:
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI"
py -3.12 -m unittest discover -s tests
```

If the temporary original artifacts have expired, recreate them using the exact
Git-archive/A-public-API instructions in
[TASK-0073B20-RESULTS](TASK-0073B20-RESULTS.md); do not substitute new-code
oracles or silently omit the historical proof requirements.

Read-only descriptor inspection (metadata only):

```powershell
py -3.12 -c "from grundschutz_ai.v3_native_catalog import native_catalog; [(print(p.spec.canonical.decode()), print(p.spec.sha256, p.spec.blob_sha256)) for p in native_catalog()]"
```

Independent identity/BLOB SHA-256 reproduction with .NET (standard JSON builds
the tagged preimage; no bridge hash factory is used in that hash calculation):

```powershell
@'
import base64,json
from grundschutz_ai.v3_native_catalog import native_catalog
for p in native_catalog():
    d=json.loads(p.spec.canonical); t=d.pop('type')
    preimage=json.dumps({'type':t,'value':d},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    print(json.dumps({'family':d['family'],'descriptor':base64.b64encode(p.spec.canonical).decode(),
                      'preimage':base64.b64encode(preimage).decode()}))
'@ | py -3.12 - | ForEach-Object {
    $item = $_ | ConvertFrom-Json
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $identity = [BitConverter]::ToString($hasher.ComputeHash([Convert]::FromBase64String($item.preimage))).Replace('-','').ToLowerInvariant()
        $blob = [BitConverter]::ToString($hasher.ComputeHash([Convert]::FromBase64String($item.descriptor))).Replace('-','').ToLowerInvariant()
        Write-Output ($item.family + ' H=' + $identity + ' S=' + $blob)
    } finally { $hasher.Dispose() }
}

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code -- Grundschutz-AI/grundschutz_ai/v2_a0.py Grundschutz-AI/grundschutz_ai/v2_compat.py Grundschutz-AI/grundschutz_ai/v3_codec.py Grundschutz-AI/grundschutz_ai/v3_schema.py Grundschutz-AI/grundschutz_ai/v3_store.py Grundschutz-AI/tests/fixtures
```

## Git status at completion

HEAD remains **2ca525161bd756d6868d2998c38b7e6479ca84b1**; no automatic commit
or staging. One existing ADR modified, seven new files (four production modules,
two test modules and this report). `git diff --check` passes. Git emits an
informational LF-to-CRLF warning for the Markdown ADR under the existing Git
settings; Python identities are tied to exact LF bytes. No Git setting changed.

```text
 M Grundschutz-AI/docs/decisions/0011-verified-source-validation-profile.md
?? Grundschutz-AI/docs/tasks/TASK-0073B22-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/v3_native.py
?? Grundschutz-AI/grundschutz_ai/v3_native_catalog.py
?? Grundschutz-AI/grundschutz_ai/v3_native_contract.py
?? Grundschutz-AI/grundschutz_ai/v3_native_worker.py
?? Grundschutz-AI/tests/test_v3_native.py
?? Grundschutz-AI/tests/test_v3_native_worker.py
```
