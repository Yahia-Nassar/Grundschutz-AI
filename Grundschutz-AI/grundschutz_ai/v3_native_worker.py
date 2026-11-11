"""Fixed isolated-interpreter entry point. No document-selected code or writers."""
import encodings.cp437  # zipfile's legacy filename decoder, before the audit guard
import encodings.utf_8_sig  # the fixed OOXML parser's only XML input encoding
import os
from pathlib import Path
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from grundschutz_ai import docx_ingestion as docx, xlsx_ingestion as xlsx
from grundschutz_ai import v2_a0 as a0, v2_codec as c
from grundschutz_ai.v3_native_catalog import select_handler, verify_available, artifact_paths
from grundschutz_ai.v3_native_contract import (
    NativeBridgeError, need, wire_load, wire_dump, frame, read_frame,
    context_policy, checked_transport, make_record, DEFAULT_EXECUTION_LIMITS,
)


def install_guard(transport):
    """Python audit restrictions, not an OS security sandbox or memory quota."""
    allowed = {os.path.normcase(os.path.abspath(str(p))) for p, _ in artifact_paths()}
    allowed.add(os.path.normcase(os.path.abspath(str(transport))))

    def guard(event, args):
        if (event.startswith(("socket.", "sqlite3.", "subprocess.", "os.spawn", "os.exec")) or
                event in {"os.system", "os.remove", "os.rename", "os.rmdir", "os.mkdir",
                          "os.link", "os.symlink", "os.truncate", "os.chmod", "os.chdir"}):
            raise NativeBridgeError("worker_side_effect")
        if event == "open":
            path, mode, flags = args
            need(isinstance(path, (str, bytes, os.PathLike)), "worker_side_effect")
            need(not (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)),
                 "worker_side_effect")
            need(os.path.normcase(os.path.abspath(os.fsdecode(path))) in allowed, "worker_side_effect")
    sys.addaudithook(guard)


def run(folder, operation, source, destination):
    need(operation in ("derive", "verify"), "invalid_operation")
    limits = DEFAULT_EXECUTION_LIMITS
    metadata = read_frame(source, limits.max_metadata_bytes)
    context = wire_load(metadata, limits.max_metadata_bytes)
    profile = select_handler(context["handler_spec_sha256"])
    verify_available(profile)
    _, config, limits = context_policy(context, profile)
    need(len(metadata) <= limits.max_metadata_bytes, "input_limit")
    raw = read_frame(source, limits.max_input_bytes)
    candidate = read_frame(source, limits.max_output_bytes) if operation == "verify" else None
    need(source.read(1) == b"", "trailing_input")
    need(len(raw) == context["original_length"] and c.sha256(raw) == context["original_sha256"],
         "source_mismatch")
    family = profile.spec.data()["family"]
    transport = checked_transport(folder, family, raw)
    # Preload Windows ctypes modules before restricting filesystem opens.
    a0._fixed_local_volume(transport)
    install_guard(transport)
    if family == "docx":
        native = docx.ingest_docx(transport, source_id=context["source_id"],
                                 limits=docx.DocxLimits(**config["reader_limits"]))
    else:
        native = xlsx.ingest_xlsx(transport, source_id=context["source_id"],
                                 limits=xlsx.XlsxLimits(**config["reader_limits"]))
    checked_transport(folder, family, raw)
    observed = wire_dump(make_record(context, native, profile), limits.max_output_bytes)
    if operation == "verify":
        need(observed == candidate, "reextraction_mismatch")
        observed = wire_dump({"protocol": "native-verify/v1", "request_id": context["request_id"],
                              "context_sha256": c.sha256(metadata), "candidate_sha256": c.sha256(candidate)})
    destination.write(frame(observed, limits.max_output_bytes))
    destination.flush()


def main():
    try:
        need(len(sys.argv) == 5 and sys.argv[1] == "--transport" and sys.argv[3] == "--operation",
             "invalid_command")
        run(Path(sys.argv[2]), sys.argv[4], sys.stdin.buffer, sys.stdout.buffer)
        return 0
    except Exception:
        # Never expose parser diagnostics, paths, source contents or partial data.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
