# TASK-004 — A.1 structured data model

Date: 2026-11-09 (Europe/Bucharest). Baseline confirmed by read-only Git: `c6f7a56` (`fix: enforce fail-closed extraction validation`), with a clean initial working tree. Scope: standard-library domain modeling and synthetic offline tests. No BSI baseline approval, production-readiness or certification claim is made.

## Files created

- `grundschutz_ai/domain.py`: frozen/slotted ITSystem, ITApplication, Location, Evidence, Relationship and ReviewRecord records; typed SourceLocator/Provenance; the four review states; two supported predicates; validation and internal fingerprints.
- `grundschutz_ai/inventory.py`: immutable inventory snapshots, unique identifiers, reference validation, version histories, dependency-bound reviews, derived system links and conflict handling.
- `tests/test_domain.py`: the explicitly fictitious fixture and 41 domain/inventory tests.
- `docs/tasks/TASK-004-RESULTS.md`: this report, limitations and reproduction commands.
- `docs/decisions/0003-domain-inventory.md`: small additional file required by AGENTS.md to record the proposed relationship/review design. These are engineering choices, not new BSI interpretations.

Existing extraction modules, tests, prompts and requirements/gate documents were not edited. No dependencies, models, network inference, database, RAG, document ingestion or document generation were introduced. No automatic commit or TASK-005 execution.

## Domain and relationship design

All records are immutable typed dataclasses, including their tuples of references and provenance. Required strings cannot be blank; revisions are positive integers; IDs use stable type prefixes. Plain strings are not accepted in place of ReviewState/Predicate enum values. Unknown states/predicates, duplicate evidence references and mutable lists of references are rejected.

| Type | Data and invariants |
|---|---|
| ITSystem | Stable `SYS-...` ID, name/asset identifier, optional description, evidence references and revision. Location/application references are read through the inventory's relationship queries. |
| ITApplication | Stable `APP-...` ID, application name/identifier, optional description, evidence references and revision. |
| Location | Stable `LOC-...` ID, full name, optional location type/description, evidence references and revision. No location-name shortening or normalization is performed. |
| Evidence | Stable `EVD-...` ID, source ID/SHA-256, exact quote, character locator, typed provenance and revision. Construction requires the original synthetic source to verify both its hash and quote at the exact locator; that source text is an InitVar and is not retained in the record. |
| Relationship | Stable `REL-...` ID, typed `hosts` (ITSystem → ITApplication) or `located_at` (ITSystem → Location), supporting evidence IDs and revision. Endpoint references must exist and have the correct types. |
| ReviewRecord | Unique `REV-...` ID, target ID, target/dependency fingerprint, one of the four states, reviewer ID when applicable, timezone-aware timestamp and reason. Approval/rejection requires a nonempty reviewer identifier. |

Evidence locators use zero-based, half-open Unicode character offsets, not bytes or inferred page numbers. Source hashes use UTF-8 SHA-256. Provenance records extraction method, candidate ID, candidate-revision SHA-256, original candidate state and extraction timestamp. This initial API requires those values explicitly; it does not invent provenance or derive it from a model's approval claim.

Inventory is the referential-integrity boundary: standalone dataclasses validate their shapes, while `add`/`revise` validate references against that snapshot. Entity names must occur in referenced evidence; relationship evidence must include both endpoint names in at least one quote. Those conservative literal checks do not prove predicate semantics, full physical-location interpretation, descriptions or real-world truth; a qualified human must review them.

ITSystem deliberately has no second writable `location_id` or applications list. `Inventory.location_id(system_id)` and `application_ids(system_id)` derive the references from the canonical relationships. These queries include proposals and are not approved-data exports. `approved_records()` separately filters current reviewed data and dependencies. Duplicate subject/predicate/object triples are rejected; add another evidence ID to a revised existing relationship instead.

An approved entity does not implicitly approve its relationships. A future consumer must join approved entities through separately approved relationship records and must not use the proposal queries to export approved facts.

## Evidence and human approval

