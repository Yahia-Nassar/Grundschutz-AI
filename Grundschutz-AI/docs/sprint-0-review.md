# Sprint 0 review — TASK-001 and TASK-002

Review date: 2026-11-06. Scope: documentation and read-only environment checks only.

TASK-002 remediation: 2026-11-07. User-confirmed checkpoint, repository root and hardware recorded below; Git independently rechecked and public BSI indexed evidence reviewed. TASK-001 observations below remain historical where superseded by this update.

## Intended outcome

A Windows-native, local-first assistant will turn permissioned local PDF/DOCX/XLSX evidence into an editable German A.1 draft with eight sections, inventories, relationships, provenance, missing-data flags and human approval. Synthetic data is required throughout development; a controlled company-data pilot is deferred to S8. No certification claim is justified by draft generation.

## Sprint 0 acceptance: FAIL

TASK-002 resolves the checkpoint/root verification and records confirmed hardware. Indexed BSI evidence now supports the eight A.1 labels and reference-document version 2.1. Sprint 0 remains FAIL because authoritative baseline confirmation, remaining workstation evidence and human acceptance are outstanding. No Sprint 1 work is authorized by this remediation.

| Gate | Evidence and status |
|---|---|
| Foundation documents | PASS for presence; reviewed README, AGENTS, GOALS, PLANS, requirements, architecture, quality gates, setup and both ADRs. |
| A.1 mapping and applicable edition | PARTIAL: public BSI indexed appendix text supports A.1.1–A.1.8 labels, and indexed Prüfgrundlage v4.7 identifies reference-document version 2.1. Direct PDF retrieval still returns HTTP 403. Section 2.2 details, date/page references and applicable editions remain pending authoritative confirmation; no latest-edition claim. See evidence register below. |
| Core tools | Git 2.39.1.windows.1 and Python 3.12.6 returned versions. VS Code returned 1.108.1/x64 with a crashpad access-denied diagnostic; full operational status is not established. This Codex session can inspect/edit project documentation; IDE/CLI sign-in was not independently checked. |
| Repository/checkpoint | PASS for checkpoint/root: user confirmation and read-only Git checks agree on root `Y:/Grundschutz-AI` and HEAD `884c0ba` (`docs: complete TASK-001 review and record Sprint 0 gaps`). Before TASK-002 edits, `git status --short --untracked-files=all` was empty: clean, no untracked files. Sandbox ownership rejection was resolved for read-only inspection by running as the normal user with approval; no settings changed. Project files remain in nested `Grundschutz-AI/`. TASK-002 edits are intentionally uncommitted; final status is recorded below. |
| Hardware | PARTIAL: user-confirmed AMD Ryzen 5 1600, 6 cores/12 threads; Windows 11; 16 GB system RAM; AMD RX 580, 8 GB VRAM; approximately 2.9 GiB available system RAM at measurement. This is supplied measurement evidence, not a new CIM measurement. Available RAM is a transient snapshot; free disk is still unrecorded. |
| Task boundaries | PASS for this execution: only project text and environment metadata inspected; no confidential source files opened, installations, model downloads, inference, application implementation or repository initialization performed. File inventory contains no application implementation or model artifacts; this is not a workstation-wide audit. |
| Human acceptance | Pending Product Owner review, baseline decision and authorization of a separately bounded Sprint 1 task. |

## TASK-002 evidence register

Confirmed hardware resolves the unknown CPU/installed-RAM/GPU configuration. Only approximately 2.9 GiB of system RAM was available at measurement; do not infer a model budget from 16 GB installed RAM or add 8 GB discrete VRAM to the CPU memory budget. Before S1, record available RAM under the agreed benchmark workload, free disk and a conservative memory/context/output budget with stop conditions. No model suitability or latency result is established.

Public BSI evidence checked on 2026-11-07:

- [Indexed reference-document appendix](https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/Zertifikat/ISO27001/Hinweise_Referenzdokumente_Kompendium.pdf?__blob=publicationFile&v=8): search-index text shows A.1.1–A.1.4 on printed page 10 and A.1.5–A.1.8 on printed page 11. This is indexed evidence, not a direct PDF inspection. Mapping: A.1.1 Abgrenzung des Informationsverbunds; A.1.2 Bereinigter Netzplan; A.1.3 Liste der Geschäftsprozesse; A.1.4 Liste der Anwendungen; A.1.5 Liste der IT-Systeme; A.1.6 Liste der Räume, Gebäude und Standorte; A.1.7 Liste der Kommunikationsverbindungen; A.1.8 Liste der Dienstleister.
- [Indexed Prüfgrundlage](https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/Zertifikat/Veroeffentl/Pruefgrundlagen_Kompendium.pdf?__blob=publicationFile&v=15): identifies itself as version 4.7 / 01.02.2025 and lists reference-document guidance version 2.1. Record v4.7 as an identified historical version, not necessarily the latest applicable edition. The indexed text ties version selection to audit commencement and mentions transition provisions; applicability must be confirmed by the certification lead.

