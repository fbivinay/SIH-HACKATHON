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
