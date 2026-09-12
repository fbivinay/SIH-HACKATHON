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
    assert "\u20b9900,000" in cost[0]          # this work
    assert "\u20b9300,000" in cost[0]          # what it is compared against
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
        "ls_term": [18, 18],
        "agency_delay_rate": [0.0, 0.0],
    })
    profile = pd.DataFrame([{
        "implementing_agency": "IDA-A", "ls_term": 18, "concentration_risk": 75.0,
        "oldest_pending_days": 0, "pending_count": 0, "top_vendor": "V",
        "top_vendor_share_pct": 70.0, "total_spend": 100.0,
        "vendor_count": 3, "transaction_count": 50,
    }])
    out = attach_agency_profile(df, profile)
    assert len(out) == 2
    assert out.loc[0, "agency_concentration_risk"] == 75.0
    assert pd.isna(out.loc[1, "agency_concentration_risk"])
    assert agency_risk_score(out.iloc[1]) == 0.0


def test_a_work_takes_its_own_terms_agency_profile():
    """The same agency, two terms, two different vendor mixes. A work must be
    matched against its own term or it inherits the wrong one."""
    df = pd.DataFrame({
        "id": [1, 2],
        "implementing_agency": ["IDA-A", "IDA-A"],
        "ls_term": [17, 18],
        "agency_delay_rate": [0.0, 0.0],
    })
    profile = pd.DataFrame([
        {"implementing_agency": "IDA-A", "ls_term": 17, "concentration_risk": 95.0,
         "oldest_pending_days": 0, "pending_count": 0, "top_vendor": "Sole Ltd",
         "top_vendor_share_pct": 99.0, "total_spend": 100.0,
         "vendor_count": 1, "transaction_count": 50},
        {"implementing_agency": "IDA-A", "ls_term": 18, "concentration_risk": 0.0,
         "oldest_pending_days": 0, "pending_count": 0, "top_vendor": "Vendor 1",
         "top_vendor_share_pct": 4.0, "total_spend": 100.0,
         "vendor_count": 25, "transaction_count": 50},
    ])
    out = attach_agency_profile(df, profile)
    assert out.loc[0, "agency_concentration_risk"] == 95.0
    assert out.loc[1, "agency_concentration_risk"] == 0.0
    assert agency_risk_score(out.iloc[0]) == 95.0
    assert agency_risk_score(out.iloc[1]) == 0.0


def test_attach_agency_profile_without_any_expenditure_data():
    df = pd.DataFrame({"id": [1], "implementing_agency": ["IDA-A"],
                       "ls_term": [18], "agency_delay_rate": [0.0]})
    out = attach_agency_profile(df, pd.DataFrame())
    assert out.loc[0, "agency_concentration_risk"] is None
    assert agency_risk_score(out.iloc[0]) == 0.0


def test_insert_columns_match_what_the_loader_builds():
    """A positional insert tuple fell one value short when `sector` was added
    to INSERT_COLUMNS - a mismatch that only shows up against a live database,
    after a full load has already run. Build by name and check it here."""
    import load_real_data as lrd

    df = pd.DataFrame({
        "work_key": ["4021|18|PATNA(DM_IDA)"],
        "description": ["Construction of CC road"], "category": ["Normal/Others"],
        "mp_name": ["Ram Kumar"], "mp_id": ["abc123"],
        "house": ["Lok Sabha"], "constituency": ["Somewhere"], "state": ["Bihar"],
        "district": ["PATNA"], "implementing_agency": ["PATNA(DM_IDA)"], "ls_term": [18],
        "amount": [300000.0], "expenditure": [300000.0], "work_status": ["completed"],
        "start_date": [None], "expected_completion": [None],
        "actual_completion": [None], "has_images": [True],
    })
    prepared = lrd.prepare_insert_frame(df)
    assert list(prepared.columns) == lrd.INSERT_COLUMNS
    assert len(prepared.iloc[0]) == len(lrd.INSERT_COLUMNS)
    # `sector` is deliberately absent: it is derived, lives in project_scores,
    # and the loader inserting it broke every nightly refresh for two days.
    assert "sector" not in lrd.INSERT_COLUMNS
    # work_name is derived in the projects_scored view since 2026-09-12, not
    # stored: a loader that still emitted it would fail against the schema.
    assert "work_name" not in lrd.INSERT_COLUMNS
    assert prepared.iloc[0]["source"] == "real"
    assert prepared.iloc[0]["work_key"] == "4021|18|PATNA(DM_IDA)"


def test_current_refresh_run_id_ignores_an_abandoned_run():
    """A run killed by a workflow timeout leaves its row at 'running' forever.
    Adopting it would stamp that abandoned attempt as this pass's success."""
    import scoring

    class FakeCursor:
        def __init__(self, rows):
            self.rows = rows
            self.sql = ""

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params=None):
            self.sql = " ".join(sql.split())

        def fetchone(self):
            return self.rows

    class FakeConn:
        def __init__(self, rows):
            self.cursor_obj = FakeCursor(rows)

        def cursor(self):
            return self.cursor_obj

    conn = FakeConn((7,))
    assert scoring.current_refresh_run_id(conn) == 7
    # The age bound has to be in the statement, or a stale row is adopted.
    assert "INTERVAL" in conn.cursor_obj.sql
    assert scoring.MAX_RUN_ADOPTION_AGE in conn.cursor_obj.sql

    assert scoring.current_refresh_run_id(FakeConn(None)) is None


