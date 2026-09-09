"""Cohort-level detectors: findings about agencies and MPs, not about works.

WHY THESE ARE SEPARATE FROM THE RISK SCORE
------------------------------------------
overall_risk_score answers "is this work unusual for its peers", and its five
components are each a property of the work. The four detectors here are
properties of a *population* - how an agency's payments fall across a year,
how its sanction amounts are distributed, how much of an MP's allocation is
still sitting there. Folding a population statistic into a single work's score
would attribute a collective pattern to whichever work happened to be in it,
which is exactly the mistake that makes a risk score unusable in a hearing.

So they are written to detector_findings, keyed on the cohort they describe,
and rendered as their own list. Nothing here moves a work's score.

WHAT EACH ONE IS AND IS NOT
---------------------------
D-01 Year-end payment burst. India's fiscal year closes on 31 March, and money
     unspent by then can lapse. An agency pushing most of a year's payments
     into that one month is the classic "spend it or lose it" pattern. Measured
     on the 2026-08-31 snapshot, 163 of 2,134 agency-years with at least 30
     payments put 40% or more of them in March, and 85 put 60% or more, against
     a flat-year expectation of 8.3%. It is not evidence of anything: an agency
     whose sanctions all arrive in Q4 will look identical.

D-02 First-digit anomaly. Genuine accounting amounts spanning several orders of
     magnitude tend to follow Benford's law. Pooled across all 270,934 payments
     the extract fits loosely - digit 1 at 29.24% against 30.10% expected - but
     per agency it does not fit at all: the median agency-term scores a MAD of
     6.2 percentage points, where Nigrini calls anything above 1.5
     "nonconformity". Administrative payments are capped, rounded and repeated
     by design, so the whole population breaks the law and an absolute
     threshold would flag every agency in the country. This detector therefore
     ranks each agency against its peers rather than against the law. It is the
     weakest of the four, it is a lead and never a finding, and the interface
     says so where it is displayed.

D-03 Idle allocation. Straight from the source's own MP summary: allocation,
     expenditure and the unspent balance. Average utilisation across 1,547
     MP-terms is 48.6%, so the median MP-term has over half its money still
     sitting there and only the worst quarter is surfaced. This is the "inefficiency" half of the brief rather
     than the "anomaly" half, and it carries no suspicion at all - MPLADS funds
     stay spendable after a term ends, so a low figure in a running term is
     normal and is reported as a figure, not an alarm.

D-04 Uniform sanction amount. Not threshold-splitting: the data does not show
     mass gathering just under a ceiling, it shows round numbers everywhere
     (22,021 works at exactly Rs 5,00,000). What it does show is agencies where
     a single amount covers every work they sanctioned - SHAHJAHANPUR's 321
     works all at Rs 2,43,000, BOKARO's 291 all at Rs 22,000. A blanket figure
     applied to hundreds of different works is not per-work costing.
"""

import math

import numpy as np
import pandas as pd

# --- D-01 ------------------------------------------------------------------
# Below this an agency-year's monthly split is noise: 6 payments landing in
# March is 50% and means nothing.
BURST_MIN_PAYMENTS = 30
# A flat year puts 1/12 (8.3%) of payments in March. Calibrated against the
# 2,134 qualifying agency-years in the 2026-08-31 snapshot, whose March share
# runs p50=5.4%, p75=15.2%, p90=32.9%, p95=53.3%. The floor sits between p75
# and p90 so roughly the worst sixth surfaces, and the ceiling above p95 so
# severity still separates the extremes instead of everything reading 100.
BURST_FLOOR_PCT = 25.0
BURST_CEILING_PCT = 75.0

