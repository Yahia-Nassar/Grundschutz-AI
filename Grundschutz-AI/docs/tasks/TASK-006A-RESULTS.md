# TASK-006A: Safe synthetic DOCX text ingestion

Date: 2026-11-09 (Europe/Bucharest). Repository root: `Y:/Grundschutz-AI`; application directory: `Y:/Grundschutz-AI/Grundschutz-AI`. Baseline confirmed by read-only Git: `24de3f4` (`feat: add local SQLite inventory persistence`), with a clean initial working tree.

## Outcome and changes

Implemented a standalone, standard-library-only reader for a deliberately limited synthetic DOCX profile. It returns immutable text segments, structural locators, the exact original bytes and separate binary/text SHA-256 hashes. Unknown, malformed, over-budget or unsupported content fails closed without a partial result. No extraction-to-inventory adapter or automatic review decision exists.

Four new files:

- `grundschutz_ai/docx_ingestion.py`: bounded ZIP/XML validation, the immutable `DocxLimits`, `DocxLocator`, `TextSegment` and `DocxExtraction` types, and `ingest_docx`.
- `tests/test_docx_ingestion.py`: 37 offline tests with fictitious DOCX fixtures created only in temporary directories outside the checkout.
- `docs/decisions/0005-document-ingestion.md`: supported/rejected profile, default budgets, locator/hash semantics and a proposed future persistence contract.
- `docs/tasks/TASK-006A-RESULTS.md`: this report and reproducible demonstration.

Existing implementation, tests, requirements, review states and SQLite schema version 1 remain unchanged. No dependencies installed; no Ollama/model/network calls, company documents, permanent source documents/databases, inventory mutation, document-generation feature, automatic commit or TASK-006B implementation. The fixture writer is test-only standard-library scaffolding, not an application document generator. Sprint 0 and the normative BSI baseline remain outside this engineering acceptance.

## Tests and acceptance

Executed from the application directory using Python 3.12:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion
```

Observed result: **191 tests run in 1.269 seconds; OK; 0 failures, 0 errors**. This includes **all 154 previous offline tests plus 37 new ingestion tests**. The optional extraction/Ollama integration classes were deliberately not selected; this task introduces no model changes or inference pathway.

Coverage includes paragraph/table order, empty and multi-paragraph cells, German/Unicode text, tabs/breaks, stable structural locators and checked character spans, binary/text/segment hashes, reproducibility, frozen results and identical text in differently packaged archives. Rejection tests cover malformed/missing parts, external relationships, macros/encryption, unknown or aliased parts, symlink ZIP members, unsupported compression, tracked changes/fields/alternate content, hidden/struck text, merged/nested/ragged tables, XML entities/DTD/processing instructions/comments, invalid metadata/CRC and forged archive sizes/counts. File, inflation ratio, aggregate/member bytes, XML structure and text/table budgets are exercised. The forged-size tests cover both an actual decompressed-size mismatch and capped inflation exceeding the configured XML budget.

The side-effect regression patches model generation, inventory additions/reviews, storage commit and ZIP filesystem extraction, and asserts none are called. Literal instruction text is returned as untrusted text only; the inventory rejects an ingestion artifact as a domain record. Synthetic temporary fixtures are cleaned up after tests. The demonstration below also confirmed removal of its temporary DOCX.

| Acceptance gate | Status |
|---|---|
| All 154 existing offline tests preserved | PASS |
| New offline ingestion regressions | PASS: 37 |
| Paragraph plus table demonstration | PASS |
| Structural locators and both provenance hashes | PASS |
| Unsupported/meaning-altering structures and budget violations rejected | PASS within tested profile |
| No automatic inference, inventory mutation or approval | PASS |
| SQLite unchanged; future persistence proposal documented | PASS |
| General Office compatibility / production security | Not established; explicitly outside scope |

## Observed synthetic demonstration

Source ID: `synthetic:task-006a-demo`; method: `docx-plain/v1`. The fictitious fixture has one body paragraph and one table with one row and two cells. Extracted text (LF separators, no trailing LF):

```text
FIKTIVES BEISPIEL: Serverinventar.
SRV-001
Rechenzentrum Rostock
```

Every segment has `part="word/document.xml"`. Indices are one-based; character offsets are zero-based, half-open and segment-local Unicode code-point positions.

| Segment text | body_index | paragraph_index | table_index | row_index | cell_index | Character span |
|---|---:|---:|---:|---:|---:|---|
| FIKTIVES BEISPIEL: Serverinventar. | 1 | 1 | null | null | null | [0, 34) |
| SRV-001 | 2 | 1 | 1 | 1 | 1 | [0, 7) |
| Rechenzentrum Rostock | 2 | 1 | 1 | 1 | 2 | [0, 21) |

Exact original DOCX binary SHA-256:

```text
6bfb1c1f6b2f4bb773a93a64c0a276d5208f4e861b3b63e81310b1e0fbc5fd05
```

Extracted text SHA-256 (`UTF-8`, no BOM):

```text
70f4aba7bd9705baa7ce67fcbbe01dd1c3dc7f262af15ddd925e3fd77f6b88c1
```

Segment UTF-8 SHA-256 values, in order:

```text
d51d55a24e2095c1656195384b92bec3ee0b3a7dd46120e708d242900379628f
7b3f6367c956b2d3d6e1a73bf6a4402fccb0c5ef17943677df93e2a93929cb9a
7971e5b627ad354ef6fb24402fb45c8d9063f8f5ff001cac41f875831f223623
```

The binary hash describes these exact fixture ZIP bytes; another ZIP writer or metadata/serialization choice can produce a different binary hash for the same text. No page numbers are invented.

## Reproduce

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion -v
py -3.12 -m unittest tests.test_docx_ingestion -v
```

