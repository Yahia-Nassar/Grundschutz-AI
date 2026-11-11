"""Hostile worker protocols and coherent observation substitution regressions."""
from dataclasses import asdict
from io import BytesIO
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from grundschutz_ai import v2_codec as c, v3_native as b, v3_native_catalog as catalog
from grundschutz_ai import v3_native_contract as contract
import test_v3_native as fixtures


class WireTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(b.NativeBridgeError): contract.wire_load(b'{"a":1,"a":2}')

    def test_noncanonical_json_rejected(self):
        for raw in (b'{"b":1,"a":2}', b'{ "a":1}', b'{"a":1.0}', b'{"a":NaN}', b'{"a":1}\n'):
            with self.subTest(raw=raw), self.assertRaises(b.NativeBridgeError): contract.wire_load(raw)

    def test_surrogate_text_rejected(self):
        with self.assertRaises(b.NativeBridgeError): contract.wire_load(b'{"a":"\\ud800"}')

    def test_wire_limit_and_nesting(self):
        with self.assertRaises(b.NativeBridgeError): contract.wire_dump({"a": "too long"}, 4)
        with self.assertRaises(b.NativeBridgeError): contract.wire_load(b"[" * 34 + b"0" + b"]" * 34)

    def test_framing_exact_and_bounded(self):
        self.assertEqual(contract.read_frame(BytesIO(contract.frame(b"ok", 2)), 2), b"ok")
        for raw in (b"", b"123", struct.pack(">Q", 3), struct.pack(">Q", 2) + b"x"):
            with self.subTest(raw=raw), self.assertRaises(b.NativeBridgeError): contract.read_frame(BytesIO(raw), 2)

    def test_ledger_limits_remain_unchanged(self):
        self.assertEqual(c.DEFAULT_LIMITS.max_bytes, 8388608)
        with self.assertRaises(c.CodecError): c.canonical_dumps("a" * 1048577)


