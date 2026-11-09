# TASK-005 — Local SQLite persistence and trusted evidence reload

Date: 2026-11-09 (Europe/Bucharest). Baseline verified by read-only Git: `0d0c320` (`fix: strengthen inventory evidence support validation`), initially clean. Scope: standard-library, synthetic-only local persistence. No production readiness, tamper-proof auditing or verified BSI certification compliance is claimed.

## Files created

- `grundschutz_ai/storage.py`: versioned SQLite store, original-source BLOBs, transactional ordered actions, strict typed reconstruction, validated replay and explicit storage errors.
- `tests/test_storage.py`: 35 synthetic-only storage/round-trip/corruption/transaction/concurrency tests, all using temporary databases outside the repository.
- `docs/decisions/0004-sqlite-persistence.md`: design proposal, ordering contract, concurrency and security/migration limits.
- `docs/tasks/TASK-005-RESULTS.md`: this report and exact reproduction commands.

No existing domain, inventory, support, extraction, test, API configuration or normative files were modified. A wrapper that records actions when they occur preserves event order without changing the domain model. No dependencies, models, CPU/GPU settings, external services, real company documents, RAG, file ingestion or document generation were introduced. No automatic Git commit; TASK-006 was not started.

## Schema and store API

Schema version 1 is explicit in PRAGMA user_version and a single metadata row, which also records event-format version 1, support policy `inventory-affirmative/v1` and the last committed sequence. Unknown/mismatched versions are rejected with `UnsupportedStoreVersion`; unrelated databases are not overwritten.

| Table | Stored data / invariant |
|---|---|
| sources | `(source_id, sha256)` primary key; exact immutable UTF-8 source bytes as a BLOB. Every historical version needed for replay is retained. |
| events | Global contiguous sequence, `add`/`revise`/`review` operation, exact typed JSON payload, optional Evidence source ID/hash foreign key. |
| metadata | Schema/event/policy versions and last global sequence. Sequence metadata changes atomically with events. |

Append-only triggers refuse ordinary source/event updates and deletes. All source and payload data use SQL parameters. Stored source IDs, even path-looking or SQL-looking strings, remain data: they are never opened as files or used to construct paths. The one database pathname is trusted operator configuration. There is no external file ingestion or automatic default database path.

`InventoryStore(path)` creates or validates the explicitly selected local file. `add(record, source_text=...)`, `revise(record, source_text=...)`, `record_review(review)` and `commit(tuple[Write, ...])` validate through the existing Inventory APIs before committing. Evidence writes require the original source text explicitly because Evidence does not retain it. `read_source(source_id, sha256)` retrieves verified local text. `load()` rebuilds the current inventory, histories and approval/conflict state. Use the store as a context manager or call `close()`.

There is intentionally no `save(existing_inventory)` shortcut. Its separate record and review tuples cannot establish the original interleaving. Existing in-memory actions must be recorded through the store as they happen, or supplied as a known, explicitly ordered Write batch. Guessing an order from an opaque snapshot is not supported.

## Event order, evidence reload and approvals

The event-order regression persists this real sequence: add Evidence → add ITSystem → approve Evidence → approve ITSystem → revise Evidence. After close/reopen, the historical decisions remain in order, but the current system is unapproved because the evidence revision invalidates its fingerprint. Replaying records before reviews would either reject the formerly valid historical approvals or misrepresent their context; the store does neither.

Every load uses a read transaction to verify and replay one consistent database state. It verifies all source BLOB hashes, decodes strict UTF-8 without newline normalization, checks referenced versions and rejects orphan/missing source references. It reconstructs Evidence using its original constructor, which rechecks quote/Unicode-character offsets and recomputes affirmative support and quote boundaries under the current policy.

Stored payloads contain only constructor fields and an allowlisted record-type tag. Derived fields and original source copies are not hidden in event JSON: `relationship_support`, `quote_before`, `quote_after` and `source_text` are absent. Unexpected/cached fields are rejected rather than trusted. JSON parsing rejects malformed input, duplicate keys, nonstandard constants, wrong shapes and unknown types; nested enums, locators, timestamps and provenance are rebuilt as typed records. No arbitrary objects or classes are loaded.

