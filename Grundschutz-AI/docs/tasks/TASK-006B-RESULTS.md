# TASK-006B: Bounded synthetic XLSX ingestion

Date: 2026-11-09 (Europe/Bucharest). Repository `Y:/Grundschutz-AI`; application directory `Y:/Grundschutz-AI/Grundschutz-AI`. Baseline confirmed by read-only Git: `d72230a` (`feat: add bounded synthetic DOCX ingestion`). Initial working tree was clean.

## Outcome and changed files

Implemented a deterministic, standard-library-only literal XLSX reader for synthetic data. It captures exact original bytes, verifies a narrowly allowlisted ZIP/OOXML package and returns immutable sheet/cell records with explicit locators, text hashes and a structural manifest. Unsupported, malformed and over-budget input raises `XlsxIngestionError` with no partial returned extraction. It creates no inventory facts, reviews or approvals.

| File | Change |
|---|---|
| `grundschutz_ai/xlsx_ingestion.py` | New immutable limits/results, explicit sheet/cell validation, inline/shared/blank text profile and provenance hashes. |
| `grundschutz_ai/ooxml_safety.py` | New shared helper containing the existing DOCX ZIP/XML mechanics, parameterized by exact required/allowed parts and trusted limits. |
| `grundschutz_ai/docx_ingestion.py` | Existing ZIP/XML functions delegate to the shared helper and retain the DOCX-specific error boundary; all Word parsing, types, limits and allowlists remain unchanged. |
| `tests/test_xlsx_ingestion.py` | 44 new offline tests; fictional workbooks are built in temporary directories outside the repository and removed. |
| `docs/decisions/0006-xlsx-ingestion.md` | Profile, rejection rules, budgets, locator/hash semantics and future persistence proposal. |
| `docs/tasks/TASK-006B-RESULTS.md` | This acceptance evidence and reproduction commands. |

The shared helper avoids duplicating the ZIP/XML security logic. Its extraction is a mechanical move with generic names/errors and caller-supplied part sets; the original 37 DOCX tests were not changed. No existing test expectations were weakened. Domain/inventory/extraction/storage code and SQLite schema version 1 remain unchanged.

## Supported and rejected structures

Supported: one or more simple visible worksheets in workbook declaration order; explicit ascending row/cell coordinates; literal inline strings; validated simple shared strings; explicit blank cells, empty text and sparse/missing cells; empty sheets/rows; German/Unicode parsed XML text. Each cell preserves workbook source ID, exact worksheet name/ordinal/part, coordinate, row, column, kind, text and UTF-8 text SHA-256.

Workbook-to-sheet relationships must be internal, canonical, unique, complete and unambiguous. Unknown/unreferenced parts and relationships fail closed. Formula cells including caches, numbers/dates/booleans/errors, styles, hidden content, merges/tables, rich strings, OOXML escaped text, links, objects, macros, dynamic/alternate content and all other unsupported elements/attributes/parts are rejected. Most ordinary Excel-generated files therefore fail this profile. ADR-0006 specifies the exact accepted subset and default limits, including 2 MiB raw bytes, 8 MiB uncompressed bytes, 100:1 member ratio, XML structural budgets, 16 worksheets and 10,000 explicit cells.

No network/model calls, dependency installation, company documents, persistent workbook/database, RAG, PDF reader, schema migration, document-generation feature, automatic commit or TASK-006C work was introduced. The workbook writer is synthetic test scaffolding only. No BSI normative baseline or Sprint 0 approval is changed.

## Exact tests executed

After moving the shared helper, the unchanged DOCX suite passed: **37 tests in 0.369 seconds; OK**.

The new XLSX suite passed: **44 tests in 0.592 seconds; OK**.

