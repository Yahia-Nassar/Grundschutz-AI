# ADR-0004: Local SQLite action log and verified evidence reload

**Status:** Proposed for human review; implemented for synthetic TASK-005 only.

## Decision

Use standard-library sqlite3 and a small `InventoryStore` wrapper around the existing immutable Inventory API. Existing domain, inventory, support and extraction code is unchanged. Call `add`, `revise`, or `record_review` on the store as each action occurs; `commit(tuple[Write, ...])` supports an explicitly ordered atomic batch. There is no snapshot-save/import API that infers event order from separate record/review histories.

The database path is explicit trusted operator configuration, intended for a local directory outside Git. Source IDs/text are parameterized SQL values and never filesystem paths. Sources are supplied as synthetic text strings, not imported files. UTF-8 encoding is strict, with no text/line-ending normalization.

## Schema version 1

| Table | Purpose |
|---|---|
| metadata | Single row containing schema version, event-format version, support-policy version and last committed global sequence. PRAGMA user_version also identifies schema version 1. |
| sources | Immutable `(source_id, sha256)` primary key and exact UTF-8 source BLOB. All historical versions referenced by events are retained. |
| events | One global integer sequence, operation (`add`, `revise`, `review`), strict typed JSON payload and nullable composite source reference. Evidence events reference sources through a foreign key. |

Ordinary updates/deletes to sources/events are blocked by append-only triggers. Metadata's last sequence changes only within the action transaction. Normal source deduplication reuses identical bytes for the same source ID/hash; every evidence revision still gets its own action, so reverting to earlier bytes cannot restore an old registration/review automatically.

Schema creation and all action writes are transactional. Domain validation precedes each event insert. A failed batch rolls back its new sources, events and sequence metadata together. Foreign keys are enabled and checked. Static schema SQL and parameterized data queries avoid source-controlled SQL. No executescript transaction shortcuts, pickle, eval, exec or arbitrary-class deserialization are used.

## Ordered replay and approval

Load runs in a read transaction. It checks schema/policy compatibility, sequence/count integrity, source references and all source bytes. It verifies SHA-256 before strict UTF-8 decoding. Evidence is reconstructed through its validated constructor with the original source string, rechecking quote character offsets and recomputing boundary/affirmative support. Derived caches (`relationship_support`, `quote_before`, `quote_after`) are omitted from payloads, not trusted on reload.

Events replay in global sequence through `Inventory.add`, `revise` and `record_review`. Reviews keep their IDs, reviewer IDs, offset-aware timestamps, reasons and exact target fingerprints. A stored `approved` string is only a proposed historical action to validate, never an independent current-state flag. `approved_records()` and conflict states are recomputed from the resulting Inventory.

Records must not all replay before reviews: a review made before an evidence revision must validate against the earlier intermediate inventory. Reordering events, losing source versions or changing a historical review target causes load failure. Missing/corrupt/unsupported data yields no partially verified inventory and no fallback to cached approvals.

## Concurrent writers and lifecycle

Each write obtains BEGIN IMMEDIATE with a zero SQLite busy timeout, then replays fresh committed state before validating new actions. Writers either execute serially or receive `StoreBusyError` without a partial commit. Callers must reload and make a deliberate retry; no automatic retry can reuse an outdated approval token. A stale review fails the unchanged Inventory fingerprint checks.

Use one store connection per thread and close it explicitly or with its context manager. Reads use a consistent transaction. Full replay is intentionally simple and suited only to small synthetic histories; it is not an indexed, incremental production read model. Retain only local database paths supplied by trusted application configuration, not user documents or model responses. SQLite URIs and in-memory aliases are refused by this file-backed prototype.

## Security and migration limits

SQLite locks, foreign keys, hashes and triggers provide useful consistency checks; they do not authenticate a human reviewer, authenticate a source author, encrypt the database, sign events or protect against someone who can rewrite the whole database coherently. Filesystem access control, authenticated review, trusted source registration, protected backups and key/signature management remain future work. Opening an arbitrary hostile database is outside the intended operator-controlled local store boundary.

Unexpected schema/event/support-policy versions are refused explicitly. No automatic schema migration, approval migration, snapshot import, history compaction or repair is implemented. Changes to support/domain fingerprint rules need a separately reviewed migration/revalidation design. Consumers must use a freshly loaded current inventory; old immutable snapshots remain historical snapshots. Load failure must block current approved-data use rather than silently falling back to an old snapshot.

All task databases are temporary, outside the checkout, and removed after connection close. No permanent production database is created. No BSI baseline or certification interpretation is changed by this engineering decision.
