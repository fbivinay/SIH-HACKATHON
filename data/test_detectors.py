import math

import pandas as pd
import pytest

import detectors as d


def payments(rows):
    return pd.DataFrame(rows, columns=[
        "implementing_agency", "ls_term", "expenditure_amount", "expenditure_date"])


# --- fiscal year -----------------------------------------------------------

def test_fiscal_year_splits_on_1_april():
    dates = pd.to_datetime(pd.Series(["2024-03-31", "2024-04-01", "2024-12-31"]))
    assert list(d.fiscal_year(dates)) == ["2023-24", "2024-25", "2024-25"]


# --- D-01 ------------------------------------------------------------------

def test_year_end_burst_flags_an_agency_that_spends_in_march():
    # Both months must sit in the SAME fiscal year, or they are two cohorts:
    # March 2024 closes FY 2023-24 and June 2024 opens FY 2024-25.
    rows = [("A", 18, 1000.0, f"2024-03-{i % 28 + 1:02d}") for i in range(40)]
    rows += [("A", 18, 1000.0, f"2024-01-{i % 28 + 1:02d}") for i in range(10)]
    out = d.year_end_burst(payments(rows))
    assert len(out) == 1
    assert out[0]["code"] == "D-01"
    assert out[0]["period"] == "2023-24"
    assert out[0]["evidence"]["march_share_pct"] == 80.0
    assert out[0]["severity"] > 90


def test_year_end_burst_ignores_an_evenly_spread_year():
    rows = [("A", 18, 1000.0, f"2024-{m:02d}-10") for m in range(1, 13) for _ in range(4)]
    assert d.year_end_burst(payments(rows)) == []


def test_year_end_burst_ignores_a_tiny_agency():
    """Six payments in March is 100% and means nothing."""
    rows = [("A", 18, 1000.0, "2024-03-10")] * 6
    assert d.year_end_burst(payments(rows)) == []


# --- D-02 ------------------------------------------------------------------

def test_first_digit_reads_the_leading_digit():
    got = d.first_digit(pd.Series([1.0, 19.0, 250.0, 9999.0, 0.4, None]))
    assert list(got) == [1, 1, 2, 9]


def test_benford_mad_is_near_zero_for_a_benford_sample():
    # digit*1000 + offset, offset kept under 1000 so the value still leads with
    # `digit` — the obvious digit*100 + i runs 100..701 and lands on 7.
    amounts = []
    for digit, share in d.BENFORD_EXPECTED.items():
        amounts += [float(digit) * 1000 + i for i in range(round(share * 10))]
    assert d.benford_mad(pd.Series(amounts)) < d.BENFORD_FLOOR_MAD


def test_benford_mad_is_large_when_one_digit_dominates():
    assert d.benford_mad(pd.Series([500.0 + i for i in range(400)])) > d.BENFORD_CEILING_MAD


def test_benford_needs_a_sample():
    assert d.benford_mad(pd.Series([100.0] * 10)) is None


# --- D-03 ------------------------------------------------------------------

def mp_rows(rows):
    return pd.DataFrame(rows, columns=[
        "mp_id", "ls_term", "mp_name", "constituency", "state",
        "allocated_amount", "amount_recommended", "utilization_pct",
        "completed_works", "recommended_works"])


def test_idle_allocation_flags_a_mostly_unspent_allocation():
    # Rs 5 crore allocated, Rs 1.25 crore committed: 75% never committed to any
    # work, which is the top of a ramp running from 35% to 75%.
    out = d.idle_allocation(mp_rows([
        ("mp1", 18, "A Member", "Somewhere", "Bihar", 5e7, 1.25e7, 5.0, 3, 40)]))
    assert len(out) == 1 and out[0]["code"] == "D-03"
    assert out[0]["evidence"]["allocated_amount"] == 5e7
    assert out[0]["severity"] == pytest.approx(100.0)


def test_idle_allocation_ignores_the_median_mp():
    """The median MP-term leaves 16.5% of its allocation uncommitted, so a
    figure near that must not be a finding - it would flag almost everybody."""
    assert d.idle_allocation(mp_rows([
        ("mp1", 18, "A Member", "X", "Bihar", 5e7, 4.2e7, 48.0, 20, 30)])) == []


def test_idle_allocation_ignores_a_fully_committed_allocation():
    assert d.idle_allocation(mp_rows([
        ("mp1", 18, "A Member", "X", "Bihar", 5e7, 4.95e7, 99.0, 40, 45)])) == []


def test_idle_allocation_is_silent_without_the_source_column():
    """A snapshot from before the source published amount_recommended cannot
    answer this question, and must not fall back to a column that measures
    payments outstanding instead."""
    df = mp_rows([("mp1", 18, "A Member", "X", "Bihar", 5e7, 0.0, 0.0, 3, 40)])
    assert d.idle_allocation(df.drop(columns=["amount_recommended"])) == []


def test_idle_allocation_ignores_an_mp_who_has_not_started():
    """No works recommended is not idle money, it is a member seated part-way
    through the term."""
    assert d.idle_allocation(mp_rows([
        ("mp1", 18, "A Member", "X", "Bihar", 5e7, 0.0, 0.0, 0, 0)])) == []


