import pandas as pd
from datetime import date
from scoring import (
    compute_delay_days, cost_risk_score, delay_risk_score,
    duplicate_risk_score, agency_risk_score, risk_level,
    build_flagged_reasons, compliance_risk_score,
)


def test_known_high_risk_project_lands_in_high_band():
    row = pd.Series({
        "actual_completion": date(2024, 6, 1),
        "expected_completion": date(2024, 1, 1),
        "cost_deviation_pct": 80.0,
        # A verbatim-duplicate description (identical text scores 1.0, and real
        # ones occur in the dataset). Was 0.92, which only reached the HIGH band
        # because duplicate_risk used to return similarity * 100 unscaled; under
        # the calibrated threshold + rescaling, 0.92 is below the noise floor.
        "max_similarity_score": 1.0,
        "agency_delay_rate": 70.0,
        "compliance_reasons": [],
    })
    row["delay_days"] = compute_delay_days(row)
    row["cost_risk"] = cost_risk_score(row)
    row["delay_risk"] = delay_risk_score(row)
    row["duplicate_risk"] = duplicate_risk_score(row)
    row["agency_risk"] = agency_risk_score(row)

    overall = (
        row["cost_risk"] * 0.25 + row["delay_risk"] * 0.25
        + row["duplicate_risk"] * 0.20 + row["agency_risk"] * 0.15
    )
    assert risk_level(overall) == "HIGH"

    reasons = build_flagged_reasons(row)
    assert any("similarity" in r for r in reasons)
    assert any("days beyond expected completion" in r for r in reasons)


def test_clean_project_lands_in_low_band():
    row = pd.Series({
        "actual_completion": date(2024, 1, 5),
        "expected_completion": date(2024, 1, 1),
        "cost_deviation_pct": 2.0,
        "max_similarity_score": 0.1,
        "agency_delay_rate": 5.0,
        "compliance_reasons": [],
    })
    row["delay_days"] = compute_delay_days(row)
    row["cost_risk"] = cost_risk_score(row)
    row["delay_risk"] = delay_risk_score(row)
    row["duplicate_risk"] = duplicate_risk_score(row)
    row["agency_risk"] = agency_risk_score(row)

    overall = (
        row["cost_risk"] * 0.25 + row["delay_risk"] * 0.25
        + row["duplicate_risk"] * 0.20 + row["agency_risk"] * 0.15
    )
    assert risk_level(overall) == "LOW"


def test_missing_dates_flagged_only_for_recommended_works():
    """Most completed works genuinely have no recommendation date on record
    (see load_real_data.py); the rule must not treat that as a compliance
    failure. It should still fire for a recommended work missing dates."""
    recommended_missing_dates = pd.Series({
        "expenditure": 0.0, "sanctioned_amount": 100.0,
        "work_status": "recommended",
        "start_date": pd.NaT, "expected_completion": pd.NaT,
        "actual_completion": pd.NaT,
    })
    score, reasons = compliance_risk_score(recommended_missing_dates)
    assert score == 20.0
    assert "Missing start or expected completion date" in reasons

    completed_missing_dates = pd.Series({
        "expenditure": 100.0, "sanctioned_amount": 100.0,
        "work_status": "completed",
        "start_date": pd.NaT, "expected_completion": pd.NaT,
        "actual_completion": date(2024, 1, 5),
    })
    score, reasons = compliance_risk_score(completed_missing_dates)
    assert score == 0.0
    assert reasons == []


def test_missing_photo_documentation_flagged_only_for_completed_works():
    """29% of completed works have Has Images = False in the source data - a
    real compliance signal. NULL (unknown) must not be treated as a violation,
    and the rule must not fire on recommended works (which have no images to
    document yet)."""
    completed_no_images = pd.Series({
        "expenditure": 100.0, "sanctioned_amount": 100.0,
        "work_status": "completed",
        "start_date": date(2024, 1, 1), "expected_completion": date(2024, 6, 1),
        "actual_completion": date(2024, 6, 1), "has_images": False,
    })
    score, reasons = compliance_risk_score(completed_no_images)
    assert score == 30.0
    assert "Completed work has no photographic documentation on record" in reasons

    completed_with_images = pd.Series({
        "expenditure": 100.0, "sanctioned_amount": 100.0,
        "work_status": "completed",
        "start_date": date(2024, 1, 1), "expected_completion": date(2024, 6, 1),
        "actual_completion": date(2024, 6, 1), "has_images": True,
    })
    score, reasons = compliance_risk_score(completed_with_images)
    assert score == 0.0
    assert reasons == []

    completed_unknown_images = pd.Series({
        "expenditure": 100.0, "sanctioned_amount": 100.0,
        "work_status": "completed",
        "start_date": date(2024, 1, 1), "expected_completion": date(2024, 6, 1),
        "actual_completion": date(2024, 6, 1), "has_images": None,
    })
    score, reasons = compliance_risk_score(completed_unknown_images)
    assert score == 0.0
    assert reasons == []

    recommended_no_images = pd.Series({
        "expenditure": 0.0, "sanctioned_amount": 100.0,
        "work_status": "recommended",
        "start_date": date(2024, 1, 1), "expected_completion": date(2025, 1, 1),
        "actual_completion": pd.NaT, "has_images": False,
    })
    score, reasons = compliance_risk_score(recommended_no_images)
    assert score == 0.0
    assert reasons == []


def test_cost_reason_never_contradicts_itself():
    """A work can be a delay/spend outlier without being expensive.

    cost_risk blends the Isolation Forest score (fit on sanctioned_amount,
    delay_days, expenditure_ratio), so it can exceed 40 while cost_deviation_pct
    is negative. Gating the sentence on cost_risk once produced "Cost is -56%
    above similar projects" on 3,539 real works. The cost sentence must key off
    the deviation itself; the multivariate signal gets its own honest wording.
    """
    outlier_but_cheap = pd.Series({
        "compliance_reasons": [],
        "cost_risk": 100.0,           # pushed up purely by the IF blend
        "cost_deviation_pct": -56.0,  # actually CHEAPER than its peers
        "iso_anomaly": 100.0,
        "delay_risk": 100.0, "delay_days": 696,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_risk": 0.0, "agency_delay_rate": 0.0,
    })
    reasons = build_flagged_reasons(outlier_but_cheap)
    assert not any("above similar projects" in r for r in reasons), reasons
    # the real signal is still explained, not silently dropped
    assert any("Unusual combination" in r for r in reasons), reasons
    assert any("696 days beyond expected completion" in r for r in reasons), reasons

    genuinely_expensive = pd.Series({
        "compliance_reasons": [],
        "cost_risk": 100.0,
        "cost_deviation_pct": 134.0,
        "iso_anomaly": 100.0,
        "delay_risk": 0.0, "delay_days": 0,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_risk": 0.0, "agency_delay_rate": 0.0,
    })
    reasons = build_flagged_reasons(genuinely_expensive)
    assert "Cost is 134% above similar projects" in reasons, reasons
    # the cost sentence wins; we don't also emit the generic anomaly line
    assert not any("Unusual combination" in r for r in reasons), reasons
