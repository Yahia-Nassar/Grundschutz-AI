"""Diagnostic-only canonical synthetic PDF reader. Not a general PDF parser."""

from dataclasses import asdict, dataclass, field, fields
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import threading
import time


METHOD = "pdf-synthetic-ascii/v1"
IMPLEMENTATION = "grundschutz_ai.pdf_ingestion/1.0.0"
_ERROR_CODES = frozenset({"input_error", "invalid_profile", "resource_limit", "worker_timeout", "worker_output_limit", "worker_protocol", "worker_failed", "worker_cleanup_failed"})


class PdfIngestionError(ValueError):
    """Bounded static diagnostic; never contains source text or partial output."""

    def __init__(self, code="invalid_profile"):
        self.code = code if code in _ERROR_CODES else "worker_failed"
        super().__init__(f"Synthetic PDF ingestion rejected: {self.code}")


@dataclass(frozen=True, slots=True)
class PdfLimits:
    max_file_bytes: int = 1024 * 1024
    max_pages: int = 16
    max_objects: int = 35
    max_stream_bytes: int = 16 * 1024
    max_depth: int = 8
    max_token_bytes: int = 128
    max_lines: int = 38
    max_line_chars: int = 60
    max_page_chars: int = 2317
    max_text_chars: int = 65_536
    worker_timeout_ms: int = 5000
    max_worker_result_bytes: int = 256 * 1024

    def __post_init__(self):
        if any(type(getattr(self, item.name)) is not int or not 1 <= getattr(self, item.name) <= item.default for item in fields(self)):
            raise PdfIngestionError("input_error")


DEFAULT_LIMITS = PdfLimits()


def _source_id(value):
    if type(value) is not str or not value.strip():
        raise PdfIngestionError("input_error")
    try:
        if len(value.encode("utf-8")) > 256:
            raise PdfIngestionError("input_error")
    except UnicodeError as exc:
        raise PdfIngestionError("input_error") from exc


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise PdfIngestionError("worker_protocol")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PdfIngestionError("worker_protocol")
            result[key] = value
        return result

    def constant(value):
        raise PdfIngestionError("worker_protocol")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PdfIngestionError("worker_protocol") from exc


@dataclass(frozen=True, slots=True)
class ObjectRef:
    number: int
    generation: int = 0

    def __post_init__(self):
        _integer(self.number, 1, 35)
        _integer(self.generation, 0, 0)


@dataclass(frozen=True, slots=True)
class PdfLine:
    ordinal: int
    text: str
    char_start: int
    char_end: int
    hex_byte_start: int
    hex_byte_end: int

    def __post_init__(self):
        _integer(self.ordinal, 1, 38)
        if type(self.text) is not str or len(self.text) > 60 or any(not 32 <= ord(character) <= 126 for character in self.text):
            raise PdfIngestionError("worker_protocol")
        _integer(self.char_start, 0, 2317)
        _integer(self.char_end, self.char_start, 2317)
        _integer(self.hex_byte_start, 0, 1024 * 1024)
        _integer(self.hex_byte_end, self.hex_byte_start, 1024 * 1024)
        if self.char_end - self.char_start != len(self.text) or self.hex_byte_end - self.hex_byte_start != 2 * len(self.text) + 2:
            raise PdfIngestionError("worker_protocol")


@dataclass(frozen=True, slots=True)
class PdfPage:
    page_index: int
    page_object: ObjectRef
    content_object: ObjectRef
    content_byte_start: int
    content_byte_end: int
    lines: tuple[PdfLine, ...]
    text: str = field(init=False)
    text_sha256: str = field(init=False)

    def __post_init__(self):
        _integer(self.page_index, 1, 16)
        if type(self.page_object) is not ObjectRef or type(self.content_object) is not ObjectRef or self.page_object.number != 2 * self.page_index + 2 or self.content_object.number != 2 * self.page_index + 3:
            raise PdfIngestionError("worker_protocol")
        _integer(self.content_byte_start, 0, 1024 * 1024)
        _integer(self.content_byte_end, self.content_byte_start, 1024 * 1024)
        if type(self.lines) is not tuple or len(self.lines) > 38 or any(type(line) is not PdfLine for line in self.lines):
            raise PdfIngestionError("worker_protocol")
        position = 0
        for index, line in enumerate(self.lines, 1):
            if line.ordinal != index or line.char_start != position:
                raise PdfIngestionError("worker_protocol")
            position = line.char_end + 1
        text = "\n".join(line.text for line in self.lines)
        if len(text) > 2317:
            raise PdfIngestionError("resource_limit")
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "text_sha256", _digest(text.encode("utf-8")))


