import pytest

from mps import mp_key, normalize_mp_name, safe_mp_key


def test_the_same_mp_written_two_ways_gets_one_id():
    """The real case from the LS17 extract, which lists this MP twice."""
    a = mp_key("Manne Srinivas Reddy(17th Lok Sabha)", "Telangana", "Lok Sabha")
    b = mp_key("Shri Manne Srinivas Reddy (17th Lok Sabha)", "Telangana", "Lok Sabha")
    c = mp_key("Manne Srinivas Reddy", "Telangana", "Lok Sabha")
    assert a == b == c


def test_every_term_marker_form_in_the_source_is_stripped():
    plain = mp_key("Mulayam Singh Yadav", "Uttar Pradesh", "Lok Sabha")
    for marked in ["Mulayam Singh Yadav (17LS)",
                   "Mulayam Singh Yadav(17th Lok Sabha)",
                   "Mulayam Singh Yadav (2022-28)",
                   "Mulayam Singh Yadav (2025-31)"]:
        assert mp_key(marked, "Uttar Pradesh", "Lok Sabha") == plain, marked


def test_parentheticals_that_are_part_of_the_name_survive():
    # '(Banerjee)', '(Dev)' and '(Lalan)' all appear in the extract as name
    # parts, not term markers. Stripping them would merge distinct MPs.
    assert normalize_mp_name("Kalyan (Banerjee)") == "kalyan banerjee"
    assert mp_key("Kalyan (Banerjee)", "West Bengal", "Lok Sabha") != mp_key(
        "Kalyan", "West Bengal", "Lok Sabha"
    )


def test_initials_written_inconsistently_do_not_split_an_mp():
    a = mp_key("A Ganeshamurthi", "Tamil Nadu", "Lok Sabha")
    b = mp_key("A. Ganeshamurthi", "Tamil Nadu", "Lok Sabha")
    c = mp_key("Ganeshamurthi", "Tamil Nadu", "Lok Sabha")
    assert a == b == c


def test_state_and_house_separate_mps_who_share_a_name():
    assert mp_key("Ram Kumar", "Bihar", "Lok Sabha") != mp_key("Ram Kumar", "Odisha", "Lok Sabha")
    assert mp_key("Ram Kumar", "Bihar", "Lok Sabha") != mp_key("Ram Kumar", "Bihar", "Rajya Sabha")


def test_ids_are_stable_across_calls():
    assert mp_key("Smt. S. Phangnon Konyak (2022-28)", "Nagaland", "Rajya Sabha") == mp_key(
        "S Phangnon Konyak", "Nagaland", "Rajya Sabha"
    )


def test_a_name_with_no_usable_text_raises():
    for junk in ["", None, "   ", "Shri", "Dr."]:
        with pytest.raises(ValueError):
            mp_key(junk, "Bihar", "Lok Sabha")


def test_safe_mp_key_returns_none_instead_of_raising():
    """A work with an unusable MP name is still a work worth loading; it just
    cannot take part in per-MP aggregates."""
    assert safe_mp_key("", "Bihar", "Lok Sabha") is None
    assert safe_mp_key("Ram Kumar", "Bihar", "Lok Sabha") is not None
