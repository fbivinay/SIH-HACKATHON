#!/usr/bin/env python3
"""Pull MPLADS export CSVs from api.empoweredindian.in for both Lok Sabha terms.

The API defaults to ls_term=18, which is how the first dump ended up being half
the data. This fetches 17 and 18 explicitly and merges each dataset into one
file with an added ls_term column.

Usage:
    python3 scripts/fetch_mplads.py                # fetch all, skip existing
    python3 scripts/fetch_mplads.py --force        # re-fetch even if present
    python3 scripts/fetch_mplads.py --only mp-summary
    python3 scripts/fetch_mplads.py --self-check   # no network, tests merge logic
"""

import argparse
import csv
import datetime
import io
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://api.empoweredindian.in/api/export"
TERMS = (17, 18)
USER_AGENT = "mplads-risk-monitor/1.0 (SIH26102 research fetch)"
DATASETS = {
    "completed-works": "mplads_completed_works",
    "recommended-works": "mplads_recommended_works",
    "expenditures": "mplads_expenditures",
    "mp-summary": "mplads_mp_summary",
}
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "MPLADS DATA"

# csv fields hold long work descriptions; the default 128KB limit is fine today
# but the cost of not caring is a hard crash mid-download.
csv.field_size_limit(10 * 1024 * 1024)


def open_export(endpoint, ls_term, attempts=3):
    """GET one export as a streaming text handle. Retries on transient errors."""
    url = f"{API}/{endpoint}?ls_term={ls_term}"
    # The API 403s urllib's default User-Agent.
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            resp = urllib.request.urlopen(req, timeout=180)
            return io.TextIOWrapper(resp, encoding="utf-8", newline="")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts:
                raise
            print(f"    retry {attempt}/{attempts - 1} after {exc}", file=sys.stderr)
            time.sleep(2 * attempt)


def merge_terms(endpoint, out_path):
    """Write one CSV combining every term, with ls_term as the last column."""
    rows_written = 0
    header = None
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_ALL)
        for term in TERMS:
            print(f"  ls_term={term} ...", end="", flush=True)
            with open_export(endpoint, term) as stream:
                reader = csv.reader(stream)
                incoming_header = next(reader)
                if header is None:
                    header = incoming_header + ["ls_term"]
                    writer.writerow(header)
                elif incoming_header + ["ls_term"] != header:
                    raise SystemExit(
                        f"{endpoint}: header changed between terms\n"
                        f"  expected {header}\n  got      {incoming_header}"
                    )
                term_rows = 0
                for row in reader:
                    writer.writerow(row + [term])
                    term_rows += 1
            rows_written += term_rows
            print(f" {term_rows} rows")
    return header, rows_written


def verify(out_path):
    """Every row has a known ls_term and the right field count."""
    with out_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        width = len(header)
        seen = set()
        count = 0
        for n, row in enumerate(reader, start=2):
            if len(row) != width:
                raise SystemExit(f"{out_path.name}:{n}: {len(row)} fields, want {width}")
            seen.add(row[-1])
            count += 1
    if seen != {str(t) for t in TERMS}:
        raise SystemExit(f"{out_path.name}: ls_term values {sorted(seen)}, want {list(TERMS)}")
    return count


def self_check():
    """Merge logic survives quoted commas and embedded newlines. No network."""
    sample = '"Work ID","Work Description"\r\n1,"Road, phase 2\nsecond line"\r\n'

    real_open = globals()["open_export"]
    globals()["open_export"] = lambda endpoint, ls_term, attempts=3: io.StringIO(sample)
    try:
        tmp = OUT_DIR.parent / ".fetch_mplads_selfcheck.csv"
        header, rows = merge_terms("fake", tmp)
        assert header == ["Work ID", "Work Description", "ls_term"], header
        assert rows == len(TERMS), rows
        assert verify(tmp) == len(TERMS)
        with tmp.open(encoding="utf-8", newline="") as fh:
            body = list(csv.reader(fh))
        assert body[1][1] == "Road, phase 2\nsecond line", body[1]
        assert body[1][2] == "17" and body[2][2] == "18", body
        tmp.unlink()
    finally:
        globals()["open_export"] = real_open
    print("self-check ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing output")
    ap.add_argument("--only", choices=sorted(DATASETS), help="fetch one dataset")
    ap.add_argument("--self-check", action="store_true", help="test merge logic offline")
    args = ap.parse_args()

    if args.self_check:
        self_check()
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    wanted = [args.only] if args.only else list(DATASETS)

    for endpoint in wanted:
        out_path = OUT_DIR / f"{DATASETS[endpoint]}_{stamp}.csv"
        if out_path.exists() and not args.force:
            print(f"{endpoint}: {out_path.name} exists, skipping (--force to redo)")
            continue
        print(f"{endpoint}:")
        _, rows = merge_terms(endpoint, out_path)
        verified = verify(out_path)
        size_mb = out_path.stat().st_size / 1e6
        print(f"  -> {out_path.name}  {verified} rows  {size_mb:.1f} MB")
        assert verified == rows, (verified, rows)


if __name__ == "__main__":
    main()