ReviewRecords retain reviewer identifiers, offset-aware ISO timestamps, reasons and target fingerprints. Replaying an `approved` review calls `Inventory.record_review`; it must be valid at that exact event position, with current evidence/endpoints and the existing human-review rules. Final approval is recomputed with `approved_records()`, not loaded from a stored current-status flag. Unknown review states or an approved string without the required valid reviewer/context are rejected. SQLite does not authenticate the claimed reviewer identity.

Actual tests confirm:

- An unchanged approved six-record fixture reloads with its six explicit synthetic review decisions and the same fingerprints.
- Evidence updates remove dependent approvals after reload. Both old and new source versions remain available.
- Returning to the original source bytes at Evidence revision 3 leaves the evidence/system proposed, not approved, despite reusing the original BLOB. Source registration/revision history does not revert.
- Rejected/needs_clarification revisions remain blocked after reopening; fresh attempted approvals are refused without a corrective revision.
- Rostock/Berlin alternative locations remain unresolved; both edges and the system require clarification, and the derived location query refuses to choose.
- Replacing evidence with the known negative hosting statement reloads with no affirmative support and leaves the relationship clarification-required. Raw model Candidate objects/dictionaries and blocked provenance cannot be inserted into approved inventory.

## Transactions, failure behavior and concurrency

Schema initialization and writes use explicit transactions. Source insertion, event insertion and last-sequence updates either all commit or all roll back. Tests inject both a later domain-validation failure and an actual SQLite trigger failure after earlier rows have been inserted: no source, event or sequence residue remains. A failing batch on an already approved inventory leaves its prior data/reviews unchanged.

Foreign-key enforcement is enabled on the store connection and checked during replay. Source/event immutability triggers are exercised directly. Contiguous sequence/head checks detect dropped/interior/deleted-tail events. Malformed or inconsistent stored data stops load without returning a partially replayed Inventory. Callers must treat that failure as no verified current inventory; they must not silently use a cached old approved snapshot.

Writes use BEGIN IMMEDIATE with SQLite timeout 0. Another active writer produces `StoreBusyError` without committing anything. A later deliberate retry can succeed after the lock is released. Each write replays fresh database state under the lock, so a second connection cannot append an approval based on an outdated fingerprint. There is no automatic retry or multi-thread sharing of a connection.

## Actual tests and round-trip demonstration

Final full offline command:

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage -v
```

Observed: `Ran 154 tests in 1.027s`, `OK`: **154 passed, 0 failed, 0 skipped**. This retains all **119** prior offline tests and adds **35** storage tests. No model inference, package installation or network call was used. Existing optional live model tests were not run or reclassified as passing.

The first storage-only run exposed a test-harness Windows cleanup issue: a raw sqlite3 connection context commits/rolls back but does not close the handle. Test inspection connections now explicitly close through a context manager. Subsequent tests passed; the 25 verified task temporary directories left by that failed cleanup were removed after the process released its handles. No cleanup errors are suppressed.

An additional actual file-backed write/close/reopen/load demonstration produced:

```text
FICTITIOUS SQLite round-trip: SRV-001 ERP-01 Rechenzentrum Rostock
Records: 6 review events: 6 approved: 6
Exact source verified: True; reconstructed inventory equals original: True
SQLite runtime: 3.45.3
Temporary database removed: True
```

The six approvals above are explicit fictional human-review operations, not automatic approval of model output. The demonstration and all tests used temporary local files outside the repository and removed them after closing connections. No permanent production database was created.

Coverage includes all requested A–N cases: empty database; full synthetic inventory/source/relationships; globally interleaved revisions and reviews; valid approvals; stale source approvals; rejected claims; location conflicts; old-source reversion; missing/corrupt sources; quote/hash/offset checks; malformed payload/schema/policy versions; complete rollback; source-controlled path/SQL refusal; and blocked raw candidates. Additional tests verify exact UTF-8/CRLF/Unicode, invalid UTF-8 even with a matching hash, cache omission/recomputation, sequence deletion/reordering, append-only guards/FKs, concurrent writers, stale second-writer reviews, unrelated databases, missing source writes and unencodable metadata.

## Exact PowerShell reproduction

All offline tests: use the 154-test command above. Storage only:

```powershell
py -3.12 -m unittest tests.test_storage -v
```

Focused persisted interleaving, unchanged explicit approvals and full round-trip:

```powershell
py -3.12 -m unittest tests.test_storage.StorageTests.test_complete_round_trip_with_original_source_and_relationships tests.test_storage.StorageTests.test_explicit_approvals_survive_valid_round_trip tests.test_storage.StorageTests.test_interleaving_reviews_before_revision_is_preserved -v
```

Standalone temporary-file demonstration (run from the application directory):

```powershell
@'
from pathlib import Path
from tempfile import TemporaryDirectory
from grundschutz_ai.domain import Evidence
from grundschutz_ai.storage import InventoryStore
from tests.test_domain import SOURCE, evidence, review, synthetic_fixture

