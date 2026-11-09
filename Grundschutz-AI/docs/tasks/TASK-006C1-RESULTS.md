# TASK-006C.1: Bounded synthetic PDF reader

Date: 2026-11-09 (Europe/Bucharest). Repository: `Y:/Grundschutz-AI`; application directory: `Y:/Grundschutz-AI/Grundschutz-AI`. Initial clean HEAD: `33ff11a` (`docs: define bounded synthetic PDF ingestion contract`). Scope was explicitly authorized by the attached TASK-006C.1 request; it does not approve Sprint 0, visually verified evidence or the BSI normative baseline.

## Outcome and files

Implemented the exact `pdf-synthetic-ascii/v1` structural reader and parent/worker contract using Python 3.12 standard library only; the confirmed test runtime is Python 3.12.6. The exact byte templates were recorded in ADR-0007 **before parser code was written**. All successful outputs are immutable, diagnostic-only and explicitly `visual_verification="not_performed"`. No PDF-derived data enters approved inventory.

| File | Change |
|---|---|
| `grundschutz_ai/pdf_ingestion.py` | New typed records, strict complete-byte parser, page/operand/quote provenance, hashes/manifests and bounded parent process/pipe supervision. |
| `grundschutz_ai/pdf_worker.py` | New private isolated worker, bounded versioned input framing and exact JSON output protocol; no paths/commands from document text. |
| `tests/test_pdf_ingestion.py` | 44 new offline tests with fictional PDF fixtures outside the repository. |
| `docs/decisions/0007-pdf-ingestion.md` | Finalized grammar and actual implementation/worker findings, preserving historical C.0 limitations. |
| `docs/tasks/TASK-006C1-RESULTS.md` | This result, demonstration, tests, limits and reproduction commands. |

All unrelated modules and existing tests remain unchanged, including DOCX/XLSX, domain/inventory, Ollama and SQLite schema version 1. No dependency, installation/download, network, OCR, company documents, production document generator, model/GPU/security-setting change, Evidence/Inventory adapter, new review/approval pathway, automatic Git commit or TASK-007 work was introduced. The PDF writer is test-only synthetic fixture scaffolding.

## Structural acceptance and actual tests

