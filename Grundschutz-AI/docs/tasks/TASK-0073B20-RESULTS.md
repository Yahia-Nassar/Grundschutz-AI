# TASK-007.3B.2.0: Native reader goldens and Gate B write-format contract

Date: **2026-11-11**, Europe/Bucharest. Repository `Y:/Grundschutz-AI`; application `Y:/Grundschutz-AI/Grundschutz-AI`.

## Result and scope

**Golden/test/architecture deliverables complete; READY FOR CONTRACT REVIEW. Gate B is not implemented or activated.**

Baseline and final HEAD: **0a8af67cf36dc6df742b88380cdde0115947172d**, `feat: add verified historical A0 ledger compatibility`. Initial tree clean. Production Python/schema/codecs, A0 fixtures, existing tests and ADR-0010 remain unchanged. No migration, production ledger modification or proposed schema-3 database was created. No dependency, model/network call, company document, BSI baseline change or automatic Git staging/commit.

Read AGENTS.md/GOALS.md/PLANS.md and requirements, ADR-0008/0009/0010, the A/B1 reports, actual codec/schema/current and frozen ledgers/catalog, readers/stagers and requested tests. Engineering experiments do not approve Sprint 0 or the normative baseline.

## Independent historical generation

Used an isolated exact **2ee9bc7cf309727e5a9f10e2982791dbc991c464** checkout exported through `git -c core.autocrlf=false archive`. All ten A module identities, both descriptor/default-policy identities, four historical fixture-helper hashes and exact **Windows fixed local NTFS/ReFS / Python 3.12.6 / SQLite 3.45.3 / LF** profile were verified before fixture creation.

The new test-only helper `tests/native_golden_oracle.py` imports application/fixture modules exclusively from that verified historical checkout in a fresh subprocess. It creates only synthetic temporary DOCX/XLSX inputs and text golden output; it never calls a ledger writer or creates a database. A0's original schema/events/compatibility fixture were not altered.

Goldens are retained literally in `tests/fixtures/b0-native-goldens.json`: **106,955 UTF-8 bytes**, SHA-256:

```text
553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b
```

The text fixture stores exact original bytes as base64, raw binary hashes/lengths, ZIP entry metadata/content hashes, complete native text/observations/locators, native manifest where defined, full integration JSON/digest, exact limits, sheet selection, reader Spec and implementation stamp. Original ZIP_STORED/member order/fixed fictitious 2020-01-01 timestamp conventions are preserved. No normalization or reconstruction of source bytes from extracted text.

The helper's extra file is justified by independently reproducible historical generation; ordinary tests consume the literal expected file and never regenerate expectations from current code. A separate proof reruns the historical producer and compares the entire output file byte-for-byte. That proof ran and passed in the acceptance suite.

## Exact source identities

| Synthetic case | Original bytes | Original binary SHA-256 |
|---|---|---|
| docx_complete | 1381 | `d8c0bfdc1b10927bc0a5e2e8833038c80c497d8bec5efd27af2fecba0f9d4299` |
| docx_coverage | 1797 | `6e9925b1b4044060ecaa8100b361f91192ea5e3bcaba54f892a1b756df14f0d4` |
| xlsx_complete | 2747 | `d12084673da49c9cf78630e1a217af3d00a9178ea03b6508c15af95422fd7345` |
| xlsx_coverage | 3374 | `fd446c23f1423a3fb2aba1df62f6bdc3370735ed2d8b54e64ac8fb6ed8ca927b` |
| xlsx_blank | 2674 | `50bffb12ffe8696952baa64b81ab5204522860608ec456663b1a7d9ce50f48a9` |
| xlsx_missing | 2658 | `bb05e75a51a2fb1895038affb438158fa88ca0d7f3a4c7ea7558d2124af777f5` |
| xlsx_empty_text | 2720 | `fd16f282b11da903e5a661e2b54e2f4ad92f2820aa22a7770e6bba2d8961a97d` |

The first DOCX is exactly historical synthetic_parts(paragraph(COMPLETE)), source `synthetic:task-0071`; text is the 92-character original sentence. XLSX complete is exactly fictional_parts(), source `synthetic:task-0072`, explicit historical SELECTION and six literal cells.

