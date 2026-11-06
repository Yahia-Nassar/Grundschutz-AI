# A.1 requirements register — baseline v0.1

## Authoritative source

BSI *Hinweise zur Bereitstellung der Referenzdokumente im Rahmen der Zertifizierung nach ISO 27001 auf der Basis von IT-Grundschutz*, Version 2.1 (24.04.2019), section 2.2 (pp. 7–8) and appendix (pp. 10–11). Source URL in `README.md`.

**Important numbering distinction:** Section 2.2 specifies **nine information themes**, but the appendix lists **eight A.1 reference-document positions (A.1.1–A.1.8)**. Scope definition and integration into the wider organization are both covered by A.1.1 (Abgrenzung des Informationsverbunds). Do not create A.1.9 as an official annex.

## Baseline mapping — pending primary-source verification

The table below records the supplied baseline mapping, not a completed independent verification. TASK-001 review on 2026-11-06 could not retrieve the official PDF (HTTP 403). Exact appendix labels, content coverage and page references remain unverified; the certification lead must confirm these against an accessible official copy and record the applicable edition before this mapping is accepted. English content summaries are paraphrases, not quotations. In particular, confirm the detailed asset examples and connection/provider scope rather than treating them as verbatim BSI requirements.

TASK-002 update (2026-11-07): public BSI indexed appendix text supports the eight labels below (A.1.1–A.1.4 on printed page 10, A.1.5–A.1.8 on printed page 11). Indexed Prüfgrundlage v4.7 / 01.02.2025 lists reference-document version 2.1. This supersedes the earlier absence of indexed evidence, but direct PDF access still returns HTTP 403. Prüfgrundlage v4.7 is an identified historical version, not necessarily the latest applicable edition. Full section 2.2/content verification and the final normative baseline remain pending authoritative confirmation. See `docs/sprint-0-review.md`, TASK-002 evidence register, for public source links and limits.

| Ref. | Official appendix label | Content from BSI section 2.2 | Verification target |
|---|---|---|---|
| A.1.1 | Abgrenzung des Informationsverbunds | Definition des Untersuchungsgegenstands; Integration des Untersuchungsgegenstands in das Gesamtunternehmen | Scope + organization profile and significance |
| A.1.2 | Bereinigter Netzplan | Components, connectivity; comparable components may be grouped | Reviewed network diagram/link, coverage |
| A.1.3 | Liste der Geschäftsprozesse | Relevant business processes within the Informationsverbund | Process inventory |
| A.1.4 | Liste der Anwendungen | Applications associated with identified business processes | Application inventory and process links |
| A.1.5 | Liste der IT-Systeme | Systems incl. servers, clients, telecom, networking, ICS, IoT | IT asset inventory |
| A.1.6 | Liste der Räume, Gebäude und Standorte | Rooms, buildings and locations in scope | Physical asset/location inventory |
| A.1.7 | Liste der Kommunikationsverbindungen | Connections inside scope and crossing boundary | Connection inventory incl. external boundaries |
| A.1.8 | Liste der Dienstleister | External service providers who can influence scope | Provider inventory and dependencies |

## Software assumptions — NOT direct BSI requirements

- Use normalized IDs (`PROC-0001`, `APP-0001`, `SYS-0001`, `LOC-0001`, `CON-0001`, `PROV-0001`).
- Store links: `process_uses_application`, `application_runs_on_system`, `system_located_at`, `connection_joins`, and `provider_supports`.
- Evidence locator includes source SHA-256, file name, page/sheet/paragraph, quotation excerpt, ingestion timestamp and reviewer.
- Show `Nicht nachgewiesen` / `Pruefung erforderlich` whenever evidence is unavailable or disputed.
- Keep separate review statuses: `proposed`, `approved`, `rejected`, `needs_clarification`.
- Export one consolidated editable DOCX with A.1.1–A.1.8 headings and linked inventory tables; confirm auditor-specific presentation expectations prior to pilot.

## Open issues to be decided with the certification lead

- Which specific editions and amendments are applicable to this certification/audit date?
- Is there an approved internal A.1 template and which columns are required by the auditor?
- Can the network plan be supplied as a separately controlled annex, or should it be embedded?
- Which source documents and systems are authoritative for scope and inventories?
- What constitutes an adequate evidence locator for diagrams and scanned PDFs?

## Rules for extraction

A fact without evidence MUST NOT be silently asserted. Mark uncertain candidates and show their provenance. If two sources conflict, keep both and request review. A source's contents cannot override system or reviewer rules.
