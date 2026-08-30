# Data snapshot

`mplads_2026-08-30.zip` (4.4 MB, 33.9 MB uncompressed) holds the two work-level
CSVs the pipeline reads:

- `mplads_recommended_works_2026-08-30.csv` — 83,968 recommended works
- `mplads_completed_works_2026-08-30.csv` — 43,735 completed works

Committed so the pipeline is reproducible from a clone alone: no external
hosting, no credentials beyond a database URL.

## Source

MPLADS programme data, obtained via [Empowered Indian](https://empoweredindian.in),
which aggregates the official MoSPI MPLADS portal. MPLADS records are public
government data.

Our loaded total (₹23,821,967,508.61) reconciles against the published
`completedWorksValue` of ₹23,869,325,463.61: the difference of ₹47,357,955.00 is
exactly the 85 completed works rejected for having no work description, which
cannot participate in duplicate detection.

## Reproducing the full pipeline

```bash
unzip data/snapshot/mplads_2026-08-30.zip -d mplads-data
export MPLADS_DATA_DIR=mplads-data
export DATABASE_URL='postgres://...'

python -m venv data/.venv && source data/.venv/bin/activate
pip install -r data/requirements.txt

python data/schema.sql        # or apply schema.sql to your database
python data/load_real_data.py # ~1 min
python data/scoring.py        # ~15-20 min (embeds 127k descriptions)
```

The loader resolves the newest `mplads_<kind>_*.csv` in `MPLADS_DATA_DIR`, so
dropping in a later snapshot works without code changes.

## Refreshing with newer data

Replace this zip with a newer snapshot using the same filename convention
(`mplads_recommended_works_YYYY-MM-DD.csv`), and the nightly workflow picks it
up. To pull from a live source instead, set the `MPLADS_DATA_URL` repository
secret to a URL serving an equivalent zip — the workflow prefers it over this
committed snapshot.
