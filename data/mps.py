"""Stable identity for a Member of Parliament.

WHY THIS EXISTS
---------------
`MP Name` is not a key. The extracts carry 1,262 distinct name strings across
the two Lok Sabha terms against 773 (LS17) and 774 (LS18) actual MPs, because
the source appends a term marker and varies honorifics and spacing:

    Smt. S. Phangnon Konyak (2022-28)
    A Ganeshamurthi(17th Lok Sabha)
    Manne Srinivas Reddy(17th Lok Sabha)
    Shri Manne Srinivas Reddy (17th Lok Sabha)      <- the same person

Group by the raw name and one MP's record splits across two identities, which
is exactly the failure that makes a per-MP utilisation figure wrong.

WHAT IT KEYS ON
---------------
Normalised name + state + house. State and house are needed because names
repeat: two different MPs can share a name, and the pair separates them. The
name is normalised by stripping the term marker and honorifics, casefolding and
collapsing whitespace, then the three are hashed to a short stable id.

VERIFIED ON THE 2026-08-31 EXTRACT
----------------------------------
773 distinct ids for LS17's 774 summary rows, 774 for LS18's 774, and 1,110
across both terms with 437 MPs serving in each. Every MP named in the works and
expenditure files resolves to an id present in the MP summary.

The LS17 shortfall is real and not a merge error: that extract lists
`Manne Srinivas Reddy(17th Lok Sabha)` and `Shri Manne Srinivas Reddy (17th Lok
Sabha)` as two rows for one MP.
"""

import hashlib
import re

from sectors import normalize

HONORIFICS = {
    "shri", "sh", "shrimati", "smt", "sri", "srimati", "dr", "prof",
    "mr", "mrs", "ms", "adv", "col", "capt", "maj", "gen", "kum", "kumari",
}

# Term markers the source appends: '(2022-28)', '(17th Lok Sabha)', '(17LS)'.
# Deliberately narrow. Other parentheticals are parts of the name - the extract
# contains '(Banerjee)', '(Dev)', '(Lalan)' - and must survive.
TERM_SUFFIX = re.compile(
    r"\(\s*(?:\d{4}\s*-\s*\d{2,4}|\d{1,2}\s*(?:st|nd|rd|th)?\s*(?:LS|Lok\s*Sabha))\s*\)",
    re.IGNORECASE,
)


def normalize_mp_name(name):
    """Strip term marker and honorifics; casefold; collapse whitespace.

    Single characters are dropped with the honorifics: initials are written
    inconsistently ('A Ganeshamurthi' / 'A. Ganeshamurthi' / 'Ganeshamurthi')
    and keeping them splits the same MP in two.
    """
    text = normalize(TERM_SUFFIX.sub(" ", str(name or "")))
    return " ".join(p for p in text.split() if p not in HONORIFICS and len(p) > 1)


def mp_key(name, state, house):
    """Short stable id for one MP. Raises if the name normalises to nothing."""
    normalized = normalize_mp_name(name)
    if not normalized:
        raise ValueError(f"unusable MP name: {name!r}")
    basis = f"{normalized}|{normalize(state)}|{normalize(house)}"
    return hashlib.sha1(basis.encode()).hexdigest()[:16]


def safe_mp_key(name, state, house):
    """mp_key, or None for a name that carries no usable text.

    Used on the works rows: a work with an unusable MP name is still a work
    worth loading and scoring; it just cannot take part in per-MP aggregates.
    """
    try:
        return mp_key(name, state, house)
    except ValueError:
        return None
