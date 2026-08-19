# GhostPost

GhostPost is an independent, unofficial transcription and searchable catalog of correspondence received by Luigi Mangione while in custody.

The project records only the limited metadata present in the public handwritten mail catalog: received date, sender initials, the last two ZIP-code digits or a geographic label, postmark information, and source-page provenance. It does **not** catalog full sender names, addresses, or letter contents.

## Current source

As of **2026-08-19**, the official legal-defense site links **MDC Mail Log 12.26.24 – 04.26.26**, an 82-page handwritten catalog covering mail received from 2024-12-26 through 2026-04-26.

- Catalog page: <https://www.luigimangioneinfo.com/pages/mail-catalog/>
- Source metadata: [`data/sources.json`](data/sources.json)
- Canonical transcription: [`data/mail_catalog.csv`](data/mail_catalog.csv)
- Browser-facing generated data: [`catalog.json`](catalog.json)

GhostPost does not mirror the source PDF. Every transcribed record keeps its source page and reading-order number so a questionable entry can be checked against the original.

## Project status

The data pipeline has been rebuilt for the current catalog format. The transcription is still a work in progress. The initial seed is the newest appendix page (PDF page 82), which makes the latest published material searchable while the older pages are backfilled.

The website displays transcription coverage prominently so partial data cannot be mistaken for a complete copy of the 82-page source.

## Data model

Each CSV row contains:

| Field | Meaning |
| --- | --- |
| `received_date` | Date the catalog groups the item as received, ISO `YYYY-MM-DD` |
| `sender_initials` | Initials exactly as transcribed, including `?` when uncertain |
| `origin_type` | `zip_suffix`, `geographic_label`, or `unknown` |
| `origin_value` | Two ZIP digits, the bracketed place label, or `?` |
| `postmark_date` | ISO postmark date when unambiguous |
| `postmark_raw` | The date/marking as written in the source |
| `postmark_status` | `known`, `unknown`, or `not_listed` |
| `source_page` | 1-based PDF page number |
| `source_entry` | Reading-order number within that page |
| `source_marker` | Superscript/footnote marker preserved from the source when present |
| `raw_entry` | Compact transcription of the handwritten entry |
| `transcription_status` | `reviewed` or `needs_review` |
| `notes` | Ambiguity or transcription notes |

The JSON Schema lives at [`schema/catalog.schema.json`](schema/catalog.schema.json).

## Build the catalog

No third-party Python packages are required.

```bash
python scripts/build_catalog.py
```

For compatibility with the old project command, this also works:

```bash
python csv_to_json_convert.py
```

The builder validates dates, enums, ZIP suffixes, unique source locators, and required fields before replacing `catalog.json`.

## Preview the site locally

Browsers normally block `fetch()` from `file://` pages, so serve the repository directory instead of double-clicking `index.html`:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/`.

## Transcription workflow

1. Open the official source PDF and choose the next untranscribed page.
2. Add rows to `data/mail_catalog.csv`, preserving questionable characters with `?` rather than guessing.
3. Keep the handwritten shorthand in `postmark_raw` and `raw_entry`.
4. Set `transcription_status` to `needs_review` when the handwriting or source marker is ambiguous.
5. Run `python scripts/build_catalog.py`.
6. Compare the generated site against the source page before committing.

## Disclaimer

GhostPost is not affiliated with Luigi Mangione, his attorneys, or the official legal-defense site. It is an independent archival/transcription project. The handwritten source is authoritative over this transcription, and transcription errors are possible.
