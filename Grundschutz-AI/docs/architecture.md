# Architecture decision draft — S0

## Local-first logical flow

```
[PDF/DOCX/XLSX, local and permissioned]
                |
      [extract & normalize]
                |
       [source/evidence store]
                |
       [retrieval + local LLM]
                |
  [candidate entities / relations]
                |
   [deterministic BSI validators]
                |
        [human review UI]
                |
    [versioned A.1 DOCX export]
```

## Components (not yet implemented)

1. **Ingestion adapters:** extraction with source references; no OCR by default; flag missing or scanned pages.
2. **Fact/evidence store:** SQLite, stable IDs, metadata, SHA-256 source version identifiers and many-to-many relationships.
3. **Retrieval:** start with SQLite full-text search; introduce vectors only if evaluation demonstrates a benefit.
4. **Local generation:** swappable runtime / model; CPU-first given Windows 11, 16 GB and RX 580; never couple application schema to a model.
5. **Validation:** deterministic completeness and referential-integrity checks; no confidence-only approval.
6. **Human review:** `proposed`, `approved`, `rejected`, `needs_clarification` states with attribution and revision history, matching the requirements register.
7. **Rendering:** DOCX first, with tables and export of missing/uncertain information; PDF conversion later.
8. **UI:** local server/desktop interface after the command-line pipeline is trustworthy.

## Security boundaries

- Source documents and inference must remain local; no outgoing request containing source content.
- Codex development sessions use only synthetic data and the repository with sensitive files excluded.
- No persistent logs of document text or personally identifiable data by default.
- Local API binds to loopback, not `0.0.0.0`, unless explicitly reviewed.
- Separate generated outputs and sensitive raw documents from source control.

## Proposed technology stack (subject to measurements)

Python 3.12, Pydantic, SQLite, pytest, `python-docx`/`docxtpl`, PyMuPDF or equivalent, `openpyxl`, optionally FastAPI, Ollama or llama.cpp. These are target choices, **not installed by Sprint 0**.

## Critical evaluation

Measure source citation accuracy, uncited factual claims, entity deduplication, link consistency, correct A.1 headings, unsupported-data markers, DOCX validity, peak RAM, and generation time. Evaluate on curated *synthetic* fixtures before real data.