Full offline command, executed from the application directory:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion
```

Observed: **235 tests in 1.871 seconds; OK; 0 failures, 0 errors**. This preserves all **191 previous offline tests** and adds **44** XLSX tests. Optional live Ollama test classes were not selected; this task adds no inference pathway.

Tests cover the nine-cell demonstration, workbook/worksheet ordering independent of ZIP/relationship/part numbering, Unicode, inline/shared text, sparse coordinates, blank/empty/missing distinctions, empty sheets/rows, coordinate bounds/duplicates/malformed/missing addresses, row mismatches, missing/duplicate/external/aliased targets, inconsistent shared-string metadata and rich/unused/duplicate definitions. They reject formulas/caches, hidden/style-dependent/merged/embedded content, unknown parts, macros and malformed ZIP/XML. Limits cover file/aggregate/member bytes, expansion ratio, entries, XML depth/nodes/attributes/namespaces/text, worksheet/cell counts and shared/extracted text budgets. Forged ZIP entry counts, false inflated-size declarations, corrupt CRCs and inconsistent local metadata are rejected.

Repeated results are equal and frozen, binary/text/manifest hashes are checked, and identical flattened text with different structure has different manifest hashes. A valid first sheet followed by an invalid second sheet raises before an extraction artifact is created, demonstrating no returned partial result. The side-effect test patches model generation, inventory add/review, storage commit, HTTP opening and archive extraction; none is called. Literal instruction/formula-looking text remains untrusted text. The inventory refuses an ingestion artifact as a domain record.

## Observed synthetic demonstration

The temporary file `fictitious.xlsx` contains exactly the requested fictitious nine cells. Source ID: `synthetic:task-006b-demo`; method: `xlsx-literal/v1`. Worksheet order: **1. IT-Systeme**. Worksheet ID `1`, relationship `rId1`, part `xl/worksheets/sheet1.xml`, explicit rows `(1, 2, 3)`. Every cell has that source ID, sheet name, ordinal `1` and part; every kind is TEXT.

| Coordinate | Row | Column | Exact text | Cell UTF-8 SHA-256 |
|---|---:|---:|---|---|
| A1 | 1 | 1 | System-ID | `242bdb0a564c13095d2c8207ec3d9bcf0810ea22c89d59d1e297feaf6da495e1` |
| B1 | 1 | 2 | Standort | `ecf34cc8921a465707b33bb5e1a4ab97fb2c4e61e8e33d3cc9de6c8646318c97` |
| C1 | 1 | 3 | Anwendung | `239a8e5fafbe0cd5780357b159800187d6212bed08ae333d04fb6d7e25d17867` |
| A2 | 2 | 1 | SRV-001 | `7b3f6367c956b2d3d6e1a73bf6a4402fccb0c5ef17943677df93e2a93929cb9a` |
| B2 | 2 | 2 | Rechenzentrum Rostock | `7971e5b627ad354ef6fb24402fb45c8d9063f8f5ff001cac41f875831f223623` |
| C2 | 2 | 3 | ERP-01 | `795aa1cbaa075804259248e644716c2cd3d28c5675c7f31147712569d8605e43` |
| A3 | 3 | 1 | SRV-002 | `1b7618da377da12f6c896cc9d45ebda1a53d9371ee5463e5370d57728f8f60fc` |
| B3 | 3 | 2 | Berlin | `dad114b6ed7342bac65c79575f6c7ff761ec26b52c1f5f7a9110532973d05df2` |
| C3 | 3 | 3 | CRM-02 | `3a7a3813b6f16182b567bcf9151031987f73363e686098fbf56015348cc3da73` |

Original binary XLSX SHA-256:

```text
bc7e1aca39406206d57375ce3d3201ee07499729e953d21cead05a8532dac792
```

Flattened extracted text SHA-256 (UTF-8, cell strings joined by LF, no trailing LF):

```text
8ba37d3f8ff7dde53e01f6c09884b20d0c2a9841897b7e7d97228eb6f4a39ed2
```

Canonical structure/provenance manifest SHA-256:

```text
9523e8ab0759a3864a588fb43d51bd197c551677d7bea137d06c177ab07bf526
```

Repeated ingestion of the same bytes, source ID and limits returned **equal results (`reproducible: true`)**. The temporary fixture was removed. Binary identity depends on the exact test ZIP metadata/serialization, whereas the manifest binds source ID, method/limits, ordered sheet identities/rows/cells/kinds/locators/text hashes. Identical flattened text alone does not establish structural identity. Repackaging can change the binary digest while preserving text and manifest hashes.

## Reproduce tests and demonstration

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion -v
py -3.12 -m unittest tests.test_xlsx_ingestion -v
```

