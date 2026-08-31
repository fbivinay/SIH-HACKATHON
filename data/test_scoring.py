import pandas as pd
from datetime import date
from scoring import (
    compute_delay_days, cost_risk_score, delay_risk_score,
    duplicate_risk_score, agency_risk_score, risk_level,
    build_flagged_reasons, compliance_risk_score, add_base_features,
    attach_agency_profile,
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
        "sanctioned_amount": 132000.0,
        "peer_median_cost": 300000.0, "peer_count": 40,
        "district": "PATNA", "sector": "Water",
        "cost_risk": 100.0,           # pushed up purely by the IF blend
        "cost_deviation_pct": -56.0,  # actually CHEAPER than its peers
        "iso_anomaly": 100.0,
        "delay_risk": 100.0, "delay_days": 696,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_risk": 0.0, "agency_delay_rate": 0.0,
    })
    reasons = build_flagged_reasons(outlier_but_cheap)
    assert not any("above" in r for r in reasons), reasons
    # the real signal is still explained, not silently dropped
    assert any("Unusual combination" in r for r in reasons), reasons
    assert any("696 days beyond expected completion" in r for r in reasons), reasons

    genuinely_expensive = pd.Series({
        "compliance_reasons": [],
        "sanctioned_amount": 702000.0,
        "peer_median_cost": 300000.0, "peer_count": 40,
        "district": "PATNA", "sector": "Water",
        "cost_risk": 100.0,
        "cost_deviation_pct": 134.0,
        "iso_anomaly": 100.0,
        "delay_risk": 0.0, "delay_days": 0,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_risk": 0.0, "agency_delay_rate": 0.0,
    })
    reasons = build_flagged_reasons(genuinely_expensive)
    assert any("134% above" in r and "median" in r for r in reasons), reasons
    # the cost sentence wins; we don't also emit the generic anomaly line
    assert not any("Unusual combination" in r for r in reasons), reasons


def _priced(**kw):
    """A row with a complete cost basis: amount, peer median, peer count."""
    base = {
        "compliance_reasons": [],
        "sanctioned_amount": 900000.0,
        "peer_median_cost": 300000.0,
        "peer_count": 40,
        "district": "JAUNPUR",
        "sector": "Street Lighting",
        "cost_deviation_pct": 200.0,
        "iso_anomaly": 0.0,
        "delay_risk": 0.0, "delay_days": 0,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_risk": 0.0, "agency_delay_rate": 0.0,
    }
    base.update(kw)
    return pd.Series(base)


def test_cost_baseline_groups_on_sector_not_category():
    """The whole point of the fix.

    Two districts' worth of works, all with category 'Normal/Others' as 98.1% of
    the real data is. Grouping on category compares a street light against the
    district's roads; grouping on sector compares lights with lights.
    """
    df = pd.DataFrame({
        "id": range(1, 9),
        "description": ["high mast light"] * 4 + ["cc road construction"] * 4,
        "category": ["Normal/Others"] * 8,
        "sector": ["Street Lighting"] * 4 + ["Roads & Paving"] * 4,
        "district": ["JAUNPUR"] * 8,
        "sanctioned_amount": [100000.0, 100000.0, 100000.0, 100000.0,
                              4000000.0, 4000000.0, 4000000.0, 4000000.0],
        "expenditure": [0.0] * 8,
        "implementing_agency": ["A"] * 8,
        "expected_completion": [None] * 8,
        "actual_completion": [None] * 8,
    })
    out = add_base_features(df)

    # Each work sits at its own sector's median, so nothing is a cost outlier.
    assert out["peer_median_cost"].tolist() == [100000.0] * 4 + [4000000.0] * 4
    assert out["cost_deviation_pct"].abs().max() == 0.0
    # Had this grouped on (district, category) every row would deviate wildly
    # from the single blended baseline.
    blended = df["sanctioned_amount"].median()
    assert blended not in set(out["peer_median_cost"])


def test_peer_median_resists_one_huge_work():
    """A single Rs 7.5 crore work must not drag the baseline for its neighbours.

    With a mean, the four normal works would each read as far below baseline and
    the outlier itself would look only moderately above it.
    """
    amounts = [300000.0] * 8 + [75000000.0]
    df = pd.DataFrame({
        "id": range(1, 10),
        "description": ["cc road"] * 9,
        "sector": ["Roads & Paving"] * 9,
        "district": ["PATNA"] * 9,
        "sanctioned_amount": amounts,
        "expenditure": [0.0] * 9,
        "implementing_agency": ["A"] * 9,
        "expected_completion": [None] * 9,
        "actual_completion": [None] * 9,
    })
    out = add_base_features(df)
    assert out["peer_median_cost"].iloc[0] == 300000.0
    assert out["cost_deviation_pct"].iloc[0] == 0.0      # a normal work reads normal
    assert out["cost_deviation_pct"].iloc[-1] > 1000.0   # the outlier reads as one


