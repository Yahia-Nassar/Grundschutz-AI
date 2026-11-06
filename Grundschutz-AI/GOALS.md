# Product charter

## Problem

Organizations hold facts relevant to A.1 Strukturanalyse across heterogeneous documents. Manual extraction creates inconsistent identifiers, missing relationships, weak evidence traceability, and costly revisions.

## Product vision

Given a local, permissioned collection of company documents, produce a **German A.1 draft**, with linked evidence, explicit uncertainty, structured inventory, missing-data report, and human approval workflow.

## MVP demonstration

With an entirely synthetic document set, the system produces an editable A.1 DOCX draft with A.1.1–A.1.8 sections, source pointers, missing-information flags, and an exportable validation report.

## Business success criteria

- Correct A.1.1–A.1.8 section structure (subject to confirmation against the applicable BSI baseline).
- All extracted statements traceable to original source file and page/sheet/paragraph or another reliable locator.
- Unsupported facts are absent or marked `Nicht nachgewiesen` / `Pruefung erforderlich`.
- Each relationship (process -> application -> system -> location/service) can be inspected.
- No confidential source files sent to cloud services during application operation.
- A human may approve/reject each proposed fact and approve the final document.
- Reproducible exports: store model, prompt, template, document revision and input hashes.

## Exclusions, initially

- A.2–A.6 generation; certification guarantees; final legal/auditor decisions.
- Arbitrary OCR, CAD/image parsing, live network scanning, automated penetration testing.
- Fine-tuning or training a foundation model from scratch.

## Roles

- Product owner: user (scope, priorities, acceptance).
- PM/architect: ChatGPT (requirements, task decomposition, review).
- Engineer: Codex (code changes following bounded tasks).
- Audit/ISMS reviewer: domain professional (sign-off for real output).