Final complete offline command:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion
```

**Observed: 279 tests in 13.276 seconds; OK; 0 failures, 0 errors.** All **235 existing tests** remain, with **44 new PDF tests**. Optional live Ollama classes were not selected. An earlier full run also passed; the count above is the final run after tightening explicit quote and file-limit assertions.

Structural regression tests exercise the private worker core directly for fast negative/boundary cases; separate end-to-end tests exercise the actual public API and real Windows subprocess lifecycle. No mocked parser output substitutes for the real-worker success/timeout/flood tests. Coverage includes:

- One/multiple/blank pages, explicit blank lines, fixed line/Kids order, printable ASCII punctuation/space preservation, exact page/line/raw-hex spans and revision-bound quote matching.
- Binary/page/document/manifest hashes, deterministic repeated results, frozen nested records and distinct blank-line structure despite identical flattened text.
- A literal golden PDF independent of the fixture builder, with explicitly pinned object offsets `[9, 58, 115, 210, 336]`, xref offset `429`, hex span `[399,405)` and fixed binary/text hashes. Every truncated prefix of a valid fixture is rejected.
- Rebuilt-xref mutations of lengths, graph references, fonts/encodings, hidden/overlapping/clipped operators and active/unsupported structures. Invalid xref/Size/generations/object boundaries, extra keys/objects, non-ASCII/control bytes, encryption/filters and appended/hidden revisions fail closed.
- Late-page corruption without a returned partial extraction; file/stream/page/object/line/token/depth/page-text/document-text boundaries, including maximum-profile acceptance and one-over rejection.
- Real five-second timeout and blocked input-writer termination, a 10 MiB attempted stdout flood with actual reads stopping after **262,145 bytes**, exact result-size boundary and one-byte-under rejection, process/thread/pipe cleanup, launch failure and second pipe-thread startup failure.
- Malformed/truncated/deep/non-JSON/duplicate-key/unknown-field worker responses; bool/int mismatches, fabricated text/spans/hashes, wrong source/configuration/visual state and nonzero exits even with valid-looking JSON. Real worker input truncation, extra bytes/keys and wrong protocol are rejected.
- Inert source instructions and formula/action-like text; no model, network, inventory/review, SQLite or source-print calls. Inventory refuses a raw extraction artifact as a domain record. Captured source bytes are preserved even when the original path changes before launch.

All fixture files are temporary and fictitious. No independent PDF library or renderer was used to validate them; the literal/byte tests establish conformance to this experimental grammar, not visual compatibility.

## Worker behavior and measured limits

The parent captures a bounded regular `.pdf` file before launch, then passes source ID, non-relaxable/tightened resource limits and those exact bytes through a private bounded frame. Production arguments contain only the trusted Python executable, `-I -S -u` and the absolute trusted worker script. `shell=False`; Windows uses `CREATE_NO_WINDOW`. No document-controlled argument, path, import, shell action or URL is executed.

The deadline starts before worker launch and is five seconds by default. The parent writes stdin and reads stdout concurrently using bounded pipe operations. It waits for process exit, EOF and completed input transfer before checking a result. Stderr is sent to DEVNULL; no document text is logged. Main-thread supervision kills stalled/oversized workers and performs bounded direct-process reaping, pipe-thread joining and handle closure. Result validation also checks the deadline before acceptance. Cleanup has a separate shared one-second budget; cleanup failure rejects the operation. There is no unlimited stdout/stderr buffer, generic PDF decompression, OS sandbox or claimed hard RSS isolation.

Separate real-process demonstration, with trusted synthetic test child programs substituted only through test instrumentation:

| Case | Observed outcome | Elapsed | Cleanup |
|---|---|---:|---|
| Worker sleeping for 60 seconds | `worker_timeout` | 5.000 s | Reaped; stdin/stdout closed |
| Child attempting 10 MiB stdout | `worker_output_limit` | 0.047 s | Reaped; stdin/stdout closed |

The overflow regression observes actual OS reads: at most 4,096 requested bytes per read and total retained input from worker stdout exactly 262,145 bytes, including one overflow-detection byte. A valid success response exactly at its tightened configured cap is accepted; one byte less rejects it. Tests assert no live `pdf-ingestion-pipe` threads or unreaped test workers remain after each operation.

Maximum supported fixture observation: **16 pages, 608 lines, 60 characters per line**, original **91,780 bytes**, document **37,087 characters** and worker result **140,788 bytes**; observed elapsed **0.204 s**. This checks the dense fixture against the 256 KiB result cap and five-second budget. It is not a general latency benchmark, hard real-time guarantee or memory measurement. Peak RSS was not measured. File I/O and OS process creation/termination cannot be preempted with an unconditional real-time guarantee by these standard-library controls.

## Observed three-page demonstration

A temporary `fictitious.pdf` was created using the test-only fixture builder, then read twice through the real public parent/worker API. Source ID: `synthetic:task-006c1-demo`; method `pdf-synthetic-ascii/v1`; implementation `grundschutz_ai.pdf_ingestion/1.0.0`; `diagnostic_only=true`; `visual_verification="not_performed"`. First observed ingestion took **0.125 s**. Repeated results were equal and the temporary PDF was removed.

Page 1 text:

```text
FIKTIVES TESTBEISPIEL
SRV-001: Rechenzentrum Rostock / ERP-01
```

Page 2 is explicitly blank. Page 3 text:

```text
SRV-002: Berlin / CRM-02
```

The exact document convenience string is `FIKTIVES TESTBEISPIEL\nSRV-001: Rechenzentrum Rostock / ERP-01\f\fSRV-002: Berlin / CRM-02`, with no trailing separator. Two form feeds preserve the blank middle page.

| Page | Page/content object refs | Content bytes | Line | Page-local character span | Original hex operand bytes |
|---:|---|---|---:|---|---|
| 1 | `4 0 R` / `5 0 R` | [381,565) | 1 | [0,21) | [412,456) |
| 1 | `4 0 R` / `5 0 R` | [381,565) | 2 | [22,61) | [478,558) |
| 2 | `6 0 R` / `7 0 R` | [740,756) | No lines | Empty page | None |
| 3 | `8 0 R` / `9 0 R` | [931,1019) | 1 | [0,24) | [962,1012) |

Indices are one-based; spans are zero-based and half-open. Character spans are page-local Unicode code-point positions in the extracted ASCII string. Byte spans reference captured PDF bytes and include operand angle brackets. No printed-page label, rendered glyph box or pixel position is invented.

The quote `Rechenzentrum Rostock` is exactly page **1**, characters **[31,52)**, bound to the source ID and original binary hash below. `verify_quote` returned true for that exact match; this confirms substring provenance only, not visual verification or factual approval.

Original binary PDF SHA-256:

```text
f5d8e49b54560e5fe2981cae8dcda3c5490527d1d66e5ff423ffd01386b1cfb6
```

Document UTF-8 text SHA-256:

```text
2a14350027847ebaf6f4605a2dad256ccbbb650d4ef3302a5d3ae0d311df49b7
```

Canonical manifest SHA-256:

```text
f16d6c47da15dd77ec18d8374527a864da6bb7b24749ecdc9b78e8b68afa1e07
```

Page UTF-8 text SHA-256 values, in order:

```text
3159493114d0799f3e8cd460b39c7e5214074694aeb62b20eb1222fa750ff886
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
df6c09e563f46d5faf6c74ec8e1b9b62d9c0529e0b7152264c161049c7a4ce2e
```

The PDF manifest binds exact binary identity, source ID, parser version, effective limits, fixed diagnostic/visual state, document text hash and complete ordered pages/lines/objects/spans. Its canonical UTF-8 JSON uses sorted keys and compact separators with no timestamps or floats. Different limits/source IDs legitimately change the manifest hash. The original bytes, not a mutable path or hash alone, support future reconstruction. Future storage must re-run the compatible bounded parser and compare every derived value; no source-store/schema or approval adapter is implemented here.

## Reproduction commands

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion tests.test_pdf_ingestion -v
py -3.12 -m unittest tests.test_pdf_ingestion -v
py -3.12 -m unittest tests.test_pdf_ingestion.PdfWorkerTests.test_parent_enforces_real_five_second_stalled_worker_deadline tests.test_pdf_ingestion.PdfWorkerTests.test_parent_caps_actual_output_reads_at_limit_plus_one -v
```