class WorkerProcessTests(unittest.TestCase):
    def hostile_child(self, script, *, limits=None):
        """Test-only Popen replacement; production has no configurable command."""
        real_popen = subprocess.Popen
        processes, commands = [], []
        def launch(command, **kwargs):
            commands.append(command)
            process = real_popen([sys.executable, "-I", "-B", "-c", script], **kwargs)
            processes.append(process)
            return process
        with tempfile.TemporaryDirectory(prefix="grundschutz-native-protocol-") as root:
            with patch.object(b.subprocess, "Popen", side_effect=launch):
                try:
                    return b._worker(Path(root), "derive", b"{}", b"x", None,
                        limits or b.ExecutionLimits(), time.monotonic() + (limits.max_seconds if limits else 2))
                finally:
                    for process in processes:
                        self.assertIsNotNone(process.poll(), "worker must be terminated and reaped")
                    self.assertEqual(len(commands), 1)
                    self.assertEqual(commands[0][1:3], ["-I", "-B"])
                    self.assertEqual(Path(commands[0][3]).name, "v3_native_worker.py")

    def test_worker_crash_reaped(self):
        with self.assertRaises(b.NativeBridgeError): self.hostile_child("import os;os._exit(7)")

    def test_incomplete_prefix_reaped(self):
        with self.assertRaises(b.NativeBridgeError):
            self.hostile_child("import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b'bad')")

    def test_incomplete_body_reaped(self):
        with self.assertRaises(b.NativeBridgeError):
            self.hostile_child("import sys,struct;sys.stdin.buffer.read();sys.stdout.buffer.write(struct.pack('>Q',9)+b'{}')")

    def test_oversized_frame_reaped(self):
        with self.assertRaises(b.NativeBridgeError):
            self.hostile_child("import sys,struct;sys.stdout.buffer.write(struct.pack('>Q',33554433));sys.stdout.buffer.flush();sys.stdin.buffer.read()")

    def test_trailing_output_reaped(self):
        with self.assertRaises(b.NativeBridgeError):
            self.hostile_child("import sys,struct;sys.stdin.buffer.read();sys.stdout.buffer.write(struct.pack('>Q',2)+b'{}extra')")

    def test_stderr_refused_reaped(self):
        with self.assertRaises(b.NativeBridgeError):
            self.hostile_child("import sys;sys.stderr.buffer.write(b'x'*5000);sys.stderr.flush();sys.stdin.buffer.read()")

    def test_timeout_terminates_and_reaps(self):
        start = time.monotonic()
        with self.assertRaisesRegex(b.NativeBridgeError, "worker_timeout"):
            self.hostile_child("import time;time.sleep(30)", limits=b.ExecutionLimits(max_seconds=1))
        self.assertLess(time.monotonic() - start, 4)

    def test_valid_frame_followed_by_hang_cannot_return(self):
        with self.assertRaisesRegex(b.NativeBridgeError, "worker_timeout"):
            self.hostile_child("import sys,struct,time;sys.stdin.buffer.read();sys.stdout.buffer.write(struct.pack('>Q',2)+b'{}');sys.stdout.flush();time.sleep(30)", limits=b.ExecutionLimits(max_seconds=1))

    def test_worker_launch_error_is_static(self):
        raw, args, _ = fixtures.case_args()
        with patch.object(b.subprocess, "Popen", side_effect=OSError("sensitive path must not appear")):
            with self.assertRaises(b.NativeBridgeError) as failure: b.extract_captured_bytes(raw, **args)
        self.assertNotIn("sensitive", str(failure.exception))

    def test_ack_forgery_refused(self):
        raw, args, _ = fixtures.case_args()
        original = b._worker
        def fake(folder, operation, *other):
            return b"{}" if operation == "verify" else original(folder, operation, *other)
        with patch.object(b, "_worker", side_effect=fake):
            with self.assertRaisesRegex(b.NativeBridgeError, "invalid_ack"): b.extract_captured_bytes(raw, **args)

    def test_forged_result_extra_authority_refused(self):
        raw, args, _ = fixtures.case_args()
        original = b._worker
        def fake(*a):
            result = contract.wire_load(original(*a))
            result["state"] = "VALID"
            return contract.wire_dump(result)
        with patch.object(b, "_worker", side_effect=fake):
            with self.assertRaises(b.NativeBridgeError): b.extract_captured_bytes(raw, **args)

    def test_worker_rejects_raw_bytes_inconsistent_with_metadata(self):
        raw, args, _ = fixtures.case_args()
        original = b._worker
        def change(folder, operation, metadata, captured, candidate, limits, deadline):
            return original(folder, operation, metadata, captured + b"changed", candidate, limits, deadline)
        with patch.object(b, "_worker", side_effect=change):
            with self.assertRaises(b.NativeBridgeError): b.extract_captured_bytes(raw, **args)

    def test_same_cumulative_deadline_for_both_workers(self):
        raw, args, _ = fixtures.case_args()
        original = b._worker
        deadlines = []
        def observe(*a):
            deadlines.append(a[-1])
            return original(*a)
        with patch.object(b, "_worker", side_effect=observe): b.extract_captured_bytes(raw, **args)
        self.assertEqual(len(deadlines), 2)
        self.assertEqual(deadlines[0], deadlines[1])

    def test_cumulative_deadline_not_reset(self):
        raw, args, _ = fixtures.case_args()
        original = b._worker
        def delayed(*a):
            time.sleep(0.6)
            return original(*a)
        with patch.object(b, "_worker", side_effect=delayed):
            with self.assertRaisesRegex(b.NativeBridgeError, "worker_timeout"):
                b.extract_captured_bytes(raw, **args, execution_limits=b.ExecutionLimits(max_seconds=1))


