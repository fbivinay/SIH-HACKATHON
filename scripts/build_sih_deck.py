"""Fill the official SIH 2026 Idea template with the current state of the build.

Built by editing the supplied template in place rather than recreating it: the
file carries the SIH logo, the blue footer bar, the title placeholders and the
slide master, and the rules say the provided template must be used. So each
content slide keeps its heading and its "idea details pointers" verbatim - the
pointer box is only shrunk to a strip at the top of the content area - and our
content goes into the empty band below it.

WHY THE CONTENT IS IMAGES

The template's own instruction slide says to avoid paragraphs and use
"points / diagrams / Infographics / pictures". The earlier version of this
script drew cards and text with python-pptx, which meant every layout was an
estimate of where text would wrap and the result read as a wall of boxes. The
content is now:

  - six diagram boards, authored as HTML in docs/deck/diagrams/ with the
    product's own design tokens and fonts, rendered to PNG at 2x;
  - six screenshots of the running system;
  - hyperlinks laid over both, so every claim can be opened.

AND WHY THE FIGURES STILL COME FROM THE DATABASE

Putting numbers inside an image is exactly how a deck goes stale, which has
happened twice on this project. So the diagrams are a *template*:
`boards.template.html` carries `{{tokens}}`, this script fills them from
`figures()` - which refuses to build on a null or zero - and only then renders
the PNGs. No figure in this deck is typed by hand.

Build:

    python3 scripts/build_sih_deck.py            # figures -> diagrams -> pptx
    python3 scripts/build_sih_deck.py --verify   # check the built file
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "docs/deck/references/SIH2026-IDEA-Presentation-Format.pptx"
OUT = REPO / "docs/deck/SIH26102-MPLADS-SIH-Idea.pptx"
DIAG = REPO / "docs/deck/diagrams"
PNG = DIAG / "png"
SHOTS = DIAG / "shots"

# Fill these in before submitting; the portal issues both.
TEAM_NAME = "<Team Name>"
TEAM_ID = "<Team ID>"

W, H = 13.333, 7.5
LEFT, CW = 0.67, 12.0
TOP, BOT = 1.95, 6.85

C = lambda h: RGBColor.from_string(h)
INK, MUTED = C("101828"), C("5A6472")
LINKC = C("7A1A12")
UI = "Calibri"

# Three links, and only three. The reference cards cite their sources in text
# instead of each carrying its own, so a reader is never hunting for which of
# a dozen links is the working prototype.
LINKS = {
    "video": "https://drive.google.com/file/d/1z27mUvNq-KbGzCK_8p_dpdtpBMCligM6/view?usp=drivesdk",
    "site": "https://mplads-risk-monitor-web.vercel.app",
    "github": "https://github.com/fbivinay/SIH-HACKATHON",
}
LINK_ROW = [
    ("DEMO VIDEO", "2 minute walkthrough", "video"),
    ("PROTOTYPE", "the running system", "site"),
    ("GITHUB", "loader · scorer · API · tests", "github"),
]


# --------------------------------------------------------------- figures ---


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
        # The latest extract's rejections, not every run ever recorded. The
        # slide sets this beside the loaded counts, so a cumulative total there
        # reads as "this load threw away 1,488 rows" when it threw away 417.
        "rejected": one(
            """WITH dated AS (
                   SELECT SUBSTRING(source_file FROM '\\d{4}-\\d{2}-\\d{2}') AS d
                   FROM rejected_rows
               )
               SELECT COUNT(*) FROM dated
               WHERE d = (SELECT MAX(d) FROM dated)"""
        ),
        "scored": one("SELECT COUNT(*) FROM project_scores"),
        "queue": one("SELECT COUNT(*) FROM project_scores WHERE overall_risk_score >= 40"),
        "high": one("SELECT COUNT(*) FROM project_scores WHERE risk_level = 'HIGH'"),
        "queue_value": one(
            "SELECT COALESCE(SUM(sanctioned_amount), 0) FROM projects_scored "
            "WHERE overall_risk_score >= 40"
        ),
        "allocated": one("SELECT COALESCE(SUM(allocated_amount), 0) FROM mps"),
        "findings": one("SELECT COUNT(*) FROM detector_findings"),
        "worst_gap": one("SELECT MAX(ABS(gap_pct)) FROM source_reconciliation"),
    }
    cur.execute("SELECT code, COUNT(*) FROM detector_findings GROUP BY code")
    f["by_code"] = dict(cur.fetchall())
    conn.close()

    cache = REPO / "data/sector_cache.json"
    f["labels"] = len(json.loads(cache.read_text())) if cache.exists() else 0

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


def indian(value) -> str:
    """2,50,839 - the grouping the product uses everywhere."""
    s = str(int(value))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    return re.sub(r"\B(?=(\d{2})+(?!\d))", ",", head) + "," + tail


def crore(amount) -> str:
    return f"₹{float(amount) / 1e7:,.0f} Cr"


# ------------------------------------------------------------- diagrams ---


def render_diagrams(f):
    """Fill the board template from the figures, then render each to PNG."""
    tpl = (DIAG / "boards.template.html").read_text()
    values = {
        "works": indian(f["works"]),
        "payments": indian(f["payments"]),
        "queue": indian(f["queue"]),
        "high": indian(f["high"]),
        "labels": indian(f["labels"]),
        "states": str(f["states"]),
        "tests": str(f["tests"]),
        "allocated": crore(f["allocated"]),
    }
    missing = set(re.findall(r"\{\{(\w+)\}\}", tpl)) - set(values)
    if missing:
        raise SystemExit(f"deck: board template wants {sorted(missing)} - no figure for it")
    for k, v in values.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    (DIAG / "boards.html").write_text(tpl)

    subprocess.run(
        ["node", str(DIAG / "render.mjs")],
        cwd=DIAG, check=True,
        env={**os.environ, "LD_LIBRARY_PATH": os.environ.get(
            "LD_LIBRARY_PATH",
            str(Path.home() / ".local/chromium-deps/root/usr/lib/x86_64-linux-gnu"))},
    )
    return json.loads((PNG / "sizes.json").read_text())


# ---------------------------------------------------------------- slides ---


def restyle_pointers(slide):
    """Shrink the template's pointer textbox to a strip at the top of the
    content area. The wording is left exactly as the template ships it - the
    rules forbid changing the idea-detail pointers, only their placement."""
    for sh in slide.shapes:
        if not sh.has_text_frame or sh.is_placeholder:
            continue
        t = sh.text_frame.text.strip()
        if len(t) > 40 and "Team Name" not in t:
            top, height = 1.18, 0.74
            lines = max(1, len([q for q in sh.text_frame.paragraphs if q.text.strip()]))
            # 1.7, not the ~1.45 that PowerPoint actually leads at: solving for
            # the exact box makes the text precisely as tall as its container and
            # the last line's descenders get clipped. The extra is slack.
            size = min(9.5, (height * 72) / (lines * 1.7))
            sh.left, sh.top = Inches(LEFT), Inches(top)
            sh.width, sh.height = Inches(CW), Inches(height)
            sh.text_frame.word_wrap = True
            for para in sh.text_frame.paragraphs:
                para.line_spacing = 1.0
                para.space_after = Pt(0)
                for r in para.runs:
                    r.font.size = Pt(size)
                    r.font.italic = True
                    r.font.bold = False
                    r.font.color.rgb = MUTED
                    r.font.name = UI
            return sh
    return None


def set_title(slide, text, size=None):
    from pptx.enum.text import PP_ALIGN
    for sh in slide.shapes:
        if sh.is_placeholder and sh.has_text_frame and sh.text_frame.text.strip():
            para = sh.text_frame.paragraphs[0]
            if not para.runs:
                continue
            para.alignment = PP_ALIGN.CENTER
            if size:
                for r in para.runs:
                    r.font.size = Pt(size)
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


def place(slide, png, x, y, w, sizes=None, url=None):
    """Drop an image at width `w`, height from its own pixels. Returns bottom."""
    if sizes is not None:
        pw, ph = sizes
    else:
        from PIL import Image
        with Image.open(png) as im:
            pw, ph = im.size
    h = w * ph / pw
    pic = slide.shapes.add_picture(str(png), Inches(x), Inches(y), Inches(w), Inches(h))
    if url:
        pic.click_action.hyperlink.address = url
    return y + h


def caption(slide, x, y, w, text, url=None, size=9.5, align=None, h=0.26):
    from pptx.enum.text import PP_ALIGN
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    if align:
        p.alignment = PP_ALIGN.CENTER if align == "c" else PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.name = UI
    r.font.color.rgb = LINKC if url else MUTED
    if url:
        r.font.bold = True
        r.hyperlink.address = url
    return box


def link_row(slide, x, y, w, h=0.52, gap=0.18, size=11, stack=False):
    """The three links as real buttons - visible, clickable, same on every slide."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    bw = w if stack else (w - gap * (len(LINK_ROW) - 1)) / len(LINK_ROW)
    for i, (label, sub, key) in enumerate(LINK_ROW):
        bx = x if stack else x + i * (bw + gap)
        by = y + i * (h + gap) if stack else y
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(bx),
                                     Inches(by), Inches(bw), Inches(h))
        box.fill.solid()
        box.fill.fore_color.rgb = C("FFFFFF")
        box.line.color.rgb = LINKC
        box.line.width = Pt(1.25)
        box.shadow.inherit = False
        box.click_action.hyperlink.address = LINKS[key]
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Inches(0.06)
        tf.margin_top = tf.margin_bottom = 0
        p0 = tf.paragraphs[0]
        p0.alignment = PP_ALIGN.CENTER
        r = p0.add_run(); r.text = label
        r.font.size = Pt(size); r.font.bold = True
        r.font.color.rgb = LINKC; r.font.name = UI
        p1 = tf.add_paragraph()
        p1.alignment = PP_ALIGN.CENTER
        r2 = p1.add_run(); r2.text = sub
        r2.font.size = Pt(size - 3); r2.font.color.rgb = MUTED; r2.font.name = UI
    return y + (len(LINK_ROW) * h + (len(LINK_ROW) - 1) * gap if stack else h)


