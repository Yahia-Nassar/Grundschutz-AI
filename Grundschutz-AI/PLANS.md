# Delivery plan / stage gates

A stage is complete only when the Product Owner reviews the deliverables and acceptance evidence.

| Sprint | Outcome | Exit gate |
|---|---|---|
| S0 — Foundation | Scope, architecture, Codex rules, Windows setup | Docs reviewed; Git repository exists; tools verified; no sensitive files |
| S1 — Local inference benchmark | Local runtime + small model comparison | Record RAM/CPU/latency/structured-JSON quality; choose model empirically |
| S2 — Structured A.1 schema | Validated entities, relationships, evidence locators | Synthetic JSON passes tests, missing and invalid links rejected |
| S3 — Deterministic DOCX prototype | A.1.1–A.1.8 from synthetic data | DOCX opens, all sections present, no fabricated fields |
| S4 — File ingestion | PDF, DOCX, XLSX local parsers | Source locators verified; scanning/OCR flagged separately |
| S5 — Retrieval + extraction | Candidate facts + evidence links | Evaluation set measures precision/recall and uncited assertions |
| S6 — Human review + rules | Review statuses, audit trail, gaps | Human can approve/reject and conflicts cannot be silently overwritten |
| S7 — End-to-end MVP | Local UI, DOCX export, validations | Offline test with synthetic corpus and repeatable results |
| S8 — Controlled pilot | Approval-gated company-document pilot | Privacy assessment, backup, threat model and user signoff |

## Current Sprint 0 backlog

- [ ] Confirm the exact BSI standard/edition required by the target certification process.
- [ ] Install Git and VS Code; select Codex extension or CLI.
- [ ] Install Python 3.12 and confirm `py -3.12 --version`.
- [ ] Initialize a local-only Git repository; make the first checkpoint.
- [ ] Read/review the 8 A.1 output sections and 9 information themes.
- [ ] Capture CPU model, available disk space, available RAM under typical load.
- [ ] Decide on source-document access permissions and review ownership.
- [ ] Approve the proposed Stage 1 hardware benchmark.

## Definition of Done for S0

1. `git --version`, `py -3.12 --version`, and `code --version` work.
2. Codex is installed, signed in, and can inspect the repository.
3. `git status` is clean after commit.
4. `docs/requirements/A1_REQUIREMENTS.md` clearly separates BSI text from assumptions.
5. No raw company documents have been loaded into Codex.
