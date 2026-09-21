"""Who each Member of Parliament is: party, age, education, terms and photo.

MPLADS publishes a member's money and works, and nothing about the member.
Parliament does: sansad.in serves every Lok Sabha member of the 17th and 18th
terms and every Rajya Sabha member ever seated, with a photograph. This script
reads both, matches them to the members in our `mps` table, and writes

  web/data/mp_profiles.json    one entry per matched mp_id, committed
  web/public/mps/<mp_id>.webp  the photograph, 120x150, committed

and, for sitting members MPLADS does not list yet, the same under "unlisted",
keyed ls-<sansad id> / rs-<sansad id>. It runs nightly in the refresh
workflow, after the MPLADS load, so a member the portal adds is matched the
next morning.

Committed for the same reason data/sector_cache.json is: a clone renders every
profile with no network call, and the site never depends on sansad.in being up.
The photographs cannot be linked instead - sansad.in sends
`Cross-Origin-Resource-Policy: same-site`, so a browser refuses to show them
on any other site.

Only what a member's public role consists of is kept. The records also carry
personal phone numbers, personal e-mail addresses, home addresses, marital
status and number of children; none of that is read into the output.

A member we cannot match with confidence is left out rather than guessed:
the page then shows initials in place of a photograph and no party, which is
honest, where a wrong match would put a stranger's face beside a member's
money. Every miss is printed.

Run: python3 scripts/fetch_mp_profiles.py   (needs DATABASE_URL)
"""

import difflib
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg2
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "web" / "data" / "mp_profiles.json"
OUT_PHOTOS = ROOT / "web" / "public" / "mps"
UA = {"User-Agent": "Mozilla/5.0 (Kasauti MPLADS verification; research use)"}
BASE = "https://sansad.in"

# Below this a name match is treated as no match. Measured on this data: true
# matches score 0.8-1.0 (titles and spellings differ, "A. Raja" vs "Raja A");
# the best wrong candidate in the same state and term sits under 0.55.
NAME_FLOOR = 0.62

HONORIFICS = {
    "shri", "smt", "sh", "dr", "adv", "advocate", "prof", "kumari", "km", "sushri",
    "ms", "mr", "mrs", "thiru", "tmt", "capt", "col", "lt", "gen", "retd",
    "sardar", "s", "choudhary", "ch", "pt", "pandit", "sri", "smti", "hon",
}