From the same directory, run this synthetic-only demonstration. It prints every required cell locator/text/hash, workbook/text/manifest hashes and reproducibility, then removes the temporary fixture:

```powershell
@'
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.xlsx_ingestion import ingest_xlsx
from tests.test_xlsx_ingestion import demonstration_parts, write_synthetic_xlsx

with TemporaryDirectory(prefix="grundschutz-ai-xlsx-demo-") as directory:
    path = Path(directory) / "fictitious.xlsx"
    write_synthetic_xlsx(path, demonstration_parts())
    result = ingest_xlsx(path, source_id="synthetic:task-006b-demo")
    print(json.dumps({
        "source_id": result.source_id,
        "method": result.method,
        "xlsx_sha256": result.xlsx_sha256,
        "text_sha256": result.text_sha256,
        "manifest_sha256": result.manifest_sha256,
        "reproducible": result == ingest_xlsx(path, source_id=result.source_id),
        "sheets": [asdict(sheet) for sheet in result.sheets],
    }, ensure_ascii=False, indent=2))
print("Temporary fixture removed:", not path.exists())
'@ | py -3.12 -
```

## Security boundaries, future persistence and limitations

There is no general spreadsheet renderer or semantic interpreter. Canonical part names, IDs, ordering, plain strings and metadata requirements are deliberately narrow; Excel-generated styles/settings/properties and many valid OOXML constructs are unsupported. Parsed XML character semantics, not the lexical spelling of entities/line endings, define literal text. No numbers/dates/formulas are converted or evaluated. Formula-looking literal strings remain potentially unsafe for future spreadsheet exports and must never be reinterpreted as commands.

Caller-provided paths/configuration are trusted; synthetic status, author identity and source truth cannot be established by parsing or hashes. Source authentication, filesystem races/local attackers, access control, retention, fuzzing and production security review remain unresolved. No source text is logged by the reader. Dataclass construction itself is not a source-authentication boundary.

Nothing is persisted and SQLite schema version 1 is unchanged. ADR-0006 proposes retaining immutable original bytes and trusted source revisions, ordered sheet/cell manifests, blank/missing distinctions, all hash types and policy versions. Future reload must hash and reingest original bytes and compare regenerated manifests before use. A future adapter must map structural locators to exact cell-local evidence quotes while retaining conflicting workbook context; the existing domain UTF-8 source hash must not be replaced by a binary workbook hash. No raw text or invalid candidate may be exported as approved inventory. Explicit human approval remains separate and revision-bound.

Next suggested step is human review of the bounded profile and provenance/context contract. No TASK-006C, full Excel compatibility, production readiness, certification coverage or normative-baseline approval is claimed.

## Git verification

The baseline remains `d72230a`. Final read-only `git status --short --untracked-files=all` reported:

```text
 M Grundschutz-AI/grundschutz_ai/docx_ingestion.py
?? Grundschutz-AI/docs/decisions/0006-xlsx-ingestion.md
?? Grundschutz-AI/docs/tasks/TASK-006B-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/ooxml_safety.py
?? Grundschutz-AI/grundschutz_ai/xlsx_ingestion.py
?? Grundschutz-AI/tests/test_xlsx_ingestion.py
```

`git diff --name-only` listed only the modified DOCX module; the other five files are new/untracked. `git diff --check` passed. All six task files also passed direct UTF-8, trailing-whitespace and final-newline checks, covering untracked files that Git diff does not inspect. Git emitted its LF-to-CRLF working-copy conversion notice; no Git configuration or security settings were changed. No matching task XLSX temporary directories remained. Git checks were read-only as the normal user. Nothing staged or committed; no unrelated tracked changes.