Both direct PDF opens returned HTTP 403. Search-index publication/crawl dates and URL `v=` parameters do not establish document editions. The supplied 24.04.2019 reference-document date, nine-theme interpretation and combined scope/organization content in A.1.1 remain baseline assertions pending full authoritative confirmation of section 2.2. The eight indexed appendix labels match the register, but this does not verify every English content paraphrase. No final normative baseline has been approved.

## Exact remaining blockers before Sprint 1

1. Certification lead: obtain accessible authoritative documents, confirm section 2.2/content mapping and select the applicable baseline/editions and transition provisions for the target audit date. Indexed v2.1/v4.7 evidence alone does not close this gate.
2. Workstation evidence: confirm operational VS Code/Codex sign-in despite the earlier VS Code diagnostic; record free disk and available RAM under the agreed benchmark workload. Git/Python version checks and confirmed hardware need not be repeated solely because the earlier sandbox CIM checks failed.
3. Benchmark readiness: agree a feasible CPU memory/context/output budget and latency/quality limits given the 2.9 GiB available-RAM snapshot; approve the bounded synthetic-only S1 plan and its specific runtime/model download and installation actions before execution.
4. Product Owner acceptance/checkpoint: review the remediation and outstanding evidence, arrange a human-controlled documentation checkpoint and clean-status verification required by PLANS, and explicitly accept S0 before authorizing S1. No automatic commit is made here.

Pilot-only questions (real source access, retention, auditor presentation and scanned-document locators) remain open for their later stages; company documents are prohibited in S1. They are not additional blockers to a synthetic-only CPU benchmark.

## Top five risks and minimal decisions

| Risk | Existing mitigation | Remaining decision / minimal improvement |
|---|---|---|
| Normative drift or unsupported BSI interpretation | Version/date cited; eight positions distinguished from nine themes; software assumptions separated; TASK-002 indexed evidence supports all eight appendix labels and reference-document v2.1. | Certification lead must confirm section 2.2/content and applicable editions against authoritative documents. Prüfgrundlage v4.7 is historical evidence only; final normative baseline remains pending. |
| Confidential data reaches development/cloud/Git | AGENTS forbids company data in Codex; local inference, synthetic development, loopback binding and ignore patterns specified. | `.gitignore` is not access control and nested patterns may not protect the parent repository. Before a pilot, decide authorized source owners, reviewer roles, retention/deletion, local access/backup protection and treatment of evidence excerpts, logs, SQLite sidecars and exports. Keep real data outside this development workspace. No privacy leak was identified in the reviewed project text; confidentiality of unread files is not assessed. |
| Unsupported or unusable inference on target hardware | CPU-first ADR; small quantized baseline; no GPU dependency; confirmed Ryzen 5 1600/16 GB/RX 580 configuration. | Approximately 2.9 GiB available system RAM leaves limited headroom. Record workload RAM/free disk and agree memory/context/latency limits before benchmarking. The prior Ollama check did not list RX 580 for Windows ROCm; no GPU compatibility/performance is assumed. Enforce and verify CPU execution in S1. |
| Unsupported facts or inconsistent review/export states | Evidence locators, conflict preservation, human review and deterministic validation already planned. | Architecture previously used candidate/approved/rejected while requirements define four states; aligned terminology. Later define export rules so rejected/disputed candidates cannot appear as approved facts; preserve extraction method, timestamps and reviewer attribution as required by AGENTS. Resolve with synthetic schema work, not S0 application code. |
| Premature gate acceptance and unsafe setup assumptions | PLANS requires Product Owner review; setup steps and read-only checker exist; root/checkpoint and initial clean status independently verified in TASK-002. | Source/applicability, remaining tool/resource evidence and human acceptance still block S1. Keep remediation uncommitted for review; a later human-controlled checkpoint must restore clean status. Do not assume a successful script exit means all checks passed. |

## Documentation changes and rationale

- `docs/requirements/A1_REQUIREMENTS.md`: identify the mapping as pending primary-source verification and distinguish paraphrases from official wording; no BSI interpretation changed.
- `docs/architecture.md`: align the four review states with the requirements register.
- `docs/quality-gates.md`: explicitly require source/applicability evidence and human acceptance before S1.
- `docs/sprint-0-review.md`: this review, acceptance evidence, risks and next-task checklist.