def get_json(path: str):
    for attempt in range(4):
        try:
            with urlopen(Request(BASE + path, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def norm_state(s: str | None) -> str:
    s = (s or "").strip().lower().replace("&", "and")
    s = re.sub(r"[^a-z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^the ", "", s)
    # One spelling each, whatever the source. Rajya Sabha writes "Keralam" and
    # "National Capital Territory of Delhi"; the portal writes neither.
    return {"nct of delhi": "delhi", "national capital territory of delhi": "delhi",
            "keralam": "kerala", "orissa": "odisha", "pondicherry": "puducherry",
            "dadra and nagar haveli and daman and diu": "dadra and nagar haveli",
            }.get(s, s)


def norm_const(s: str | None) -> str:
    s = (s or "").lower()
    s = re.sub(r"\((sc|st)\)", "", s)
    return re.sub(r"[^a-z]", "", s)


def name_tokens(s: str | None) -> list[str]:
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)          # "(2024-30)", "(17th Lok Sabha)"
    s = re.sub(r"[^a-z ]", " ", s)
    return [t for t in s.split() if t not in HONORIFICS and len(t) > 1]


def name_score(a: str, b: str) -> float:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    # Order-free: sansad writes "Raja A", the portal "A. Raja".
    seq = difflib.SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    overlap = len(set(ta) & set(tb)) / min(len(set(ta)), len(set(tb)))
    return max(seq, overlap * 0.95)


def years(s: str | None) -> tuple[int, int] | None:
    """'2024-30', '2024-2030' -> (2024, 2030)."""
    m = re.search(r"(\d{4})\s*-\s*(\d{2,4})", s or "")
    if not m:
        return None
    a, b = int(m.group(1)), m.group(2)
    b = int(b) if len(b) == 4 else (a // 100) * 100 + int(b)
    return a, b


def fetch_lok_sabha(term: int) -> list[dict]:
    first = get_json(f"/api_ls/member?loksabha={term}&page=1&size=1")
    total = first["metaDatasDto"]["totalElements"]
    rows = get_json(f"/api_ls/member?loksabha={term}&page=1&size={total}")["membersDtoList"]
    print(f"Lok Sabha {term}: {len(rows)} members")
    return rows


def fetch_rajya_sabha() -> list[dict]:
    out, page = [], 1
    while True:
        d = get_json(f"/api_rs/member/sitting-members?page={page}&size=500")
        out += d["records"]
        if page >= d["_metadata"]["totalPages"]:
            break
        page += 1
    # Only members whose seat overlaps the two terms this record covers.
    keep = [r for r in out if (y := years(r.get("term"))) and y[1] >= 2019]
    print(f"Rajya Sabha: {len(out)} records, {len(keep)} seated since 2019")
    return keep


def ls_profile(m: dict) -> dict:
    return {
        "sansad_id": m["mpsno"],
        "source": "Lok Sabha",
        "name": (m.get("mpFirstLastName") or "").strip(),
        "party": (m.get("partyFname") or "").strip() or None,
        "party_short": (m.get("partySname") or "").strip() or None,
        "gender": m.get("gender") or None,
        "age": m.get("age"),
        "qualification": (m.get("qualification") or "").strip() or None,
        "profession": ", ".join(
            p for p in [(m.get("profession") or "").strip(), (m.get("profession2") or "").strip()] if p
        ) or None,
        "terms_served": m.get("noOfTerms"),
        "lok_sabhas": (m.get("lsExpr") or "").strip() or None,
        "status": m.get("status"),
        "image": m.get("imageUrl"),
    }


def rs_profile(m: dict) -> dict:
    last, first = (m.get("lastName") or "").strip(), (m.get("firstName") or "").strip()
    return {
        "sansad_id": m["mpsno"],
        "source": "Rajya Sabha",
        "name": " ".join(p for p in [first, last] if p) or (m.get("name") or "").strip(),
        "party": (m.get("party") or "").strip() or None,
        "party_short": (m.get("partyCode") or "").strip() or None,
        "gender": m.get("gender") or None,
        "age": m.get("age"),
        "qualification": None,
        "profession": None,
        "terms_served": m.get("termCount"),
        "rs_term": (m.get("term") or "").strip() or None,
        "status": (m.get("status") or "").strip() or None,
        "image": m.get("imageUrl"),
    }


def _match_ls(o: dict, roster: list[dict], taken: set) -> tuple[float, dict | None, bool]:
    state = norm_state(o["state"])
    roster = [m for m in roster if m["mpsno"] not in taken]
    pool = [m for m in roster if norm_state(m.get("stateName")) == state]
    same_seat = [m for m in pool if norm_const(m.get("constName")) == norm_const(o["constituency"])]
    # A seat usually has one member; a by-election gives it two, and then the
    # name decides. With no seat match (a spelling), the name decides across
    # the state, at the same floor.
    cands = same_seat or pool
    scored = sorted(((name_score(o["mp_name"], m["mpFirstLastName"]), m) for m in cands),
                    key=lambda x: -x[0])
    best = scored[0] if scored else (0.0, None)
    # One member on the seat that term is very likely the member, however the
    # two sources spell the name ("VISHAL" and "Vishaldada Prakashbapu Patil"
    # hold Sangli in the 18th) - but not certainly: a member who won the seat
    # and later moved is listed at the new one, leaving the by-election winner
    # alone on the old seat. The one-record-per-term pass in match() is what
    # catches that; the 0.3 floor keeps an unrelated name out regardless.
    ok = best[1] is not None and (
        (len(same_seat) == 1 and best[0] >= 0.3) or best[0] >= NAME_FLOOR
    )
    if not ok:
        # The 17th's roster lists each member at their CURRENT seat, so one who
        # moved (Wayanad to Rae Bareli) is not in the old state at all. Across
        # the whole term, then, at a much stricter floor and only when the
        # name is unambiguous, since a common name can recur elsewhere.
        anywhere = sorted(((name_score(o["mp_name"], m["mpFirstLastName"]), m) for m in roster),
                          key=lambda x: -x[0])
        if anywhere and anywhere[0][0] >= 0.9 and (len(anywhere) == 1 or anywhere[1][0] < 0.9):
            best, ok = anywhere[0], True
    return best[0], best[1], ok


def _match_rs(o: dict, rs: list[dict]) -> tuple[float, dict | None, bool]:
    state = norm_state(o["state"])
    want = years(o["mp_name"])
    # A nominated member is filed under "Nominated", not under the state the
    # portal attributes their fund to.
    nominated = "nominated" in (o["constituency"] or "").lower()
    pool = [m for m in rs if norm_state(m.get("state")) in
            ({state, "nominated"} if nominated else {state})]
    scored = []
    for m in pool:
        s = name_score(o["mp_name"], m.get("name") or "")
        # The portal writes the seat's years into the name: a record with the
        # same years is the same seat, not a namesake.
        if want and years(m.get("term")) == want:
            s += 0.1
        scored.append((s, m))
    scored.sort(key=lambda x: -x[0])
    best = scored[0] if scored else (0.0, None)
    return best[0], best[1], best[1] is not None and best[0] >= NAME_FLOOR


def match(ours: list[dict], ls: dict[int, list[dict]], rs: list[dict]):
    """Match every member, then make sure no Lok Sabha record stands for two
    different members in the same term.

    Two of our rows in one term wanting the same record means one of them is
    wrong - measured: Akhilesh Yadav, who won Azamgarh in 2019 and now sits for
    Kannauj, was matched to Dinesh Lal Yadav, who won Azamgarh's by-election.
    The stronger match keeps the record and the other is matched again without
    it, which is how Akhilesh reaches his own record at Kannauj.
    """
    taken: dict[int, set] = {17: set(), 18: set()}
    result: dict[str, tuple[float, dict | None, bool]] = {}
    pending = [o for o in ours if o["house"] == "Lok Sabha"]
    for _ in range(5):
        for o in pending:
            result[o["mp_id"]] = _match_ls(o, ls[o["ls_term"]], taken[o["ls_term"]])
        claims: dict[tuple, list] = {}
        for o in (x for x in ours if x["house"] == "Lok Sabha"):
            score, rec, ok = result[o["mp_id"]]
            if ok:
                claims.setdefault((o["ls_term"], rec["mpsno"]), []).append((score, o))
        pending = []
        for (term, sid), who in claims.items():
            if len(who) > 1:
                # The winner keeps it; everyone else is re-matched without it.
                who.sort(key=lambda x: -x[0])
                taken[term].add(sid)
                pending += [loser for _, loser in who[1:]]
        if not pending:
            break

    matched, missed = {}, []
    for o in ours:
        score, rec, ok = result[o["mp_id"]] if o["house"] == "Lok Sabha" else _match_rs(o, rs)
        if ok:
            matched[o["mp_id"]] = (ls_profile if o["house"] == "Lok Sabha" else rs_profile)(rec)
        else:
            name = rec and (rec.get("mpFirstLastName") or rec.get("name"))
            missed.append((o, score, name))
    return matched, missed


def fetch_photo(mp_id: str, url: str | None) -> bool:
    if not url:
        return False
    dest = OUT_PHOTOS / f"{mp_id}.webp"
    if dest.exists():
        return True
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=UA), timeout=60) as r:
                raw = r.read()
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            # Cover-crop to 4:5 and shrink: shown at most 96px wide, twice
            # that for high-density screens, and ~4KB rather than ~18KB.
            w, h = img.size
            tw = min(w, int(h * 4 / 5))
            th = int(tw * 5 / 4)
            left, top = (w - tw) // 2, max(0, (h - th) // 3)
            img = img.crop((left, top, left + tw, top + th)).resize((120, 150), Image.LANCZOS)
            img.save(dest, "WEBP", quality=72, method=6)
            return True
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return False