| Primary literal vector | DOCX complete | XLSX complete |
|---|---|---|
| Native text SHA-256 | `cfe8ce9a7794a4582b89f9cd6df145cc3f5b4b83f2f2f837414b4a0bd81b531d` | `13361eadb0f700c06a08264073c85a979a3fdd788b5b026f3f63e9b80f526adf` |
| Native manifest SHA-256 | **null; no DOCX native manifest** | `5a0b36a32b5728627e094166e9899b5206b88f6563d2b5efb958de774af72660` |
| Integration SHA-256 | `08c66fb331418bdf1ef164cf2d57f167f0eb2c15b7e05c75d4d7ba14934d0e96` | `668ff566ba1e321fe4c5516603e4c8baf13746f828bd232a65d6053f2b1f69c7` |
| Reader implementation stamp | `c4d61c972ec670cdf00b18de62cae0dc88df4a62d0745fe79d5d0681a762af12` | `4198a751148d1dbce974b06f449443ea954beb186d5a56798eac8be1e1131cb0` |

XLSX selection is exactly {name:IT-Systeme, ordinal:1, sheet_id:1, relationship_id:rId1, part:xl/worksheets/sheet1.xml}. Headers/cells/row/column/coordinate and BLANK versus TEXT are frozen. DOCX complete locator is body=1/paragraph=1, table/row/cell=null, word/document.xml, segment span [0,92); no page number.

Additional coverage cases preserve a DOCX table's empty paragraph, all ordered locators and whitespace/decomposed Unicode; an XLSX extra empty worksheet; explicit B2 BLANK, missing B2 and B2 TEXT "". Blank and empty TEXT share **eb248059702fcc40e2604f5a4218489b1e7caad7f61464f69a990aaa7084d3ae** native text SHA-256, yet have distinct native manifests. Dropping the empty second sheet leaves text unchanged but changes native/integration structure. Flattened text alone cannot validate provenance.

## Tests and independence

Added **30 tests** in `tests/test_v2_reader_goldens.py`:

- Literal file/binary/text/native/integration identities, ZIP conventions and exact runtime/reader artifacts.
- Exact native and current integration profile conformance for complete/coverage fixtures.
- Unicode codepoint offsets and untouched whitespace/NFD, header/sheet/cell coordinates and missing/blank/empty semantics.
- Detection of changed bytes/text/stamp/manifests/locators/headers/selection and incomplete document/sheet coverage, including unchanged-text structural differences.
- Repackaging preserves native semantic content while changing binary/integration identity.
- A0's deliberately invalid Office-labelled quarantine bytes fail native parsing.
- No model/network/database/inventory/review side effects.
- Fresh historical producer output exactly equals the literal expected file.

The current integration tests intentionally compare current DocumentSnapshot/WorkbookSnapshot outputs against historical literals as **profile conformance**. They do not generate historical expectations, choose compatibility handlers or drive Gate A. The independent producer only executes verified old code; existing historical replay uses its unchanged frozen handler/policy bridge. A future legitimate current-profile change needs a new reviewed profile/vector set, not replacement of these A expectations.

Mutation cases deliberately construct untrusted cache/dataclass variants and show exact golden comparison rejects them; they do not claim a production Gate B rejection API already exists. Frozen dataclasses alone cannot attest re-extraction. No fabricated value is accepted as an approved fact.

## Proposed physical write profile

[ADR-0011](../decisions/0011-verified-source-validation-profile.md) selects one concrete proposal:

- **PRAGMA user_version=3**, metadata schema_version=3, physical profile **sqlite-source-validation/v1**, feature_profile **verified-source/v1**.
- **ledger-event/v3**, canonical-json/v1, genesis **store-init/v2**. Existing A schema 2/event v2 remain frozen and mutually refused for writing.
- Fresh new files only. No automatic A upgrade, event rewriting, migration/import or cross-store registration reuse. Existing Gate A read-only API stays available.
- Fifteen STRICT tables with exact PK/FK/UNIQUE/CHECK requirements; only metadata/head/registry projections mutable. Twelve immutable tables need 24 UPDATE/DELETE guards.
- Explicit handler-spec/capture/derivation/terminal tables. B replaces A's registration_observations layout with complete immutable events plus one capture/one terminal mirror; no A rows are migrated.
- New source-start/v2, source-fail/v2, reader-handler-register/v1 and **source.validated/source-valid/v1** contracts are proposals only. Ten allowed B event kinds; future candidate/queue/domain/export/import tags remain refused.
- Deterministic **derivation-ref/v2** binds store/source/registration/capture, exact reader/handler/policy/stamp/limits, raw bytes, native text/native manifest and integration manifest. Separate tagged reference identity versus canonical BLOB digest.
- Native/integration JSON retains exact historical wire encoding. Stored manifests are bounded opaque bytes compared against complete re-extraction, avoiding an incompatible application of the ledger decoder's 1 MiB string cap to nested XLSX native-manifest JSON.

