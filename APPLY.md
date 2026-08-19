# Apply this refresh

This directory contains replacement/new files for the GhostPost repository. It intentionally does not include the existing `reference_images/` directory or other archival files.

From the root of your local `GhostPost` clone, create a branch first:

```bash
git switch main
git pull --ff-only
git switch -c catalog-pipeline-refresh
```

Copy the contents of `GhostPost-refresh/` into the repository root, overwriting `.gitignore`, `README.md`, `csv_to_json_convert.py`, and `index.html` when prompted. Do **not** delete files that are not present in the refresh package.

Then validate and commit:

```bash
python3 scripts/build_catalog.py
python3 -m json.tool catalog.json >/dev/null
git status --short
git add .gitignore README.md TRANSCRIPTION_NOTES.md catalog.json csv_to_json_convert.py \
  data/mail_catalog.csv data/sources.json index.html schema/catalog.schema.json scripts/build_catalog.py
git commit -m "refresh catalog pipeline"
git push -u origin catalog-pipeline-refresh
```

Open a pull request from `catalog-pipeline-refresh` to `main` after reviewing the diff.
