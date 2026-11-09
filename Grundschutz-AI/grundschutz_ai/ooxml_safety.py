"""Internal bounded ZIP/XML mechanics shared by the DOCX and XLSX profiles.

The caller supplies trusted limits and an exact part allowlist. No archive
members are extracted to disk, no references are followed, and no I/O occurs.
"""

from io import BytesIO
import re
import stat
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib


class OOXMLSafetyError(ValueError):
    """Unsupported, malformed or over-budget OOXML package/XML."""


_CENTRAL = struct.Struct("<4s6H3I5H2I")
_LOCAL = struct.Struct("<4s5H3I2H")


def read_package(raw: bytes, limits, *, required_parts, allowed_parts) -> dict[str, bytes]:
    """Preflight central records before ZipFile allocation; bound actual inflate."""
    if len(raw) < 22 or not raw.startswith(b"PK\x03\x04"):
        raise OOXMLSafetyError("Not a supported OOXML ZIP container")
    signature, disk, cd_disk, disk_count, count, cd_size, cd_start, comment = struct.unpack_from("<4s4H2IH", raw, len(raw) - 22)
    if signature != b"PK\x05\x06" or disk or cd_disk or disk_count != count or comment:
        raise OOXMLSafetyError("ZIP comments, spanning, ZIP64 or trailing data are unsupported")
    if count > limits.max_entries or cd_start + cd_size != len(raw) - 22:
        raise OOXMLSafetyError("ZIP entry count or central-directory bounds exceeded")
    position = cd_start
    for _ in range(count):
        if position + _CENTRAL.size > len(raw) - 22:
            raise OOXMLSafetyError("Malformed ZIP central directory")
        entry = _CENTRAL.unpack_from(raw, position)
        name_size, extra_size, comment_size = entry[10:13]
        if entry[0] != b"PK\x01\x02" or not 0 < name_size <= 128 or extra_size or comment_size or entry[13]:
            raise OOXMLSafetyError("Unsupported ZIP central record")
        position += _CENTRAL.size + name_size + extra_size + comment_size
    if position != cd_start + cd_size:
        raise OOXMLSafetyError("ZIP entry count does not cover the central directory")

    with zipfile.ZipFile(BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) != count or len(set(names)) != len(names) or len({name.casefold() for name in names}) != len(names):
            raise OOXMLSafetyError("Duplicate or inconsistent ZIP entries")
        if not required_parts <= set(names) or not set(names) <= allowed_parts:
            raise OOXMLSafetyError("Missing required OOXML part or unsupported package part")
        if sum(info.file_size for info in infos) > limits.max_uncompressed_bytes:
            raise OOXMLSafetyError("Uncompressed ZIP size limit exceeded")
        parts, position = {}, 0
        for info in sorted(infos, key=lambda item: item.header_offset):
            mode = info.external_attr >> 16
            if info.flag_bits not in (0, 0x800) or info.extract_version > 20 or info.extra or info.comment:
                raise OOXMLSafetyError("Encrypted or unsupported ZIP member")
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG) or info.orig_filename != info.filename:
                raise OOXMLSafetyError("Non-regular or suspicious ZIP member")
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise OOXMLSafetyError("Unsupported ZIP compression")
            if info.file_size > limits.max_xml_bytes or info.file_size > limits.max_ratio * max(1, info.compress_size):
                raise OOXMLSafetyError("ZIP member XML size or decompression ratio limit exceeded")
            if info.header_offset != position or position + _LOCAL.size > cd_start:
                raise OOXMLSafetyError("Overlapping or unparsed ZIP local data")
            local = _LOCAL.unpack_from(raw, position)
            if local[0] != b"PK\x03\x04" or local[1] != info.extract_version or local[2] != info.flag_bits or local[3] != info.compress_type:
                raise OOXMLSafetyError("ZIP local/central metadata mismatch")
            if local[6:9] != (info.CRC, info.compress_size, info.file_size) or local[10]:
                raise OOXMLSafetyError("ZIP size/CRC metadata mismatch or unsupported extra field")
            name_start = position + _LOCAL.size
            data_start = name_start + local[9]
            data_end = data_start + info.compress_size
            if data_end > cd_start or raw[name_start:data_start].decode("utf-8" if info.flag_bits & 0x800 else "cp437") != info.filename:
                raise OOXMLSafetyError("ZIP local member name/bounds mismatch")
            compressed = raw[data_start:data_end]
            if info.compress_type == zipfile.ZIP_STORED:
                content = compressed
            else:
                decoder = zlib.decompressobj(-15)
                content = decoder.decompress(compressed, limits.max_xml_bytes + 1)
                if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                    raise OOXMLSafetyError("Truncated, oversized or ambiguous DEFLATE stream")
            if len(content) != info.file_size or len(content) > limits.max_xml_bytes or zlib.crc32(content) & 0xFFFFFFFF != info.CRC:
                raise OOXMLSafetyError("Actual ZIP output differs from declared size/CRC")
            parts[info.filename] = content
            position = data_end
        if position != cd_start:
            raise OOXMLSafetyError("Unparsed bytes before ZIP central directory")
        return parts


class _BudgetTreeBuilder(ET.TreeBuilder):
    def __init__(self, limits):
        super().__init__()
        self.limits, self.depth, self.nodes, self.characters, self.namespaces = limits, 0, 0, 0, 0

    def start(self, tag, attrs):
        self.depth += 1
        self.nodes += 1
        if self.depth > self.limits.max_xml_depth or self.nodes > self.limits.max_xml_nodes:
            raise OOXMLSafetyError("XML structural limit exceeded")
        if len(attrs) > self.limits.max_xml_attributes or len(tag) + sum(len(key) + len(value) for key, value in attrs.items()) > self.limits.max_attribute_chars:
            raise OOXMLSafetyError("XML attribute limit exceeded")
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        return result

    def data(self, data):
        self.characters += len(data)
        if self.characters > self.limits.max_xml_chars:
            raise OOXMLSafetyError("XML character budget exceeded")
        return super().data(data)

    def start_ns(self, prefix, uri):
        self.namespaces += 1
        if self.namespaces > self.limits.max_namespaces or len(prefix or "") + len(uri) > self.limits.max_attribute_chars:
            raise OOXMLSafetyError("XML namespace limit exceeded")


def parse_xml(content: bytes, limits):
    text = content.decode("utf-8-sig", errors="strict")
    if "\x00" in text or "<!" in text:
        raise OOXMLSafetyError("DTD, entities, CDATA and XML comments are unsupported")
    declaration = re.match(r"<\?xml\s+version=['\"]1\.0['\"](?:\s+encoding=['\"]UTF-8['\"])?(?:\s+standalone=['\"](?:yes|no)['\"])?\s*\?>", text, re.IGNORECASE)
    remainder = text[declaration.end():] if declaration else text
    if "<?" in remainder:
        raise OOXMLSafetyError("Unsupported XML encoding declaration or processing instruction")
    parser = ET.XMLParser(target=_BudgetTreeBuilder(limits))
    return ET.fromstring(text, parser=parser)