The reader Spec identifies historical semantics; the future native bridge has a separately pinned handler identity/capability. The two current A0 catalog entries grant only source_ledger_read. No new handler identity/hash/capability was invented, enrolled or enabled. Combined reviewed implementation/handler count stays within four.

## Transaction and validation contract

One command/one event/singleton transaction group. Captured originals are immutable SQLite BLOBs; the new validation command never reads a mutable original path. Initial target parse/rebuild is outside the write lock, then BEGIN IMMEDIATE, complete replay and exact expected global/source/policy/handler comparison. Fresh/precommit replays may repeat native verification under the lock in the first bounded profile, with one cumulative command deadline across all passes; no unverified cache shortcut. Lock-hold cost/worker termination must be measured in future acceptance. Event, all derivation BLOBs, reference, terminal VALID mirror and counters commit atomically or roll back together.

Existing native APIs are path-based. The contract therefore requires a pinned byte-to-reader bridge using bounded private temporary transport, as the existing private _read_captured helpers demonstrate, plus exact returned-byte/source/limit comparison. It does not assume an existing public byte-ingestion API or trust a mutable current staging helper.

Permitted states are uncaptured PENDING, captured PENDING, terminal FAILED and terminal VALID after complete verified re-extraction only. FAILED/VALID cannot be changed in place. Reopened captured PENDING can be explicitly validated from immutable bytes; uncaptured reopen cannot silently reacquire an old path's capture authority.

The highest started revision is always head. New PENDING invalidates any older VALID for current use; late old completion needs fresh tokens and unchanged active policy and cannot replace the newer head. Identical-byte re-registration and ZIP repackaging require new identities/validation. Policy changes retain old historical terminal decisions but block current applicability; no implicit revalidation or old-head fallback. Stale/SQL/disk/timeout failures publish no partial derivation; only actually committed failure/exhaustion is reported durable.

Full native structural VALID is separate from proposal eligibility. All segments/sheets/cells—including extra, blank, missing and empty structures—remain covered. Unsupported inventory grammar/headers or extra sheets can be native-valid yet later block Gate C. No validation event authorizes Evidence, Inventory, review or export.

Future replay must independently re-extract every VALID registration, compare all manifests/locators/limits/reference columns, enforce original-byte/count/time budgets and refuse complete trusted loading on unknown handlers, impossible order, mismatches or incomplete context. Fully verified blocked history may be returned; no partial trusted prefix/cache fallback.

## Actual acceptance evidence

Focused run with isolated historical producer enabled:

```text
Ran 30 tests in 0.810s

OK
```

Final complete suite, with both original A0 and native producer proofs enabled:

```text
Ran 580 tests in 31.828s

OK (skipped=5)
```

**575 passed, 0 failures, 0 errors, 5 existing optional Ollama tests skipped.** All **545 previously passing tests** and **30 new tests** ran successfully. Original A-created DB proof and fresh historical native producer reproduction both ran; they were not skipped or substituted with current-produced expectations. No failing test was weakened.

The original A0 DB remains unchanged at SHA-256 **5f218c87db968a3c5588fca7ff6b90ffc5c1d4c3dc1d5f6fbef36aaa9c84d537**. Existing SQL fixture, A harness, production modules and compatibility tests are unchanged. Without proof environment variables, the corresponding original-file/producer proofs are explicitly skipped; that result is not equivalent to this acceptance run.

Additional verification: UTF-8/whitespace/fences/links, exact fixture hash/length, syntax, read-only Git checks, and tracked diff confirming zero production/existing-test changes. No source.validated or B schema was physically implemented/tested.

## Changed files and Git status

Only five new files:

| File | Purpose |
|---|---|
| tests/fixtures/b0-native-goldens.json | Literal authentic A-native bytes/hashes/complete manifests/structure. |
| tests/test_v2_reader_goldens.py | Thirty focused offline golden/conformance/proof regressions. |
| tests/native_golden_oracle.py | Necessary reproducible test-only old-checkout verifier/producer. |
| docs/decisions/0011-verified-source-validation-profile.md | Concrete B physical/schema/event/transaction/state/replay/threat contract. |
| docs/tasks/TASK-0073B20-RESULTS.md | This report and reproduction evidence. |

ADR-0010 is unchanged; no correction was necessary. Repository-root final short status:

```text
?? Grundschutz-AI/docs/decisions/0011-verified-source-validation-profile.md
?? Grundschutz-AI/docs/tasks/TASK-0073B20-RESULTS.md
?? Grundschutz-AI/tests/fixtures/b0-native-goldens.json
?? Grundschutz-AI/tests/native_golden_oracle.py
?? Grundschutz-AI/tests/test_v2_reader_goldens.py
```

