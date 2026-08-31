"""Vendor concentration at the implementing-agency grain.

WHY THIS EXISTS
---------------
Every other risk signal in this system is about a work: its cost, its delay,
whether it duplicates another. Vendor concentration is about the agency doing
the spending, and it is the closest thing this dataset holds to a
procurement-capture indicator: an implementing agency that routes most of its
money through one vendor is not necessarily doing anything wrong, but it is the
kind of thing a verifier should look at.

The expenditure extract carries 62,680 distinct vendors across 772 agencies and
270,934 transactions. load_real_data.py has kept the file on disk unused since
the real-data ingest; this reads it.

WHY IT IS NOT ATTACHED TO WORKS
-------------------------------
The expenditure file has no Work ID, and its `Work Description` holds one of
just 119 coarse category labels across all 270,934 rows, not a per-work
description. There is no join to an individual work and none is attempted (see
load_real_data.py's own note). Concentration is therefore computed per
implementing agency and reaches a work only through that work's agency.

Terms are pooled. The `projects` table carries no ls_term column, so a
per-term profile could not be joined back to a work anyway; the raw
`expenditures` rows keep theirs for when that changes.
"""

import pandas as pd

# Herfindahl-Hirschman Index of vendor share of an agency's spend. 1.0 is a
# single vendor taking everything; 1/n is n vendors sharing equally. The ramp
# below starts at 0.10 (roughly ten equal vendors) and saturates at 0.60
# (roughly one vendor taking three-quarters).
HHI_FLOOR = 0.10
HHI_CEILING = 0.60

# An agency with a handful of transactions produces a meaningless HHI: two
# payments to one vendor is 1.0 and says nothing. Below this, concentration
# scores 0.
MIN_TRANSACTIONS = 20

# Payment ageing. 4,480 of 270,934 transactions sit at 'Payment In-Progress' -
# a narrow but high-precision signal, so it earns a small weight rather than none.
PENDING_FLOOR_DAYS = 90
PENDING_CEILING_DAYS = 730

PAYMENT_SUCCESS = "Payment Success"


def ramp(value, floor, ceiling):
    """0 at or below floor, 100 at or above ceiling, linear between."""
    if value is None or pd.isna(value):
        return 0.0
    if value <= floor:
        return 0.0
    return float(min((value - floor) / (ceiling - floor) * 100, 100.0))


def vendor_hhi(amounts_by_vendor):
    """HHI over a Series of spend indexed by vendor.

    Uses spend share, not transaction count: an agency that pays one vendor
    once for most of its budget is concentrated even if it pays fifty others
    small amounts often.
    """
    total = amounts_by_vendor.sum()
    if total <= 0:
        return 0.0
    shares = amounts_by_vendor / total
    return float((shares**2).sum())


def concentration_risk(hhi, transaction_count):
    if transaction_count is None or transaction_count < MIN_TRANSACTIONS:
        return 0.0
    return round(ramp(hhi, HHI_FLOOR, HHI_CEILING), 2)


def pending_risk(oldest_pending_days):
    return round(ramp(oldest_pending_days, PENDING_FLOOR_DAYS, PENDING_CEILING_DAYS), 2)


def build_agency_vendor_profile(expenditures, as_of):
    """One row per implementing agency, from raw expenditure transactions.

    `expenditures` needs columns: implementing_agency, vendor,
    expenditure_amount, expenditure_date, payment_status.
    """
    if expenditures.empty:
        return pd.DataFrame(
            columns=[
                "implementing_agency", "vendor_count", "transaction_count",
                "total_spend", "vendor_hhi", "top_vendor", "top_vendor_share_pct",
                "pending_count", "oldest_pending_days", "concentration_risk",
            ]
        )

    as_of = pd.Timestamp(as_of)
    dates = pd.to_datetime(expenditures["expenditure_date"], errors="coerce")
    pending_mask = expenditures["payment_status"] != PAYMENT_SUCCESS

    rows = []
    for agency, group in expenditures.groupby("implementing_agency", sort=False):
        by_vendor = group.groupby("vendor")["expenditure_amount"].sum().sort_values(ascending=False)
        total = float(by_vendor.sum())
        pending = group[pending_mask.loc[group.index]]
        oldest = dates.loc[pending.index].min()
        hhi = vendor_hhi(by_vendor)
        transaction_count = int(len(group))
        rows.append({
            "implementing_agency": agency,
            "vendor_count": int(by_vendor.size),
            "transaction_count": transaction_count,
            "total_spend": round(total, 2),
            "vendor_hhi": round(hhi, 4),
            "top_vendor": by_vendor.index[0] if by_vendor.size else None,
            "top_vendor_share_pct": round(float(by_vendor.iloc[0] / total * 100), 2) if total > 0 else 0.0,
            "pending_count": int(len(pending)),
            "oldest_pending_days": 0 if pd.isna(oldest) else int((as_of - oldest).days),
            "concentration_risk": concentration_risk(hhi, transaction_count),
        })
    return pd.DataFrame(rows)


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def concentration_reason(row):
    """The sentence a verifier acts on, or None when there is nothing to say."""
    if not row.get("concentration_risk"):
        return None
    return (
        f"{float(row['top_vendor_share_pct']):.0f}% of this agency's "
        f"Rs {float(row['total_spend']):,.0f} spend went to one vendor "
        f"({row['top_vendor']}), across {_plural(int(row['vendor_count']), 'vendor')} "
        f"and {_plural(int(row['transaction_count']), 'transaction')}"
    )


def pending_reason(row):
    if not pending_risk(row.get("oldest_pending_days")):
        return None
    return (
        f"{_plural(int(row['pending_count']), 'payment')} still in progress, "
        f"oldest {int(row['oldest_pending_days'])} days"
    )