`add`, `revise` and `record_review` return new Inventory snapshots. Existing snapshots and historical record/review tuples remain unchanged. Record revisions must increase by exactly one, IDs cannot be reused, and new reviews cannot have timestamps preceding the latest recorded review. There is no deletion/overwrite operation or public snapshot constructor accepting review history.

All new records start unapproved. The application computes `revision_digest(target_id)` over target data and its current evidence/provenance/source versions. Relationships also bind endpoint data/evidence. System fingerprints also bind outgoing relationship records and object data/evidence, so adding a new location/application claim invalidates the previous system approval. Review decisions are not included recursively in hashes; their current validity is checked separately.

A new ReviewRecord must match the current fingerprint exactly. For approval, supporting evidence must already be explicitly approved; relationships additionally require approved endpoints. Names/support are revalidated against current evidence at approval, not just initial insertion. Current unresolved location conflicts or stale sources prevent approval. Rejection/clarification of the exact current target revision cannot be cleared by appending `proposed` or `approved`: revise the data/evidence first, then obtain a new human decision. Revoked evidence removes dependent objects/relationships from the approved view while preserving earlier decisions.

Evidence with model/candidate provenance `needs_clarification`, `rejected` or `approved` is refused at the inventory boundary: only a validated proposal is admissible, and human approval is a separate ReviewRecord. Raw extractor Candidate objects and field dictionaries are refused regardless of their state. There is intentionally no extraction-to-domain adapter or string/dictionary deserializer that could smuggle an approval into inventory. The domain/inventory modules do not import the Ollama client or extraction implementation.

Source changes must be registered explicitly through new/revised Evidence. The most recently registered evidence for a source ID defines its currently known content revision. Fingerprints bind both the current source hash and its registration ID/revision. Registering a new revision therefore invalidates prior bindings, even if a later registration returns to the same bytes. This is deliberately conservative: even another registration of identical content can require fresh review. Sources are not watched on disk.

## Multiple and contradictory evidence

Multiple sources are separate Evidence IDs with original source identifiers, hashes, locators and provenance. An object or relationship may reference several. Claims are not merged by a model or silently overwritten by the newest source.

Different unrejected `located_at` claims for the same system preserve both alternatives and mark the system/edges `needs_clarification`. `location_id` refuses to choose a location. Explicitly rejecting an alternative resolves that cardinality conflict without deleting the rejected record, evidence or review. The surviving alternative is not automatically approved. Multiple hosted applications are allowed.

The one-location conflict rule is an initial engineering assumption documented in ADR-0003. It is not a verified BSI requirement or a complete model for movable, virtual or grouped systems. Future work must add temporal validity, field-level claims and richer conflict reasons. Arbitrary semantic contradictions inside prose or descriptions are not automatically detected; a human must record clarification/rejection and a future reviewed adapter must expose all conflicting candidates.

## Fictitious fixture

`tests.test_domain.synthetic_fixture()` creates the requested objects and relationships, all proposed:

| ID | Fictitious value / reference |
|---|---|
| SYS-001 | SRV-001 |
| APP-001 | ERP-01 |
| LOC-001 | Rechenzentrum Rostock |
| EVD-001 | Source `synthetic:task-004`, labelled `FIKTIVES TESTBEISPIEL` in the fixture source, with the exact supporting synthetic German sentence, hash, character locator and synthetic provenance. |
| REL-001 | SYS-001 `hosts` APP-001; EVD-001 |
| REL-002 | SYS-001 `located_at` LOC-001; EVD-001 |

The literal source label is `FIKTIVES TESTBEISPIEL — keine reale Infrastruktur.`. Fixture timestamps and reviewer identities are explicitly synthetic test data, not claimed real audit events. `approved_fixture()` is a test helper that invokes explicit fictional human-review operations in dependency order; it is not a production automatic-approval path.

## Tests executed

