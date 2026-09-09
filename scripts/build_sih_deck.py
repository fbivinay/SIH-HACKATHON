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

import math
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
                 "An AI-powered monitoring system that reads MPLADS project data, "
                 "detects suspicious patterns/anomalies and inefficiencies, assigns "
                 "a risk score, and helps authorities decide which projects need "
                 "verification."),
                ("Theme", "<Theme as listed on the portal>"),
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
    set_title(s[1], "MPLADS RISK MONITOR")
    set_team_badge(s[1])
    restyle_pointers(s[1])
    y = TOP
    steps = [
        ("READ", "250,839 works, 272,263\npayments, 1,547 MP-terms"),
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
        card(s[1], LEFT, y, cw3, "How it addresses the problem",
             "Reads the published MPLADS record end to end and scores every work "
             "against comparable works in the same district and sector. 48,542 works "
             "clear the review threshold, carrying Rs 4,662 Cr of sanction. Officials "
             "get them ranked, not a spreadsheet.", BLUE, min_h=3.35, tag="s2a"),
        card(s[1], LEFT + cw3 + 0.18, y, cw3, "Innovation and uniqueness",
             "Every flag names the record that produced it. Cohort patterns are kept "
             "at cohort grain instead of being blamed on one work. Reviewer decisions "
             "are pinned to a work identity that survives the nightly reload, so a "
             "verdict is never reattached to a different work, and every decision "
             "ever recorded on one survives the next.", GREEN, min_h=3.35, tag="s2b"),
        card(s[1], LEFT + 2 * (cw3 + 0.18), y, cw3, "What it does not claim",
             "A score is not an allegation - it means a work does not resemble its "
             "peers. No field is invented: progress %, beneficiary counts and geo-tags "
             "are not published for MPLADS, so they are not shown. The rule book states "
             "what cannot be checked at all. No LLM can move a score.", AMBER, min_h=3.35,
             tag="s2c"),
    ]

    # ------------------------------------------------------------- slide 3 --
    set_title(s[2], "TECHNICAL APPROACH")
    set_team_badge(s[2])
    restyle_pointers(s[2])
    y = TOP
    stacks = [
        ("AI / ML", "MiniLM sentence transformer\nIsolation Forest\nBenford + HHI statistics\npandas, scikit-learn"),
        ("BACKEND", "FastAPI, read-mostly\nPostgres on Neon\nPooled, retries dead links\nOne authenticated write"),
        ("FRONTEND", "Next.js App Router\nTypeScript, Tailwind\nServer-rendered\nLeaflet map"),
        ("PLATFORM", "Vercel, two projects\nGitHub Actions nightly\n85 automated tests\nLive since day one"),
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
    dets = [("D-01 Year-end burst", "311"), ("D-02 First-digit", "137"),
            ("D-03 Idle allocation", "255"), ("D-04 Uniform amount", "209")]
    dw = (CW - 3 * 0.14) / 4
    for i, (name, n) in enumerate(dets):
        chip(s[2], LEFT + i * (dw + 0.14), y, dw, name, n + " findings", GREEN, h=0.74)
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
            [("Not a proposal — already built, deployed and refreshing nightly: "
              "250,839 works scored, all 36 states reconciled against the source, live at mplads-risk-monitor-web.vercel.app",
              12.5, True, BLUE_D, UI)])
    y += 0.70 + 0.24

    hs = [
        card(s[3], LEFT, y, cw3, "Feasibility",
             "The data is already public and machine-readable: four CSVs, refreshed "
             "nightly by a scheduled job that loads in 2 minutes and scores in about "
             "20. No ministry integration, no new reporting burden on any officer, "
             "no hardware. 85 automated tests run against the pipeline and the API.",
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
    stats = [("250,839", "works scored, both terms"),
             ("Rs 11,682 Cr", "allocated, 18th Lok Sabha"),
             ("48,542", "works above the threshold"),
             ("Rs 4,662 Cr", "sanction awaiting review"),
             ("912", "cohort findings")]
    sw = (CW - 4 * 0.14) / 5
    for i, (value, label) in enumerate(stats):
        chip(s[4], LEFT + i * (sw + 0.14), y, sw, label, value, BLUE_D, h=0.82)
    y += 0.82 + 0.24

    who = [("Member of Parliament",
            "Sees which of their own recommendations are stalling, and how much of the allocation is still idle."),
           ("District authority",
            "Gets a ranked shortlist instead of a register, with the evidence for each flag already assembled."),
           ("State nodal officer",
            "Ranks all 36 states and UTs on money committed against money paid, then drops "
            "straight into that state's queue."),
           ("Ministry (MoSPI)",
            "Sees national patterns and where scheme rules are breaking, without waiting for a manual audit.")]
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
    h_data = card(s[5], LEFT, y, cw2, "Data and scheme rules",
         "MPLADS programme data via Empowered Indian (empoweredindian.in), which "
         "aggregates the official MoSPI portal at mplads.mospi.gov.in — 250,839 works, "
         "272,263 payments, 1,547 MP-terms across 776 districts and 62,969 vendors.\n"
         "MPLADS Guidelines, Ministry of Statistics and Programme Implementation: "
         "permissible works, sanction ceilings and the annual entitlement per MP.\n"
         "Reconciled against the source's own published totals; 4,372 rows rejected "
         "and recorded rather than silently dropped.",
         BLUE, bs=11, min_h=3.85, tag="s6a")
    h_left = card(s[5], LEFT + cw2 + 0.20, y, cw2, "Methods",
         "Liu, Ting and Zhou (2008), Isolation Forest — multivariate outliers over "
         "amount, delay and spend.\n"
         "Reimers and Gurevych (2019), Sentence-BERT — all-MiniLM-L6-v2 embeddings, "
         "cosine 0.94 within a district and sector, for duplicate sanctions.\n"
         "Newcomb-Benford first-digit law, with Nigrini's MAD — used peer-relative, "
         "because the population itself does not conform.\n"
         "Herfindahl-Hirschman Index — vendor concentration per implementing agency.",
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