class ObservationTests(unittest.TestCase):
    def tamper(self, name, mutate, *, coherent=False):
        raw, args, _ = fixtures.case_args(name)
        original = b._worker
        operations = []
        def worker(folder, operation, metadata, captured, candidate, limits, deadline):
            operations.append(operation)
            wire = original(folder, operation, metadata, captured, candidate, limits, deadline)
            if operation != "derive": return wire
            record = contract.wire_load(wire)
            mutate(record)
            if coherent:
                context = contract.wire_load(metadata)
                profile = catalog.select_handler(context["handler_spec_sha256"])
                _, config, _ = contract.context_policy(context, profile)
                reconstruct = contract._docx_native if name.startswith("docx") else contract._xlsx_native
                native = reconstruct(captured, context, config, record["observations"])
                record = contract.make_record(context, native, profile)
            return contract.wire_dump(record)
        with patch.object(b, "_worker", side_effect=worker):
            with self.assertRaises(b.NativeBridgeError): b.extract_captured_bytes(raw, **args)
        if coherent: self.assertEqual(operations, ["derive", "verify"])

    def test_forged_hash_claim(self):
        self.tamper("docx_complete", lambda r: r.update(native_text_sha256="0" * 64))

    def test_missing_observations_field(self):
        self.tamper("docx_complete", lambda r: r.pop("observations"))

    def test_missing_docx_segment_coherent_hashes_rejected(self):
        self.tamper("docx_coverage", lambda r: r["observations"].pop(), coherent=True)

    def test_docx_location_altered_coherent_hashes_rejected(self):
        def alter(record):
            item = record["observations"][0]
            item["text"] = item["text"].replace("Rostock", "FALSCH!")
            item["text_sha256"] = c.sha256(item["text"].encode())
        self.tamper("docx_complete", alter, coherent=True)

    def test_omitted_empty_xlsx_sheet_coherent_hashes_rejected(self):
        self.tamper("xlsx_coverage", lambda r: r["observations"].pop(), coherent=True)

    def test_blank_changed_to_empty_text_coherent_hashes_rejected(self):
        def alter(record):
            cell = next(c for s in record["observations"] for c in s["cells"] if c["kind"] == "blank")
            cell["kind"] = "text"
        self.tamper("xlsx_blank", alter, coherent=True)

    def test_empty_text_changed_to_missing_coherent_hashes_rejected(self):
        def alter(record):
            cells = record["observations"][0]["cells"]
            cells.remove(next(c for c in cells if c["text"] == "" and c["kind"] == "text"))
        self.tamper("xlsx_empty_text", alter, coherent=True)

    def test_unknown_cell_kind_rejected(self):
        self.tamper("xlsx_blank", lambda r: r["observations"][0]["cells"][0].update(kind="missing"))

    def test_forged_source_id_rejected(self):
        self.tamper("docx_complete", lambda r: r.update(source_id="forged"))

    def test_forged_handler_claim_rejected(self):
        self.tamper("docx_complete", lambda r: r.update(handler_spec_sha256="0" * 64))


class AuditGuardTests(unittest.TestCase):
    def denied(self, expression):
        # Separate test interpreter: hooks cannot be removed from this process.
        app = str(Path(__file__).resolve().parents[1])
        code = ("import sys,socket,sqlite3,subprocess;from pathlib import Path;"
                "sys.path.insert(0," + repr(app) + ");"
                "from grundschutz_ai.v3_native_worker import install_guard;"
                "from grundschutz_ai.v3_native_contract import NativeBridgeError;"
                "install_guard(Path('C:/synthetic-absent/captured.docx'));\n"
                "try: " + expression + "\n"
                "except NativeBridgeError: sys.exit(0)\n"
                "else: sys.exit(9)")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, timeout=3,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_network_creation_denied(self): self.denied("socket.socket()")
    def test_sqlite_connection_denied(self): self.denied("sqlite3.connect(':memory:')")
    def test_process_creation_denied(self): self.denied("subprocess.Popen([sys.executable,'-V'])")
    def test_file_write_denied(self): self.denied("open('C:/synthetic-absent/captured.docx','wb')")
    def test_unlisted_read_denied(self): self.denied("open('C:/synthetic-absent/never-read.txt','rb')")


if __name__ == "__main__":
    unittest.main()