Final offline command:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests -v
```

Observed: `Ran 99 tests in 0.151s`, `OK`; **99 passed, 0 failed, 0 skipped**. This includes **41 domain/inventory tests and all 58 existing offline extraction tests**. The existing fail-closed source validation remains intact.

An earlier discovery run, before the final two approval-regression tests were added, also passed: `Ran 102 tests in 0.120s`, `OK (skipped=5)` (97 offline passes and five optional live skips). The final command above includes both added regressions. No live Ollama test was run for TASK-004: it changes no inference code and requires offline acceptance. The historical strict injection-quality failure remains documented in TASK-003 results and has not been reclassified as passing.

Tests cover valid records, frozen data/snapshots, bad field types/IDs/revisions, duplicate IDs/triples, missing/unrelated evidence, invalid endpoints, unsupported states/predicates, reviewer/reason/timestamp requirements, preserved review history, source quote/hash/locator verification, raw/blocked candidate rejection, stale data/source/candidate reviews, source updates through other evidence IDs, source-content reversion, evidence revocation, support rechecking before reapproval, explicit new review after a blocked revision, location conflicts/resolution and multiple hosted applications.

JSON snapshot serialization/deserialization is deliberately not supported in this task, so no round-trip acceptance is claimed. Canonical JSON is used internally only for fingerprints; it is not an approval import format.

To rerun only the new domain tests:

```powershell
py -3.12 -m unittest tests.test_domain -v
```

To use full discovery with optional live tests disabled:

```powershell
Remove-Item Env:GRUNDSCHUTZ_RUN_INTEGRATION -ErrorAction SilentlyContinue
py -3.12 -m unittest discover -s tests -v
```

## Remaining risks and limits

- Trusted application code supplies candidate provenance and reviewer identities. Enum/record checks do not authenticate a human, sign a review, prove the candidate digest came from a validator, or defend against malicious Python code rewriting private state. There is no model adapter in this task; future integration must rerun extraction validation and establish trustworthy provenance before constructing records. Copying diagnostic fields into a newly forged proposal is not an authorized workflow.
- Every consumer must use the latest inventory snapshot and approved view. Old immutable snapshots intentionally retain historical decisions; they are not a durable shared current-state authority. A future application must implement authenticated review, durable transactional storage and controlled snapshot/version access.
- Source text is verified during Evidence construction but not retained here. The future evidence store must preserve permissioned source versions for reinspection. External source changes and candidate status changes that have not been registered are unknown to this in-memory inventory.
- Literal quote occurrence and endpoint-name checks do not establish full semantics, validate every description, infer complete German locations from arbitrary prose, deduplicate aliases, or prove factual truth. Human domain review remains necessary. This is an initial subset of A.1 entities, not the full eight-section output schema.
- Conflict handling initially covers alternative `located_at` edges. Broader time-dependent, field-level and linguistic contradictions need a separately reviewed design. No document generation, approved-data export format or JSON snapshot loader exists yet.
- This prototype is not production-ready, and applicable BSI certification requirements remain pending authoritative confirmation. No BSI baseline was changed and TASK-005 was not started.

Next suggested action: human review of ADR-0003, the evidence/review API and its immutable revision behavior before authorizing a subsequent task.

## Git checks

Initial read-only normal-user checks confirmed the supplied baseline `c6f7a56` and a clean working tree. Sandbox Git queries encounter the existing ownership guard; normal-user read-only verification is used without changing Git/security settings. No automatic staging or commit. Final file status/checks are recorded below.

Final read-only verification: HEAD remains `c6f7a56`; no tracked modifications; exactly the following five untracked additions. `git diff --check` passed for tracked files; the separate standard-library whitespace check passed for all five additions. Code/text changes were reviewed. The fixture smoke check confirmed derived location `LOC-001`, applications `('APP-001',)` and zero initially approved records. This status note and query docstrings were then added to the same files without changing behavior or creating another file.

```text
?? Grundschutz-AI/docs/decisions/0003-domain-inventory.md
?? Grundschutz-AI/docs/tasks/TASK-004-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/domain.py
?? Grundschutz-AI/grundschutz_ai/inventory.py
?? Grundschutz-AI/tests/test_domain.py
```