@dataclass(frozen=True, slots=True)
class PdfQuote:
    source_id: str
    pdf_sha256: str
    page_index: int
    char_start: int
    char_end: int
    text: str

    def __post_init__(self):
        _source_id(self.source_id)
        if type(self.pdf_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", self.pdf_sha256):
            raise PdfIngestionError("input_error")
        _integer(self.page_index, 1, 16)
        _integer(self.char_start, 0, 2316)
        _integer(self.char_end, self.char_start + 1, 2317)
        if type(self.text) is not str or len(self.text) != self.char_end - self.char_start:
            raise PdfIngestionError("input_error")


@dataclass(frozen=True, slots=True)
class PdfExtraction:
    """Untrusted diagnostic artifact. Construction is not an approval boundary."""

    source_id: str
    original_bytes: bytes = field(repr=False)
    pages: tuple[PdfPage, ...]
    limits: PdfLimits = DEFAULT_LIMITS
    method: str = field(default=METHOD, init=False)
    implementation: str = field(default=IMPLEMENTATION, init=False)
    diagnostic_only: bool = field(default=True, init=False)
    visual_verification: str = field(default="not_performed", init=False)
    pdf_sha256: str = field(init=False)
    text: str = field(init=False)
    text_sha256: str = field(init=False)
    manifest_json: str = field(init=False)
    manifest_sha256: str = field(init=False)

    def __post_init__(self):
        _source_id(self.source_id)
        if type(self.original_bytes) is not bytes or type(self.limits) is not PdfLimits or len(self.original_bytes) > self.limits.max_file_bytes:
            raise PdfIngestionError("input_error")
        if type(self.pages) is not tuple or not 1 <= len(self.pages) <= self.limits.max_pages or any(type(page) is not PdfPage for page in self.pages) or 3 + 2 * len(self.pages) > self.limits.max_objects:
            raise PdfIngestionError("worker_protocol")
        previous_end = 0
        for index, page in enumerate(self.pages, 1):
            if page.page_index != index or not previous_end <= page.content_byte_start <= page.content_byte_end <= len(self.original_bytes) or page.content_byte_end - page.content_byte_start > self.limits.max_stream_bytes or len(page.lines) > self.limits.max_lines or len(page.text) > self.limits.max_page_chars:
                raise PdfIngestionError("worker_protocol")
            cursor = page.content_byte_start
            prefix = b"BT\n/F1 12 Tf\n"
            if self.original_bytes[cursor:cursor + len(prefix)] != prefix:
                raise PdfIngestionError("worker_protocol")
            cursor += len(prefix)
            for line in page.lines:
                matrix = f"1 0 0 1 72 {770 - 18 * (line.ordinal - 1)} Tm\n".encode("ascii")
                operand = b"<" + line.text.encode("ascii").hex().upper().encode("ascii") + b">"
                if len(line.text) > self.limits.max_line_chars or len(operand) > self.limits.max_token_bytes or line.hex_byte_start != cursor + len(matrix) or line.hex_byte_end != line.hex_byte_start + len(operand):
                    raise PdfIngestionError("worker_protocol")
                expected = matrix + operand + b" Tj\n"
                if self.original_bytes[cursor:cursor + len(expected)] != expected:
                    raise PdfIngestionError("worker_protocol")
                cursor += len(expected)
            if cursor + 3 != page.content_byte_end or self.original_bytes[cursor:cursor + 3] != b"ET\n":
                raise PdfIngestionError("worker_protocol")
            previous_end = page.content_byte_end
        text = "\f".join(page.text for page in self.pages)
        if len(text) > self.limits.max_text_chars:
            raise PdfIngestionError("resource_limit")
        binary_hash, text_hash = _digest(self.original_bytes), _digest(text.encode("utf-8"))
        manifest = _json({"source_id": self.source_id, "pdf_sha256": binary_hash, "method": self.method, "implementation": self.implementation, "limits": asdict(self.limits), "diagnostic_only": True, "visual_verification": "not_performed", "text_sha256": text_hash, "pages": [asdict(page) for page in self.pages]})
        object.__setattr__(self, "pdf_sha256", binary_hash)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "text_sha256", text_hash)
        object.__setattr__(self, "manifest_json", manifest)
        object.__setattr__(self, "manifest_sha256", _digest(manifest.encode("utf-8")))

    def quote(self, page_index: int, start: int, end: int) -> PdfQuote:
        _integer(page_index, 1, len(self.pages))
        page = self.pages[page_index - 1]
        _integer(start, 0, len(page.text) - 1)
        _integer(end, start + 1, len(page.text))
        return PdfQuote(self.source_id, self.pdf_sha256, page_index, start, end, page.text[start:end])

    def verify_quote(self, quote: PdfQuote) -> bool:
        return (type(quote) is PdfQuote and quote.source_id == self.source_id and quote.pdf_sha256 == self.pdf_sha256 and quote.page_index <= len(self.pages) and quote.char_end <= len(self.pages[quote.page_index - 1].text) and self.pages[quote.page_index - 1].text[quote.char_start:quote.char_end] == quote.text)