Run this separate demonstration from the same directory. It uses test-only synthetic fixture helpers and removes the fixture on completion:

```powershell
@'
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.docx_ingestion import ingest_docx
from tests.test_docx_ingestion import paragraph, table, synthetic_parts, write_synthetic_docx

with TemporaryDirectory(prefix="grundschutz-ai-docx-demo-") as directory:
    path = Path(directory) / "fictitious.docx"
    write_synthetic_docx(path, synthetic_parts(
        paragraph("FIKTIVES BEISPIEL: Serverinventar."),
        table([["SRV-001", "Rechenzentrum Rostock"]]),
    ))
    result = ingest_docx(path, source_id="synthetic:task-006a-demo")
    print(json.dumps({
        "source_id": result.source_id,
        "method": result.method,
        "docx_sha256": result.docx_sha256,
        "text_sha256": result.text_sha256,
        "text": result.text,
        "segments": [{"text": item.text, "locator": asdict(item.locator),
                      "text_sha256": item.text_sha256} for item in result.segments],
    }, ensure_ascii=False, indent=2))
print("Temporary fixture removed:", not path.exists())
'@ | py -3.12 -
```

## Remaining limitations and risks

The exact allowlisted package/XML subset and every default limit are specified in ADR-0005. Only three required parts and an optional empty document-relationships part are accepted. Most Word-generated documents contain additional styles/settings/theme/properties and will be refused. Formatting, numbering, headers/footers, comments, tracked changes, hyperlinks, fields, embedded/alternate objects, nested/merged tables and layout-dependent content are unsupported. No rendering, page mapping, visual-equivalence verification, language interpretation, prompt-injection immunity or complete Office conformance is claimed. Unicode text is preserved rather than interpreted as instructions or visually normalized.

The input must be an explicitly trusted synthetic local path. The reader cannot determine whether data is actually synthetic or authenticate the source author. Hashes identify captured bytes/text; they do not prove real-world truth or protect against a coherent malicious rewrite. Filesystem races/local attacker protection, authenticated source handling, adversarial fuzzing and production security review remain unresolved.

The returned original bytes make future reproducible reload possible, but nothing is persisted here. Raw bytes, ordered segments, locators, both hash types, method/profile and source revisions must be bound and revalidated through a separately reviewed local persistence contract. Existing domain character locators do not yet map to DOCX structure. Selecting segments for evidence must preserve contradictory context and must not bypass existing fail-closed support validation. No ingestion-to-inventory adapter is provided. Downstream document generation must never export raw ingestion text or invalid candidate diagnostics as approved facts.

Next suggested work is human review of this bounded profile, its acceptance evidence and the proposed persistence/context-binding contract. TASK-006B has not begun. No production readiness or verified BSI certification coverage is claimed.

## Git verification

Baseline remains `24de3f4`. The initial tree was clean. Final read-only `git status --short --untracked-files=all` reported exactly:

```text
?? Grundschutz-AI/docs/decisions/0005-document-ingestion.md
?? Grundschutz-AI/docs/tasks/TASK-006A-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/docx_ingestion.py
?? Grundschutz-AI/tests/test_docx_ingestion.py
```

`git diff --name-only` was empty and `git diff --check` passed. Since Git's diff check does not inspect untracked files, all four new files were also checked directly for strict UTF-8 decoding, trailing whitespace and final newlines; all passed. No matching task DOCX temporary directories remained. These checks used read-only Git as the normal user without changing repository ownership/security settings. No files staged and no commit created.
