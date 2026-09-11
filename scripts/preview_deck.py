#!/usr/bin/env python3
"""Render the built deck to PNGs so it can actually be looked at.

There is no LibreOffice on this machine and no sudo to install one, so this
reads the .pptx back with python-pptx and redraws each slide as absolutely
positioned HTML at the same inch coordinates, then screenshots it in the same
headless Chrome the diagram boards use.

It is an approximation, and the one place it differs matters: PowerPoint's text
layout is not Chrome's, so a text box that fits here could still wrap
differently there. It is exact for images and shape geometry, which is what
actually goes wrong - overlaps, overflow, and things landing on the footer bar.

    python3 scripts/preview_deck.py            # docs/deck/preview/slide-N.png
"""

import html
import shutil
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

REPO = Path(__file__).resolve().parent.parent
DECK = REPO / "docs/deck/SIH26102-MPLADS-SIH-Idea.pptx"
OUTDIR = REPO / "docs/deck/preview"
RENDER_DIR = REPO / "docs/deck/diagrams"          # has node_modules
PX = 96.0                                         # preview pixels per inch


def inches(v):
    return 0.0 if v is None else Emu(v).inches


def colour(fmt):
    try:
        if fmt.type is not None and fmt.fore_color.type is not None:
            return "#" + str(fmt.fore_color.rgb)
    except Exception:
        pass
    return None


def run_html(shape, imgdir, out):
    """Emit one shape as a positioned div, recursing into groups."""
    x, y = inches(shape.left) * PX, inches(shape.top) * PX
    w, h = inches(shape.width) * PX, inches(shape.height) * PX
    style = f"left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px"

    if shape.shape_type == 13:  # PICTURE
        img = shape.image
        name = f"img{len(list(imgdir.glob('img*')))}.{img.ext}"
        (imgdir / name).write_bytes(img.blob)
        out.append(f'<img class="s" style="{style}" src="imgs/{name}">')
        return

    fill = colour(shape.fill) if hasattr(shape, "fill") else None
    line = None
    if hasattr(shape, "line"):
        try:
            line = "#" + str(shape.line.color.rgb)
        except Exception:
            line = None
    box = style
    if fill:
        box += f";background:{fill}"
    if line:
        box += f";border:1.5px solid {line};border-radius:8px"

    inner = ""
    if shape.has_text_frame:
        for p in shape.text_frame.paragraphs:
            if not p.runs:
                continue
            align = {2: "center", 3: "right", 4: "justify"}.get(
                getattr(p.alignment, "value", None), "left")
            spans = []
            for r in p.runs:
                f = r.font
                sz = f.size.pt if f.size else 12
                col = "#000"
                try:
                    if f.color and f.color.type is not None:
                        col = "#" + str(f.color.rgb)
                except Exception:
                    pass
                weight = "700" if f.bold else "400"
                style_i = "italic" if f.italic else "normal"
                und = "underline" if r.hyperlink.address else "none"
                spans.append(
                    f'<span style="font-size:{sz}pt;color:{col};font-weight:{weight};'
                    f'font-style:{style_i};text-decoration:{und}">{html.escape(r.text)}</span>')
            inner += f'<div style="text-align:{align}">{"".join(spans)}</div>'
    out.append(f'<div class="s" style="{box}">{inner}</div>')


def main():
    if not DECK.exists():
        raise SystemExit(f"no deck at {DECK} - run build_sih_deck.py first")
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    imgdir = OUTDIR / "imgs"
    imgdir.mkdir(parents=True)

    prs = Presentation(str(DECK))
    sw, sh = inches(prs.slide_width) * PX, inches(prs.slide_height) * PX
    pages = []
    for i, slide in enumerate(prs.slides, 1):
        out = []
        for shape in slide.shapes:
            try:
                run_html(shape, imgdir, out)
            except Exception as e:            # a shape we cannot draw is not fatal
                out.append(f'<!-- {shape.name}: {e} -->')
        pages.append(
            f'<div class="slide" id="slide{i}" '
            f'style="width:{sw:.0f}px;height:{sh:.0f}px">{"".join(out)}</div>')

    (OUTDIR / "preview.html").write_text(
        "<!doctype html><meta charset=utf-8><style>"
        "body{margin:0;background:#555;font-family:Calibri,Carlito,sans-serif}"
        ".slide{position:relative;background:#fff;overflow:hidden;margin:24px}"
        ".s{position:absolute;box-sizing:border-box;overflow:hidden}"
        "img.s{object-fit:contain}"
        "</style>" + "".join(pages))

    subprocess.run(["node", "-e", f"""
      const {{ chromium }} = await import('playwright-core');
      const b = await chromium.launch({{ executablePath: process.env.DECK_CHROME ||
        `${{process.env.HOME}}/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`,
        args: ['--no-sandbox'] }});
      const p = await b.newPage({{ viewport: {{ width: 1400, height: 900 }}, deviceScaleFactor: 1.5 }});
      await p.goto('file://{OUTDIR}/preview.html');
      await p.waitForTimeout(700);
      for (let i = 1; i <= {len(pages)}; i++) {{
        const el = await p.$('#slide' + i);
        await el.screenshot({{ path: '{OUTDIR}/slide-' + i + '.png' }});
      }}
      await b.close();
    """], cwd=RENDER_DIR, check=True,
        env={"PATH": __import__("os").environ["PATH"],
             "HOME": str(Path.home()),
             "LD_LIBRARY_PATH": str(Path.home() /
                                    ".local/chromium-deps/root/usr/lib/x86_64-linux-gnu")})
    print(f"wrote {len(pages)} previews to {OUTDIR}")


if __name__ == "__main__":
    main()
