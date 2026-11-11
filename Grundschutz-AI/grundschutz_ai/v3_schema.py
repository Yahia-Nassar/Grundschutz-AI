"""Frozen schema-3 physical layout. SQL is inert until explicit fresh creation."""
from types import MappingProxyType

from .v3_codec import PHYSICAL_PROFILE, canonical_dumps, fingerprint

TABLES = MappingProxyType({
    "store_metadata": """CREATE TABLE store_metadata (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1), store_uuid TEXT NOT NULL CHECK(length(store_uuid)=32 AND store_uuid NOT GLOB '*[^0-9a-f]*') UNIQUE,
    schema_version INTEGER NOT NULL CHECK(schema_version=3),
    event_codec TEXT NOT NULL CHECK(event_codec='ledger-event/v3'),
    serialization_version TEXT NOT NULL CHECK(serialization_version='canonical-json/v1'),
    feature_profile TEXT NOT NULL CHECK(feature_profile='verified-source/v1'),
    last_sequence INTEGER NOT NULL CHECK(last_sequence>=1), last_event_hash TEXT NOT NULL CHECK(length(last_event_hash)=64 AND last_event_hash NOT GLOB '*[^0-9a-f]*'),
    FOREIGN KEY(last_sequence,last_event_hash) REFERENCES events(sequence,event_sha256) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "content_blobs": """CREATE TABLE content_blobs (
    sha256 TEXT NOT NULL CHECK(length(sha256)=64 AND sha256 NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, byte_length INTEGER NOT NULL CHECK(byte_length>=0),
    content BLOB NOT NULL CHECK(length(content)=byte_length)
) STRICT""",
    "implementation_specs": """CREATE TABLE implementation_specs (
    implementation_hash TEXT NOT NULL CHECK(length(implementation_hash)=64 AND implementation_hash NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, descriptor_blob_sha256 TEXT NOT NULL CHECK(length(descriptor_blob_sha256)=64 AND descriptor_blob_sha256 NOT GLOB '*[^0-9a-f]*'),
    FOREIGN KEY(descriptor_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "reader_handler_specs": """CREATE TABLE reader_handler_specs (
    handler_spec_hash TEXT NOT NULL CHECK(length(handler_spec_hash)=64 AND handler_spec_hash NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, reader_spec_hash TEXT NOT NULL CHECK(length(reader_spec_hash)=64 AND reader_spec_hash NOT GLOB '*[^0-9a-f]*'),
    descriptor_blob_sha256 TEXT NOT NULL CHECK(length(descriptor_blob_sha256)=64 AND descriptor_blob_sha256 NOT GLOB '*[^0-9a-f]*'), registration_event INTEGER NOT NULL UNIQUE CHECK(registration_event>=1),
    UNIQUE(handler_spec_hash,reader_spec_hash),
    FOREIGN KEY(reader_spec_hash) REFERENCES implementation_specs(implementation_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(descriptor_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registration_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "policy_specs": """CREATE TABLE policy_specs (
    policy_spec_hash TEXT NOT NULL CHECK(length(policy_spec_hash)=64 AND policy_spec_hash NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, implementation_hash TEXT NOT NULL CHECK(length(implementation_hash)=64 AND implementation_hash NOT GLOB '*[^0-9a-f]*'), config_blob_sha256 TEXT NOT NULL CHECK(length(config_blob_sha256)=64 AND config_blob_sha256 NOT GLOB '*[^0-9a-f]*'),
    FOREIGN KEY(implementation_hash) REFERENCES implementation_specs(implementation_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(config_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "registries": """CREATE TABLE registries (
    registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('docx','xlsx')),
    session_id TEXT NOT NULL CHECK(length(session_id)=32 AND session_id NOT GLOB '*[^0-9a-f]*') UNIQUE, created_event INTEGER NOT NULL UNIQUE CHECK(created_event>=1),
    FOREIGN KEY(created_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "policy_activations": """CREATE TABLE policy_activations (
    registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*'), revision INTEGER NOT NULL CHECK(revision>=1),
    policy_spec_hash TEXT NOT NULL CHECK(length(policy_spec_hash)=64 AND policy_spec_hash NOT GLOB '*[^0-9a-f]*'), policy_fingerprint TEXT NOT NULL CHECK(length(policy_fingerprint)=64 AND policy_fingerprint NOT GLOB '*[^0-9a-f]*'),
    event_sequence INTEGER NOT NULL UNIQUE CHECK(event_sequence>=1), activated_at TEXT NOT NULL,
    PRIMARY KEY(registry_id,revision),
    FOREIGN KEY(registry_id) REFERENCES registries(registry_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(policy_spec_hash) REFERENCES policy_specs(policy_spec_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "logical_sources": """CREATE TABLE logical_sources (
    source_id TEXT PRIMARY KEY CHECK(length(CAST(source_id AS BLOB)) BETWEEN 1 AND 256),
    registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*'), kind TEXT NOT NULL CHECK(kind IN ('docx','xlsx')),
    created_event INTEGER NOT NULL UNIQUE CHECK(created_event>=1), UNIQUE(registry_id,source_id),
    FOREIGN KEY(registry_id) REFERENCES registries(registry_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(created_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "registrations": """CREATE TABLE registrations (
    registration_id TEXT NOT NULL CHECK(length(registration_id)=32 AND registration_id NOT GLOB '*[^0-9a-f]*') PRIMARY KEY,
    source_id TEXT NOT NULL CHECK(length(CAST(source_id AS BLOB)) BETWEEN 1 AND 256),
    registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*'), revision INTEGER NOT NULL CHECK(revision>=1),
    predecessor_registration_id TEXT CHECK(predecessor_registration_id IS NULL OR (length(predecessor_registration_id)=32 AND predecessor_registration_id NOT GLOB '*[^0-9a-f]*')), policy_revision INTEGER NOT NULL CHECK(policy_revision>=1),
    reader_spec_hash TEXT NOT NULL CHECK(length(reader_spec_hash)=64 AND reader_spec_hash NOT GLOB '*[^0-9a-f]*'), handler_spec_hash TEXT NOT NULL CHECK(length(handler_spec_hash)=64 AND handler_spec_hash NOT GLOB '*[^0-9a-f]*'),
    selection_json BLOB NOT NULL CHECK(length(selection_json) BETWEEN 4 AND 4096),
    start_event INTEGER NOT NULL UNIQUE CHECK(start_event>=1),
    CHECK((revision=1 AND predecessor_registration_id IS NULL) OR
          (revision>1 AND predecessor_registration_id IS NOT NULL AND predecessor_registration_id<>registration_id)),
    UNIQUE(source_id,revision), UNIQUE(source_id,revision,registration_id),
    UNIQUE(registration_id,registry_id,policy_revision,reader_spec_hash,handler_spec_hash),
    FOREIGN KEY(registry_id,source_id) REFERENCES logical_sources(registry_id,source_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(predecessor_registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registry_id,policy_revision) REFERENCES policy_activations(registry_id,revision) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(handler_spec_hash,reader_spec_hash) REFERENCES reader_handler_specs(handler_spec_hash,reader_spec_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(start_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "source_captures": """CREATE TABLE source_captures (
    registration_id TEXT NOT NULL CHECK(length(registration_id)=32 AND registration_id NOT GLOB '*[^0-9a-f]*') PRIMARY KEY,
    capture_event_sequence INTEGER NOT NULL UNIQUE CHECK(capture_event_sequence>=1),
    binary_sha256 TEXT NOT NULL CHECK(length(binary_sha256)=64 AND binary_sha256 NOT GLOB '*[^0-9a-f]*'), byte_length INTEGER NOT NULL CHECK(byte_length BETWEEN 0 AND 2097152),
    UNIQUE(registration_id,capture_event_sequence,binary_sha256),
    FOREIGN KEY(registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(capture_event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(binary_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "derivations": """CREATE TABLE derivations (
    derivation_sha256 TEXT NOT NULL CHECK(length(derivation_sha256)=64 AND derivation_sha256 NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, registration_id TEXT NOT NULL CHECK(length(registration_id)=32 AND registration_id NOT GLOB '*[^0-9a-f]*') UNIQUE, registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*'),
    kind TEXT NOT NULL CHECK(kind IN ('docx','xlsx')),
    capture_event_sequence INTEGER NOT NULL CHECK(capture_event_sequence>=1),
    binary_sha256 TEXT NOT NULL CHECK(length(binary_sha256)=64 AND binary_sha256 NOT GLOB '*[^0-9a-f]*'), byte_length INTEGER NOT NULL CHECK(byte_length BETWEEN 0 AND 2097152),
    reader_spec_hash TEXT NOT NULL CHECK(length(reader_spec_hash)=64 AND reader_spec_hash NOT GLOB '*[^0-9a-f]*'), handler_spec_hash TEXT NOT NULL CHECK(length(handler_spec_hash)=64 AND handler_spec_hash NOT GLOB '*[^0-9a-f]*'), policy_revision INTEGER NOT NULL CHECK(policy_revision>=1),
    policy_spec_hash TEXT NOT NULL CHECK(length(policy_spec_hash)=64 AND policy_spec_hash NOT GLOB '*[^0-9a-f]*'), policy_fingerprint TEXT NOT NULL CHECK(length(policy_fingerprint)=64 AND policy_fingerprint NOT GLOB '*[^0-9a-f]*'), reader_limits_sha256 TEXT NOT NULL CHECK(length(reader_limits_sha256)=64 AND reader_limits_sha256 NOT GLOB '*[^0-9a-f]*'),
    reader_method TEXT NOT NULL, reader_implementation_sha256 TEXT NOT NULL CHECK(length(reader_implementation_sha256)=64 AND reader_implementation_sha256 NOT GLOB '*[^0-9a-f]*'),
    native_text_sha256 TEXT NOT NULL CHECK(length(native_text_sha256)=64 AND native_text_sha256 NOT GLOB '*[^0-9a-f]*'), native_manifest_sha256 TEXT CHECK(native_manifest_sha256 IS NULL OR (length(native_manifest_sha256)=64 AND native_manifest_sha256 NOT GLOB '*[^0-9a-f]*')), integration_manifest_sha256 TEXT NOT NULL CHECK(length(integration_manifest_sha256)=64 AND integration_manifest_sha256 NOT GLOB '*[^0-9a-f]*'),
    derivation_blob_sha256 TEXT NOT NULL CHECK(length(derivation_blob_sha256)=64 AND derivation_blob_sha256 NOT GLOB '*[^0-9a-f]*'), validated_event_sequence INTEGER NOT NULL UNIQUE CHECK(validated_event_sequence>=1),
    CHECK((kind='docx' AND reader_method='docx-plain/v1' AND native_manifest_sha256 IS NULL) OR
          (kind='xlsx' AND reader_method='xlsx-literal/v1' AND native_manifest_sha256 IS NOT NULL)),
    UNIQUE(registration_id,derivation_sha256),
    FOREIGN KEY(registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registration_id,registry_id,policy_revision,reader_spec_hash,handler_spec_hash) REFERENCES registrations(registration_id,registry_id,policy_revision,reader_spec_hash,handler_spec_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registration_id,capture_event_sequence,binary_sha256) REFERENCES source_captures(registration_id,capture_event_sequence,binary_sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(reader_spec_hash) REFERENCES implementation_specs(implementation_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(handler_spec_hash) REFERENCES reader_handler_specs(handler_spec_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(policy_spec_hash) REFERENCES policy_specs(policy_spec_hash) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registry_id,policy_revision) REFERENCES policy_activations(registry_id,revision) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(native_text_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(native_manifest_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(integration_manifest_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(derivation_blob_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(validated_event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "source_terminals": """CREATE TABLE source_terminals (
    registration_id TEXT NOT NULL CHECK(length(registration_id)=32 AND registration_id NOT GLOB '*[^0-9a-f]*') PRIMARY KEY,
    terminal_event_sequence INTEGER NOT NULL UNIQUE CHECK(terminal_event_sequence>=1),
    state TEXT NOT NULL CHECK(state IN ('valid','failed')), derivation_sha256 TEXT CHECK(derivation_sha256 IS NULL OR (length(derivation_sha256)=64 AND derivation_sha256 NOT GLOB '*[^0-9a-f]*')),
    failure_phase TEXT CHECK(failure_phase IN ('capture','validation','environment','interrupted','capacity')),
    issue_json BLOB NOT NULL CHECK(length(issue_json) BETWEEN 2 AND 1024),
    CHECK((state='valid' AND derivation_sha256 IS NOT NULL AND failure_phase IS NULL AND issue_json=x'5b5d') OR
          (state='failed' AND derivation_sha256 IS NULL AND failure_phase IS NOT NULL AND length(issue_json)>2)),
    FOREIGN KEY(registration_id) REFERENCES registrations(registration_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registration_id,derivation_sha256) REFERENCES derivations(registration_id,derivation_sha256) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(terminal_event_sequence) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "source_heads": """CREATE TABLE source_heads (
    source_id TEXT PRIMARY KEY CHECK(length(CAST(source_id AS BLOB)) BETWEEN 1 AND 256),
    revision INTEGER NOT NULL CHECK(revision>=1), registration_id TEXT NOT NULL CHECK(length(registration_id)=32 AND registration_id NOT GLOB '*[^0-9a-f]*') UNIQUE,
    last_event INTEGER NOT NULL CHECK(last_event>=1),
    FOREIGN KEY(source_id,revision,registration_id) REFERENCES registrations(source_id,revision,registration_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(last_event) REFERENCES events(sequence) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "registry_state": """CREATE TABLE registry_state (
    registry_id TEXT NOT NULL CHECK(length(registry_id)=32 AND registry_id NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, policy_revision INTEGER NOT NULL CHECK(policy_revision>=1),
    epoch INTEGER NOT NULL CHECK(epoch>=1), history_units INTEGER NOT NULL CHECK(history_units>=0),
    exhausted INTEGER NOT NULL CHECK(exhausted IN (0,1)), retained_bytes INTEGER NOT NULL CHECK(retained_bytes>=0),
    retained_text_chars INTEGER NOT NULL CHECK(retained_text_chars>=0),
    retained_manifest_bytes INTEGER NOT NULL CHECK(retained_manifest_bytes>=0),
    derivation_count INTEGER NOT NULL CHECK(derivation_count>=0),
    FOREIGN KEY(registry_id) REFERENCES registries(registry_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(registry_id,policy_revision) REFERENCES policy_activations(registry_id,revision) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
    "events": """CREATE TABLE events (
    sequence INTEGER PRIMARY KEY CHECK(sequence>=1), event_id TEXT NOT NULL CHECK(length(event_id)=32 AND event_id NOT GLOB '*[^0-9a-f]*') UNIQUE, transaction_id TEXT NOT NULL CHECK(length(transaction_id)=32 AND transaction_id NOT GLOB '*[^0-9a-f]*') UNIQUE,
    transaction_index INTEGER NOT NULL CHECK(transaction_index=1),
    transaction_count INTEGER NOT NULL CHECK(transaction_count=1),
    kind TEXT NOT NULL, payload_codec TEXT NOT NULL, payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*'),
    previous_event_sha256 TEXT CHECK(previous_event_sha256 IS NULL OR (length(previous_event_sha256)=64 AND previous_event_sha256 NOT GLOB '*[^0-9a-f]*')), event_sha256 TEXT NOT NULL CHECK(length(event_sha256)=64 AND event_sha256 NOT GLOB '*[^0-9a-f]*') UNIQUE,
    occurred_at TEXT NOT NULL, actor_id TEXT CHECK(actor_id IS NULL OR length(CAST(actor_id AS BLOB)) BETWEEN 1 AND 256),
    envelope_json BLOB NOT NULL CHECK(length(envelope_json) BETWEEN 1 AND 8388608),
    CHECK((sequence=1 AND previous_event_sha256 IS NULL AND kind='store.initialized') OR
          (sequence>1 AND previous_event_sha256 IS NOT NULL AND kind<>'store.initialized')),
    CHECK((kind='store.initialized' AND payload_codec='store-init/v2') OR
          (kind='implementation.registered' AND payload_codec='implementation-register/v1') OR
          (kind='reader.handler_registered' AND payload_codec='reader-handler-register/v1') OR
          (kind='registry.created' AND payload_codec='registry-create/v1') OR
          (kind='policy.activated' AND payload_codec='policy-activate/v1') OR
          (kind='source.started' AND payload_codec='source-start/v2') OR
          (kind='source.captured' AND payload_codec='source-capture/v1') OR
          (kind='source.failed' AND payload_codec='source-fail/v2') OR
          (kind='source.validated' AND payload_codec='source-valid/v1') OR
          (kind='registry.exhausted' AND payload_codec='registry-exhaust/v1')),
    UNIQUE(sequence,event_sha256),
    FOREIGN KEY(payload_sha256) REFERENCES content_blobs(sha256) DEFERRABLE INITIALLY DEFERRED
) STRICT""",
})
MUTABLE = frozenset(("store_metadata", "source_heads", "registry_state"))
TRIGGERS = MappingProxyType({
    "content_blobs_no_update": "CREATE TRIGGER content_blobs_no_update BEFORE UPDATE ON content_blobs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "content_blobs_no_delete": "CREATE TRIGGER content_blobs_no_delete BEFORE DELETE ON content_blobs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "implementation_specs_no_update": "CREATE TRIGGER implementation_specs_no_update BEFORE UPDATE ON implementation_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "implementation_specs_no_delete": "CREATE TRIGGER implementation_specs_no_delete BEFORE DELETE ON implementation_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "reader_handler_specs_no_update": "CREATE TRIGGER reader_handler_specs_no_update BEFORE UPDATE ON reader_handler_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "reader_handler_specs_no_delete": "CREATE TRIGGER reader_handler_specs_no_delete BEFORE DELETE ON reader_handler_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "policy_specs_no_update": "CREATE TRIGGER policy_specs_no_update BEFORE UPDATE ON policy_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "policy_specs_no_delete": "CREATE TRIGGER policy_specs_no_delete BEFORE DELETE ON policy_specs BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "registries_no_update": "CREATE TRIGGER registries_no_update BEFORE UPDATE ON registries BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "registries_no_delete": "CREATE TRIGGER registries_no_delete BEFORE DELETE ON registries BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "policy_activations_no_update": "CREATE TRIGGER policy_activations_no_update BEFORE UPDATE ON policy_activations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "policy_activations_no_delete": "CREATE TRIGGER policy_activations_no_delete BEFORE DELETE ON policy_activations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "logical_sources_no_update": "CREATE TRIGGER logical_sources_no_update BEFORE UPDATE ON logical_sources BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "logical_sources_no_delete": "CREATE TRIGGER logical_sources_no_delete BEFORE DELETE ON logical_sources BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "registrations_no_update": "CREATE TRIGGER registrations_no_update BEFORE UPDATE ON registrations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "registrations_no_delete": "CREATE TRIGGER registrations_no_delete BEFORE DELETE ON registrations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "source_captures_no_update": "CREATE TRIGGER source_captures_no_update BEFORE UPDATE ON source_captures BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "source_captures_no_delete": "CREATE TRIGGER source_captures_no_delete BEFORE DELETE ON source_captures BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "derivations_no_update": "CREATE TRIGGER derivations_no_update BEFORE UPDATE ON derivations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "derivations_no_delete": "CREATE TRIGGER derivations_no_delete BEFORE DELETE ON derivations BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "source_terminals_no_update": "CREATE TRIGGER source_terminals_no_update BEFORE UPDATE ON source_terminals BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "source_terminals_no_delete": "CREATE TRIGGER source_terminals_no_delete BEFORE DELETE ON source_terminals BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "events_no_update": "CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
    "events_no_delete": "CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'immutable schema-3 history'); END",
})
STATEMENTS = tuple(TABLES.values()) + tuple(TRIGGERS.values())

# Frozen SQLite-generated UNIQUE/PK indexes, including their exact column order.
# No user CREATE INDEX statements exist; no sqlite_* object is silently ignored.
INDEX_CONTRACT = (
    ("content_blobs", "sqlite_autoindex_content_blobs_1", 1, "pk", 0, ("sha256",)),
    ("derivations", "sqlite_autoindex_derivations_1", 1, "pk", 0, ("derivation_sha256",)),
    ("derivations", "sqlite_autoindex_derivations_2", 1, "u", 0, ("registration_id",)),
    ("derivations", "sqlite_autoindex_derivations_3", 1, "u", 0, ("validated_event_sequence",)),
    ("derivations", "sqlite_autoindex_derivations_4", 1, "u", 0, ("registration_id", "derivation_sha256")),
    ("events", "sqlite_autoindex_events_1", 1, "u", 0, ("event_id",)),
    ("events", "sqlite_autoindex_events_2", 1, "u", 0, ("transaction_id",)),
    ("events", "sqlite_autoindex_events_3", 1, "u", 0, ("event_sha256",)),
    ("events", "sqlite_autoindex_events_4", 1, "u", 0, ("sequence", "event_sha256")),
    ("implementation_specs", "sqlite_autoindex_implementation_specs_1", 1, "pk", 0, ("implementation_hash",)),
    ("logical_sources", "sqlite_autoindex_logical_sources_1", 1, "pk", 0, ("source_id",)),
    ("logical_sources", "sqlite_autoindex_logical_sources_2", 1, "u", 0, ("created_event",)),
    ("logical_sources", "sqlite_autoindex_logical_sources_3", 1, "u", 0, ("registry_id", "source_id")),
    ("policy_activations", "sqlite_autoindex_policy_activations_1", 1, "u", 0, ("event_sequence",)),
    ("policy_activations", "sqlite_autoindex_policy_activations_2", 1, "pk", 0, ("registry_id", "revision")),
    ("policy_specs", "sqlite_autoindex_policy_specs_1", 1, "pk", 0, ("policy_spec_hash",)),
    ("reader_handler_specs", "sqlite_autoindex_reader_handler_specs_1", 1, "pk", 0, ("handler_spec_hash",)),
    ("reader_handler_specs", "sqlite_autoindex_reader_handler_specs_2", 1, "u", 0, ("registration_event",)),
    ("reader_handler_specs", "sqlite_autoindex_reader_handler_specs_3", 1, "u", 0, ("handler_spec_hash", "reader_spec_hash")),
    ("registrations", "sqlite_autoindex_registrations_1", 1, "pk", 0, ("registration_id",)),
    ("registrations", "sqlite_autoindex_registrations_2", 1, "u", 0, ("start_event",)),
    ("registrations", "sqlite_autoindex_registrations_3", 1, "u", 0, ("source_id", "revision")),
    ("registrations", "sqlite_autoindex_registrations_4", 1, "u", 0, ("source_id", "revision", "registration_id")),
    ("registrations", "sqlite_autoindex_registrations_5", 1, "u", 0, ("registration_id", "registry_id", "policy_revision", "reader_spec_hash", "handler_spec_hash")),
    ("registries", "sqlite_autoindex_registries_1", 1, "pk", 0, ("registry_id",)),
    ("registries", "sqlite_autoindex_registries_2", 1, "u", 0, ("session_id",)),
    ("registries", "sqlite_autoindex_registries_3", 1, "u", 0, ("created_event",)),
    ("registry_state", "sqlite_autoindex_registry_state_1", 1, "pk", 0, ("registry_id",)),
    ("source_captures", "sqlite_autoindex_source_captures_1", 1, "pk", 0, ("registration_id",)),
    ("source_captures", "sqlite_autoindex_source_captures_2", 1, "u", 0, ("capture_event_sequence",)),
    ("source_captures", "sqlite_autoindex_source_captures_3", 1, "u", 0, ("registration_id", "capture_event_sequence", "binary_sha256")),
    ("source_heads", "sqlite_autoindex_source_heads_1", 1, "pk", 0, ("source_id",)),
    ("source_heads", "sqlite_autoindex_source_heads_2", 1, "u", 0, ("registration_id",)),
    ("source_terminals", "sqlite_autoindex_source_terminals_1", 1, "pk", 0, ("registration_id",)),
    ("source_terminals", "sqlite_autoindex_source_terminals_2", 1, "u", 0, ("terminal_event_sequence",)),
    ("store_metadata", "sqlite_autoindex_store_metadata_1", 1, "u", 0, ("store_uuid",)),
)
SCHEMA_FINGERPRINT = "75aff3f9223ad7244702a6ef130c9382185f6957d72659c6ee43c2defa08c15c"


def expected_objects():
    return {**{name: ("table", sql) for name, sql in TABLES.items()},
            **{name: ("trigger", sql) for name, sql in TRIGGERS.items()},
            **{name: ("index", None) for _, name, _, _, _, _ in INDEX_CONTRACT}}


def expected_indexes():
    return [{"table": table, "name": name, "unique": unique, "origin": origin,
             "partial": partial, "columns": list(columns),
             "collations": ["BINARY"] * len(columns), "descending": [0] * len(columns)}
            for table, name, unique, origin, partial, columns in INDEX_CONTRACT]


def fingerprint_preimage():
    return {"physical_profile": PHYSICAL_PROFILE, "user_version": 3, "encoding": "UTF-8",
            "objects": [{"name": name, "kind": kind, "sql": sql}
                        for name, (kind, sql) in sorted(expected_objects().items())],
            "indexes": expected_indexes()}


def schema_fingerprint():
    return fingerprint("sqlite-schema/v3", fingerprint_preimage())
