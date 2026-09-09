#!/usr/bin/env python3
"""Reconcile our figures against the official MoSPI MPLADS dashboard.

The problem statement names https://mplads.mospi.gov.in/digigov/dashboard.html
as the dataset. We load from Empowered Indian, which aggregates that portal and
publishes clean CSV exports the official site does not - but "an aggregator of
the official source" is a claim, and a claim about provenance should be
checkable rather than asserted. This checks it.

The portal's own pre-login dashboard calls these endpoints, so they are the
public interface of the designated dataset:

    POST /rest/PreLoginDashboardData/getTilesData      {"uname": "<combo>"}
    POST /rest/PreLoginDashboardData/getTenureData     {"uname": "<combo>"}
    POST /rest/PreLoginDashboardData/getStateData      {}

`combo` is "0,0,<tenure>,<house>". House 2 is Lok Sabha, 1 is Rajya Sabha, 0 is
both - which is the whole reason the official totals looked wrong beside ours at
first glance: the dashboard opens on Lok Sabha only (Rs 8,333.67 Cr) while our
figures cover both houses (Rs 11,702.42 Cr officially).

Usage:
    python3 scripts/verify_mospi.py
"""

import json
import os
import pathlib
import re
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

BASE = "https://mplads.mospi.gov.in/rest/PreLoginDashboardData/"
BOTH_HOUSES = "0,0,0,0"
CRORE = 1e7
ALLOC = "Allocated Limit for Hon'ble MPs"
EXPEND = "Expenditure on Completed and On-going Works as on Date"


def post(endpoint, payload):
    request = urllib.request.Request(
        BASE + endpoint,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            # Named so the portal's operators can see who is calling and why.
            "User-Agent": "kasauti/1.0 (SIH26102 MPLADS oversight; reconciliation)",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        # The portal serves cp1252 rupee signs and non-breaking spaces, which
        # strict UTF-8 decoding rejects outright.
        return json.loads(response.read().decode("utf-8", "replace"))


def rupees(text):
    """'�83,33,66,73,298.01' -> 83336673298.01"""
    digits = re.sub(r"[^\d.]", "", text or "")
    return float(digits) if digits else 0.0


def official(combo=BOTH_HOUSES):
    tiles = post("getTilesData", {"uname": combo})
    first = lambda key, i=0: (tiles.get(key) or [""])[i]
    return {
        "allocated": rupees(first(ALLOC)),
        "expenditure": rupees(first(EXPEND)),
        "recommended_works": int(rupees(first("Works Recommended"))),
        "recommended_value": rupees(first("Works Recommended", 1)),
        "sanctioned_works": int(rupees(first("Works Sanctioned"))),
        "sanctioned_value": rupees(first("Works Sanctioned", 1)),
        "completed_works": int(rupees(first("Works Completed"))),
        "completed_value": rupees(first("Works Completed", 1)),
        "tenure": (tiles.get("Current Tenure") or [{}])[0].get("CAPTION"),
    }


def ours():
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(allocated_amount), 0)::float,
                       COALESCE(SUM(total_expenditure), 0)::float
                FROM mps WHERE ls_term = 18
            """)
            allocated, expenditure = cur.fetchone()
            cur.execute("""
                SELECT COUNT(*) FILTER (WHERE work_status = 'recommended'),
                       COUNT(*) FILTER (WHERE work_status = 'completed'),
                       COALESCE(SUM(expenditure) FILTER (WHERE work_status='completed'), 0)::float
                FROM projects WHERE ls_term = 18
            """)
            recommended, completed, completed_value = cur.fetchone()
    finally:
        conn.close()
    return {
        "allocated": allocated,
        "expenditure": expenditure,
        # Ours counts every work on record; the portal's "Works Recommended"
        # counts the whole pipeline, so recommended + completed is the
        # comparable figure.
        "recommended_works": recommended + completed,
        "completed_works": completed,
        "completed_value": completed_value,
    }


def store(rows, tenure):
    """Persist the comparison so the interface can show it without calling the
    portal on every page load."""
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute("TRUNCATE source_reconciliation")
            for name, ours_v, theirs_v, unit in rows:
                gap = (ours_v - theirs_v) / theirs_v * 100 if theirs_v else None
                cur.execute(
                    """INSERT INTO source_reconciliation
                       (metric, ours, official, unit, gap_pct, note)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    [name, round(ours_v, 2), round(theirs_v, 2),
                     "crore" if unit else "count",
                     None if gap is None else round(gap, 2),
                     f"Official MoSPI dashboard, both houses, {tenure}"],
                )
    finally:
        conn.close()


def main():
    try:
        theirs = official()
    except Exception as err:  # noqa: BLE001
        print(f"Could not reach the official portal: {str(err)[:120]}")
        return 2
    mine = ours()

    print(f"Official MoSPI dashboard, both houses, {theirs['tenure']}")
    print(f"{'figure':22}{'ours':>18}{'MoSPI':>18}{'gap':>10}")
    rows = [
        ("Allocated", mine["allocated"] / CRORE, theirs["allocated"] / CRORE, "Cr"),
        ("Expenditure", mine["expenditure"] / CRORE, theirs["expenditure"] / CRORE, "Cr"),
        ("Works in pipeline", mine["recommended_works"], theirs["recommended_works"], ""),
        ("Works completed", mine["completed_works"], theirs["completed_works"], ""),
        ("Completed value", mine["completed_value"] / CRORE, theirs["completed_value"] / CRORE, "Cr"),
    ]
    worst = 0.0
    for name, a, b, unit in rows:
        gap = (a - b) / b * 100 if b else float("nan")
        worst = max(worst, abs(gap))
        fmt = (lambda v: f"{v:,.1f} {unit}") if unit else (lambda v: f"{v:,.0f}")
        print(f"{name:22}{fmt(a):>18}{fmt(b):>18}{gap:>9.1f}%")

    try:
        store(rows, theirs["tenure"])
        print("\nrecorded in source_reconciliation")
    except Exception as err:  # noqa: BLE001 - reporting must not fail the check
        print(f"\ncould not record: {str(err)[:100]}")

    print(f"largest gap: {worst:.1f}%")
    print("\nThe portal also publishes a stage we do not model: Works Sanctioned, "
          f"{theirs['sanctioned_works']:,} works worth "
          f"Rs {theirs['sanctioned_value']/CRORE:,.0f} Cr, sitting between "
          "recommended and completed. The export we load has no sanction flag, "
          "so a work here is recommended or completed and nothing in between.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