# --- D-02 ------------------------------------------------------------------
# Benford needs both a sample and a spread. 150 payments is the usual floor
# quoted for a first-digit test to mean anything at the digit level.
BENFORD_MIN_PAYMENTS = 150
# Mean absolute deviation across the nine digits, in percentage points.
#
# Nigrini's published bands - "close conformity" under 0.6, "nonconformity"
# above 1.5 - are useless here, and finding that out is itself a result: across
# the 587 agency-terms with enough payments, the MAD runs p50=6.2, p75=8.9,
# p90=11.2, p99=15.3. Every single one is "nonconformant" by the textbook.
#
# That is not 587 frauds. MPLADS payments are capped, rounded and repeated by
# design, so the population simply does not follow Benford, and an absolute
# threshold would flag all of it. These bounds are therefore peer-relative -
# p75 and just above p99 of the observed distribution - so the detector ranks
# an agency against other agencies rather than against a law its whole
# population breaks. It is the weakest of the four, and the UI says so.
BENFORD_FLOOR_MAD = 9.0
BENFORD_CEILING_MAD = 15.5

# --- D-03 ------------------------------------------------------------------
# An MP-term with a token allocation produces a meaningless percentage.
IDLE_MIN_ALLOCATION = 1_00_00_000  # Rs 1 crore
# Unspent share across the 1,540 qualifying MP-terms runs p50=52.6%, p75=80.0%,
# p90=97.9%. Half of every allocation being unspent is the norm here, so a
# floor anywhere near it flags almost everybody and identifies nobody. p75 is
# the floor: 385 MP-terms, the worst quarter.
IDLE_FLOOR_PCT = 80.0
IDLE_CEILING_PCT = 100.0
# An MP who has recommended nothing has not started, which is a different thing
# from money sitting idle and mostly catches members seated part-way through a
# term. 88 of the 385 MP-terms over the floor are in that position; excluding
# them leaves 297, and every one of those has recommended works to show for the
# allocation it has not spent.
IDLE_MIN_RECOMMENDED_WORKS = 1

# --- D-04 ------------------------------------------------------------------
UNIFORM_MIN_WORKS = 25
# Round amounts are normal, so the ramp only opens well above what a district
# repeating Rs 5,00,000 for genuinely similar works would produce. Across 1,285
# qualifying agency-terms the share on the commonest amount runs p50=22.5%,
# p90=47.2%, p99=83.0%, max 97.8% - so this floor is about p87 and the ceiling
# sits beyond p99.
UNIFORM_FLOOR_PCT = 40.0
UNIFORM_CEILING_PCT = 95.0

FISCAL_YEAR_END_MONTH = 3

BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) * 100 for d in range(1, 10)}

FINDING_COLUMNS = [
    "code", "subject_type", "subject", "ls_term", "period",
    "severity", "headline", "evidence",
]


def ramp(value, floor, ceiling):
    """0 at or below floor, 100 at or above ceiling, linear between."""
    if value is None or pd.isna(value):
        return 0.0
    if value <= floor:
        return 0.0
    return float(min((value - floor) / (ceiling - floor) * 100, 100.0))


def fiscal_year(dates):
    """Indian fiscal year label for a date series: April 2024 -> '2024-25'."""
    year = dates.dt.year
    start = year.where(dates.dt.month > FISCAL_YEAR_END_MONTH, year - 1)
    return start.astype("Int64").astype(str) + "-" + (start % 100 + 1).astype("Int64").astype(str).str.zfill(2)


def first_digit(amounts):
    """Leading digit of the absolute value, dropping anything under 1.

    Vectorised through numpy rather than a per-row map: this runs once per
    agency over 270,934 payments in total, and the elementwise version was the
    slowest thing in the detector pass by a wide margin. String slicing is
    slower still - formatting Decimals dominated an earlier attempt.
    """
    a = pd.to_numeric(amounts, errors="coerce").abs()
    a = a[a.notna() & (a >= 1)].astype(float)
    if a.empty:
        return pd.Series(dtype=int)
    lead = np.floor(a / np.power(10.0, np.floor(np.log10(a.to_numpy()))))
    return lead.astype(int)


def digit_shares(digits):
    """Observed percentage per leading digit, and the sample size."""
    counts = digits.value_counts()
    total = int(counts.sum())
    if total == 0:
        return {}, 0
    return {d: counts.get(d, 0) / total * 100 for d in range(1, 10)}, total


