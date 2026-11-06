# TASK-001 — Review and finalize Sprint 0 foundation

You are a senior Python architect assisting a local-first BSI IT-Grundschutz A.1 document generation project.

**Read first:** `AGENTS.md`, `GOALS.md`, `PLANS.md`, `docs/requirements/A1_REQUIREMENTS.md`, `docs/architecture.md`.

## Objective

Review the existing Sprint 0 project files for completeness, contradictions, privacy leaks, unsupported BSI interpretations, and Windows 11 16GB/RX580 hardware assumptions. Recommend the minimum necessary improvements.

## Sources and boundaries

- Source baseline: BSI *Hinweise zur Bereitstellung der Referenzdokumente*, V2.1 (24.04.2019), section 2.2 and appendix. Verify version applicability only through publicly available sources; don't imply it is the latest binding edition.
- A.1 has **8 numbered reference items** A.1.1–A.1.8, covering **9 information themes**. A.1.1 combines scope definition and organizational integration.
- Never request, read, paste, or upload real company files.
- Do not download models, install dependencies, create backend/application logic, run model inference or initialize remote repositories.

## Tasks

1. Inspect the repository and summarize its intended outcome.
2. Identify the top five technical, normative and privacy risks; identify which are already mitigated and which need decisions.
3. Verify that `A1_REQUIREMENTS.md` describes official BSI sections accurately, and flags assumptions.
4. Propose any edits to documentation needed to meet Sprint 0 acceptance criteria. Keep edits minimal.
5. Provide a checklist for the next Sprint 1 task: benchmarking CPU-only LLM inference with synthetic German IT-Grundschutz prompts.

## Acceptance criteria

- No application code, dependencies or LLMs installed.
- No confidential files accessed.
- Report includes changed-file list (or 'no changes'), assumptions, open questions and a clear PASS/FAIL Sprint 0 gate status.
- Human review required before moving to Sprint 1.