def unlisted(matched: dict, term18_ids: set, ls18: list[dict], rs: list[dict], our_states: set) -> dict:
    """Sitting members with no row in the MPLADS record at all.

    The portal lists a member once their fund account exists, so a member
    seated weeks ago - thirteen Rajya Sabha members elected in 2026, and one
    Lok Sabha member - is in Parliament and not yet in MPLADS. They are still
    members, and a page of "every member" that leaves them out is wrong. They
    are listed with Parliament's profile and no money at all: nothing is
    shown for a figure the source does not publish (CLAUDE.md §1).
    """
    used = {(p["source"], p["sansad_id"]) for k, p in matched.items() if k in term18_ids}
    # Our spelling of each state, so the page's state filter finds them.
    canon = {norm_state(x): x for x in our_states}
    out = {}
    for m in ls18:
        if m.get("status") == "Sitting" and ("Lok Sabha", m["mpsno"]) not in used:
            p = ls_profile(m)
            p.update(house="Lok Sabha", seat=(m.get("constName") or "").strip() or None,
                     state=canon.get(norm_state(m.get("stateName")), (m.get("stateName") or "").strip()))
            out[f"ls-{m['mpsno']}"] = p
    for m in rs:
        if (m.get("status") or "").strip() == "Sitting" and ("Rajya Sabha", m["mpsno"]) not in used:
            p = rs_profile(m)
            st = norm_state(m.get("state"))
            p.update(house="Rajya Sabha", seat="Nominated" if st == "nominated" else None,
                     state=None if st == "nominated" else canon.get(st, (m.get("state") or "").strip()))
            out[f"rs-{m['mpsno']}"] = p
    return out


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT mp_id, ls_term, mp_name, constituency, state, house FROM mps")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    # One profile per mp_id; a member in both terms is matched on the later.
    ours = {}
    for r in sorted(rows, key=lambda r: r["ls_term"]):
        ours[r["mp_id"]] = r
    ours = list(ours.values())
    print(f"Our members: {len(ours)} distinct mp_id")

    ls = {17: fetch_lok_sabha(17), 18: fetch_lok_sabha(18)}
    rs = fetch_rajya_sabha()
    matched, missed = match(ours, ls, rs)
    for o, s, cand in sorted(missed, key=lambda x: (x[0]["house"], x[0]["state"])):
        print(f"  MISS {o['house']:<11} {o['ls_term']} {o['state']:<18} "
              f"{o['mp_name']!r:<45} best={s:.2f} {cand!r}")
    # Checked BEFORE anything is written. This runs nightly and its output is
    # committed; a sansad.in outage or a changed response shape must leave
    # yesterday's file in place, not replace it with a half-matched one.
    if len(matched) < 0.9 * len(ours):
        sys.exit(f"Only {len(matched)} of {len(ours)} matched - nothing written.")

    extra = unlisted(matched, {r["mp_id"] for r in rows if r["ls_term"] == 18}, ls[18], rs,
                     {r["state"] for r in rows if r["state"]})

    OUT_PHOTOS.mkdir(parents=True, exist_ok=True)
    everyone = {**matched, **extra}
    with ThreadPoolExecutor(4) as ex:  # gentle: four at a time
        got = dict(zip(everyone, ex.map(lambda k: fetch_photo(k, everyone[k]["image"]), everyone)))
    for k, p in everyone.items():
        p["photo"] = f"/mps/{k}.webp" if got[k] else None
        p.pop("image", None)

    body = {"source": "https://sansad.in (Lok Sabha and Rajya Sabha member records)",
            "profiles": dict(sorted(matched.items())),
            "unlisted": dict(sorted(extra.items()))}
    # Rewritten only when something in it changed, so a quiet night makes no
    # commit and no redeploy: fetched_at alone would differ every run.
    try:
        old = json.loads(OUT_JSON.read_text())
        old.pop("fetched_at", None)
    except Exception:
        old = None
    if old == body:
        print("\nProfiles unchanged - file left as it was.")
    else:
        OUT_JSON.write_text(json.dumps(
            {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **body},
            ensure_ascii=False, indent=1) + "\n")
        print("\nProfiles written.")

    print(f"Matched {len(matched)} of {len(ours)}; sitting but not in MPLADS {len(extra)}; "
          f"photos {sum(got.values())} of {len(everyone)}; unmatched {len(missed)}")
    # A producer that silently produced nothing looks like a clean run (§9).
    if sum(got.values()) < 0.9 * len(everyone):
        print("WARNING: fewer than 90% of photographs were fetched.")


if __name__ == "__main__":
    main()
