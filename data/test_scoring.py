import pandas as pd
from datetime import date
from scoring import (
    compute_delay_days, cost_risk_score, delay_risk_score,
    duplicate_risk_score, agency_risk_score, risk_level,
    build_flagged_reasons,
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