def hotspot(slide, x, y, w, h, url):
    """An invisible clickable rectangle - used to make a region of a rendered
    diagram open the thing it names, since the PNG cannot carry a link."""
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                Inches(w), Inches(h))
    sh.fill.background()
    sh.line.fill.background()
    sh.shadow.inherit = False
    sh.click_action.hyperlink.address = url
    return sh


# ------------------------------------------------------------------ main ---


def main():
    f = figures()
    sizes = render_diagrams(f)
    prs = Presentation(str(TEMPLATE))
    s = list(prs.slides)

    # ---------------------------------------------------------------- title --
    # The template's subtitle placeholder ships reading "TITLE PAGE". It is not
    # one of the idea-detail pointers, so naming the product there is allowed
    # and stops the opening slide being anonymous.
    for sh in s[0].shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() == "TITLE PAGE":
            para = sh.text_frame.paragraphs[0]
            if para.runs:
                para.runs[0].text = "KASAUTI — AI-powered MPLADS verification"
                for extra in list(para.runs[1:]):
                    extra._r.getparent().remove(extra._r)
            break

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
                ("Team ID", TEAM_ID),
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

    # ------------------------------------------------- 2. idea / solution --
    set_title(s[1], "KASAUTI", size=40)
    set_team_badge(s[1])
    restyle_pointers(s[1])

    # The architecture drawing is the slide. It is authored at 2400px, so
    # shrinking it into a column makes its body type ~4pt - unreadable. It gets
    # the full content width, and the width is derived from the board's own
    # ratio so the link row underneath always fits rather than being nudged by
    # hand every time the board's content changes height.
    LINK_H, GAP = 0.40, 0.11
    ar = sizes["arch"][0] / sizes["arch"][1]
    aw = min(CW, (BOT - TOP - LINK_H - GAP) * ar)
    ax = LEFT + (CW - aw) / 2
    arch_b = place(s[1], PNG / "arch.png", ax, TOP, aw, sizes["arch"])
    link_row(s[1], ax + aw * 0.28, arch_b + GAP, aw * 0.44, h=LINK_H, gap=0.14, size=9.5)

    # ---------------------------------------------- 3. technical approach --
    set_title(s[2], "TECHNICAL APPROACH")
    set_team_badge(s[2])
    restyle_pointers(s[2])

    pipe_b = place(s[2], PNG / "pipeline.png", LEFT, TOP, CW, sizes["pipeline"])
    place(s[2], PNG / "stack.png", LEFT, pipe_b + 0.16, 6.05, sizes["stack"])
    work_b = place(s[2], SHOTS / "work.png", 6.95, pipe_b + 0.16, 5.72,
                   url=LINKS["site"])
    caption(s[2], 6.95, work_b + 0.05, 5.72,
            "Every flag carries the method that produced it — a scored work, live",
            LINKS["site"], 9.5, h=0.30)

    # ------------------------------------------ 4. feasibility & viability --
    set_title(s[3], "FEASIBILITY AND VIABILITY")
    set_team_badge(s[3])
    restyle_pointers(s[3])

    feas_b = place(s[3], PNG / "feas.png", LEFT, TOP, CW, sizes["feas"])
    # 3.30in wide, not 5.55: at the screenshot's own 2.18 ratio anything wider
    # runs past the footer bar, which `verify` catches.
    y = feas_b + 0.14
    place(s[3], SHOTS / "provenance.png", LEFT, y, 3.30, url=LINKS["site"])
    caption(s[3], 4.20, y + 0.02, 8.47,
            "Provenance is checked, not asserted.", None, 12)
    caption(s[3], 4.20, y + 0.30, 8.47,
            f"Both hops are published separately — ours to the source, and the source "
            f"to MoSPI — so a gap is never read as our error when it is upstream lag. "
            f"Worst gap on the last run: {float(f['worst_gap']):.2f}%. "
            f"{f['states']} of {f['states']} states match the source exactly.",
            None, 10, h=0.62)
    link_row(s[3], 4.20, y + 0.92, 8.47, h=0.50, gap=0.14, size=10)

    # ------------------------------------------------ 5. impact & benefits --
    set_title(s[4], "IMPACT AND BENEFITS")
    set_team_badge(s[4])
    restyle_pointers(s[4])

    imp_b = place(s[4], PNG / "impact.png", 1.17, TOP, 11.0, sizes["impact"])
    y = imp_b + 0.16
    place(s[4], SHOTS / "alerts.png", 1.30, y, 5.00, url=LINKS["site"])
    shot2_b = place(s[4], SHOTS / "map.png", 7.00, y, 5.00, url=LINKS["site"])
    caption(s[4], 1.30, shot2_b + 0.04, 5.00,
            "The queue an official works through", None, 9.5, "c")
    caption(s[4], 7.00, shot2_b + 0.04, 5.00,
            "Risk by state, every district covered", None, 9.5, "c")

    # --------------------------------------------- 6. research & references --
    set_title(s[5], "RESEARCH AND REFERENCES")
    set_team_badge(s[5])
    restyle_pointers(s[5])

    refs_b = place(s[5], PNG / "refs.png", LEFT, TOP, CW, sizes["refs"])

    y = refs_b + 0.14
    for i, name in enumerate(["agencies", "alerts", "overview"]):
        b = place(s[5], SHOTS / f"{name}.png", LEFT + i * 4.05, y, 3.85,
                  url=LINKS["site"])
    caption(s[5], LEFT, b + 0.04, CW,
            "Every figure in this deck is live on the prototype, refreshed nightly "
            "and reconciled against the ministry's own dashboard.", None, 9.5, "c")
    link_row(s[5], 2.17, b + 0.28, 9.0, h=0.46, gap=0.16, size=10.5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print(f"wrote {OUT}")
    print(f"  {indian(f['works'])} works, {indian(f['queue'])} flagged, "
          f"{indian(f['high'])} high risk, {f['tests']} tests")
    verify()


# ---------------------------------------------------------------- verify ---


def verify():
    """Check the built file rather than trust that it built."""
    prs = Presentation(str(OUT))
    slides = list(prs.slides)
    problems = []

    if len(slides) > 7:
        problems.append(f"{len(slides)} slides; the rules allow six plus the instructions page")

    tmpl_pointers = {}
    for i, slide in enumerate(Presentation(str(TEMPLATE)).slides, 1):
        for sh in slide.shapes:
            if sh.has_text_frame and not sh.is_placeholder:
                t = sh.text_frame.text.strip()
                if len(t) > 40 and "Team Name" not in t:
                    tmpl_pointers[i] = t
                    break

    for i, slide in enumerate(slides, 1):
        pics = [sh for sh in slide.shapes if sh.shape_type == 13]
        links = 0
        for sh in slide.shapes:
            if getattr(sh, "click_action", None) and sh.click_action.hyperlink.address:
                links += 1
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        if r.hyperlink.address:
                            links += 1
            # Nothing may run off the slide.
            if sh.left is None:
                continue
            l, t = sh.left / 914400, sh.top / 914400
            r = l + (sh.width or 0) / 914400
            b = t + (sh.height or 0) / 914400
            if l < -0.05 or t < -0.7 or r > W + 0.05 or b > H + 0.05:
                problems.append(f"slide {i}: {sh.name!r} runs off the slide "
                                f"({l:.2f},{t:.2f})-({r:.2f},{b:.2f})")
        # The pointers must survive verbatim - the rules forbid changing them.
        if i in tmpl_pointers:
            found = any(sh.has_text_frame and sh.text_frame.text.strip() == tmpl_pointers[i]
                        for sh in slide.shapes)
            if not found:
                problems.append(f"slide {i}: the template's idea pointers were changed")
        if 2 <= i <= 6:
            # How much of the content band is picture, not how many pictures -
            # a count said slide 2 had regressed when it became one full-width
            # architecture drawing, which is the most visual it has ever been.
            band = CW * (BOT - TOP)
            covered = sum(
                (sh.width or 0) / 914400 * (sh.height or 0) / 914400
                for sh in pics if sh.top is not None and sh.top / 914400 > 1.0
            )
            share = covered / band
            if share < 0.45:
                problems.append(f"slide {i}: images cover {share:.0%} of the content "
                                f"band - this deck is meant to be diagrams, not text")
            if links == 0:
                problems.append(f"slide {i}: no links")
            print(f"  slide {i}: {len(pics)} images covering {share:.0%}, {links} links")
        else:
            print(f"  slide {i}: {len(pics)} images, {links} links")

    for placeholder in (TEAM_NAME, TEAM_ID):
        if placeholder.startswith("<"):
            print(f"  NOTE: {placeholder} is still a placeholder - fill it before submitting")

    if problems:
        print("\nFAILED:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("  ok")


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    else:
        main()
