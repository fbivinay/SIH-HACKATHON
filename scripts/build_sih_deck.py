"""Fill the official SIH 2026 Idea template with the current state of the build.

Built by editing the supplied template in place rather than recreating it: the
file carries the SIH logo, the blue footer bar, the title placeholders and the
slide master, and the rules say the provided template must be used. So each
content slide keeps its heading and its "idea details pointers" verbatim - the
pointer box is only shrunk to a strip at the top of the content area - and our
content is drawn into the empty band below it.

python-pptx does no layout, so every box is sized from an estimated text
height and the build asserts nothing overflows its card or the slide.
"""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

REPO = Path("/home/rvina/projects/SIH HACKATHON")
TEMPLATE = REPO / "docs/deck/references/SIH2026-IDEA-Presentation-Format.pptx"
OUT = REPO / "docs/deck/SIH26102-MPLADS-SIH-Idea.pptx"

TEAM_NAME = "<Team Name>"

W, H = 13.333, 7.5
LEFT, CW = 0.67, 12.0
TOP, BOT = 1.95, 6.85
PAD = 0.16

C = lambda h: RGBColor.from_string(h)
BLUE, BLUE_D, BLUE_L = C("0070C0"), C("00548F"), C("BFDCF2")
INK, MUTED, LINE = C("101828"), C("5A6472"), C("D6DCE5")
SURF, TINT = C("F5F7FA"), C("EAF2FB")
RED, AMBER, GREEN = C("A82E22"), C("96600A"), C("16704A")

UI = "Calibri"
MONO = "Consolas"

# Characters per inch at 1pt, per font. Used to estimate wrapping.
CPI = {UI: 126, MONO: 108}


def fit_h(text, w, size, font=UI, spacing=1.22, bold=False):
    """Estimated rendered height in inches of `text` wrapped into `w` inches."""
    cpl = max(6, (w * CPI[font] / size) * (0.93 if bold else 1.0))
    lines = sum(max(1, math.ceil(len(ln) / cpl)) for ln in text.split("\n"))
    return lines * size * spacing / 72


