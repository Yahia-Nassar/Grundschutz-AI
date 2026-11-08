"""Pure, deliberately bounded support checks; no general German semantics."""

from dataclasses import dataclass, field
import re


SUPPORT_POLICY = "inventory-affirmative/v1"
SYNTHETIC_HEADER = "FIKTIVES TESTBEISPIEL — keine reale Infrastruktur.\n"
_ID = r"[A-Z][A-Z0-9]*-[A-Z0-9]+"
_PLACE = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]*(?:-[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]*)*"
_LOCATION = rf"Rechenzentrum {_PLACE}(?: {_PLACE})*(?:, Raum [A-Z0-9]+(?:-[A-Z0-9]+)*)?"
_AFFIRMATIVE = re.compile(
    rf"Der Server (?P<system>{_ID}) "
    rf"(?:befindet sich im (?P<location>{_LOCATION}) und )?"
    rf"betreibt die Anwendung (?P<application>{_ID})\."
)
_AMBIGUOUS_LOCATION = re.compile(
    r"\b(?:nicht|kein|keine|keinem|keinen|keiner|keines|ohne|statt|unbekannt|unklar|null|none)\b",
    re.IGNORECASE,
)


def complete_name_occurs(quote: str, name: str, *, before: str = "", after: str = "") -> bool:
    """Require a complete name inside the quote with original-source boundaries.

    Quote clipping must not turn a prefix/suffix of a source identifier into a
    complete identifier. Adjacent characters are captured during source checking.
    """
    if not name.strip():
        return False
    context = before + quote + after
    return any(
        len(before) <= match.start() and match.end() <= len(before) + len(quote)
        for match in re.finditer(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", context)
    )


@dataclass(frozen=True, slots=True)
class AffirmativeSupport:
    system: str
    application: str
    location: str | None
    policy: str = field(default=SUPPORT_POLICY, init=False)

    def supports(self, predicate: str, subject: str, target: str) -> bool:
        if subject != self.system:
            return False
        if predicate == "hosts":
            return target == self.application
        if predicate == "located_at":
            return self.location is not None and target == self.location
        return False


def assess_source(source: str, quote_start: int, quote_end: int) -> AffirmativeSupport | None:
    """Assess the whole source while it is available, not a possibly clipped quote.

    Accept one affirmative inventory sentence, optional surrounding whitespace,
    and optionally the exact synthetic fixture header. No arbitrary comments,
    instructions, negative claims or multiple sentences are discarded. The quote
    must cover the entire assertion. Unsupported evidence may still be retained
    as a source artifact, but cannot establish an affirmative relationship.
    """
    start, end = len(source) - len(source.lstrip()), len(source.rstrip())
    if source.startswith(SYNTHETIC_HEADER, start):
        start += len(SYNTHETIC_HEADER)
        start += len(source[start:end]) - len(source[start:end].lstrip())
    match = _AFFIRMATIVE.fullmatch(source, start, end)
    if match is None or quote_start > match.start() or quote_end < match.end():
        return None
    location = match.group("location")
    if location is not None and _AMBIGUOUS_LOCATION.search(location):
        return None
    return AffirmativeSupport(match.group("system"), match.group("application"), location)
