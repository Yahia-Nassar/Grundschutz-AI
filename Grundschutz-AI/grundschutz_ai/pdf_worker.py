"""Private isolated PDF worker. No user-controlled arguments, paths or imports."""

from pathlib import Path
import struct
import sys

# -I -S excludes the script directory, user site, sitecustomize and PYTHONPATH.
# Add only this explicitly trusted application root for the private worker API.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from grundschutz_ai.pdf_ingestion import (
    PdfIngestionError, PdfLimits, _json, _loads, _parse_canonical,
)


def _read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        chunk = stream.read(min(65536, size - len(result)))
        if not chunk:
            raise PdfIngestionError("worker_protocol")
        result.extend(chunk)
    return bytes(result)


def main():
    try:
        source = sys.stdin.buffer
        length = struct.unpack(">I", _read_exact(source, 4))[0]
        if not 1 <= length <= 16 * 1024:
            raise PdfIngestionError("worker_protocol")
        header = _loads(_read_exact(source, length))
        if type(header) is not dict or set(header) != {"protocol", "source_id", "limits", "raw_size"} or type(header["protocol"]) is not int or header["protocol"] != 1 or type(header["limits"]) is not dict:
            raise PdfIngestionError("worker_protocol")
        limits = PdfLimits(**header["limits"])
        if set(header["limits"]) != set(limits.__dataclass_fields__) or type(header["raw_size"]) is not int or not 0 <= header["raw_size"] <= limits.max_file_bytes:
            raise PdfIngestionError("worker_protocol")
        raw = _read_exact(source, header["raw_size"])
        if source.read(1):
            raise PdfIngestionError("worker_protocol")
        result = _parse_canonical(raw, header["source_id"], limits)
        message = _json({"protocol": 1, "kind": "ok", "manifest": _loads(result.manifest_json.encode("utf-8")), "manifest_sha256": result.manifest_sha256}).encode("utf-8")
        if len(message) > limits.max_worker_result_bytes:
            raise PdfIngestionError("worker_output_limit")
    except PdfIngestionError as exc:
        message = _json({"protocol": 1, "kind": "error", "code": exc.code}).encode("utf-8")
    except (ValueError, TypeError, OSError, RecursionError):
        message = b'{"protocol":1,"kind":"error","code":"worker_failed"}'
    sys.stdout.buffer.write(message)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
