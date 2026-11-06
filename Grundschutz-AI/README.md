# Grundschutz AI

**Status:** Sprint 0 — planning and workstation setup; no application code yet.

Grundschutz AI is a **local-first**, evidence-based assistant for drafting **A.1 Strukturanalyse** for ISO 27001 certification on the basis of BSI IT-Grundschutz. The first release is *not* an automated certification tool. Its output must be checked and approved by a qualified human reviewer.

## Target workstation

- OS: Windows 11 (native development, no WSL requirement).
- RAM: 16 GB.
- GPU: AMD Radeon RX 580, 8 GB VRAM. Not listed as a supported Ollama ROCm GPU on Windows. CPU-first; Vulkan is experimental until benchmarked.
- Formats in scope: PDF, DOCX, XLSX. Scanned PDFs and diagrams require separate evaluation.
- UI / report language: German; project discussions: Romanian; technical documentation and code: English.

## Read in this order

1. `GOALS.md` — problem and success criteria.
2. `docs/requirements/A1_REQUIREMENTS.md` — verified source scope and design hypotheses.
3. `docs/architecture.md` — proposed architecture and data lifecycle.
4. `PLANS.md` — stage gates and sprint milestones.
5. `AGENTS.md` — binding rules for Codex.
6. `docs/setup-windows.md` — machine setup and checks.
7. `tasks/CODEX_TASK_001.md` — first Codex assignment.

## Non-goals for Sprint 0

No LLM installation, no AI training, no real company data ingestion, no browser calls containing company files, no production integrations, and no claims of audit compliance.

## Normative baseline

BSI, *Hinweise zur Bereitstellung der Referenzdokumente im Rahmen der Zertifizierung nach ISO 27001 auf der Basis von IT-Grundschutz*, Version 2.1, 24 April 2019, section 2.2 and appendix (A.1.1–A.1.8). Before production use, review all currently binding BSI certification specifications and applicable BSI-Standard 200-2 / IT-Grundschutz editions.

Official URL: https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/Zertifikat/ISO27001/Hinweise_Referenzdokumente_Kompendium.pdf?__blob=publicationFile&v=8