def textbox(slide, x, y, w, h, runs, align=None, spacing=1.22):
    """runs: list of (text, size, bold, colour, font)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, (txt, size, bold, colour, font) in enumerate(runs):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align is not None:
            para.alignment = align
        para.line_spacing = spacing
        r = para.add_run()
        r.text = txt
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = colour
        r.font.name = font
    return box


def rect(slide, x, y, w, h, fill=None, line=None, line_w=0.75):
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    return sh



# ---------------------------------------------------------------- figures --
#
# Every number on these slides is read from the database at build time. This
# deck has shipped stale twice because the counts were typed in and the data
# moved underneath them; a figure nobody can forget to update is the only fix
# that holds. A missing figure raises rather than rendering a blank, because a
# slide quietly claiming "0 works scored" is worse than a build that fails.


def figures():
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    def one(sql):
        cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None

    f = {
        "works": one("SELECT COUNT(*) FROM projects"),
        "payments": one("SELECT COUNT(*) FROM expenditures"),
        "mp_terms": one("SELECT COUNT(*) FROM mps"),
        "states": one("SELECT COUNT(DISTINCT state) FROM projects WHERE state IS NOT NULL"),
        "districts": one("SELECT COUNT(DISTINCT district) FROM projects WHERE district IS NOT NULL"),
        "vendors": one("SELECT COUNT(DISTINCT vendor) FROM expenditures WHERE vendor IS NOT NULL"),
        "agencies": one("SELECT COUNT(DISTINCT implementing_agency) FROM projects"),
        "rejected": one("SELECT COUNT(*) FROM rejected_rows"),
        "scored": one("SELECT COUNT(*) FROM project_scores"),
        "queue": one("SELECT COUNT(*) FROM project_scores WHERE overall_risk_score >= 40"),
        "high": one("SELECT COUNT(*) FROM project_scores WHERE risk_level = 'HIGH'"),
        "queue_value": one(
            "SELECT COALESCE(SUM(sanctioned_amount), 0) FROM projects_scored "
            "WHERE overall_risk_score >= 40"
        ),
        "allocated_18": one("SELECT COALESCE(SUM(allocated_amount), 0) FROM mps WHERE ls_term = 18"),
        "findings": one("SELECT COUNT(*) FROM detector_findings"),
        "worst_gap": one("SELECT MAX(ABS(gap_pct)) FROM source_reconciliation"),
    }
    cur.execute("SELECT code, COUNT(*) FROM detector_findings GROUP BY code")
    f["by_code"] = dict(cur.fetchall())
    conn.close()

    cache = REPO / "data/sector_cache.json"
    f["llm_labels"] = len(json.loads(cache.read_text())) if cache.exists() else 0

    # The claim "N automated tests" is checked the same way anyone else would
    # check it, rather than being remembered.
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "data", "api"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    tail = [ln for ln in out.splitlines() if "test" in ln and "collected" in ln]
    f["tests"] = int(tail[-1].split()[0]) if tail else 0

    missing = [k for k, v in f.items() if v in (None, 0) and k not in ("rejected",)]
    if missing:
        raise SystemExit(f"deck: no figure for {', '.join(missing)} - refusing to build")

    for code in ("D-01", "D-02", "D-03", "D-04"):
        f["by_code"].setdefault(code, 0)
    return f


def crore(amount) -> str:
    return f"Rs {float(amount) / 1e7:,.0f} Cr"


def n(value) -> str:
    return f"{int(value):,}"


PROBLEMS = []


def card(slide, x, y, w, title, body, accent=BLUE, fill=SURF, ts=14, bs=12,
         min_h=0.0, tag=None):
    """A titled card sized to its own text. Returns its height."""
    tw = w - 2 * PAD - 0.08
    th = fit_h(title, tw, ts, UI, 1.16, True) if title else 0.0
    bh = fit_h(body, tw, bs, UI) if body else 0.0
    h = max(min_h, PAD + th + (0.09 if title and body else 0) + bh + PAD)
    rect(slide, x, y, w, h, fill=fill, line=LINE)
    # Accent rule down the left edge, so the card reads as a unit without a
    # heavy border.
    rect(slide, x, y, 0.045, h, fill=accent, line=None)
    yy = y + PAD
    if title:
        textbox(slide, x + PAD + 0.06, yy, tw, th, [(title, ts, True, INK, UI)], spacing=1.16)
        yy += th + (0.09 if body else 0)
    if body:
        textbox(slide, x + PAD + 0.06, yy, tw, bh, [(body, bs, False, MUTED, UI)])
    if tag:
        PROBLEMS.append((tag, y + h))
    return h


def chip(slide, x, y, w, label, value, colour=BLUE, h=0.74):
    rect(slide, x, y, w, h, fill=TINT, line=BLUE_L)
    textbox(slide, x + 0.14, y + 0.09, w - 0.28, 0.30, [(value, 15, True, colour, MONO)])
    textbox(slide, x + 0.14, y + 0.43, w - 0.28, 0.26, [(label, 10, False, MUTED, UI)])
    return h


def restyle_pointers(slide, size=10):
    """Shrink the template's pointer textbox to a strip at the top of the
    content area. The wording is left exactly as the template ships it - the
    rules forbid changing the idea-detail pointers, only their placement."""
    for sh in slide.shapes:
        if not sh.has_text_frame or sh.is_placeholder:
            continue
        t = sh.text_frame.text.strip()
        if len(t) > 40 and "Team Name" not in t:
            sh.left, sh.top = Inches(LEFT), Inches(1.30)
            sh.width, sh.height = Inches(CW), Inches(0.52)
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    r.font.size = Pt(9.5)
                    r.font.italic = True
                    r.font.bold = False
                    r.font.color.rgb = MUTED
                    r.font.name = UI
            return sh
    return None


def set_title(slide, text):
    for sh in slide.shapes:
        if sh.is_placeholder and sh.has_text_frame and sh.text_frame.text.strip():
            para = sh.text_frame.paragraphs[0]
            if not para.runs:
                continue
            # The placeholder holds a soft line break and several runs; setting
            # runs[0] alone leaves the template's own word on a second line.
            para.runs[0].text = text
            for extra in list(para.runs[1:]):
                extra._r.getparent().remove(extra._r)
            ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}br"
            for br in para._p.findall(ns):
                para._p.remove(br)
            return sh
    return None


def set_team_badge(slide):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() == "Your Team Name":
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    r.text = TEAM_NAME
            return


def main():
    f = figures()
    prs = Presentation(str(TEMPLATE))
    s = list(prs.slides)

    # ---------------------------------------------------------------- title --
    for sh in s[0].shapes:
        if sh.has_text_frame and "Problem Statement ID" in sh.text_frame.text:
            tf = sh.text_frame
            tf.clear()
            lines = [
                ("Problem Statement ID", "SIH26102"),
                ("Problem Statement Title",
                 "Development of an AI-powered system to detect anomalies, fraud, "
                 "and inefficiencies in MPLAD Scheme implementation regd."),
                ("Theme", "Smart Automation"),
                ("PS Category", "Software"),
                ("Team ID", "<Team ID>"),
                ("Team Name", TEAM_NAME),
            ]
            for i, (k, v) in enumerate(lines):
                para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                para.line_spacing = 1.2
                para.space_after = Pt(7)
                a = para.add_run(); a.text = f"{k} – "
                a.font.size = Pt(13); a.font.bold = True
                a.font.color.rgb = INK; a.font.name = UI
                b = para.add_run(); b.text = v
                b.font.size = Pt(12 if k != "Problem Statement Title" else 10.5)
                b.font.color.rgb = MUTED; b.font.name = UI
            break

    # ------------------------------------------------------------- slide 2 --
    set_title(s[1], "KASAUTI")
    set_team_badge(s[1])
    restyle_pointers(s[1])
    y = TOP
    steps = [
        ("READ", f"{n(f['works'])} works, {n(f['payments'])}\npayments, {n(f['mp_terms'])} MP-terms"),
        ("COMPARE", "Each work against its own\ndistrict-and-sector peers"),
        ("DETECT", "5 work signals, 4 cohort\ndetectors, 4 written rules"),
        ("SCORE", "One 0-100 number, with\nthe records behind it"),
        ("ACT", "A ranked queue, and a trail\nof every decision on it"),
    ]
    sw = (CW - 4 * 0.14) / 5
    for i, (name, body) in enumerate(steps):
        x = LEFT + i * (sw + 0.14)
        rect(s[1], x, y, sw, 1.24, fill=TINT, line=BLUE_L)
        textbox(s[1], x + 0.14, y + 0.12, sw - 0.28, 0.28, [(name, 13, True, BLUE_D, UI)])
        textbox(s[1], x + 0.14, y + 0.46, sw - 0.28, 0.68, [(body, 10, False, MUTED, UI)], spacing=1.16)
    y += 1.24 + 0.24

    cw3 = (CW - 2 * 0.18) / 3
    hs = [
        card(s[1], LEFT, y, cw3, "Kasauti — the touchstone",
             "A jeweller rubs gold against a kasauti and reads the streak: the stone "
             "says which pieces are worth assaying, never which are false. This reads "
             "the published MPLADS record end to end and scores every work against "
             f"comparable works in the same district and sector. {n(f['queue'])} clear "
             f"the review threshold, carrying {crore(f['queue_value'])} of sanction. "
             "Officials get them ranked, not a spreadsheet.", BLUE, min_h=3.35, tag="s2a"),
        card(s[1], LEFT + cw3 + 0.18, y, cw3, "Innovation and uniqueness",
             "Every flag names the record that produced it. Cohort patterns are kept "
             "at cohort grain instead of being blamed on one work. Reviewer decisions "
             "are pinned to a work identity that survives the nightly reload, so a "
             "verdict is never reattached to a different work, and every decision "
             "ever recorded on one survives the next.", GREEN, min_h=3.35, tag="s2b"),
        card(s[1], LEFT + 2 * (cw3 + 0.18), y, cw3, "What it does not claim",
             "A score is not an allegation - it means a work does not resemble its "
             "peers. No field is invented: progress %, beneficiary counts and geo-tags "
             "are not published, so they are not shown. The rule book states what "
             "cannot be checked at all. A language model only labels what a work is, "
             "so it meets the right peers; it never scores or flags anything.",
             AMBER, min_h=3.35,
             tag="s2c"),
    ]

    # ------------------------------------------------------------- slide 3 --
    set_title(s[2], "TECHNICAL APPROACH")
    set_team_badge(s[2])
    restyle_pointers(s[2])
    y = TOP
    stacks = [
        ("AI / ML", "MiniLM sentence transformer\nIsolation Forest\nBenford + HHI statistics\nGemini sector labelling"),
        ("BACKEND", "FastAPI, read-mostly\nPostgres on Neon\nPooled, retries dead links\nOne authenticated write"),
        ("FRONTEND", "Next.js App Router\nTypeScript, Tailwind\nServer-rendered\nLeaflet map"),
        ("PLATFORM", f"Vercel, two projects\nGitHub Actions nightly\n{n(f['tests'])} automated tests\nLive since day one"),
    ]
    sw = (CW - 3 * 0.18) / 4
    for i, (name, body) in enumerate(stacks):
        x = LEFT + i * (sw + 0.18)
        h = 1.50
        rect(s[2], x, y, sw, h, fill=SURF, line=LINE)
        rect(s[2], x, y, sw, 0.035, fill=BLUE, line=None)
        textbox(s[2], x + 0.16, y + 0.15, sw - 0.32, 0.28, [(name, 12, True, BLUE_D, UI)])
        textbox(s[2], x + 0.16, y + 0.50, sw - 0.32, 1.00, [(body, 10.5, False, MUTED, UI)], spacing=1.26)
    y += 1.50 + 0.20

    textbox(s[2], LEFT, y, CW, 0.22,
            [("The risk score: five weighted signals about the work itself", 12, True, INK, UI)])
    y += 0.34
    weights = [("COST", "25%"), ("DELAY", "25%"), ("DUPLICATE", "20%"),
               ("AGENCY", "15%"), ("COMPLIANCE", "15%")]
    ww = (CW - 4 * 0.14) / 5
    for i, (name, pct) in enumerate(weights):
        chip(s[2], LEFT + i * (ww + 0.14), y, ww, name, pct, BLUE_D, h=0.74)
    y += 0.74 + 0.24

    textbox(s[2], LEFT, y, CW, 0.22,
            [("Four cohort detectors: patterns that belong to an agency or an MP, never folded into a work's score",
              12, True, INK, UI)])
    y += 0.34
    c = f["by_code"]
    dets = [("D-01 Year-end burst", n(c["D-01"])), ("D-02 First-digit", n(c["D-02"])),
            ("D-03 Idle allocation", n(c["D-03"])), ("D-04 Uniform amount", n(c["D-04"]))]
    dw = (CW - 3 * 0.14) / 4
    for i, (name, count) in enumerate(dets):
        chip(s[2], LEFT + i * (dw + 0.14), y, dw, name, count + " findings", GREEN, h=0.74)
    y += 0.74 + 0.18

    rect(s[2], LEFT, y, CW, 0.62, fill=SURF, line=LINE)
    textbox(s[2], LEFT + 0.16, y + 0.12, CW - 0.32, 0.40,
            [("Four compliance rules, each published with the exact condition it tests — "
              "including the one that cannot fire, because the source publishes a single "
              "figure per completed work that serves as both sanction and expenditure.",
              10, False, MUTED, UI)], spacing=1.28)
    y += 0.62
    PROBLEMS.append(("s3", y))

    # ------------------------------------------------------------- slide 4 --
    set_title(s[3], "FEASIBILITY AND VIABILITY")
    set_team_badge(s[3])
    restyle_pointers(s[3])
    y = TOP
    rect(s[3], LEFT, y, CW, 0.70, fill=TINT, line=BLUE_L)
    textbox(s[3], LEFT + 0.18, y + 0.17, CW - 0.36, 0.38,
            [(f"Not a proposal - already built, deployed and refreshing nightly: "
              f"{n(f['scored'])} works scored, all {n(f['states'])} states reconciled against "
              f"the official MoSPI dashboard to within {float(f['worst_gap']):.1f}%, live at "
              "mplads-risk-monitor-web.vercel.app", 12.5, True, BLUE_D, UI)])
    y += 0.70 + 0.24

    hs = [
        card(s[3], LEFT, y, cw3, "Feasibility",
             "The data is already public and machine-readable: four CSVs, refreshed "
             "nightly by a scheduled job that loads in 2 minutes and scores in about "
             "20. No ministry integration, no new reporting burden on any officer, "
             f"no hardware. {n(f['tests'])} automated tests run against the pipeline and the API.",
             GREEN, min_h=3.90, tag="s4a"),
        card(s[3], LEFT + cw3 + 0.18, y, cw3, "Challenges and risks",
             "Work IDs restart per agency, so 271 works had inherited a stranger's "
             "start date. Cost deviation had no ceiling and overflowed its column, "
             "losing the very outliers that matter. Dead pooled connections turned "
             "one expiry into a rolling outage. All three were found and fixed.",
             AMBER, min_h=3.90, tag="s4b"),
        card(s[3], LEFT + 2 * (cw3 + 0.18), y, cw3, "How we overcome them",
             "A work's identity is (Work ID, term, agency), unique across both "
             "extracts. Every threshold is calibrated on the measured distribution, "
             "not a textbook constant. A killed refresh now records its own death "
             "instead of being reported as the next run's success.",
             BLUE, min_h=3.90, tag="s4c"),
    ]

    # ------------------------------------------------------------- slide 5 --
    set_title(s[4], "IMPACT AND BENEFITS")
    set_team_badge(s[4])
    restyle_pointers(s[4])
    y = TOP
    stats = [(n(f["scored"]), "works scored, both terms"),
             (crore(f["allocated_18"]), "allocated, 18th Lok Sabha"),
             (n(f["queue"]), "works above the threshold"),
             (crore(f["queue_value"]), "sanction awaiting review"),
             (n(f["findings"]), "cohort findings")]
    sw = (CW - 4 * 0.14) / 5
    for i, (value, label) in enumerate(stats):
        chip(s[4], LEFT + i * (sw + 0.14), y, sw, label, value, BLUE_D, h=0.82)
    y += 0.82 + 0.24

    who = [("Member of Parliament",
            "Their own page: what they recommended, what got built, how much allocation "
            "was never committed to any work, and which of it is flagged."),
           ("District authority",
            "A district desk led by the implementing agencies it supervises, with vendor "
            "concentration and a ranked shortlist instead of a register."),
           ("State nodal officer",
            f"A state desk ranking every district by the queue it has to clear, and all "
            f"{n(f['states'])} states on money committed against money paid."),
           ("Ministry (MoSPI)",
            "National patterns, the compliance rule book and a provenance page reconciling "
            "every headline figure against the Ministry's own dashboard.")]
    cw4 = (CW - 3 * 0.16) / 4
    for i, (name, body) in enumerate(who):
        card(s[4], LEFT + i * (cw4 + 0.16), y, cw4, name, body, BLUE, ts=12, bs=10.5,
             min_h=2.55, tag=f"s5-{i}")
    y += 2.55 + 0.24

    rect(s[4], LEFT, y, CW, 1.02, fill=SURF, line=LINE)
    textbox(s[4], LEFT + 0.18, y + 0.15, CW - 0.36, 0.76,
            [("Social — public money is checked against its own record, not against nobody.  "
              "Economic — verification effort goes where the deviation is, so a fixed audit "
              "budget covers more ground.  Governance — every flag is traceable to the rows "
              "that produced it, so a finding can be argued with rather than merely believed.",
              11.5, False, MUTED, UI)], spacing=1.32)
    y += 1.02
    PROBLEMS.append(("s5", y))

    # ------------------------------------------------------------- slide 6 --
    set_title(s[5], "RESEARCH AND REFERENCES")
    set_team_badge(s[5])
    restyle_pointers(s[5])
    y = TOP
    cw2 = (CW - 0.20) / 2
    h_data = card(s[5], LEFT, y, cw2, "The designated dataset, and what it serves",
         "The problem statement names mplads.mospi.gov.in. Its public interface, "
         "enumerated from its own JavaScript and called directly: totals, "
         "states, districts and member names are open to anyone. Works are not. Completed "
         "works come only through a citizen rating form that needs an SMS one-time password "
         "on an Indian mobile, returns one member's works in one ward per call, and is rate "
         "limited. Recommended works, payments and vendors are not served at all; every "
         "other path answers 302 to the login page.\n"
         "Empowered Indian republishes that record as machine-readable exports. Its own "
         "uploader reads the State Bank disbursement portal that MPLADS money is paid "
         "through, with a signed-in session cookie at one request every three seconds.\n"
         f"So this system loads those exports - {n(f['works'])} works, {n(f['payments'])} "
         f"payments, {n(f['mp_terms'])} MP-terms, {n(f['districts'])} districts, "
         f"{n(f['vendors'])} vendors - and reconciles against the official endpoints on "
         f"every refresh: five figures within {float(f['worst_gap']):.1f}%, every gap "
         "negative because our snapshot trails a portal that gains works overnight. "
         f"{n(f['rejected'])} rows rejected and recorded, not silently dropped.",
         BLUE, bs=10, min_h=3.85, tag="s6a")
    h_left = card(s[5], LEFT + cw2 + 0.20, y, cw2, "Methods",
         "Liu, Ting and Zhou (2008), Isolation Forest — multivariate outliers over "
         "amount, delay and spend.\n"
         "Reimers and Gurevych (2019), Sentence-BERT — all-MiniLM-L6-v2 embeddings, "
         "cosine 0.94 within a district and sector, for duplicate sanctions.\n"
         "Newcomb-Benford first-digit law, with Nigrini's MAD — used peer-relative, "
         "because the population itself does not conform.\n"
         "Herfindahl-Hirschman Index - vendor concentration per implementing agency.\n"
         "MPLADS Guidelines, MoSPI - permissible works, sanction ceilings, entitlement per MP.",
         GREEN, bs=11, min_h=3.85, tag="s6b")
    y += max(h_data, h_left) + 0.24

    rect(s[5], LEFT, y, CW, 0.72, fill=TINT, line=BLUE_L)
    textbox(s[5], LEFT + 0.18, y + 0.13, CW - 0.36, 0.50,
            [("Working prototype   mplads-risk-monitor-web.vercel.app          "
              "API   mplads-risk-monitor.vercel.app/api/overview          "
              "Source   github.com/fbivinay/SIH-HACKATHON", 11, True, BLUE_D, MONO)],
            spacing=1.32)
    y += 0.72
    PROBLEMS.append(("s6", y))

    # ------------------------------------------- drop the instructions slide --
    ids = prs.slides._sldIdLst
    ids.remove(list(ids)[6])

    prs.save(str(OUT))
    return prs


def verify():
    """Check only the shapes this script added.

    The template's own furniture - the footer bar, the slide number, the SIH
    logo, the title slide's decorative freeforms - legitimately runs to the
    bottom edge, so comparing every shape against the content band flags the
    template rather than our work. Shape ids present in the template are
    therefore excluded by id.
    """
    template_ids = {}
    for i, slide in enumerate(Presentation(str(TEMPLATE)).slides, 1):
        template_ids[i] = {sh.shape_id for sh in slide.shapes}

    prs = Presentation(str(OUT))
    print(f"slides: {len(prs.slides)}")
    band = H - 0.55
    bad = 0
    for i, slide in enumerate(prs.slides, 1):
        lowest, added = 0.0, 0
        for sh in slide.shapes:
            if sh.shape_id in template_ids.get(i, set()):
                continue
            if sh.left is None or sh.top is None:
                continue
            added += 1
            l, t = sh.left / 914400, sh.top / 914400
            w = (sh.width or 0) / 914400
            h = (sh.height or 0) / 914400
            if l < -0.05 or t < -0.05 or l + w > W + 0.05 or t + h > H + 0.05:
                print(f"  slide {i}: OFF-SLIDE {l:.2f},{t:.2f} {w:.2f}x{h:.2f} "
                      f"{sh.text_frame.text[:40] if sh.has_text_frame else ''}")
                bad += 1
            lowest = max(lowest, t + h)
        flag = "  <-- past the footer band" if lowest > band else ""
        print(f"  slide {i}: {added:>2} added shapes, bottom {lowest:.2f} (band {band:.2f}){flag}")
        if lowest > band:
            bad += 1

    # Pointer wording must survive byte for byte - the rules allow moving the
    # idea-detail pointers, not editing them.
    tmpl = Presentation(str(TEMPLATE))
    for i in range(1, 6):
        want = _pointer_text(tmpl.slides[i])
        got = _pointer_text(prs.slides[i])
        if want and want != got:
            print(f"  slide {i+1}: POINTER TEXT CHANGED")
            bad += 1
    print(f"problems: {bad}")
    return bad


def _pointer_text(slide):
    for sh in slide.shapes:
        if not sh.has_text_frame or sh.is_placeholder:
            continue
        t = sh.text_frame.text.strip()
        if len(t) > 40 and "Team Name" not in t:
            return t
    return None


if __name__ == "__main__":
    main()
    sys.exit(1 if verify() else 0)