def test_thin_peer_groups_score_no_cost_risk():
    """A median over three works is not a baseline."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "description": ["borewell"] * 3,
        "sector": ["Water"] * 3,
        "district": ["RANCHI"] * 3,
        "sanctioned_amount": [100000.0, 100000.0, 5000000.0],
        "expenditure": [0.0] * 3,
        "implementing_agency": ["A"] * 3,
        "expected_completion": [None] * 3,
        "actual_completion": [None] * 3,
    })
    out = add_base_features(df)
    assert out["peer_count"].tolist() == [3, 3, 3]
    # The 50x work is real, but with two peers we cannot say so responsibly.
    assert out["cost_deviation_pct"].tolist() == [0.0, 0.0, 0.0]
    assert cost_risk_score(out.iloc[2]) == 0.0


def test_sector_is_recomputed_when_missing():
    """Scoring a database loaded before the sector column must not group
    every work in a district together."""
    df = pd.DataFrame({
        "id": [1, 2],
        "description": ["high mast light near temple", "cc road paver block"],
        "district": ["JAUNPUR"] * 2,
        "sanctioned_amount": [100000.0, 900000.0],
        "expenditure": [0.0] * 2,
        "implementing_agency": ["A"] * 2,
        "expected_completion": [None] * 2,
        "actual_completion": [None] * 2,
    })
    out = add_base_features(df)
    assert out["sector"].tolist() == ["Street Lighting", "Roads & Paving"]


def test_cost_reason_states_its_comparison_basis():
    """A verifier who cannot see the basis cannot act on the flag."""
    reasons = build_flagged_reasons(_priced())
    cost = [r for r in reasons if "median" in r]
    assert len(cost) == 1, reasons
    assert "Rs 900,000" in cost[0]          # this work
    assert "Rs 300,000" in cost[0]          # what it is compared against
    assert "Street Lighting" in cost[0]     # the peer group
    assert "JAUNPUR" in cost[0]
    assert "40 peer works" in cost[0]       # how many peers stand behind it
    assert "200% above" in cost[0]


def test_no_cost_reason_without_a_basis():
    # Thin peer group: scored 0 upstream, and no sentence claiming otherwise.
    assert not any("median" in r for r in build_flagged_reasons(_priced(peer_count=3)))
    # Row predating the columns: silence, not a crash and not a vague claim.
    stale = _priced()
    del stale["peer_median_cost"]
    assert not any("median" in r for r in build_flagged_reasons(stale))


def test_agency_risk_takes_the_worst_signal_not_a_blend():
    """Adding a component must never lower an existing score.

    A weighted blend would have halved every agency's delay-driven risk the
    moment concentration was added, silently changing scores in a change that
    was supposed to be additive.
    """
    delay_only = pd.Series({"agency_delay_rate": 70.0})
    assert agency_risk_score(delay_only) == 70.0

    also_concentrated = pd.Series({
        "agency_delay_rate": 70.0, "agency_concentration_risk": 90.0,
    })
    assert agency_risk_score(also_concentrated) == 90.0

    concentration_only = pd.Series({
        "agency_delay_rate": 0.0, "agency_concentration_risk": 90.0,
    })
    assert agency_risk_score(concentration_only) == 90.0


def test_agency_reason_names_the_component_that_drove_the_score():
    """agency_risk is a max, so attributing it to the delay rate
    unconditionally reported a delay problem on an agency flagged purely for
    vendor concentration."""
    concentrated = pd.Series({
        "compliance_reasons": [], "cost_deviation_pct": 0.0, "iso_anomaly": 0.0,
        "delay_risk": 0.0, "delay_days": 0,
        "duplicate_risk": 0.0, "max_similarity_score": 0.1,
        "agency_delay_rate": 5.0,
        "agency_concentration_risk": 88.0,
        "agency_top_vendor_share_pct": 71.0, "agency_total_spend": 9400000.0,
        "agency_top_vendor": "KRIDL BHUSIRI", "agency_vendor_count": 6,
        "agency_transaction_count": 120, "agency_oldest_pending_days": 0,
        "agency_pending_count": 0,
    })
    concentrated["agency_risk"] = agency_risk_score(concentrated)
    reasons = build_flagged_reasons(concentrated)
    assert any("KRIDL BHUSIRI" in r for r in reasons), reasons
    assert not any("delay rate" in r for r in reasons), reasons

    delayed = concentrated.copy()
    delayed["agency_delay_rate"] = 92.0
    delayed["agency_risk"] = agency_risk_score(delayed)
    reasons = build_flagged_reasons(delayed)
    assert any("92% delay rate" in r for r in reasons), reasons
    assert not any("KRIDL BHUSIRI" in r for r in reasons), reasons


def test_works_of_an_agency_with_no_expenditures_keep_scoring():
    """Left join, not inner: no vendor data must cost the signal, not the rows."""
    df = pd.DataFrame({
        "id": [1, 2],
        "implementing_agency": ["IDA-A", "IDA-UNKNOWN"],
        "agency_delay_rate": [0.0, 0.0],
    })
    profile = pd.DataFrame([{
        "implementing_agency": "IDA-A", "concentration_risk": 75.0,
        "oldest_pending_days": 0, "pending_count": 0, "top_vendor": "V",
        "top_vendor_share_pct": 70.0, "total_spend": 100.0,
        "vendor_count": 3, "transaction_count": 50,
    }])
    out = attach_agency_profile(df, profile)
    assert len(out) == 2
    assert out.loc[0, "agency_concentration_risk"] == 75.0
    assert pd.isna(out.loc[1, "agency_concentration_risk"])
    assert agency_risk_score(out.iloc[1]) == 0.0


def test_attach_agency_profile_without_any_expenditure_data():
    df = pd.DataFrame({"id": [1], "implementing_agency": ["IDA-A"], "agency_delay_rate": [0.0]})
    out = attach_agency_profile(df, pd.DataFrame())
    assert out.loc[0, "agency_concentration_risk"] is None
    assert agency_risk_score(out.iloc[0]) == 0.0
