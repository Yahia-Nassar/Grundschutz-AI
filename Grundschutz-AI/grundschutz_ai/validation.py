"""Strict JSON, evidence and bounded semantic validation without dependencies."""

from dataclasses import dataclass
import json
import re
from typing import Any


FIELDS = ("system_id", "standort", "anwendung_id")
SOURCE_COVERAGE_ERROR = (
    "Source must contain exactly one supported inventory assertion with only surrounding whitespace; "
    "additional or unsupported source content requires clarification"
)
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        name: {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "evidence_quote": {"type": ["string", "null"]},
            },
            "required": ["value", "evidence_quote"],
            "additionalProperties": False,
        }
        for name in FIELDS
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}

# This is a prototype support rule, not a BSI rule or general German parser.
# Full field spans are retained to reject truncated values and quotes drawn
# solely from unrelated instructions elsewhere in the source.
_ASSERTION = re.compile(
    r"(?<!\S)Der Server (?P<system_id>[A-Z][A-Z0-9]*-[A-Z0-9]+) "
    r"(?:befindet sich im (?P<standort>[^.\r\n]+?) und )?"
    r"betreibt die Anwendung (?P<anwendung_id>[A-Z][A-Z0-9]*-[A-Z0-9]+)\."
    r"(?=\s|$)",
    re.MULTILINE,
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Non-JSON constant: {value}")


def strict_json_loads(text: str) -> Any:
    """Reject duplicate keys, NaN, Infinity, trailing text and malformed JSON."""
    return json.loads(
        text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
    )


@dataclass(frozen=True)
class ValidationResult:
    fields: dict | None
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _quote_covers(
    source: str, quote: str, start: int, end: int, assertion_start: int, assertion_end: int
) -> bool:
    offset = source.find(quote)
    while offset != -1:
        if assertion_start <= offset <= start and end <= offset + len(quote) <= assertion_end:
            return True
        offset = source.find(quote, offset + 1)
    return False


def validate_response(response: str, source: str) -> ValidationResult:
    """Validate one candidate; never repair model output or invent evidence.

    Exactly one assertion must cover every non-whitespace source character.
    Unparsed content, including comments and instructions, fails closed.
    This checks the documented synthetic grammar, not real-world truth or
    source authorship. Invalid fields remain untrusted diagnostics only.
    """
    try:
        data = strict_json_loads(response)
    except (ValueError, TypeError, RecursionError):
        return ValidationResult(None, ("Invalid model JSON",))
    if not isinstance(data, dict):
        return ValidationResult(None, ("Model output must be a JSON object",))

    errors = []
    if set(data) != set(FIELDS):
        errors.append("Required fields must be exactly system_id, standort, anwendung_id")

    matches = list(_ASSERTION.finditer(source))
    assertion = matches[0] if len(matches) == 1 else None
    if (
        assertion is None
        or source[:assertion.start()].strip()
        or source[assertion.end():].strip()
    ):
        errors.append(SOURCE_COVERAGE_ERROR)

    for name in FIELDS:
        field = data.get(name)
        if not isinstance(field, dict) or set(field) != {"value", "evidence_quote"}:
            errors.append(f"{name}: required properties are exactly value and evidence_quote")
            continue
        value, quote = field["value"], field["evidence_quote"]
        if any(item is not None and not isinstance(item, str) for item in (value, quote)):
            errors.append(f"{name}: value and evidence_quote must be strings or null")
            continue
        if any(isinstance(item, str) and item.strip().casefold() == "null" for item in (value, quote)):
            errors.append(f"{name}: string 'null' is invalid; missing information requires JSON null")
        if (value is None) != (quote is None):
            errors.append(f"{name}: missing value and evidence_quote must both be null")
            continue
        if value is not None:
            if not value.strip() or not quote.strip():
                errors.append(f"{name}: empty strings are not missing information; use null")
            if quote not in source:
                errors.append(f"{name}: evidence_quote is not an exact source substring")
            if not re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", quote):
                errors.append(f"{name}: value is not supported by evidence_quote")

        if assertion is not None:
            expected = assertion.group(name)
            if value != expected:
                errors.append(f"{name}: value differs from the complete source assertion")
            elif expected is not None and not _quote_covers(
                source, quote, *assertion.span(name), *assertion.span()
            ):
                errors.append(f"{name}: quote must stay within the inventory assertion and cover the complete field")
        elif not source.strip() and value is not None:
            errors.append(f"{name}: empty source cannot support a value")

    return ValidationResult(data, tuple(errors))
