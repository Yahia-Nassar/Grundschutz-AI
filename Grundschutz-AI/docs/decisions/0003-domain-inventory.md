# ADR-0003: Immutable inventory and revision-bound human review

**Status:** Proposed for human review; implemented as the synthetic TASK-004 experiment and hardened in TASK-004.1.

## Decision and rationale

Keep typed, frozen domain records separate from extraction and Ollama. Store location and application links once, as `located_at` and `hosts` relationships. Derive IT-system references through inventory queries instead of duplicating them in mutable entity fields. Evidence references are required on named objects and relationships.

Use immutable in-memory snapshots and append-only record/review tuples. Stable IDs survive increasing integer revisions. An approval identifies a fingerprint covering current target data, evidence, provenance/candidate revision, source registration, and relevant endpoints/relationships. Any changed dependency requires fresh explicit review; model status never grants approval. No snapshot import or persistence is introduced.

One system may host multiple applications. For this initial experiment, multiple unrejected `located_at` alternatives are an unresolved conflict: both claims and the system require clarification. A reviewer can reject an alternative without deleting its evidence/history. This is a conservative engineering assumption; it is not a BSI statement that systems can never have multiple physical locations. More complex system groupings, temporal moves, mobile assets and service scope require a separately reviewed model.

Register multiple sources as distinct Evidence records. Add supporting evidence IDs to the same relationship for the same subject/predicate/object, rather than creating duplicate independent edges. Represent contradictory claims as separate alternatives with separate evidence and review decisions. The latest registered evidence revision establishes the currently known source content version; it does not select which conflicting fact is true. Record the source registration in fingerprints so returning to old bytes cannot silently restore earlier approvals.

## Limits

This is an API for trusted application code using synthetic data. It does not authenticate reviewers, discover external source changes, establish semantic truth from quotes, implement a secure audit database, or accept raw extractor candidates. A future adapter must rerun source/candidate validation and establish trustworthy provenance before constructing proposals. A future renderer must consume only current, explicitly human-approved revisions and validated dependencies. Evidence occurrence checks and human-review identifiers are not proof of identity or certification.

No applicable BSI baseline, A.1 interpretation or existing normative register is changed by this decision proposal.

## TASK-004.1: Bounded affirmative support

Substring co-occurrence is insufficient support. Named objects require complete, case-sensitive literal names, with word/hyphen identifier boundaries checked in the original source context. Evidence construction captures the adjacent characters before/after its quote so clipping a quote cannot turn `SRV-0012` into evidence for `SRV-001`. The complete name must still be inside the quote; adjacent context cannot fill missing quoted characters.

Relationship support is computed by a small pure helper independent of the domain enums, extraction client and external services. For this narrow prototype it accepts only these full affirmative source forms:

```text
Der Server <ID> betreibt die Anwendung <ID>.
Der Server <ID> befindet sich im Rechenzentrum <Place>[, Raum <ID>] und betreibt die Anwendung <ID>.
```

IDs are uppercase alphanumeric hyphenated identifiers. Place names are capitalized words/hyphenated words; room identifiers are uppercase alphanumeric/hyphenated. Negated/ambiguous location terms and all unsupported forms fail closed. Optional surrounding whitespace and the exact already-declared synthetic header `FIKTIVES TESTBEISPIEL — keine reale Infrastruktur.` followed by a newline are allowed. No arbitrary preamble, comment, instruction, second sentence or contradictory update is stripped. This domain support rule is deliberately narrower than general German prose and is not a general semantic parser.

The quote must cover the whole affirmative assertion. Every cited relationship Evidence must affirm the actual predicate and exact subject/object values in their proper roles; matching two names does not suffice, and a positive citation cannot override a negative/unsupported cited source. The original source is assessed while available as an InitVar, preventing a selected quote from concealing contradictory trailing source content.

Evidence retains only immutable derived support metadata and boundary characters, not the original text. The derived fields cannot be supplied through the ordinary Evidence constructor or dataclass replacement. Derived support and its policy version participate in revision fingerprints; previous bindings cannot silently remain valid under a changed rule. Add/revise and explicit approval recheck support; existing unsupported claims require clarification and cannot appear in the approved view. An explicit rejection of the current revision remains rejected, with history intact. Evidence artifacts can still faithfully quote negative statements: approving the artifact's provenance never approves an affirmative relationship inferred from it.

Exact syntactic support does not prove real-world truth, trustworthy authorship, or authenticated human review. Those boundaries remain necessary. No BSI interpretation was changed.

## TASK-005 preparation only: Trustworthy local source retention

`Evidence.source_text` is an InitVar. A SHA-256 cannot reconstruct the original text; the derived support cache and quote cannot replace it. Before any future persistence loader can restore reviewable evidence:

1. Retain or securely reference immutable source versions in a permissioned local source store outside Git. Bind source ID, version, content hash and an opaque trusted local object reference; source/model text must not choose arbitrary filesystem paths. Preserve exact original text/encoding and line endings for the Unicode-character locator contract. If later parsers produce text from original files, preserve both original-file and extracted-text hashes plus the parser/version and locator mapping.
2. On load, resolve the authorized source reference, verify the expected UTF-8 text hash, check the exact quote/character span, and reconstruct Evidence using the original text. Recompute boundaries and affirmative support under the recorded/current policy. Never trust a serialized derived-support flag or a stored `approved` string as validation.
3. Missing, changed, truncated, inaccessible or mismatched source content must block approval and require clarification. Source/policy/candidate updates require revision-bound review; preserve old decisions and their source references without automatically reactivating them when content reverts.
4. Preserve provenance, source registration ordering, immutable record revisions and append-only human decisions together. Authenticate source registration and reviewer identity; hashes provide integrity, not authorship. Define access, retention, backup and deletion rules so deleting a required source version cannot leave a falsely approved current view.

These are documented prerequisites only. No store, SQLite schema, loader, migration, file ingestion or TASK-005 implementation is included in TASK-004.1.
