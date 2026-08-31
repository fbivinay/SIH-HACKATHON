import pytest

from sectors import classify_sector, normalize, verify, OTHER


def test_order_decides_when_several_keywords_match():
    # 'high mast light along main road' is a light, not a road: lighting is
    # tested first. This is the property the rule ORDER encodes, so reordering
    # SECTOR_RULES should break this test.
    assert classify_sector("Installation of high mast light along main road") == "Street Lighting"
    assert classify_sector("Construction of CC road with paver blocks") == "Roads & Paving"


def test_hindi_transliterations_classify():
    # Roughly a third of real descriptions use them; missing these would dump
    # them all into Other and rebuild the bug this module fixes.
    assert classify_sector("Nirman of nali from Ram house to Shyam house") == "Drainage & Sanitation"
    assert classify_sector("Marammat of mandir premises") == "Religious & Cultural"
    assert classify_sector("Sadak nirman gram panchayat Bhojpur") == "Roads & Paving"


def test_road_and_drain_together_is_a_road():
    """2,307 real works name both. The road is the primary asset and sets the
    cost scale, so roads are tested before drainage - but a drain named on its
    own is still a drain."""
    assert classify_sector("Providing CC Road with Drainage on Both Sides") == "Roads & Paving"
    assert classify_sector("Construction of PUCCA Drain from Ajoy to Pranab") == "Drainage & Sanitation"


def test_keywords_match_words_not_substrings():
    """Place names are full of accidental hits: 'marg' inside 'Margao',
    'rasta' inside 'Sarasta'. A community toilet classified as a road before
    the matcher used word boundaries."""
    assert classify_sector("Construction of Community Toilet at Margao Ward 13") == "Drainage & Sanitation"
    assert classify_sector("Repair of hall at Sarasta village") == "Community Buildings"


def test_common_real_descriptions():
    assert classify_sector("Boring of hand pump in gram panchayat") == "Water"
    assert classify_sector("Construction of community hall at ward 4") == "Community Buildings"
    assert classify_sector("Additional classroom at primary school") == "Education"
    assert classify_sector("Purchase of furniture for panchayat office") == "Equipment & Vehicles"


def test_unmatched_and_empty_descriptions_are_other():
    assert classify_sector("zzz qqq") == OTHER
    assert classify_sector("") == OTHER
    assert classify_sector(None) == OTHER


def test_normalize_ignores_case_punctuation_and_spacing():
    assert normalize("  Road,  PHASE 2. ") == normalize("road phase 2")


def test_verify_rejects_a_classifier_that_stopped_matching():
    # The failure mode worth catching: rules drift out of date, everything
    # lands in Other, and cost scoring silently compares every work in a
    # district against every other work again.
    with pytest.raises(ValueError, match="Other"):
        verify(["zzz unclassifiable"] * 20)


def test_verify_accepts_a_normal_mix():
    counts = verify(["high mast light", "cc road", "hand pump", "community hall"] * 5)
    assert counts[OTHER] == 0