def test_idle_allocation_ignores_a_token_allocation():
    """A percentage of a tiny allocation is not a finding."""
    assert d.idle_allocation(mp_rows([
        ("mp1", 18, "A Member", "X", "Bihar", 1000.0, 0.0, 0.0, 0, 5)])) == []


# --- D-04 ------------------------------------------------------------------

def works(rows):
    return pd.DataFrame(rows, columns=["implementing_agency", "ls_term", "sanctioned_amount"])


def test_uniform_amount_flags_one_amount_covering_everything():
    out = d.uniform_sanction_amount(works([("A", 18, 243000.0)] * 30))
    assert len(out) == 1 and out[0]["code"] == "D-04"
    assert out[0]["evidence"]["share_pct"] == 100.0
    assert out[0]["severity"] == 100.0


def test_uniform_amount_ignores_a_varied_agency():
    rows = [("A", 18, float(100000 + i * 1000)) for i in range(40)]
    assert d.uniform_sanction_amount(works(rows)) == []


def test_uniform_amount_ignores_a_small_agency():
    assert d.uniform_sanction_amount(works([("A", 18, 500000.0)] * 5)) == []


# --- wiring ----------------------------------------------------------------

def test_run_all_returns_rows_shaped_for_the_table():
    findings = d.run_all(
        works([("A", 18, 243000.0)] * 30),
        payments([("A", 18, 1000.0, f"2024-03-{i % 28 + 1:02d}") for i in range(40)]),
        mp_rows([("mp1", 18, "A Member", "X", "Bihar", 5e7, 1e7, 2.0, 3, 40)]),
    )
    assert {f["code"] for f in findings} == {"D-01", "D-04", "D-03"}
    for f in findings:
        assert set(f) == set(d.FINDING_COLUMNS)
        assert 0 < f["severity"] <= 100


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_idle_allocation_reports_one_fund_once():
    """The source gives a Rajya Sabha member a row in both Lok Sabha terms with
    identical figures. 231 members do, and that turned 286 into 358 findings."""
    rows = [
        ("rs1", 17, "A Member", "Rajya Sabha", "Bihar", 5e7, 1e7, 2.0, 3, 40),
        ("rs1", 18, "A Member", "Rajya Sabha", "Bihar", 5e7, 1e7, 2.0, 3, 40),
    ]
    out = d.idle_allocation(mp_rows(rows))
    assert len(out) == 1
    assert out[0]["ls_term"] == 18


def test_idle_allocation_keeps_both_terms_when_the_funds_differ():
    """A Lok Sabha member really does hold two separate allocations."""
    rows = [
        ("ls1", 17, "A Member", "X", "Bihar", 5e7, 1e7, 2.0, 3, 40),
        ("ls1", 18, "A Member", "X", "Bihar", 8e7, 2e7, 2.0, 3, 40),
    ]
    assert len(d.idle_allocation(mp_rows(rows))) == 2


def test_idle_allocation_ignores_a_member_who_has_barely_started():
    """Below the 10th percentile of activity (17 works) the member is in their
    first months, not sitting on funds."""
    assert d.idle_allocation(mp_rows([
        ("mp1", 18, "New Member", "X", "Bihar", 5e7, 1e6, 1.0, 0, 2)])) == []


def test_every_detector_survives_an_empty_frame():
    """fetch_expenditures returns pd.DataFrame(cur.fetchall()), which on zero
    rows is 0x0 - no columns at all - so dropna(subset=["x"]) raises KeyError on
    a name that is simply absent.

    A snapshot with no expenditure file is documented as supported (the
    2026-08-30 one had none). D-01, D-03 and D-04 all had the emptiness guard
    AFTER the subset access, so run_all died on the first of them and the whole
    scoring pass with it. D-04 stayed hidden until D-01 was fixed, because
    run_all never reached it.
    """
    import pandas as pd

    import detectors

    empty = pd.DataFrame([])
    for name, fn in (
        ("D-01", detectors.year_end_burst),
        ("D-02", detectors.first_digit_anomaly),
        ("D-03", detectors.idle_allocation),
        ("D-04", detectors.uniform_sanction_amount),
    ):
        assert fn(empty) == [], f"{name} should find nothing in an empty frame"
    assert detectors.run_all(empty, empty, empty) == []


def test_scores_are_written_before_the_detectors_run():
    """A detector failure must not discard a finished scoring pass.

    The comment in scoring.py claimed this was already true. It was not: the
    detectors ran after the scores were COMPUTED but before they were WRITTEN,
    and outside the try/except, so any exception threw away fifty minutes of
    work held in memory.
    """
    import inspect

    import scoring

    body = inspect.getsource(scoring)
    main = body[body.index('if __name__ == "__main__":'):]
    assert main.index("write_scores(conn, scored)") < main.index("detectors.run_all"), (
        "scores must be committed before the detectors are given a chance to fail"
    )
    after = main[main.index("detectors.run_all"):]
    assert "except Exception" in after, (
        "a detector failure must be caught and reported, not raised"
    )