def mad_from_shares(observed):
    """Mean absolute deviation from Benford, in percentage points."""
    return float(
        sum(abs(observed.get(d, 0.0) - BENFORD_EXPECTED[d]) for d in range(1, 10)) / 9
    )


def benford_mad(amounts):
    """Mean absolute deviation from Benford's first-digit law, or None when
    there is not enough to compare."""
    digits = first_digit(amounts)
    if len(digits) < BENFORD_MIN_PAYMENTS:
        return None
    observed, total = digit_shares(digits)
    if total == 0:
        return None
    return mad_from_shares(observed)


def _finding(code, subject_type, subject, ls_term, period, severity, headline, evidence):
    return {
        "code": code,
        "subject_type": subject_type,
        "subject": subject,
        "ls_term": None if ls_term is None or pd.isna(ls_term) else int(ls_term),
        "period": period,
        "severity": round(float(severity), 2),
        "headline": headline,
        "evidence": evidence,
    }


def year_end_burst(expenditures):
    """D-01. Share of an agency's fiscal-year payments falling in March."""
    df = expenditures.dropna(subset=["expenditure_date"]).copy()
    if df.empty:
        return []
    df["expenditure_date"] = pd.to_datetime(df["expenditure_date"])
    df["fy"] = fiscal_year(df["expenditure_date"])
    df["is_march"] = df["expenditure_date"].dt.month == FISCAL_YEAR_END_MONTH

    grouped = df.groupby(["implementing_agency", "ls_term", "fy"], dropna=False).agg(
        payments=("expenditure_amount", "size"),
        march_payments=("is_march", "sum"),
        march_amount=("expenditure_amount", lambda s: float(s[df.loc[s.index, "is_march"]].sum())),
        total_amount=("expenditure_amount", "sum"),
    )
    grouped = grouped[grouped["payments"] >= BURST_MIN_PAYMENTS]
    if grouped.empty:
        return []
    grouped["march_share"] = grouped["march_payments"] / grouped["payments"] * 100

    out = []
    for (agency, term, fy), row in grouped.iterrows():
        severity = ramp(row["march_share"], BURST_FLOOR_PCT, BURST_CEILING_PCT)
        if severity <= 0:
            continue
        out.append(_finding(
            "D-01", "agency", agency, term, fy, severity,
            f"{row['march_share']:.0f}% of this agency's {int(row['payments'])} payments in "
            f"FY {fy} were made in March alone",
            {
                "payments": int(row["payments"]),
                "march_payments": int(row["march_payments"]),
                "march_share_pct": round(float(row["march_share"]), 1),
                "march_amount": round(float(row["march_amount"]), 2),
                "total_amount": round(float(row["total_amount"]), 2),
                "expected_share_pct": round(100 / 12, 1),
            },
        ))
    return out


def first_digit_anomaly(expenditures):
    """D-02. Departure from Benford's first-digit law, per agency and term."""
    out = []
    if expenditures.empty:
        return out
    for (agency, term), group in expenditures.groupby(
        ["implementing_agency", "ls_term"], dropna=False
    ):
        # Digits are extracted once and reused for the MAD, the severity and
        # the evidence. Calling benford_mad() here and then re-deriving the
        # distribution for the evidence walked every payment twice.
        digits = first_digit(group["expenditure_amount"])
        if len(digits) < BENFORD_MIN_PAYMENTS:
            continue
        shares, total = digit_shares(digits)
        if total == 0:
            continue
        mad = mad_from_shares(shares)
        severity = ramp(mad, BENFORD_FLOOR_MAD, BENFORD_CEILING_MAD)
        if severity <= 0:
            continue
        observed = {str(d): round(v, 2) for d, v in shares.items()}
        worst = max(range(1, 10), key=lambda d: abs(shares.get(d, 0.0) - BENFORD_EXPECTED[d]))
        out.append(_finding(
            "D-02", "agency", agency, term, None, severity,
            f"Leading digits across {total} payments depart from the expected "
            f"distribution (MAD {mad:.2f}); digit {worst} appears "
            f"{observed[str(worst)]:.1f}% against {BENFORD_EXPECTED[worst]:.1f}% expected",
            {
                "payments": total,
                "mad": round(mad, 3),
                "observed_pct": observed,
                "expected_pct": {str(d): round(v, 2) for d, v in BENFORD_EXPECTED.items()},
                "worst_digit": worst,
            },
        ))
    return out