HEAD remains **0a8af67cf36dc6df742b88380cdde0115947172d**; no staged/committed changes. Tracked diff is empty, including all production Python, schemas, existing tests/fixtures and v1 storage. No scratch archive remains; synthetic documents/generation output and historical checkout are outside Git. No binary SQLite fixture was added.

## Exact reproduction

Use this LF-packaged tree and the exact reviewed runtime. Current retained artifacts:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b20-r9fmvckp/a0-checkout/Grundschutz-AI"
$env:GRUNDSCHUTZ_A0_ORACLE = "C:/Users/HASHAR~1/AppData/Local/Temp/grundschutz-ai-task0073b1-e9eeso_1/fixture-reviewed/oracle.sqlite"
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest tests.test_v2_reader_goldens -v
py -3.12 -m unittest discover -s tests
```

Rebuild both independent proofs from the immutable old commit when those temporary artifacts are unavailable:

```powershell
Set-Location Y:/Grundschutz-AI
$goldenRoot = Join-Path $env:TEMP ("grundschutz-ai-native-review-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $goldenRoot | Out-Null
$goldenArchive = Join-Path (Get-Location) (".task0073b20-" + [guid]::NewGuid().ToString("N") + ".tar")
git -c core.autocrlf=false archive --format=tar --output=$goldenArchive 2ee9bc7
$goldenCheckout = Join-Path $goldenRoot "checkout"
@'
from pathlib import Path
import sys, tarfile
archive, target = map(Path, sys.argv[1:])
with tarfile.open(archive) as stream:
    stream.extractall(target, filter="data")
archive.unlink()
'@ | py -3.12 - $goldenArchive $goldenCheckout

Set-Location Y:/Grundschutz-AI/Grundschutz-AI
$env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT = Join-Path $goldenCheckout "Grundschutz-AI"
$nativeOutput = Join-Path $goldenRoot "native-goldens.json"
py -3.12 tests/native_golden_oracle.py --checkout $env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT --output $nativeOutput
Get-FileHash -Algorithm SHA256 -LiteralPath $nativeOutput
# Expected SHA256: 553ede8d62d7a4f13a09966be411c9ef274fe1d351d2caedc8676652c9b5497b
# This is a comparison artifact; do not overwrite the committed literal fixture.
$oracleOutput = Join-Path $goldenRoot "a0-oracle"
py -3.12 tests/a0_oracle.py --checkout $env:GRUNDSCHUTZ_NATIVE_A_CHECKOUT --output $oracleOutput
# Stop if either strict producer fails; do not substitute current code/values.
$env:GRUNDSCHUTZ_A0_ORACLE = Join-Path $oracleOutput "oracle.sqlite"
$env:GRUNDSCHUTZ_RUN_INTEGRATION = "0"
py -3.12 -m unittest tests.test_v2_reader_goldens -v
py -3.12 -m unittest discover -s tests

Set-Location Y:/Grundschutz-AI
git rev-parse HEAD
git status --short
git diff --exit-code
git diff --check
```

These commands create only synthetic test artifacts outside Git and an immediately removed export scratch archive; they do not install or migrate anything. The existing A0 oracle command necessarily creates its temporary schema-2 fixture, never the proposed B schema.

## Limitations and exact blockers before Gate B implementation

Human review must accept or revise the schema-3/event-v3 choice, fifteen-table constraints/24 guards, payloads, terminal/currentness rules and resource accounting. Future code must supply reviewed literal DDL/fingerprint, exact pinned native handler artifacts/host matrix and capability gating, bounded manifest serializers and enforceable parser worker deadlines, then atomic writer/replay/recovery implementation.

The future ADR threat matrix still needs executable tests for forged native/integration metadata with coherent hashes, explicit selection/locator/kind mismatches, missing handlers/policies, stale and late completion, process crashes before/after commit, resource exhaustion/control-event failure, A0 read-only preservation and disabled later gates. The new tests validate historical native vectors/profile conformance, not that unimplemented persistence behavior.

Only the exact LF A0 runtime/package is proven. Existing narrow Office readers do not provide general document compatibility, visual/authentic source validation or real-world truth. Full unsigned corpus/actor replacement remains an authenticity risk. Golden equality cannot authenticate a reviewer or make source content factual.

**source.validated, Gate C/D persistence, Evidence/Inventory/ReviewRecord, approval, export, PDF promotion and migration remain disabled.** No new normative baseline or production/certification readiness claim. Stop at TASK-007.3B.2.0; review this contract before authorizing any Gate B implementation.
