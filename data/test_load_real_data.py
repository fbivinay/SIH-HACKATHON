"""Checks on work identity. Run: python data/test_load_real_data.py"""
import pandas as pd

from load_real_data import work_key


def test_work_key_separates_same_id_in_same_term():
    """Work IDs restart per implementing agency, not just per term. Two real
    rows from the 2026-08-31 snapshot: Work ID 241, term 17, one in Andhra
    Pradesh and one in Odisha. Keyed on (Work ID, ls_term) they collide, and
    the Odisha work inherits the Andhra work's recommendation date."""
    df = pd.DataFrame(
        {
            "Work ID": [241, 241],
            "ls_term": [17, 17],
            "IDA": [
                "Dr. B.R. Ambedkar Konaseema(DISTRICT COLLECTOR_IDA)",
                "KHORDHA(DISTRICT COLLECTOR KHORDHA_IDA)",
            ],
        }
    )
    keys = work_key(df)
    assert keys.nunique() == 2, keys.tolist()
    assert keys.iloc[0].startswith("241|17|")


def test_work_key_survives_a_snapshot_without_ls_term():
    """Older snapshots hold one term only; the key still forms, with term 0."""
    df = pd.DataFrame({"Work ID": [7], "IDA": ["  SOME AGENCY  "]})
    assert work_key(df).iloc[0] == "7|0|SOME AGENCY"


def test_work_key_is_stable_for_identical_input():
    df = pd.DataFrame({"Work ID": ["9"], "ls_term": [18], "IDA": ["A"]})
    assert work_key(df).iloc[0] == work_key(df.copy()).iloc[0] == "9|18|A"


if __name__ == "__main__":
    test_work_key_separates_same_id_in_same_term()
    test_work_key_survives_a_snapshot_without_ls_term()
    test_work_key_is_stable_for_identical_input()
    print("work_key checks passed")


# --- the unchanged-extract skip, 2026-09-12 ----------------------------------


def test_fingerprint_is_order_independent_and_value_sensitive():
    """The nightly skips a rewrite when the extract fingerprints the same as
    what is loaded. That is only safe if row order does not move the hash
    (the source does not order its export) and one changed value does."""
    import pandas as pd
    import load_real_data as lrd

    base = pd.DataFrame({
        "work_key": ["b|18|X", "a|18|X"], "description": ["two", "one"],
        "ls_term": [18, 18], "mp_name": ["m", "m"], "mp_id": ["1", "1"],
        "house": ["LS", "LS"], "constituency": ["c", "c"], "state": ["S", "S"],
        "district": ["D", "D"], "category": ["k", "k"],
        "implementing_agency": ["ag", "ag"], "amount": [10.0, 20.0],
        "expenditure": [0.0, 0.0], "work_status": ["Recommended"] * 2,
        "start_date": [None, None], "expected_completion": [None, None],
        "actual_completion": [None, None], "has_images": [False, False],
    })
    shuffled = base.iloc[::-1].reset_index(drop=True)
    assert lrd.extract_fingerprint(base, None, None) == lrd.extract_fingerprint(shuffled, None, None)

    changed = base.copy()
    changed.loc[0, "amount"] = 10.01
    assert lrd.extract_fingerprint(base, None, None) != lrd.extract_fingerprint(changed, None, None)


def test_loaded_fingerprint_follows_what_was_written_not_what_succeeded():
    """A run that wrote the tables and then failed has still changed what is
    on disk. Comparing tonight's extract against an older *success* would skip
    the rewrite while the tables held something else. Reproduced for real on
    2026-09-12: a mutated test extract was loaded, closed as 'failed', and the
    next run of the genuine extract declared itself unchanged."""
    import load_real_data as lrd

    class Cur:
        sql = None
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, *args): Cur.sql = sql
        def fetchone(self): return ("x",)
    class Conn:
        def cursor(self): return Cur()
        def rollback(self): pass

    lrd.loaded_fingerprint(Conn())
    assert "status = 'success'" not in Cur.sql
    assert "rows_loaded IS NOT NULL" in Cur.sql
