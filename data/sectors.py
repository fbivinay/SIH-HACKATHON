"""Derive a work sector from its description.

WHY THIS EXISTS
---------------
scoring.py compares a work's cost against its peers. "Peer" was
(district, category), but `category` is not a usable stratifier: it is
'Normal/Others' for 241,767 of the 246,487 loaded rows (98.1%), and the source
API's own /mplads/sectors endpoint returns the same four buckets. With the
category half of the key inert, cost deviation compared a Rs 30,000 street light
against a district average that also contained Rs 40,00,000 roads, so nearly
every cheap work looked suspiciously cheap and every road looked suspiciously
dear.

The description text is the only place the kind of work is actually recorded.
This module reads it.

HOW IT CLASSIFIES
-----------------
Ordered keyword rules, first match wins. Order is load-bearing and is what the
tests pin. Two calls worth knowing:

  * 'installation of high mast light along main road' is a light, not a road,
    so lighting is tested first.
  * 2,307 works name both a road and a drain ('CC Road with Drainage on Both
    Sides'). The road is the primary asset and sets the cost scale, so roads
    are tested before drainage; a drain named on its own still classifies as
    drainage. Keywords cover the Hindi
transliterations that appear throughout the source ('nirman', 'mandir',
'sadak', 'nali', 'shauchalay'), because a third of descriptions use them.

Measured on the 2026-08-31 extract of 124,353 completed works: 82.9% land in a
named sector, 17.1% in 'Other'.

  Street Lighting 24.5%   Roads & Paving 22.4%   Water 9.7%
  Community Buildings 7.6%   Education 7.0%   Drainage & Sanitation 3.9%
  Religious & Cultural 2.4%   Equipment & Vehicles 1.9%   Sports 1.7%
  Boundary & Protection 1.4%   Health 0.5%

'Other' is a real bucket, not a failure: those works still form a peer group
with each other inside their district. What it must not become is the majority,
which is the failure mode `category` had. verify() below asserts that.
"""

import re
import unicodedata

OTHER = "Other"

# First match wins. Reordering changes classifications - see the tests.
SECTOR_RULES = [
    ("Street Lighting", ["high mast", "highmast", "street light", "streetlight",
                         "solar light", "led light", "mast light", "light pole",
                         "solar street", "lighting", "lights", "prakash"]),
    ("Roads & Paving", ["road", "paver", "interlocking", "pathway", "culvert",
                        "bridge", "marg", "sadak", "rasta", "footpath",
                        "cc block", "khadanja"]),
    ("Water", ["water", "borewell", "bore well", "hand pump", "handpump",
               "tubewell", "tube well", "pipeline", "tanker", "overhead tank",
               "jal", "pond", "talab", "kuan"]),
    ("Drainage & Sanitation", ["drain", "nali", "sewer", "toilet", "soak pit",
                               "sanitation", "shauchalay", "septic"]),
    ("Education", ["school", "classroom", "vidyalaya", "college", "library",
                   "anganwadi", "hostel", "shiksha", "pustakalaya"]),
    ("Health", ["hospital", "health centre", "health center", "phc", "chc",
                "ambulance", "dispensary", "aarogya", "swasthya"]),
    ("Community Buildings", ["community hall", "panchayat ghar", "bhawan", "bhavan",
                             "chaupal", "samudayik", "shed", "hall",
                             "community centre", "community center",
                             "rain shelter", "waiting", "barat ghar"]),
    ("Religious & Cultural", ["mandir", "temple", "masjid", "church", "gurudwara",
                              "samadhi", "statue", "pratima", "murti", "ghat"]),
    ("Sports", ["playground", "stadium", "sports", "khel", "gym", "park"]),
    ("Boundary & Protection", ["boundary wall", "retaining wall", "chardiwari",
                               "fencing", "protection wall", "wall"]),
    ("Equipment & Vehicles", ["purchase", "computer", "furniture", "generator",
                              "machine", "vehicle", "equipment", "cctv",
                              "cooler", "bench", "desk"]),
]


def normalize(text):
    """Casefold, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


# Keywords match whole words with an optional plural, not raw substrings.
#
# Raw substrings hit inside place names - 'marg' in 'Margao', 'rasta' in
# 'Sarasta' - and classified a community toilet as a road. Bare \b...\b then
# went too far the other way and dropped 13,454 works into Other, because the
# source pluralises constantly: 'bore wells', 'hand pumps', 'community halls',
# 'benches', 'roads'. The optional (?:e?s)? suffix keeps both: 'Margao' still
# fails the trailing boundary, 'borewells' still matches 'borewell'.
_MATCHERS = [
    (sector, re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")(?:e?s)?\b"))
    for sector, keywords in SECTOR_RULES
]


def classify_sector(description):
    norm = normalize(description)
    if not norm:
        return OTHER
    for sector, matcher in _MATCHERS:
        if matcher.search(norm):
            return sector
    return OTHER


def verify(descriptions, max_other_share=0.40):
    """Assert the classifier still stratifies. Returns the sector counts.

    A classifier that dumps everything into one bucket is exactly the bug this
    module was written to fix, so failing loudly beats scoring against a
    baseline that silently means nothing again.
    """
    from collections import Counter

    counts = Counter(classify_sector(d) for d in descriptions)
    total = sum(counts.values())
    if not total:
        return counts
    other_share = counts[OTHER] / total
    if other_share > max_other_share:
        raise ValueError(
            f"sector classifier put {other_share:.1%} of {total} works in "
            f"{OTHER!r} (limit {max_other_share:.0%}). The keyword rules no "
            f"longer match this data; fix them before scoring."
        )
    return counts


if __name__ == "__main__":
    samples = [
        ("Installation of high mast light near main road, Village Rampur", "Street Lighting"),
        ("Upgradation of Road from Madhavaram Village to Company Indlu", "Roads & Paving"),
        ("Construction of community hall at ward no 4", "Community Buildings"),
        ("Boring of hand pump in gram panchayat Bhojpur", "Water"),
        ("Nirman of nali from Shri Ram house to Ram Lal house", "Drainage & Sanitation"),
        ("Providing CC Road with Drainage on Both Sides at New colony", "Roads & Paving"),
        ("Construction of Community Toilet at Hazrapara Tarun Tirtha Ward 13", "Drainage & Sanitation"),
        ("Construction of boundary wall of primary school", "Education"),
        ("Purchase of computers for the district library", "Education"),
        ("Repair of mandir premises", "Religious & Cultural"),
        ("", OTHER),
        ("zzz unclassifiable", OTHER),
    ]
    for text, expected in samples:
        got = classify_sector(text)
        assert got == expected, f"{text!r}: expected {expected}, got {got}"
    assert normalize("  Road,  PHASE 2. ") == normalize("road phase 2")
    try:
        verify(["zzz"] * 10)
    except ValueError:
        pass
    else:
        raise AssertionError("verify() should reject an all-Other classification")
    print(f"sectors self-check ok ({len(samples)} cases)")
