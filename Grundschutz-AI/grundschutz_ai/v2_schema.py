"""Fixed A-only schema 2. No reserved B--E tables or activation flags."""

TABLES = {
    "store_metadata": """CREATE TABLE store_metadata (
        singleton INTEGER PRIMARY KEY CHECK(singleton=1), store_uuid TEXT NOT NULL UNIQUE,
        schema_version INTEGER NOT NULL CHECK(schema_version=2), event_codec TEXT NOT NULL,
        serialization_version TEXT NOT NULL, feature_profile TEXT NOT NULL CHECK(feature_profile='staging_only'),
        last_sequence INTEGER NOT NULL CHECK(last_sequence>=1), last_event_hash TEXT NOT NULL
    ) STRICT""",
    "content_blobs": """CREATE TABLE content_blobs (
        sha256 TEXT PRIMARY KEY, byte_length INTEGER NOT NULL CHECK(byte_length>=0), content BLOB NOT NULL,
        CHECK(length(content)=byte_length)
    ) STRICT""",
    "implementation_specs": """CREATE TABLE implementation_specs (
        implementation_hash TEXT PRIMARY KEY, descriptor_blob_sha256 TEXT NOT NULL,
        FOREIGN KEY(descriptor_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "policy_specs": """CREATE TABLE policy_specs (
        policy_spec_hash TEXT PRIMARY KEY, implementation_hash TEXT NOT NULL, config_blob_sha256 TEXT NOT NULL,
        FOREIGN KEY(implementation_hash) REFERENCES implementation_specs(implementation_hash) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(config_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "registries": """CREATE TABLE registries (
        registry_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('docx','xlsx')),
        session_id TEXT NOT NULL UNIQUE, created_event INTEGER NOT NULL UNIQUE,
        FOREIGN KEY(created_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "policy_activations": """CREATE TABLE policy_activations (
        registry_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>=1), policy_spec_hash TEXT NOT NULL,
        policy_fingerprint TEXT NOT NULL, event_sequence INTEGER NOT NULL UNIQUE, activated_at TEXT NOT NULL,
        PRIMARY KEY(registry_id,revision),
        FOREIGN KEY(registry_id) REFERENCES registries(registry_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(policy_spec_hash) REFERENCES policy_specs(policy_spec_hash) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "logical_sources": """CREATE TABLE logical_sources (
        source_id TEXT PRIMARY KEY, registry_id TEXT NOT NULL, kind TEXT NOT NULL,
        created_event INTEGER NOT NULL UNIQUE, UNIQUE(registry_id,source_id),
        FOREIGN KEY(registry_id) REFERENCES registries(registry_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(created_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "registrations": """CREATE TABLE registrations (
        registration_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, registry_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>=1), predecessor_registration_id TEXT,
        policy_revision INTEGER NOT NULL, reader_spec_hash TEXT NOT NULL, selection_json BLOB NOT NULL,
        start_event INTEGER NOT NULL UNIQUE,
        UNIQUE(source_id,revision), UNIQUE(source_id,revision,registration_id),
        FOREIGN KEY(registry_id,source_id) REFERENCES logical_sources(registry_id,source_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(predecessor_registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(registry_id,policy_revision) REFERENCES policy_activations(registry_id,revision) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(reader_spec_hash) REFERENCES implementation_specs(implementation_hash) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(start_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "registration_observations": """CREATE TABLE registration_observations (
        event_sequence INTEGER PRIMARY KEY, registration_id TEXT NOT NULL,
        observation TEXT NOT NULL CHECK(observation IN ('pending','captured','failed')),
        blob_sha256 TEXT, issue_json BLOB NOT NULL,
        UNIQUE(registration_id,observation),
        FOREIGN KEY(event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "source_heads": """CREATE TABLE source_heads (
        source_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, registration_id TEXT NOT NULL UNIQUE,
        last_event INTEGER NOT NULL,
        FOREIGN KEY(source_id,revision,registration_id) REFERENCES registrations(source_id,revision,registration_id) DEFERRABLE INITIALLY DEFERRED,
        FOREIGN KEY(last_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "registry_state": """CREATE TABLE registry_state (
        registry_id TEXT PRIMARY KEY, policy_revision INTEGER NOT NULL, epoch INTEGER NOT NULL CHECK(epoch>=1),
        history_units INTEGER NOT NULL CHECK(history_units>=0), exhausted INTEGER NOT NULL CHECK(exhausted IN (0,1)),
        retained_bytes INTEGER NOT NULL CHECK(retained_bytes>=0),
        FOREIGN KEY(registry_id,policy_revision) REFERENCES policy_activations(registry_id,revision) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
    "events": """CREATE TABLE events (
        sequence INTEGER PRIMARY KEY CHECK(sequence>=1), event_id TEXT NOT NULL UNIQUE,
        transaction_id TEXT NOT NULL UNIQUE, transaction_index INTEGER NOT NULL CHECK(transaction_index=1),
        transaction_count INTEGER NOT NULL CHECK(transaction_count=1), kind TEXT NOT NULL, payload_codec TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL, previous_event_sha256 TEXT, event_sha256 TEXT NOT NULL UNIQUE,
        occurred_at TEXT NOT NULL, actor_id TEXT, envelope_json BLOB NOT NULL,
        FOREIGN KEY(payload_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
    ) STRICT""",
}

MUTABLE = frozenset(("store_metadata", "source_heads", "registry_state"))
TRIGGERS = {
    f"{table}_no_{operation.lower()}":
        f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
        "BEGIN SELECT RAISE(ABORT, 'immutable ledger history'); END"
    for table in TABLES if table not in MUTABLE for operation in ("UPDATE", "DELETE")
}
STATEMENTS = tuple(TABLES.values()) + tuple(TRIGGERS.values())


def expected_objects():
    return {**{name: ("table", sql) for name, sql in TABLES.items()},
            **{name: ("trigger", sql) for name, sql in TRIGGERS.items()}}
