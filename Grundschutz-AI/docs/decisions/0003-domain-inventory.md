# ADR-0003: Immutable inventory and revision-bound human review

**Status:** Proposed for human review; implemented as the synthetic TASK-004 experiment.

## Decision and rationale

Keep typed, frozen domain records separate from extraction and Ollama. Store location and application links once, as `located_at` and `hosts` relationships. Derive IT-system references through inventory queries instead of duplicating them in mutable entity fields. Evidence references are required on named objects and relationships.

Use immutable in-memory snapshots and append-only record/review tuples. Stable IDs survive increasing integer revisions. An approval identifies a fingerprint covering current target data, evidence, provenance/candidate revision, source registration, and relevant endpoints/relationships. Any changed dependency requires fresh explicit review; model status never grants approval. No snapshot import or persistence is introduced.

One system may host multiple applications. For this initial experiment, multiple unrejected `located_at` alternatives are an unresolved conflict: both claims and the system require clarification. A reviewer can reject an alternative without deleting its evidence/history. This is a conservative engineering assumption; it is not a BSI statement that systems can never have multiple physical locations. More complex system groupings, temporal moves, mobile assets and service scope require a separately reviewed model.

Register multiple sources as distinct Evidence records. Add supporting evidence IDs to the same relationship for the same subject/predicate/object, rather than creating duplicate independent edges. Represent contradictory claims as separate alternatives with separate evidence and review decisions. The latest registered evidence revision establishes the currently known source content version; it does not select which conflicting fact is true. Record the source registration in fingerprints so returning to old bytes cannot silently restore earlier approvals.

## Limits

This is an API for trusted application code using synthetic data. It does not authenticate reviewers, discover external source changes, establish semantic truth from quotes, implement a secure audit database, or accept raw extractor candidates. A future adapter must rerun source/candidate validation and establish trustworthy provenance before constructing proposals. A future renderer must consume only current, explicitly human-approved revisions and validated dependencies. Evidence occurrence checks and human-review identifiers are not proof of identity or certification.

No applicable BSI baseline, A.1 interpretation or existing normative register is changed by this decision proposal.
