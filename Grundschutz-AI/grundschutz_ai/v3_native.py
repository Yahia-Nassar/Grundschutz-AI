"""Nonpersistent captured-byte native bridge; no source states or SQL API."""
from dataclasses import asdict
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from . import v2_codec as c, v2_a0 as a0
from .v3_native_catalog import select_handler, verify_available
from .v3_native_contract import (
    NativeBridgeError, ExecutionLimits, DEFAULT_EXECUTION_LIMITS, SheetSelection,
    VerifiedNativeExtraction, need, wire_load, wire_dump, frame, read_frame,
    context_policy, checked_transport, materialize,
)

__all__ = ("extract_captured_bytes", "NativeBridgeError", "ExecutionLimits",
           "SheetSelection", "VerifiedNativeExtraction")


def _worker(folder, operation, metadata, raw, candidate, limits, deadline):
    """One pinned child; bounded pipe readers, cumulative parent deadline."""
    need(time.monotonic() < deadline, "worker_timeout")
    command = [sys.executable, "-I", "-B", str(Path(__file__).with_name("v3_native_worker.py").resolve()),
               "--transport", str(folder), "--operation", operation]
    environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP")
                   if key in os.environ}
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             shell=False, cwd=folder, env=environment,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    result, errors = [], []
    failed = threading.Event()

    def writer():
        try:
            for value, maximum in ((metadata, limits.max_metadata_bytes), (raw, limits.max_input_bytes)):
                child.stdin.write(frame(value, maximum))
            if operation == "verify":
                child.stdin.write(frame(candidate, limits.max_output_bytes))
            child.stdin.close()
        except Exception:
            errors.append("worker_input")
            failed.set()

    def reader():
        try:
            result.append(read_frame(child.stdout, limits.max_output_bytes))
            need(child.stdout.read(1) == b"", "trailing_output")
        except Exception:
            errors.append("worker_protocol")
            failed.set()

    def stderr():
        try:
            if child.stderr.read(limits.max_stderr_bytes + 1):
                errors.append("worker_stderr")
                failed.set()
        except Exception:
            errors.append("worker_protocol")
            failed.set()

    threads = [threading.Thread(target=target, daemon=True) for target in (writer, reader, stderr)]
    try:
        for thread in threads:
            thread.start()
        while child.poll() is None or any(thread.is_alive() for thread in threads):
            need(not failed.is_set(), errors[0] if errors else "worker_protocol")
            need(time.monotonic() < deadline, "worker_timeout")
            failed.wait(min(0.01, max(0, deadline - time.monotonic())))
        need(child.returncode == 0 and not errors and len(result) == 1, "worker_failed")
        return result[0]
    finally:
        if child.poll() is None:
            child.kill()
        # Termination/reaping is always attempted before transport cleanup. A
        # separate two-second cleanup grace cannot authorize a late result.
        try:
            child.wait(timeout=2)
        finally:
            for thread in threads:
                if thread.ident is not None:
                    thread.join(timeout=0.1)
            for stream in (child.stdin, child.stdout, child.stderr):
                stream.close()


def _identity(path):
    meta = path.lstat()
    need(not stat.S_ISLNK(meta.st_mode) and not getattr(meta, "st_file_attributes", 0) & 1024,
         "unsafe_transport")
    return meta.st_dev, meta.st_ino


def _cleanup(folder, root_identity, filename, file_identity):
    """Delete only the verified owned file and directory, never recursively."""
    need(_identity(folder) == root_identity and folder.name.startswith(".grundschutz-native-"),
         "cleanup_failed")
    path = folder / filename
    if path.exists():
        need(file_identity is not None and _identity(path) == file_identity and path.stat().st_nlink == 1,
             "cleanup_failed")
        path.unlink()
    folder.rmdir()  # Unknown files cause refusal, never recursive deletion.


def extract_captured_bytes(original_bytes, *, source_id, handler_sha256, reader_spec_sha256,
                           policy_spec, expected_sha256, expected_length, selection=None,
                           execution_limits=DEFAULT_EXECUTION_LIMITS):
    """Extract explicit captured bytes. All identities/configuration are trusted inputs.

    A successful return verifies native mechanics only. It conveys no source
    registration, eligibility, evidence validity, review decision or approval.
    """
    folder = None
    root_identity = file_identity = None
    filename = None
    try:
        need(type(original_bytes) is bytes and type(execution_limits) is ExecutionLimits, "invalid_input")
        need(len(original_bytes) <= execution_limits.max_input_bytes, "input_limit")
        need(type(expected_length) is int and expected_length == len(original_bytes) and
             type(expected_sha256) is str and expected_sha256 == c.sha256(original_bytes), "source_mismatch")
        need(selection is None or type(selection) is SheetSelection, "invalid_selection")
        need(type(policy_spec) is c.Spec, "invalid_policy")
        profile = select_handler(handler_sha256)
        context = {"protocol": "native-request/v1", "request_id": uuid.uuid4().hex,
                   "source_id": source_id, "handler_spec_sha256": handler_sha256,
                   "reader_spec_sha256": reader_spec_sha256, "policy_spec": policy_spec.data(),
                   "selection": None if selection is None else asdict(selection),
                   "original_sha256": expected_sha256, "original_length": expected_length,
                   "execution_limits": asdict(execution_limits)}
        context_policy(context, profile)
        metadata = wire_dump(context, execution_limits.max_metadata_bytes)
        verify_available(profile)
        deadline = time.monotonic() + execution_limits.max_seconds
        family = profile.spec.data()["family"]
        filename = "captured." + family
        # Verify the trusted OS temporary root before creating anything there.
        temp_root = Path(tempfile.gettempdir()).resolve()
        class FileLimit:
            max_database_bytes = execution_limits.max_input_bytes
        a0._path(temp_root / ".grundschutz-native-probe", FileLimit())
        folder = Path(tempfile.mkdtemp(prefix=".grundschutz-native-", dir=temp_root))
        root_identity = _identity(folder)
        path = folder / filename
        with path.open("xb") as stream:
            file_identity = _identity(path)
            stream.write(original_bytes)
        checked_transport(folder, family, original_bytes)
        candidate = _worker(folder, "derive", metadata, original_bytes, None, execution_limits, deadline)
        checked_transport(folder, family, original_bytes)
        result = materialize(context, wire_load(candidate, execution_limits.max_output_bytes), original_bytes, profile)
        # Reparse in a fresh pinned worker to detect omitted/coherently altered
        # observations, not merely internally consistent attacker hashes.
        ack = _worker(folder, "verify", metadata, original_bytes, candidate, execution_limits, deadline)
        need(wire_load(ack, execution_limits.max_output_bytes) == {
            "protocol": "native-verify/v1", "request_id": context["request_id"],
            "context_sha256": c.sha256(metadata), "candidate_sha256": c.sha256(candidate)}, "invalid_ack")
        checked_transport(folder, family, original_bytes)
        verify_available(profile)
        need(time.monotonic() < deadline, "worker_timeout")
        return result
    except NativeBridgeError:
        raise
    except Exception as exc:
        raise NativeBridgeError("native_refused") from exc
    finally:
        if folder is not None:
            try:
                _cleanup(folder, root_identity, filename, file_identity)
            except Exception as exc:
                raise NativeBridgeError("cleanup_failed") from exc
