"""Run the fixed synthetic fixture only: python -m grundschutz_ai."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .extraction import DEFAULT_CONFIG, OllamaClient, extract_inventory


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract the bundled synthetic German fixture")
    parser.add_argument("--timeout", type=float, default=DEFAULT_CONFIG.timeout_seconds)
    args = parser.parse_args()
    try:
        config = replace(DEFAULT_CONFIG, timeout_seconds=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    source = (Path(__file__).resolve().parent.parent / "tests/fixtures/sample_de.txt").read_text(
        encoding="utf-8"
    ).strip()
    candidate = extract_inventory(source, "synthetic:sample_de", OllamaClient(config))
    print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2))
    return 0 if candidate.review_state == "proposed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
