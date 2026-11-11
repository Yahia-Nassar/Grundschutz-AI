"""Private native derivation construction and shared verification budgets.

No SQL, original paths, event append, cached observations or approval authority.
The frozen native bridge is the sole parser/manifest implementation.
"""
from dataclasses import dataclass
import math
import time

from . import v3_codec as c, v3_native as native, v3_native_catalog as catalog
from .v3_native_contract import ExecutionLimits, SheetSelection, NativeBridgeError
from ._v3_capture import LedgerLimitError, CorruptLedgerError


class VerificationBudget:
    """One absolute operation deadline; ten seconds per persistent context.

    Elapsed bridge work includes preflight/transport/cleanup, not just workers.
    Repeated complete replays share this object but NEVER native observations.
    """
    def __init__(self, deadline):
        self.deadline = deadline
        self.spent = {}

    def check(self):
        if time.monotonic() >= self.deadline:
            raise LedgerLimitError("Native ledger cumulative deadline exceeded")

    @staticmethod
    def context(store_uuid, registration, policy):
        return (store_uuid, registration.registry_id, registration.ref,
                registration.capture_event_sequence, registration.handler_spec_hash,
                policy.revision, policy.spec.sha256)

    def charge_derivation(self, store_uuid, registration, policy, started):
        key = self.context(store_uuid, registration, policy)
        self.spent[key] += time.monotonic() - started
        self.check()
        if self.spent[key] >= 10:
            raise LedgerLimitError("Native document derivation allowance exhausted")

    def extract(self, store_uuid, registration, policy, raw):
        self.check()
        key = self.context(store_uuid, registration, policy)
        started = time.monotonic()
        seconds = math.floor(min(10 - self.spent.get(key, 0), self.deadline - started))
        if seconds < 1:
            raise LedgerLimitError("Native document cumulative allowance exhausted")
        profile = catalog.select_handler(registration.handler_spec_hash)
        # The bridge checks availability too; these checks bind timeout classification.
        catalog.verify_available(profile)
        try:
            selection = c.canonical_loads(registration.selection_json)
            result = native.extract_captured_bytes(raw, source_id=registration.ref.source_id,
                handler_sha256=registration.handler_spec_hash,
                reader_spec_sha256=registration.reader_spec_hash, policy_spec=policy.spec,
                expected_sha256=registration.binary_sha256, expected_length=registration.byte_length,
                selection=None if selection is None else SheetSelection(**selection),
                execution_limits=ExecutionLimits(max_seconds=seconds))
        except NativeBridgeError:
            # Frozen bridge cleanup failures override worker_timeout. A surviving
            # timeout code therefore means cleanup completed; verify trust again.
            catalog.verify_available(profile)
            self.check()
            raise
        finally:
            elapsed = time.monotonic() - started
            self.spent[key] = self.spent.get(key, 0) + elapsed
        self.check()
        if elapsed >= seconds or self.spent[key] >= 10:
            raise LedgerLimitError("Late native result refused")
        return result


@dataclass(frozen=True, slots=True)
class DerivedContent:
    reference: c.DerivationRef
    text: bytes
    native_manifest: bytes | None
    integration: bytes

    @property
    def blobs(self):
        return (self.text, self.integration, self.reference.canonical) + (
            () if self.native_manifest is None else (self.native_manifest,))


def derive(store_uuid, registration, policy, raw, budget):
    """Every call executes both pinned native worker passes; no result cache."""
    result = budget.extract(store_uuid, registration, policy, raw)
    started = time.monotonic()
    if (type(result) is not native.VerifiedNativeExtraction or result.original_bytes != raw or
            result.source_id != registration.ref.source_id or result.policy_spec != policy.spec or
            result.handler_spec.sha256 != registration.handler_spec_hash):
        raise CorruptLedgerError("Native derivation context mismatch")
    text = result.native.text.encode("utf-8", errors="strict")
    cfg = policy.spec.data()["config"]
    reference = c.DerivationRef(c.canonical_dumps(dict(type="derivation-ref/v2",
        store_uuid=store_uuid, registry_id=registration.registry_id, registration=registration.ref.data(),
        kind=registration.kind, capture_event_sequence=registration.capture_event_sequence,
        binary_sha256=registration.binary_sha256, byte_length=registration.byte_length,
        reader_spec_hash=registration.reader_spec_hash, handler_spec_hash=registration.handler_spec_hash,
        policy_revision=registration.policy_revision, policy_spec_hash=policy.spec.sha256,
        policy_fingerprint=policy.policy_fingerprint,
        reader_limits_sha256=c.fingerprint("reader-limits/v1", cfg["reader_limits"]),
        reader_method=result.native.method, reader_implementation_sha256=result.reader_implementation_sha256,
        native_text_sha256=c.sha256(text), native_manifest_sha256=result.native_manifest_sha256,
        integration_manifest_sha256=result.integration_manifest_sha256)))
    budget.charge_derivation(store_uuid, registration, policy, started)
    return DerivedContent(reference, text, result.native_manifest, result.integration_manifest)


def derivation_row(reference, event_sequence):
    d = reference.data()
    names = ("registry_id kind capture_event_sequence binary_sha256 byte_length reader_spec_hash "
        "handler_spec_hash policy_revision policy_spec_hash policy_fingerprint reader_limits_sha256 "
        "reader_method reader_implementation_sha256 native_text_sha256 native_manifest_sha256 "
        "integration_manifest_sha256").split()
    return (reference.sha256, d["registration"]["registration_id"], *(d[name] for name in names),
            reference.blob_sha256, event_sequence)


def retention(replay, registration, derived):
    """All-history role accounting, distinct even for one shared physical BLOB."""
    rid = registration.registry_id
    data = derived.reference.data()
    text_key = data["native_text_sha256"]
    text_chars = replay.registries[rid].retained_text_chars
    if text_key not in replay.reg_text[rid]:
        text_chars += len(derived.text.decode("utf-8", errors="strict"))
    manifest_bytes = replay.registries[rid].retained_manifest_bytes
    for role, raw in (("native", derived.native_manifest), ("integration", derived.integration)):
        if raw is not None and c.sha256(raw) not in replay.reg_manifests[rid, role]:
            manifest_bytes += len(raw)
    return text_chars, manifest_bytes