Synthetic demonstration from the same directory:

```powershell
@'
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.pdf_ingestion import ingest_pdf
from tests.test_pdf_ingestion import synthetic_pdf

with TemporaryDirectory(prefix='grundschutz-ai-pdf-demo-') as folder:
    path = Path(folder) / 'fictitious.pdf'
    path.write_bytes(synthetic_pdf([
        ['FIKTIVES TESTBEISPIEL', 'SRV-001: Rechenzentrum Rostock / ERP-01'],
        [],
        ['SRV-002: Berlin / CRM-02'],
    ]))
    result = ingest_pdf(path, source_id='synthetic:task-006c1-demo')
    start = result.pages[0].text.index('Rechenzentrum Rostock')
    quote = result.quote(1, start, start + 21)
    print(json.dumps({
        'source_id': result.source_id, 'method': result.method,
        'implementation': result.implementation,
        'diagnostic_only': result.diagnostic_only,
        'visual_verification': result.visual_verification,
        'pdf_sha256': result.pdf_sha256, 'text_sha256': result.text_sha256,
        'manifest_sha256': result.manifest_sha256, 'text': result.text,
        'pages': [asdict(page) for page in result.pages],
        'quote': asdict(quote), 'quote_matches_source': result.verify_quote(quote),
        'reproducible': result == ingest_pdf(path, source_id=result.source_id),
    }, indent=2))
print('Temporary PDF removed:', not path.exists())
'@ | py -3.12 -
```