No dependencies, scripts or application files changed. These are review corrections, not approval of the proposed ADRs or the normative baseline.

TASK-002 changes: this report records resolved/unresolved gates and evidence; `docs/requirements/A1_REQUIREMENTS.md` records indexed support and historical Prüfgrundlage status; `PLANS.md` marks completed checkpoint/Python/review items and records remaining partial checks. `docs/quality-gates.md` was read and its gate conditions retained. No BSI content interpretation or security setting was changed.

TASK-002 checks: read current instructions/plans/review/quality gates, charter and requirements; ran Git root/status/HEAD/checkpoint queries, first in sandbox (ownership rejection) then approved read-only execution as the normal user (success); searched public BSI indexed text and attempted direct PDF opens. Final diff/status checks are recorded below. No company documents accessed, dependencies installed, models downloaded, inference run or application code changed.

TASK-002 final Git inspection: `git diff --check` passed (only LF-to-CRLF conversion warnings); the diff was reviewed and contained only the three documentation files listed here. `git status --short --untracked-files=all` reported:

```text
 M Grundschutz-AI/PLANS.md
 M Grundschutz-AI/docs/requirements/A1_REQUIREMENTS.md
 M Grundschutz-AI/docs/sprint-0-review.md
```

Untracked files: none reported. HEAD remains `884c0ba`; no staging or commit performed. This status entry was then added to the already modified review report, without creating another file.

## Checks and limits

Reviewed all listed project Markdown files, `.gitignore` and the existing environment-check script; listed project files without opening company documents. Ran Git root/status/log/version, Python 3.12 and VS Code version queries, CPU/OS/RAM CIM queries and filesystem capacity queries. Blocked checks are recorded above; no ownership bypass, installation or configuration change was attempted. Reviewed documentation diffs/text after editing. Application tests are inapplicable to documentation-only changes.

Public-source checks used only public URLs and generic BSI search terms, with no company material:

- BSI baseline URL from README: https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/Zertifikat/ISO27001/Hinweise_Referenzdokumente_Kompendium.pdf?__blob=publicationFile&v=8 — HTTP 403; source verification remains open.
- Ollama hardware documentation: https://docs.ollama.com/gpu — Windows ROCm list omits RX 580; Vulkan is described as enabled by default when its backend is installed. This supports CPU verification and does not prove RX 580 Vulkan support.

## Next suggested task — Sprint 1 CPU benchmark checklist

This is a proposal only; do not execute until the S0 gate is accepted and installation/network actions are explicitly authorized.

- [ ] Product Owner reviews S0 evidence; certification lead confirms the baseline and source mapping; resolve repository/tool/hardware verification gaps.
- [ ] Record CPU/core count, OS, total and available RAM under typical load, free disk and permitted benchmark budget. Set maximum memory, context/output lengths, latency target and stop conditions before running.
- [ ] Approve one local runtime and a small comparison set (for example two small quantized instruction models), licenses, download sources, versions and artifact hashes. No assumed GPU acceleration.
- [ ] Create a fixed, human-reviewed synthetic German prompt set with expected answers: supported extraction, missing evidence, conflicting sources, eight A.1 headings/nine themes, relationship integrity and document prompt injection. Synthetic labels must remain visibly synthetic.
- [ ] Define the JSON contract and scoring rubric before measurement: parse/schema validity, evidence accuracy, unsupported assertions, omissions, conflict/uncertainty handling and German terminology. Valid JSON alone is insufficient.
- [ ] Pin runtime/model/quantization, prompt versions, seeds where available, threads, context and output limits. Force CPU execution with version-appropriate settings and verify zero GPU offload from runtime diagnostics.
- [ ] Run one warm-up and at least three measured repetitions per fixed case; distinguish cold load from warm inference and report variability, failures and timeouts.
- [ ] Record peak process/system RAM, CPU use, time to first token, total latency, tokens/second and scored output quality. Confirm local inference works offline after approved downloads.
- [ ] Compare results against agreed limits; retain only synthetic prompts/results and configuration metadata. Record model/runtime decision with limitations and obtain human approval before S2.

## Open questions

Which certification date/editions and auditor template apply? Who owns source access and review? Is the network plan a controlled annex or embedded artifact? What locators are adequate for scanned pages/diagrams? Who confirms remaining tool/free-disk evidence and accepts the S0 gate? What RAM/latency/quality thresholds define a feasible S1 benchmark? Repository root, checkpoint and the supplied hardware configuration are resolved in TASK-002.