def idle_allocation(mps):
    """D-03. How much of an MP-term's allocation is still unspent."""
    df = mps.dropna(subset=["allocated_amount"]).copy()
    df = df[df["allocated_amount"] >= IDLE_MIN_ALLOCATION]
    # df.get on a missing column returns None, and pd.to_numeric(None) is a
    # bare float rather than a Series - which is how this first shipped, and it
    # failed only against a real frame. Build the Series explicitly.
    recommended = (
        pd.to_numeric(df["recommended_works"], errors="coerce").fillna(0)
        if "recommended_works" in df.columns
        else pd.Series(IDLE_MIN_RECOMMENDED_WORKS, index=df.index)
    )
    df = df[recommended >= IDLE_MIN_RECOMMENDED_WORKS]
    if df.empty:
        return []
    unspent = pd.to_numeric(df["unspent_amount"], errors="coerce").fillna(0.0)
    allocated = pd.to_numeric(df["allocated_amount"], errors="coerce")
    df["unspent_share"] = (unspent / allocated * 100).clip(lower=0)

    out = []
    for _, row in df.iterrows():
        severity = ramp(row["unspent_share"], IDLE_FLOOR_PCT, IDLE_CEILING_PCT)
        if severity <= 0:
            continue
        rec = int(recommended.loc[row.name])
        done = 0 if pd.isna(row.get("completed_works")) else int(row["completed_works"])
        out.append(_finding(
            "D-03", "mp", row["mp_id"], row["ls_term"], None, severity,
            f"{row['mp_name']} has recommended {rec} works and completed {done}, "
            f"with {row['unspent_share']:.0f}% of the allocation unspent",
            {
                "mp_name": row["mp_name"],
                "constituency": row.get("constituency"),
                "state": row.get("state"),
                "allocated_amount": float(row["allocated_amount"]),
                "unspent_amount": float(unspent.loc[row.name]),
                "unspent_share_pct": round(float(row["unspent_share"]), 1),
                "utilization_pct": None if pd.isna(row.get("utilization_pct")) else float(row["utilization_pct"]),
                "recommended_works": rec,
                "completed_works": done,
            },
        ))
    return out


def uniform_sanction_amount(projects):
    """D-04. Share of an agency's works carrying its single commonest amount."""
    df = projects.dropna(subset=["sanctioned_amount"]).copy()
    if df.empty:
        return []
    out = []
    for (agency, term), group in df.groupby(["implementing_agency", "ls_term"], dropna=False):
        works = len(group)
        if works < UNIFORM_MIN_WORKS:
            continue
        counts = group["sanctioned_amount"].value_counts()
        amount = counts.index[0]
        share = counts.iloc[0] / works * 100
        severity = ramp(share, UNIFORM_FLOOR_PCT, UNIFORM_CEILING_PCT)
        if severity <= 0:
            continue
        out.append(_finding(
            "D-04", "agency", agency, term, None, severity,
            f"{share:.0f}% of this agency's {works} works were sanctioned at exactly "
            f"Rs {float(amount):,.0f}",
            {
                "works": works,
                "amount": float(amount),
                "works_at_amount": int(counts.iloc[0]),
                "share_pct": round(float(share), 1),
                "distinct_amounts": int(counts.size),
            },
        ))
    return out


def run_all(projects, expenditures, mps):
    """Every detector, as one list of findings ready for detector_findings."""
    findings = []
    findings += year_end_burst(expenditures)
    findings += first_digit_anomaly(expenditures)
    findings += idle_allocation(mps)
    findings += uniform_sanction_amount(projects)
    return findings
