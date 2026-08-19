#!/usr/bin/env python3
"""Build GhostPost's browser-facing JSON from the canonical CSV transcription.

The CSV is deliberately the source of truth because it is easy to audit, edit in a
spreadsheet, diff in Git, and review against the handwritten source. The generated
catalog.json is deterministic: running this script twice without changing the inputs
produces the same output.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


# Resolve every path from the repository root instead of from the caller's current
# working directory. This keeps the script predictable whether it is run from the
# repo root, scripts/, an IDE, or a CI job.
REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "mail_catalog.csv"
SOURCE_PATH = REPO_ROOT / "data" / "sources.json"
OUTPUT_PATH = REPO_ROOT / "catalog.json"

FIELDS = [
    "received_date",
    "sender_initials",
    "origin_type",
    "origin_value",
    "postmark_date",
    "postmark_raw",
    "postmark_status",
    "source_page",
    "source_entry",
    "source_marker",
    "raw_entry",
    "transcription_status",
    "notes",
]

ORIGIN_TYPES = {"zip_suffix", "geographic_label", "unknown"}
POSTMARK_STATUSES = {"known", "unknown", "not_listed"}
TRANSCRIPTION_STATUSES = {"reviewed", "needs_review"}
INITIALS_RE = re.compile(r"^[A-Z?]{1,4}$")
ZIP_SUFFIX_RE = re.compile(r"^\d{2}$")


class CatalogError(ValueError):
    """Raised for a human-fixable data validation problem."""


def parse_iso_date(value: str, *, field: str, row_number: int) -> str:
    """Validate an ISO date while preserving the original string value."""
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(
            f"row {row_number}: {field} must be YYYY-MM-DD, got {value!r}"
        ) from exc
    return value


def load_sources() -> dict:
    """Load the source metadata embedded into the generated catalog."""
    try:
        payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CatalogError(f"missing source metadata: {SOURCE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"invalid JSON in {SOURCE_PATH}: {exc}") from exc

    source = payload.get("primary_source")
    if not isinstance(source, dict):
        raise CatalogError("data/sources.json must contain a primary_source object")
    return source


def normalize_row(raw: dict[str, str], row_number: int) -> dict:
    """Trim, validate, and type-convert one CSV row."""
    row = {field: (raw.get(field) or "").strip() for field in FIELDS}

    row["received_date"] = parse_iso_date(
        row["received_date"], field="received_date", row_number=row_number
    )

    initials = row["sender_initials"].upper()
    if not INITIALS_RE.fullmatch(initials):
        raise CatalogError(
            f"row {row_number}: sender_initials must contain only A-Z or ?, got {initials!r}"
        )
    row["sender_initials"] = initials

    if row["origin_type"] not in ORIGIN_TYPES:
        raise CatalogError(
            f"row {row_number}: invalid origin_type {row['origin_type']!r}"
        )

    if not row["origin_value"]:
        raise CatalogError(f"row {row_number}: origin_value may not be blank")

    if row["origin_type"] == "zip_suffix" and not ZIP_SUFFIX_RE.fullmatch(
        row["origin_value"]
    ):
        raise CatalogError(
            f"row {row_number}: zip_suffix origin_value must be exactly two digits"
        )

    if row["postmark_status"] not in POSTMARK_STATUSES:
        raise CatalogError(
            f"row {row_number}: invalid postmark_status {row['postmark_status']!r}"
        )

    if row["postmark_status"] == "known":
        if not row["postmark_date"]:
            raise CatalogError(
                f"row {row_number}: known postmark requires postmark_date"
            )
        row["postmark_date"] = parse_iso_date(
            row["postmark_date"], field="postmark_date", row_number=row_number
        )
    elif row["postmark_date"]:
        raise CatalogError(
            f"row {row_number}: {row['postmark_status']} postmark must not have postmark_date"
        )

    if row["transcription_status"] not in TRANSCRIPTION_STATUSES:
        raise CatalogError(
            f"row {row_number}: invalid transcription_status {row['transcription_status']!r}"
        )

    for integer_field in ("source_page", "source_entry"):
        try:
            value = int(row[integer_field])
        except ValueError as exc:
            raise CatalogError(
                f"row {row_number}: {integer_field} must be an integer"
            ) from exc
        if value < 1:
            raise CatalogError(
                f"row {row_number}: {integer_field} must be greater than zero"
            )
        row[integer_field] = value

    if not row["raw_entry"]:
        raise CatalogError(f"row {row_number}: raw_entry may not be blank")

    return row


def load_entries() -> list[dict]:
    """Read and validate the canonical CSV transcription."""
    try:
        handle = CSV_PATH.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError as exc:
        raise CatalogError(f"missing canonical CSV: {CSV_PATH}") from exc

    with handle:
        reader = csv.DictReader(handle)
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise CatalogError(
                "data/mail_catalog.csv is missing columns: " + ", ".join(missing)
            )

        entries = [
            normalize_row(raw, row_number)
            for row_number, raw in enumerate(reader, start=2)
            if any((value or "").strip() for value in raw.values())
        ]

    # Stable ordering makes Git diffs boring and useful. source_entry preserves the
    # handwritten reading order when several records share a received date/page.
    entries.sort(
        key=lambda entry: (
            entry["received_date"],
            entry["source_page"],
            entry["source_entry"],
        )
    )

    # A page/entry pair is our source locator and therefore must be unique.
    seen: set[tuple[int, int]] = set()
    for entry in entries:
        locator = (entry["source_page"], entry["source_entry"])
        if locator in seen:
            raise CatalogError(
                f"duplicate source locator page={locator[0]} entry={locator[1]}"
            )
        seen.add(locator)

    return entries


def build() -> dict:
    """Assemble the deterministic JSON payload consumed by index.html."""
    source = load_sources()
    entries = load_entries()
    transcribed_pages = sorted({entry["source_page"] for entry in entries})

    return {
        "schema_version": 1,
        "source": source,
        "entry_count": len(entries),
        "transcribed_pages": transcribed_pages,
        "entries": entries,
    }


def main() -> int:
    try:
        payload = build()
    except CatalogError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 1

    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"[+] wrote {payload['entry_count']} entries from "
        f"{len(payload['transcribed_pages'])} source page(s) to {OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