def test_fetch_mps_selects_every_column_the_detectors_read():
    """D-03 shipped silent for a whole scoring run because fetch_mps did not
    select amount_recommended. The guard did its job; nothing checked that the
    query supplied what the detector needs."""
    import inspect

    import scoring

    sql = inspect.getsource(scoring.fetch_mps)
    for column in ("mp_id", "ls_term", "mp_name", "allocated_amount",
                   "amount_recommended", "completed_works", "recommended_works"):
        assert column in sql, f"fetch_mps does not select {column}"

def test_scores_are_keyed_on_something_a_reload_cannot_move():
    """The reason the loader is allowed to leave project_scores alone.

    It used to truncate, because a score keyed on projects.id attaches to
    whichever work inherits that id after a reload - right only for as long as
    the upstream row order never changes. Truncating fixed the correctness
    problem and created an availability one: no scores anywhere for the ~25
    minutes until scoring caught up.

    Keying on work_key fixes both, so this pins the three halves of that
    bargain: the key, the loader not clearing, and the swap being atomic.
    """
    import inspect

    import load_real_data as lrd
    import scoring

    assert scoring.SCORE_COLUMNS[0] == "work_key", (
        "a score must be keyed on the identifier that survives a reload"
    )
    assert "similar_work_id" not in scoring.SCORE_COLUMNS, (
        "the matched duplicate must be named by work_key too - an id here "
        "points at a different work after the next reload"
    )

    load_body = inspect.getsource(lrd.load)
    assert "TRUNCATE project_scores" not in load_body, (
        "the loader must not clear scores; that is what emptied the site "
        "between the load finishing and scoring catching up"
    )

    # TRUNCATE and INSERT in one transaction is what lets the loader leave the
    # table alone: a reader sees the whole previous run or the whole new one.
    write_body = inspect.getsource(scoring.write_scores)
    assert "TRUNCATE project_scores" in write_body
    assert write_body.count("conn.commit()") == 1, (
        "the clear and the refill must commit together or readers see empty"
    )


class _RecordingCursor:
    """Captures the SQL fetch_projects actually runs, and answers it minimally."""

    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append(" ".join(sql.split()))

    def fetchone(self):
        return {"count": sum(1 for r in self.rows if r["work_key"] is None)}

    def fetchall(self):
        last = self.executed[-1]
        # Stand in for the database: honour the filter if the query asks for it.
        if "work_key IS NOT NULL" in last:
            return [r for r in self.rows if r["work_key"] is not None]
        return list(self.rows)


class _RecordingConn:
    def __init__(self, rows):
        self.cur = _RecordingCursor(rows)

    def cursor(self, **kwargs):
        return self.cur


def test_scoring_skips_rows_that_cannot_carry_a_score():
    """A project with no work_key cannot be scored, because project_scores is
    keyed on work_key.

    Harmless while scores were keyed on projects.id, which is never null.
    Rekeying made it fatal: generate_synthetic.py writes demo rows with no
    work_key, load() deliberately preserves them (it deletes only
    source = 'real'), and fetch_projects read every row unfiltered - so the
    pass died on a not-null violation at the very last statement, after about
    fifty minutes of computation.

    Asserted against the SQL actually executed. An earlier version of this test
    used inspect.getsource and passed on the explanatory comment above the
    query, which is no test at all.
    """
    import scoring

    conn = _RecordingConn([
        {"id": 1, "work_key": "101|18|AGENCY_IDA", "description": "a road"},
        {"id": 2, "work_key": None, "description": "a synthetic demo row"},
    ])
    df = scoring.fetch_projects(conn)

    assert list(df["work_key"]) == ["101|18|AGENCY_IDA"], (
        "a row with no work_key reached scoring; write_scores would abort the "
        "whole pass on the not-null constraint"
    )
    row_query = [q for q in conn.cur.executed if q.startswith("SELECT * FROM projects")]
    assert row_query and "work_key IS NOT NULL" in row_query[0], (
        f"the row query must exclude unkeyable rows, got: {row_query}"
    )


def test_the_loader_only_removes_scores_whose_work_is_gone():
    """The loader is allowed to touch project_scores in exactly one way.

    Asserting only that it never says TRUNCATE leaves the obvious mistake
    uncovered: an unconditional DELETE FROM project_scores, or the orphan
    cleanup moved up beside the projects delete - where it reads like tidying
    and would empty the table, because projects is momentarily empty there.
    """
    import inspect

    import load_real_data as lrd

    body = inspect.getsource(lrd.load)
    clears = [
        line.strip()
        for line in body.splitlines()
        if "project_scores" in line and ("DELETE" in line or "TRUNCATE" in line)
    ]
    assert len(clears) == 1, f"expected one guarded delete, found: {clears}"
    delete_stmt = body[body.index("DELETE FROM project_scores"):]
    assert "NOT EXISTS" in delete_stmt[:400], (
        "scores may only be deleted for works that have left the source; an "
        "unguarded delete empties the table the site is reading"
    )