class _Cursor:
    def __init__(self, raw, limits, start=0, end=None):
        self.raw, self.limits, self.position = raw, limits, start
        self.end = len(raw) if end is None else end
        if not 0 <= start <= self.end <= len(raw):
            raise PdfIngestionError()

    def take(self, expected):
        if self.position + len(expected) > self.end or not self.raw.startswith(expected, self.position):
            raise PdfIngestionError()
        self.position += len(expected)

    def uint(self, ending, maximum):
        start = self.position
        while self.position < self.end and 48 <= self.raw[self.position] <= 57:
            self.position += 1
            if self.position - start > min(10, self.limits.max_token_bytes):
                raise PdfIngestionError("resource_limit")
        value = self.raw[start:self.position]
        if not value or value.startswith(b"0"):
            raise PdfIngestionError()
        number = int(value)
        if number > maximum:
            raise PdfIngestionError("resource_limit")
        self.take(ending)
        return number


def _parse_canonical(raw: bytes, source_id: str, limits: PdfLimits) -> PdfExtraction:
    """Private worker parser; public callers must use the bounded parent API."""
    _source_id(source_id)
    if type(raw) is not bytes or type(limits) is not PdfLimits or len(raw) > limits.max_file_bytes:
        raise PdfIngestionError("resource_limit")
    if limits.max_depth < 3 or limits.max_token_bytes < len(b"/WinAnsiEncoding"):
        raise PdfIngestionError("resource_limit")
    cursor, offsets = _Cursor(raw, limits), []

    def object_start(number):
        offsets.append(cursor.position)
        cursor.take(f"{number} 0 obj\n".encode("ascii"))

    cursor.take(b"%PDF-1.4\n")
    object_start(1)
    cursor.take(b"<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    object_start(2)
    cursor.take(b"<< /Type /Pages /Count ")
    count = cursor.uint(b" /Kids [", limits.max_pages)
    if 3 + 2 * count > limits.max_objects:
        raise PdfIngestionError("resource_limit")
    cursor.take(" ".join(f"{2 * index + 2} 0 R" for index in range(1, count + 1)).encode("ascii"))
    cursor.take(b"] >>\nendobj\n")
    object_start(3)
    cursor.take(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>\nendobj\n")
    pages = []
    for index in range(1, count + 1):
        page_object, content_object = 2 * index + 2, 2 * index + 3
        object_start(page_object)
        cursor.take(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_object} 0 R >>\nendobj\n".encode("ascii"))
        object_start(content_object)
        cursor.take(b"<< /Length ")
        length = cursor.uint(b" >>\nstream\n", limits.max_stream_bytes)
        start, end = cursor.position, cursor.position + length
        stream = _Cursor(raw, limits, start, end)
        stream.take(b"BT\n/F1 12 Tf\n")
        lines, character = [], 0
        while not raw.startswith(b"ET\n", stream.position):
            ordinal = len(lines) + 1
            if ordinal > limits.max_lines:
                raise PdfIngestionError("resource_limit")
            stream.take(f"1 0 0 1 72 {770 - 18 * (ordinal - 1)} Tm\n".encode("ascii"))
            operand_start = stream.position
            stream.take(b"<")
            digits = stream.position
            while stream.position < stream.end and raw[stream.position] in b"0123456789ABCDEF":
                stream.position += 1
                if stream.position - digits > 2 * limits.max_line_chars or stream.position - digits + 2 > limits.max_token_bytes:
                    raise PdfIngestionError("resource_limit")
            hexadecimal = raw[digits:stream.position]
            if len(hexadecimal) % 2:
                raise PdfIngestionError()
            stream.take(b">")
            operand_end = stream.position
            decoded = bytes.fromhex(hexadecimal.decode("ascii"))
            if any(not 32 <= byte <= 126 for byte in decoded):
                raise PdfIngestionError()
            text = decoded.decode("ascii")
            if character + len(text) > limits.max_page_chars:
                raise PdfIngestionError("resource_limit")
            lines.append(PdfLine(ordinal, text, character, character + len(text), operand_start, operand_end))
            character += len(text) + 1
            stream.take(b" Tj\n")
        stream.take(b"ET\n")
        if stream.position != end:
            raise PdfIngestionError()
        cursor.position = end
        cursor.take(b"endstream\nendobj\n")
        pages.append(PdfPage(index, ObjectRef(page_object), ObjectRef(content_object), start, end, tuple(lines)))
    xref = cursor.position
    cursor.take(f"xref\n0 {len(offsets) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets:
        cursor.take(f"{offset:010d} 00000 n \n".encode("ascii"))
    cursor.take(f"trailer\n<< /Size {len(offsets) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    if cursor.position != len(raw):
        raise PdfIngestionError()
    return PdfExtraction(source_id, raw, tuple(pages), limits)


def _decode_result(raw, original, source_id, limits):
    data = _loads(raw)
    if type(data) is not dict or type(data.get("protocol")) is not int or data["protocol"] != 1:
        raise PdfIngestionError("worker_protocol")
    if data.get("kind") == "error":
        if set(data) != {"protocol", "kind", "code"} or type(data["code"]) is not str or data["code"] not in _ERROR_CODES:
            raise PdfIngestionError("worker_protocol")
        raise PdfIngestionError(data["code"])
    if set(data) != {"protocol", "kind", "manifest", "manifest_sha256"} or data["kind"] != "ok" or type(data["manifest"]) is not dict:
        raise PdfIngestionError("worker_protocol")
    manifest = data["manifest"]
    try:
        records = manifest["pages"]
        if type(records) is not list or not 1 <= len(records) <= limits.max_pages:
            raise PdfIngestionError("worker_protocol")
        pages = []
        for record in records:
            if type(record) is not dict or set(record) != {"page_index", "page_object", "content_object", "content_byte_start", "content_byte_end", "lines", "text", "text_sha256"} or type(record["lines"]) is not list or len(record["lines"]) > limits.max_lines:
                raise PdfIngestionError("worker_protocol")
            if any(type(item) is not dict or set(item) != {"number", "generation"} for item in (record["page_object"], record["content_object"])):
                raise PdfIngestionError("worker_protocol")
            if any(type(item) is not dict or set(item) != {"ordinal", "text", "char_start", "char_end", "hex_byte_start", "hex_byte_end"} for item in record["lines"]):
                raise PdfIngestionError("worker_protocol")
            pages.append(PdfPage(record["page_index"], ObjectRef(**record["page_object"]), ObjectRef(**record["content_object"]), record["content_byte_start"], record["content_byte_end"], tuple(PdfLine(**item) for item in record["lines"])))
        result = PdfExtraction(source_id, original, tuple(pages), limits)
        # Compare canonical bytes too: Python equality alone equates bool/int.
        if _json(manifest) != result.manifest_json or type(data["manifest_sha256"]) is not str or data["manifest_sha256"] != result.manifest_sha256:
            raise PdfIngestionError("worker_protocol")
        return result
    except (KeyError, TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise PdfIngestionError("worker_protocol") from exc


def _worker_command():
    return [sys.executable, "-I", "-S", "-u", str(Path(__file__).with_name("pdf_worker.py").resolve())]


def _cleanup_worker(process, threads):
    deadline = time.monotonic() + 1.0
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        for thread in threads:
            thread.join(timeout=max(0, deadline - time.monotonic()))
        if any(thread.is_alive() for thread in threads):
            raise PdfIngestionError("worker_cleanup_failed")
        for pipe in (process.stdin, process.stdout):
            if pipe is not None and not pipe.closed:
                pipe.close()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PdfIngestionError("worker_cleanup_failed") from exc


def _run_worker(original, source_id, limits):
    header = _json({"protocol": 1, "source_id": source_id, "limits": asdict(limits), "raw_size": len(original)}).encode("utf-8")
    payload = struct.pack(">I", len(header)) + header + original
    deadline = time.monotonic() + limits.worker_timeout_ms / 1000
    try:
        process = subprocess.Popen(_worker_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, shell=False, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, ValueError) as exc:
        raise PdfIngestionError("worker_failed") from exc
    output, failures, threads = bytearray(), [], []
    notify, read_done, write_done, overflow = (threading.Event() for _ in range(4))

    def write_input():
        try:
            view = memoryview(payload)
            while view:
                count = os.write(process.stdin.fileno(), view[:65536])
                if count <= 0:
                    raise OSError("write failed")
                view = view[count:]
        except (OSError, ValueError):
            failures.append("write")
        finally:
            process.stdin.close()
            write_done.set()
            notify.set()

    def read_output():
        try:
            while True:
                chunk = os.read(process.stdout.fileno(), min(4096, limits.max_worker_result_bytes + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > limits.max_worker_result_bytes:
                    overflow.set()
                    break
        except (OSError, ValueError):
            failures.append("read")
        finally:
            process.stdout.close()
            read_done.set()
            notify.set()

    try:
        for target in (write_input, read_output):
            thread = threading.Thread(target=target, name="pdf-ingestion-pipe", daemon=True)
            thread.start()
            threads.append(thread)
        while True:
            if overflow.is_set():
                raise PdfIngestionError("worker_output_limit")
            if time.monotonic() >= deadline:
                raise PdfIngestionError("worker_timeout")
            if process.poll() is not None and read_done.is_set() and write_done.is_set():
                break
            notify.wait(timeout=min(0.01, max(0, deadline - time.monotonic())))
            notify.clear()
        if failures or process.returncode != 0:
            raise PdfIngestionError("worker_failed")
        result = _decode_result(bytes(output), original, source_id, limits)
        if time.monotonic() >= deadline:
            raise PdfIngestionError("worker_timeout")
        return result
    except RuntimeError as exc:
        raise PdfIngestionError("worker_failed") from exc
    finally:
        _cleanup_worker(process, threads)


def ingest_pdf(path: str | Path, *, source_id: str, limits: PdfLimits = DEFAULT_LIMITS) -> PdfExtraction:
    """Only public ingestion API: capture a trusted synthetic file, then isolate."""
    _source_id(source_id)
    if not isinstance(path, (str, Path)) or type(limits) is not PdfLimits:
        raise PdfIngestionError("input_error")
    try:
        path = Path(path)
        if path.suffix.casefold() != ".pdf" or path.is_symlink():
            raise PdfIngestionError("input_error")
        with path.open("rb") as file:
            metadata = os.fstat(file.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limits.max_file_bytes:
                raise PdfIngestionError("resource_limit")
            original = file.read(limits.max_file_bytes + 1)
        if len(original) > limits.max_file_bytes:
            raise PdfIngestionError("resource_limit")
        return _run_worker(original, source_id, limits)
    except PdfIngestionError:
        raise
    except (OSError, ValueError) as exc:
        raise PdfIngestionError("input_error") from exc
