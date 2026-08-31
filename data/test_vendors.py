import pandas as pd
import pytest

from vendors import (
    build_agency_vendor_profile, concentration_reason, concentration_risk,
    pending_reason, pending_risk, vendor_hhi, MIN_TRANSACTIONS,
)


def _exp(agency, vendor, amount, day="2026-01-01", status="Payment Success", term=18):
    return {"implementing_agency": agency, "ls_term": term, "vendor": vendor,
            "expenditure_amount": float(amount), "expenditure_date": day,
            "payment_status": status}


def test_hhi_is_one_for_a_single_vendor():
    assert vendor_hhi(pd.Series({"A": 500.0})) == 1.0


def test_hhi_is_one_over_n_for_equal_vendors():
    assert vendor_hhi(pd.Series({"A": 25.0, "B": 25.0, "C": 25.0, "D": 25.0})) == pytest.approx(0.25)


def test_hhi_uses_spend_share_not_transaction_count():
    """One big payment to one vendor is concentration even if fifty small
    payments go elsewhere - which is the shape worth catching."""
    concentrated = pd.Series({"Big": 900.0, "Small": 100.0})
    spread = pd.Series({"Big": 500.0, "Small": 500.0})
    assert vendor_hhi(concentrated) > vendor_hhi(spread)


def test_hhi_of_no_spend_is_zero_not_a_crash():
    assert vendor_hhi(pd.Series(dtype=float)) == 0.0
    assert vendor_hhi(pd.Series({"A": 0.0})) == 0.0


def test_thin_agencies_score_no_concentration():
    """Two payments to one vendor is an HHI of 1.0 and means nothing."""
    assert concentration_risk(1.0, transaction_count=2) == 0.0
    assert concentration_risk(1.0, transaction_count=MIN_TRANSACTIONS) == 100.0


def test_concentration_risk_scales_between_floor_and_ceiling():
    assert concentration_risk(0.10, 100) == 0.0      # ~ten equal vendors
    mid = concentration_risk(0.35, 100)
    assert 0 < mid < 100
    assert concentration_risk(0.60, 100) == 100.0    # ~one vendor takes 3/4


def test_pending_risk_grows_with_the_oldest_unpaid_transaction():
    assert pending_risk(30) == 0.0
    assert pending_risk(0) == 0.0
    assert pending_risk(None) == 0.0
    assert 0 < pending_risk(400) < pending_risk(700)
    assert pending_risk(5000) == 100.0


def test_profile_aggregates_per_agency():
    df = pd.DataFrame([
        *[_exp("IDA-A", "Dominant Ltd", 100) for _ in range(20)],
        *[_exp("IDA-A", f"Small {i}", 1) for i in range(5)],
        *[_exp("IDA-B", f"Vendor {i}", 100) for i in range(25)],
    ])
    profile = build_agency_vendor_profile(df, as_of="2026-08-31").set_index("implementing_agency")

    a, b = profile.loc["IDA-A"], profile.loc["IDA-B"]
    assert a["vendor_count"] == 6 and a["transaction_count"] == 25
    assert a["top_vendor"] == "Dominant Ltd"
    assert a["top_vendor_share_pct"] == pytest.approx(99.75, abs=0.01)
    assert a["concentration_risk"] > 90          # one vendor takes nearly all
    assert b["concentration_risk"] == 0.0        # 25 equal vendors, HHI 0.04


def test_profile_measures_pending_payments_only():
    df = pd.DataFrame([
        *[_exp("IDA-A", "V", 100, day="2020-01-01") for _ in range(20)],
        _exp("IDA-A", "V", 100, day="2025-01-01", status="Payment In-Progress"),
    ])
    row = build_agency_vendor_profile(df, as_of="2026-01-01").iloc[0]
    assert row["pending_count"] == 1
    # aged from the pending row (2025), not the older successful ones (2020)
    assert row["oldest_pending_days"] == 365  # 2025 is not a leap year


def test_profile_of_no_expenditures_is_empty_not_a_crash():
    """A snapshot with no expenditure file is supported; it must cost the
    signal, not the run."""
    empty = build_agency_vendor_profile(pd.DataFrame(), as_of="2026-08-31")
    assert empty.empty
    assert "concentration_risk" in empty.columns


def test_reasons_name_the_vendor_and_the_basis():
    row = {"concentration_risk": 80.0, "top_vendor_share_pct": 74.0,
           "total_spend": 12500000.0, "top_vendor": "Aditya Construction",
           "vendor_count": 9, "transaction_count": 140}
    reason = concentration_reason(row)
    assert "74%" in reason
    assert "Aditya Construction" in reason
    assert "Rs 12,500,000" in reason
    assert "9 vendors" in reason and "140 transactions" in reason


def test_no_reason_when_there_is_nothing_to_say():
    assert concentration_reason({"concentration_risk": 0.0}) is None
    assert pending_reason({"oldest_pending_days": 10, "pending_count": 1}) is None


def test_terms_are_profiled_separately():
    """An agency's vendor mix in one Lok Sabha says nothing about the other.

    Pooling diluted both: a vendor taking everything in one term looked like a
    minority share across the pair.
    """
    df = pd.DataFrame([
        *[_exp("IDA-A", "Sole Ltd", 100, term=17) for _ in range(25)],
        *[_exp("IDA-A", f"Vendor {i}", 100, term=18) for i in range(25)],
    ])
    profile = build_agency_vendor_profile(df, as_of="2026-08-31")
    assert len(profile) == 2

    by_term = profile.set_index("ls_term")
    assert by_term.loc[17, "concentration_risk"] == 100.0   # one vendor took it all
    assert by_term.loc[17, "vendor_count"] == 1
    assert by_term.loc[18, "concentration_risk"] == 0.0     # 25 equal vendors
    assert by_term.loc[18, "vendor_count"] == 25


def test_expenditures_without_a_term_column_still_profile():
    """Snapshots predating ls_term hold one term; they must not fail the run."""
    df = pd.DataFrame([
        {"implementing_agency": "IDA-A", "vendor": "V", "expenditure_amount": 100.0,
         "expenditure_date": "2026-01-01", "payment_status": "Payment Success"}
        for _ in range(25)
    ])
    profile = build_agency_vendor_profile(df, as_of="2026-08-31")
    assert len(profile) == 1
    assert profile.iloc[0]["ls_term"] == 0