## Acceptance boundaries and remaining limitations

| Gate | Status |
|---|---|
| Finalized canonical grammar and complete-byte structural validation | PASS for tested synthetic profile |
| Immutable provenance, exact page/quote/raw-byte mappings and separate hashes | PASS |
| Real parent-enforced worker deadline/output caps and tested cleanup | PASS on this Windows/Python environment |
| All existing and new offline regressions | PASS: 279 |
| No inference, inventory/review/SQLite side effects | PASS within tested API and inspected trusted worker |
| Independent visual verification / renderer compatibility | NOT PERFORMED; unavailable |
| Approved PDF-derived inventory, general PDF support, production readiness | Outside scope; not authorized/established |

The parser intentionally rejects virtually all ordinary PDFs: only exact canonical ASCII/Courier/WinAnsi, single-column, uncompressed, flat-page-tree syntax is accepted. German umlauts/ß and other Unicode mappings, arbitrary layouts/fonts, scans/images, hidden/clipped/overlapping/rotated graphics/text, forms/annotations/attachments/actions, encryption, incremental updates and unknown structures are unsupported. No repair, OCR or partial result is returned. Structural conformance cannot prove visual glyph correspondence, source authenticity or real-world truth. Every result explicitly says visual verification was not performed, and no independent renderer/library was introduced.

The worker is a trusted local Python subprocess, not an OS sandbox: no hard RSS guarantee, process-tree sandbox or defense against a compromised runtime/application code/local attacker is claimed. It never spawns descendants or executes source instructions. The parent validates derived output but trusts that worker for the full original-file grammar verdict; it does not rerun a general PDF parser in the parent. Source authentication, filesystem races/permissions, protected retention, fuzzing, PDF conformance/visual interoperability and future policy migration remain unresolved. The controlled synthetic input path/configuration is a caller responsibility. Dataclass construction is not authenticated evidence.

No artifact, raw diagnostic or PDF-derived value may enter approved inventory or document generation through this task. Explicit page/line quote matching remains a diagnostic capability only. There is no Evidence/Inventory adapter and no new review state or human-approval route. Any future integration must retain full conflicting document context and require separately reviewed provenance/migration and revision-bound human decisions; it must not substitute binary hashes for existing UTF-8 evidence source hashes.

Recommendation: **READY FOR REVIEW for the bounded diagnostic structural prototype**, with visual verification explicitly unresolved. Next suggested action is human review of the grammar, lifecycle evidence and limitations. TASK-007 has not started, and no production/BSI compliance claim is made.

## Git verification

HEAD remains `33ff11a`. Final read-only status:

```text
 M Grundschutz-AI/docs/decisions/0007-pdf-ingestion.md
?? Grundschutz-AI/docs/tasks/TASK-006C1-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/pdf_ingestion.py
?? Grundschutz-AI/grundschutz_ai/pdf_worker.py
?? Grundschutz-AI/tests/test_pdf_ingestion.py
```

`git diff --name-only` listed only ADR-0007; the four other task files are new/untracked. Explicit diffs for domain, storage, DOCX/XLSX and shared OOXML code were empty. `git diff --check` passed; all five files also passed direct strict UTF-8, trailing-whitespace and final-newline checks, covering new files that Git diff does not inspect. Git emitted its existing LF-to-CRLF conversion notice; no configuration or security settings were changed. No task PDF temporary directories remained. Nothing staged or committed and no unrelated working-tree changes. Git ran read-only as the normal user without ownership changes.