with TemporaryDirectory(prefix="grundschutz-ai-task005-demo-") as temporary:
    database = Path(temporary) / "roundtrip.sqlite3"
    with InventoryStore(database) as store:
        for record in synthetic_fixture().records:
            before = store.add(record, source_text=SOURCE if isinstance(record, Evidence) else None)
        for identifier in ("EVD-001", "APP-001", "LOC-001", "SYS-001", "REL-001", "REL-002"):
            before = store.record_review(review(before, identifier))
    with InventoryStore(database) as reopened:
        after = reopened.load()
        assert after == before
        assert reopened.read_source("synthetic:task-004", evidence().source_sha256) == SOURCE
        print(after.get("SYS-001").name, after.get("APP-001").name, after.get("LOC-001").name)
        print("Records:", len(after.records), "reviews:", len(after.review_history()), "approved:", len(after.approved_records()))
print("Temporary database removed:", not database.exists())
'@ | py -3.12 -
```

## Remaining security and architecture limitations

- This is plaintext local SQLite storage. Hashes/triggers/FKs detect many inconsistencies but do not authenticate reviewers/authors, encrypt sources, sign events or stop an attacker who can coherently rewrite the entire database and fingerprints. It is not tamper-proof auditing. Protect the configured local database, its directory and backups; authenticated source/review workflows remain outside this task.
- The explicitly supplied database path must be a trusted local operator choice outside Git. Source text/IDs cannot choose a path. Filesystem locality, access controls, network-share semantics, encryption and backup/restore permissions are not managed by this prototype.
- Full source verification and full replay happen on each write and load. This prioritizes understandable validation over scale and may use substantial memory/time on large histories. There is no incremental index, pagination, compaction, migration or production performance claim.
- Existing in-memory snapshots remain historical objects. Callers must load current state before current-data use; write operations independently validate fresh state. There is no notification service updating other processes' held snapshots.
- Schema/event/policy changes fail explicitly; there is no migration/repair path. A future migration must preserve action order and historical source versions without automatically restoring approvals. No old snapshot can be imported safely by guessing interleaving.
- Syntactic support remains deliberately narrow and does not prove real-world truth or discover unreferenced contradictions. Human review and authenticated source handling remain necessary. Applicable BSI requirements remain pending authoritative confirmation.

Next suggested action: human review of ADR-0004, the store API and corruption/concurrency tests before separately authorizing further work. TASK-006 was not started.

## Git verification

Initial read-only normal-user Git checks confirmed baseline `0d0c320` and a clean tree. Sandbox Git queries encounter the existing ownership guard; no ownership/Git/security setting was changed. Final file/status checks are recorded below. No staging or automatic commit was performed.

Final read-only Git inspection: HEAD remains `0d0c320`; no tracked-file modifications; exactly these four untracked additions. `git diff --check` passed for tracked files, and a separate standard-library whitespace check passed for all four additions. The final temporary-directory check found zero TASK-005 test/demo directories remaining. This status note was then added to the same report without changing implementation or creating an additional file.

```text
?? Grundschutz-AI/docs/decisions/0004-sqlite-persistence.md
?? Grundschutz-AI/docs/tasks/TASK-005-RESULTS.md
?? Grundschutz-AI/grundschutz_ai/storage.py
?? Grundschutz-AI/tests/test_storage.py
```
