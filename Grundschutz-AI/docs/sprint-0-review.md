# TASK-001 — Sprint 0 review

Review date: 2026-11-06. Scope: documentation and read-only environment checks only.

## Intended outcome

A Windows-native, local-first assistant will turn permissioned local PDF/DOCX/XLSX evidence into an editable German A.1 draft with eight sections, inventories, relationships, provenance, missing-data flags and human approval. Synthetic data is required throughout development; a controlled company-data pilot is deferred to S8. No certification claim is justified by draft generation.

## Sprint 0 acceptance: FAIL

TASK-001 review deliverables are complete, but Sprint 0 cannot be accepted. The authoritative source mapping, applicable edition, Git checkpoint/clean status, target hardware evidence and Product Owner acceptance are outstanding. Do not move to Sprint 1 until a human reviews and accepts the gate evidence.

| Gate | Evidence and status |
|---|---|
| Foundation documents | PASS for presence; reviewed README, AGENTS, GOALS, PLANS, requirements, architecture, quality gates, setup and both ADRs. |
| A.1 mapping and applicable edition | FAIL: eight positions/nine themes and combined A.1.1 are internally consistent with the task baseline. Official PDF retrieval returned HTTP 403; exact labels, summaries, page references and edition applicability could not be independently verified. Public BSI searches returned no results. V2.1 (24.04.2019) remains a proposed baseline, not the latest binding edition. |
| Core tools | Git 2.39.1.windows.1 and Python 3.12.6 returned versions. VS Code returned 1.108.1/x64 with a crashpad access-denied diagnostic; full operational status is not established. This Codex session can inspect/edit project documentation; IDE/CLI sign-in was not independently checked. |
| Repository/checkpoint | FAIL: Git rejected status, root and log queries because of ownership mismatch at the parent workspace repository. No security exception or Git configuration was changed; first checkpoint and clean status remain unverified. Project documents are under the nested `Grundschutz-AI` directory. Confirm the intended repository root and ignore-file scope before staging anything. |
| Hardware | FAIL for evidence: CIM CPU/OS/RAM queries were denied and drive queries provided no usable capacity values. Windows 11, 16 GB RAM and RX 580 8 GB are supplied target assumptions, not measured facts. |
| Task boundaries | PASS for this execution: only project text and environment metadata inspected; no confidential source files opened, installations, model downloads, inference, application implementation or repository initialization performed. File inventory contains no application implementation or model artifacts; this is not a workstation-wide audit. |
| Human acceptance | Pending Product Owner review, baseline decision and authorization of a separately bounded Sprint 1 task. |

## Top five risks and minimal decisions

| Risk | Existing mitigation | Remaining decision / minimal improvement |
|---|---|---|
| Normative drift or unsupported BSI interpretation | Version/date cited; eight positions distinguished from nine themes; software assumptions separated. | Certification lead must verify section 2.2 and appendix against an accessible official copy, including A.1.1 integration, exact labels, grouping, asset examples and service/connection scope; select applicable editions/amendments. Do not label the mapping independently verified yet. |
| Confidential data reaches development/cloud/Git | AGENTS forbids company data in Codex; local inference, synthetic development, loopback binding and ignore patterns specified. | `.gitignore` is not access control and nested patterns may not protect the parent repository. Before a pilot, decide authorized source owners, reviewer roles, retention/deletion, local access/backup protection and treatment of evidence excerpts, logs, SQLite sidecars and exports. Keep real data outside this development workspace. No privacy leak was identified in the reviewed project text; confidentiality of unread files is not assessed. |
| Unsupported or unusable inference on target hardware | CPU-first ADR; small quantized baseline; no GPU dependency. | Measure actual CPU, available RAM under normal load and disk capacity. Ollama's public Windows ROCm list does not include RX 580; Vulkan availability does not establish compatibility or useful performance on this workstation. Explicitly enforce and verify CPU execution for S1, since runtime defaults may enable Vulkan. Agree RAM/context/latency limits before benchmarking. |
| Unsupported facts or inconsistent review/export states | Evidence locators, conflict preservation, human review and deterministic validation already planned. | Architecture previously used candidate/approved/rejected while requirements define four states; aligned terminology. Later define export rules so rejected/disputed candidates cannot appear as approved facts; preserve extraction method, timestamps and reviewer attribution as required by AGENTS. Resolve with synthetic schema work, not S0 application code. |
| Premature gate acceptance and unsafe setup assumptions | PLANS requires Product Owner review; setup steps and read-only checker exist. | Quality gates lacked explicit source/applicability and human handoff conditions; clarified them. Setup commands are future human actions requiring approval, not TASK-001 instructions to install. Resolve repository ownership through the owner/administrator without bypassing protections, verify the correct root/checkpoint, and rerun blocked checks in an authorized environment. Do not assume a successful script exit means all checks passed. |

## Documentation changes and rationale

- `docs/requirements/A1_REQUIREMENTS.md`: identify the mapping as pending primary-source verification and distinguish paraphrases from official wording; no BSI interpretation changed.
- `docs/architecture.md`: align the four review states with the requirements register.
- `docs/quality-gates.md`: explicitly require source/applicability evidence and human acceptance before S1.
- `docs/sprint-0-review.md`: this review, acceptance evidence, risks and next-task checklist.

No dependencies, scripts or application files changed. These are review corrections, not approval of the proposed ADRs or the normative baseline.

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

Which certification date/editions and auditor template apply? Who owns source access and review? Is the network plan a controlled annex or embedded artifact? What locators are adequate for scanned pages/diagrams? Is the parent workspace the intended Git root? Who can supply authorized hardware and checkpoint evidence? What RAM/latency/quality thresholds define a successful S1 benchmark?
