#!/usr/bin/env python3
"""Emit the explainer composition, timed to the narration that was actually generated.

Twelve scenes, each held exactly as long as its voice-over line plus a gap.
Those lengths are measured from the rendered mp3s rather than estimated from
word counts - the first script was written against 142 wpm from a single short
line, and the real rate over number-heavy copy came out at ~145, which is the
difference between 2:00 and 2:45.

Re-run after regenerating any narration segment:

    python3 video-explainer/build.py
"""

import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent
OUT = HERE / "composition" / "index.html"


def measure(path):
    """Seconds of audio in `path`, per ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


# Measured from the source WAVs, not the mp3s the page loads. An mp3 container
# reports encoder delay and padding in its duration - 11.544s where the audio
# is 11.48s - and the browser reports the decoded length, so timing a clip off
# the container makes every slot ~0.06s too long and `check` flags all twelve.
DUR = [[f.stem, measure(f)] for f in sorted((HERE / "vo").glob("*.wav"))]
if not DUR:
    raise SystemExit("no narration in video-explainer/vo - generate it first")

# Silence between one line ending and the next beginning. Long enough that the
# scenes do not feel spliced, short enough that it never reads as a stall.
GAP = 0.45
# The last scene holds on the wordmark after the narration stops.
TAIL = 1.6


def layout():
    """Scene start/duration from the measured voice-over lengths."""
    scenes, t = [], 0.0
    for i, (name, d) in enumerate(DUR):
        last = i == len(DUR) - 1
        span = d + (TAIL if last else GAP)
        scenes.append({"key": name.split("-", 1)[1], "start": round(t, 3),
                       "dur": round(span, 3), "vo": name, "voDur": d})
        t += span
    return scenes, round(t, 3)


SCENES, TOTAL = layout()
S = {s["key"]: s for s in SCENES}


def at(key, offset):
    """An absolute timeline position, `offset` seconds into a scene."""
    return round(S[key]["start"] + offset, 3)


# A fixed lattice for the isolation-forest scatter. Generated here, at build
# time, rather than in the page: a render must be deterministic, and an
# unseeded Math.random in the composition would give a different picture on
# every frame.
def scatter():
    """A dense population and the few points sitting outside it.

    The first version scattered everything uniformly and tagged whatever
    landed near the edge - which drew no cluster at all, so the picture did
    not say "these few are unlike the rest". This draws the population as an
    actual cluster: radius biased hard toward the centre, then a handful of
    points placed well outside it.
    """
    import math
    seed = 7

    def rnd():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) % (1 << 31)
        return (seed >> 7) / (1 << 24)

    inliers = []
    while len(inliers) < 105:
        # r**1.7 pulls most points in toward the middle, so the cloud has a
        # dense core and thins out - what a real peer group looks like.
        r = rnd() ** 1.7 * 0.60
        a = rnd() * 2 * math.pi
        x, y = 50 + math.cos(a) * r * 96, 50 + math.sin(a) * r * 92
        inliers.append((round(x, 2), round(y, 2), False))

    # Placed, not sampled: the whole point of the panel is that these sit
    # clearly apart, and leaving that to a PRNG risks one landing in the cloud.
    outliers = [(8, 16), (91, 22), (13, 84), (88, 79), (50, 6), (95, 50), (6, 55)]
    return inliers, [(x, y, True) for x, y in outliers]


INLIERS, OUTLIERS = scatter()

dots = "\n".join(
    f'            <span class="pt" style="left:{x}%;top:{y}%"></span>'
    for x, y, _ in INLIERS
)
odots = "\n".join(
    f'            <span class="pt is-out" style="left:{x}%;top:{y}%"></span>'
    for x, y, _ in OUTLIERS
)

COMPONENTS = [("Cost", "25%", 1.0), ("Delay", "25%", 1.0), ("Duplication", "20%", 0.8),
              ("Agency", "15%", 0.6), ("Compliance", "15%", 0.6)]
comp_rows = "\n".join(
    f'''            <div class="row" id="sc-r{i}">
              <div class="row-name">{n}</div>
              <div class="row-weight">{w}</div>
              <div class="bar-track"><div class="bar-fill" data-w="{s}"></div></div>
            </div>''' for i, (n, w, s) in enumerate(COMPONENTS, 1)
)

DETECTORS = [
    ("D-01", "Year-end payment burst", "An agency paying most of its invoices in March"),
    ("D-02", "First-digit anomaly", "Leading digits that diverge from the agency's peers"),
    ("D-03", "Idle allocation", "A member's funds never committed to any work"),
    ("D-04", "Uniform sanction amount", "The same round figure, again and again"),
]
det_cards = "\n".join(
    f'''            <div class="dcard" id="dc-{i}">
              <div class="dcode">{c}</div>
              <div class="dname">{n}</div>
              <div class="ddesc">{d}</div>
            </div>''' for i, (c, n, d) in enumerate(DETECTORS, 1)
)

STEPS = [("Load", "250,839 works"), ("Label", "new sectors"),
         ("Score", "five components"), ("Reconcile", "against MoSPI")]
step_els = "\n".join(
    f'''            <div class="step" id="st-{i}">
              <div class="step-n">{i}</div>
              <div class="step-name">{n}</div>
              <div class="step-sub">{d}</div>
            </div>''' for i, (n, d) in enumerate(STEPS, 1)
)

NOT_PUBLISHED = ["Progress percentage", "Beneficiary count", "Geo-tag", "Bill value"]
np_items = "\n".join(
    f'            <div class="np" id="np-{i}"><span class="np-x">not published</span>{t}</div>'
    for i, t in enumerate(NOT_PUBLISHED, 1)
)

vo_audio = "\n".join(
    f'      <audio id="vo-{s["key"]}" src="assets/vo/{s["vo"]}.mp3" '
    f'data-start="{s["start"]}" data-duration="{s["voDur"]}" data-volume="1"></audio>'
    for s in SCENES
)

scene_open = {}
for s in SCENES:
    scene_open[s["key"]] = (
        f'<section id="s-{s["key"]}" class="clip {{tone}}" '
        f'data-start="{s["start"]}" data-duration="{s["dur"]}">'
    )


HTML = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Kasauti — how it works</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      /* GENERATED FILE - edit video-explainer/build.py, not this.
         Scene timings come from the measured narration in vo/durations.json. */
      @font-face {{
        font-family: "Geist";
        src: url("assets/fonts/geist.woff2") format("woff2");
        font-weight: 100 900; font-style: normal; font-display: block;
      }}
      @font-face {{
        font-family: "Geist Mono";
        src: url("assets/fonts/geist-mono.woff2") format("woff2");
        font-weight: 400; font-style: normal; font-display: block;
      }}

      /* The product's tokens. Colour only ever means risk - the one exception
         is the two words "AI powered", exactly as on the site. */
      :root {{
        --slab: #0b0b0c; --slab-2: #17171a;
        --ground: #f1f1f2; --surface: #ffffff;
        --on-slab: #fafafa; --on-slab-2: #b6b6bf; --on-slab-3: #8e8e99;
        --ink: #0b0b0c; --ink-2: #4a4a52; --ink-3: #6b6b74;
        --risk-high: #a82e22; --risk-medium: #96600a; --risk-low: #16704a;
        --risk-high-dark: #f2695c;
        --ai-red: #7a1a12; --ai-red-dark: #e0685c;
        --line: #e3e3e6; --line-strong: #d2d2d7;
        --ui: "Geist", ui-sans-serif, system-ui, sans-serif;
        --mono: "Geist Mono", ui-monospace, SFMono-Regular, monospace;
      }}
      body {{ margin: 0; background: #000; font-family: var(--ui);
             -webkit-font-smoothing: antialiased; }}
      #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; display: grid; place-items: center; }}
      .dark {{ background: var(--slab); color: var(--on-slab); }}
      .light {{ background: var(--ground); color: var(--ink); }}
      .stack {{ display: flex; flex-direction: column; align-items: center; }}
      .wrap {{ width: 1500px; }}

      .eyebrow {{ font-family: var(--mono); font-size: 21px; font-weight: 500;
                  letter-spacing: 0.24em; text-transform: uppercase; }}
      .dark .eyebrow {{ color: var(--on-slab-3); }}
      .light .eyebrow {{ color: var(--ink-3); }}
      .figure {{ font-family: var(--mono); font-variant-numeric: tabular-nums;
                 font-weight: 500; letter-spacing: -0.02em; line-height: 1; }}
      .display {{ font-weight: 650; letter-spacing: -0.035em; line-height: 1.06; margin: 0; }}
      .say {{ font-size: 40px; font-weight: 450; letter-spacing: -0.02em; }}
      .dark .say {{ color: var(--on-slab-2); }}
      .light .say {{ color: var(--ink-2); }}

      /* 1 problem */
      #pb-count {{ font-size: 220px; }}
      #pb-money {{ margin-top: 30px; font-size: 58px; color: var(--on-slab-2); }}
      #pb-line {{ margin-top: 56px; font-size: 50px; font-weight: 500;
                  letter-spacing: -0.02em; color: var(--on-slab); }}

      /* 2 what */
      #wh-head {{ margin-top: 36px; font-size: 88px; max-width: 1400px; text-align: center; }}
      #wh-sub {{ margin-top: 34px; font-size: 38px; color: var(--ink-2); }}
      .ai-eyebrow {{ display: flex; align-items: center; gap: 0.55em;
                     font-family: var(--mono); font-size: 20px; font-weight: 600;
                     letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-3); }}
      .ai-dot {{ width: 11px; height: 11px; border-radius: 50%; background: var(--risk-low); }}
      .ai-word {{ color: var(--ai-red); }}
      .dark .ai-word {{ color: var(--ai-red-dark); }}

      /* 3 provenance */
      #pv-chain {{ display: flex; align-items: stretch; gap: 0; margin-top: 56px; }}
      .node {{ width: 400px; padding: 34px 30px; border-radius: 20px;
               background: var(--slab-2); border: 1px solid rgba(255,255,255,0.11); }}
      .node-k {{ font-family: var(--mono); font-size: 18px; letter-spacing: 0.18em;
                 text-transform: uppercase; color: var(--on-slab-3); }}
      .node-n {{ margin-top: 14px; font-size: 34px; font-weight: 550;
                 letter-spacing: -0.02em; color: var(--on-slab); }}
      .node-d {{ margin-top: 12px; font-size: 22px; color: var(--on-slab-2); line-height: 1.4; }}
      .arrow {{ width: 100px; display: grid; place-items: center;
                font-family: var(--mono); font-size: 30px; color: var(--on-slab-3); }}
      #pv-note {{ margin-top: 46px; font-size: 30px; color: var(--on-slab-2); }}

      /* 4 score */
      .row {{ display: grid; grid-template-columns: 1fr auto; align-items: baseline;
              row-gap: 12px; margin-bottom: 22px; }}
      .row-name {{ font-size: 36px; font-weight: 500; letter-spacing: -0.02em; }}
      .row-weight {{ font-family: var(--mono); font-variant-numeric: tabular-nums;
                     font-size: 27px; color: var(--ink-3); }}
      .bar-track {{ grid-column: 1 / -1; height: 6px; border-radius: 999px;
                    background: var(--line-strong); overflow: hidden; }}
      .bar-fill {{ height: 100%; border-radius: 999px; background: var(--ink-2);
                   transform-origin: left center; }}
      #sc-bands {{ display: flex; gap: 18px; margin-top: 44px; }}
      .band {{ flex: 1; padding: 20px 24px; border-radius: 14px; background: var(--surface);
               border: 1px solid var(--line); }}
      .band-n {{ font-family: var(--mono); font-size: 19px; letter-spacing: 0.16em;
                 text-transform: uppercase; }}
      .band-r {{ margin-top: 8px; font-family: var(--mono); font-size: 30px;
                 font-variant-numeric: tabular-nums; color: var(--ink); }}

      /* 5 forest */
      #fo-plot {{ position: relative; width: 900px; height: 560px; margin-top: 40px;
                  border: 1px solid rgba(255,255,255,0.14); border-radius: 18px;
                  background: var(--slab-2); }}
      .pt {{ position: absolute; width: 9px; height: 9px; border-radius: 50%;
             background: var(--on-slab-3); margin: -4.5px 0 0 -4.5px; }}
      .pt.is-out {{ width: 15px; height: 15px; margin: -7.5px 0 0 -7.5px;
                    background: var(--risk-high); }}
      #fo-side {{ width: 470px; }}

      /* 6 bert */
      .desc {{ width: 620px; padding: 30px 32px; border-radius: 18px; background: var(--slab-2);
               border: 1px solid rgba(255,255,255,0.11); font-size: 28px; line-height: 1.45;
               color: var(--on-slab); }}
      #bt-mid {{ width: 220px; display: grid; place-items: center; }}
      /* The dark-mode risk red. The light-ground #a82e22 measures 2.88:1 on
         the slab, under the 3:1 large-text floor. */
      #bt-score {{ font-family: var(--mono); font-size: 66px; color: var(--risk-high-dark);
                   font-variant-numeric: tabular-nums; }}

      /* 7 gemini */
      .lab {{ display: grid; grid-template-columns: 1fr 120px 380px; align-items: center;
              gap: 24px; padding: 22px 0; border-bottom: 1px solid rgba(255,255,255,0.10); }}
      .lab-src {{ font-size: 30px; color: var(--on-slab); }}
      .lab-ar {{ font-family: var(--mono); font-size: 24px; color: var(--on-slab-3);
                 text-align: center; }}
      .lab-out {{ font-family: var(--mono); font-size: 24px; letter-spacing: 0.06em;
                  text-transform: uppercase; color: var(--on-slab-2);
                  border: 1px solid rgba(255,255,255,0.16); border-radius: 999px;
                  padding: 8px 18px; text-align: center; }}
      .lab-out.is-abstain {{ color: var(--on-slab-3); }}

      /* 8 detectors */
      #dt-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 22px;
                  margin-top: 46px; }}
      .dcard {{ padding: 30px 32px; border-radius: 18px; background: var(--surface);
                border: 1px solid var(--line); }}
      .dcode {{ font-family: var(--mono); font-size: 20px; letter-spacing: 0.16em;
                color: var(--ink-3); }}
      .dname {{ margin-top: 12px; font-size: 32px; font-weight: 550; letter-spacing: -0.02em; }}
      .ddesc {{ margin-top: 10px; font-size: 23px; color: var(--ink-2); line-height: 1.4; }}

      /* 9 queue */
      #qu-wrap {{ display: flex; margin-top: 64px; }}
      .fcol {{ width: 500px; display: flex; flex-direction: column; align-items: center; }}
      .ffig {{ font-size: 104px; }}
      .ffig.is-risk {{ color: var(--risk-high); }}
      .flab {{ margin-top: 22px; font-family: var(--mono); font-size: 20px;
               letter-spacing: 0.2em; text-transform: uppercase; color: var(--ink-3); }}

      /* 10 why */
      #wy-badge {{ display: inline-flex; align-items: center; gap: 0.5em;
                   padding: 0.4em 1em; border: 1px solid rgba(255,255,255,0.14);
                   border-radius: 999px; background: rgba(255,255,255,0.05);
                   font-family: var(--mono); font-size: 21px; font-weight: 550;
                   letter-spacing: 0.08em; text-transform: uppercase; color: var(--on-slab-2); }}
      #wy-head {{ margin-top: 30px; font-size: 62px; }}
      .reason {{ padding: 20px 0 20px 32px; border-left: 2px solid rgba(255,255,255,0.16);
                 margin-bottom: 22px; }}
      .reason-text {{ font-size: 34px; font-weight: 450; letter-spacing: -0.015em; }}
      .reason-method {{ margin-top: 10px; font-family: var(--mono); font-size: 19px;
                        letter-spacing: 0.14em; text-transform: uppercase;
                        color: var(--on-slab-3); }}

      /* 11 refresh */
      #rf-steps {{ display: flex; gap: 20px; margin-top: 50px; }}
      .step {{ flex: 1; padding: 30px 26px; border-radius: 18px; background: var(--surface);
               border: 1px solid var(--line); }}
      .step-n {{ font-family: var(--mono); font-size: 20px; color: var(--ink-3); }}
      .step-name {{ margin-top: 14px; font-size: 34px; font-weight: 600;
                    letter-spacing: -0.025em; }}
      .step-sub {{ margin-top: 8px; font-family: var(--mono); font-size: 20px;
                   color: var(--ink-3); }}
      #rf-note {{ margin-top: 44px; font-size: 30px; color: var(--ink-2); }}

      /* 12 limits */
      .np {{ display: flex; align-items: center; gap: 24px; font-size: 38px;
             color: var(--on-slab); padding: 18px 0; }}
      .np-x {{ font-family: var(--mono); font-size: 18px; letter-spacing: 0.16em;
               text-transform: uppercase; color: var(--on-slab-3);
               border: 1px solid rgba(255,255,255,0.18); border-radius: 999px;
               padding: 7px 16px; }}
      #lm-l1 {{ margin-top: 60px; font-size: 52px; font-weight: 500;
                letter-spacing: -0.025em; color: var(--on-slab-2); }}
      #lm-l2 {{ margin-top: 20px; font-size: 66px; font-weight: 650;
                letter-spacing: -0.03em; color: var(--on-slab); }}
      #lm-mark {{ margin-top: 70px; display: flex; align-items: center; gap: 24px; }}
      #lm-logo {{ width: 74px; height: 74px; border-radius: 20px; background: var(--on-slab);
                  position: relative; overflow: hidden; }}
      .slash {{ position: absolute; width: 12px; height: 98px; background: var(--slab);
                top: -12px; transform: rotate(26deg); }}
      .slash.a {{ left: 20px; }} .slash.b {{ left: 43px; }}
      #lm-name {{ font-size: 66px; font-weight: 650; letter-spacing: -0.035em; }}
      #lm-sub {{ margin-top: 26px; font-family: var(--mono); font-size: 20px;
                 letter-spacing: 0.2em; color: var(--on-slab-3); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-width="1920" data-height="1080" data-duration="{TOTAL}" data-fps="30">

      <!-- 1 -->
      {scene_open['problem'].format(tone='dark')}
        <div class="stack">
          <div class="eyebrow">MPLADS works published</div>
          <div id="pb-count" class="figure" style="margin-top:36px">0</div>
          <div id="pb-money" class="figure">&#8377;19,804 Cr allocated</div>
          <div id="pb-line">Nobody has read them all.</div>
        </div>
      </section>

      <!-- 2 -->
      {scene_open['what'].format(tone='light')}
        <div class="stack">
          <div id="wh-eyebrow" class="ai-eyebrow">
            <span class="ai-dot"></span><span class="ai-word">AI powered</span>
            <span>&middot; Gemini Flash Lite &middot; Isolation Forest &middot; Sentence-BERT</span>
          </div>
          <h1 id="wh-head" class="display">Every MPLADS work, checked against its peers.</h1>
          <div id="wh-sub">A touchstone, not a verdict.</div>
        </div>
      </section>

      <!-- 3 -->
      {scene_open['provenance'].format(tone='dark')}
        <div class="wrap">
          <div id="pv-title" class="eyebrow">Where the data comes from</div>
          <div id="pv-chain">
            <div class="node" id="pv-n1">
              <div class="node-k">Designated source</div>
              <div class="node-n">MoSPI portal</div>
              <div class="node-d">Totals and members open. Individual works only behind an OTP-gated form.</div>
            </div>
            <div class="arrow" id="pv-a1">&rarr;</div>
            <div class="node" id="pv-n2">
              <div class="node-k">Bulk export</div>
              <div class="node-n">Empowered Indian</div>
              <div class="node-d">The same record, published as CSV the official site does not offer.</div>
            </div>
            <div class="arrow" id="pv-a2">&rarr;</div>
            <div class="node" id="pv-n3">
              <div class="node-k">This system</div>
              <div class="node-n">Kasauti</div>
              <div class="node-d">Reconciled against MoSPI's own endpoints on every refresh.</div>
            </div>
          </div>
          <div id="pv-note">Both hops are shown on the site &mdash; ours, and upstream lag.</div>
        </div>
      </section>

      <!-- 4 -->
      {scene_open['score'].format(tone='light')}
        <div class="wrap">
          <div id="sc-title" class="eyebrow">What the score is made of</div>
          <div style="margin-top:44px">
{comp_rows}
          </div>
          <div id="sc-bands">
            <div class="band" id="bd-1"><div class="band-n" style="color:var(--risk-low)">Low</div><div class="band-r">0 &ndash; 39</div></div>
            <div class="band" id="bd-2"><div class="band-n" style="color:var(--risk-medium)">Medium</div><div class="band-r">40 &ndash; 69</div></div>
            <div class="band" id="bd-3"><div class="band-n" style="color:var(--risk-high)">High</div><div class="band-r">70 &ndash; 100</div></div>
          </div>
        </div>
      </section>

      <!-- 5 -->
      {scene_open['forest'].format(tone='dark')}
        <div style="display:flex;align-items:center;gap:80px">
          <div id="fo-plot" data-layout-allow-overflow="true">
{dots}
{odots}
          </div>
          <div id="fo-side">
            <div class="eyebrow">Model 1 &middot; scikit-learn</div>
            <div id="fo-name" class="display" style="margin-top:22px;font-size:58px">Isolation Forest</div>
            <div id="fo-desc" class="say" style="margin-top:26px;font-size:32px">Learns what a normal sanction looks like for a sector and district, and isolates the works that sit outside it.</div>
          </div>
        </div>
      </section>

      <!-- 6 -->
      {scene_open['bert'].format(tone='dark')}
        <div class="stack">
          <div id="bt-title" class="eyebrow">Model 2 &middot; sentence-transformers</div>
          <div id="bt-name" class="display" style="margin-top:20px;font-size:58px">Sentence-BERT</div>
          <div style="display:flex;align-items:center;margin-top:46px">
            <div class="desc" id="bt-a">Construction of CC road from main road to school in ward 4</div>
            <div id="bt-mid">
              <div>
                <div id="bt-score" class="figure">0.94</div>
                <div class="eyebrow" style="text-align:center;margin-top:10px">cosine</div>
              </div>
            </div>
            <div class="desc" id="bt-b">Construction of C.C. road from main road to school, ward no. 4</div>
          </div>
          <div id="bt-note" class="say" style="margin-top:40px;font-size:30px">Threshold measured on this data &mdash; the foot of the genuine near-duplicate tail.</div>
        </div>
      </section>

      <!-- 7 -->
      {scene_open['gemini'].format(tone='dark')}
        <div class="wrap">
          <div id="gm-title" class="eyebrow">Model 3 &middot; <span class="ai-word">AI powered</span> &middot; gemini-flash-lite</div>
          <div id="gm-name" class="display" style="margin-top:20px;font-size:56px">It labels. It never judges.</div>
          <div style="margin-top:40px">
            <div class="lab" id="gl-1">
              <div class="lab-src">Muktidham Nirman</div>
              <div class="lab-ar">&rarr;</div>
              <div class="lab-out">Religious &amp; Cultural</div>
            </div>
            <div class="lab" id="gl-2">
              <div class="lab-src">Nala nirman ward 12</div>
              <div class="lab-ar">&rarr;</div>
              <div class="lab-out">Drainage</div>
            </div>
            <div class="lab" id="gl-3">
              <div class="lab-src">Vividh karya</div>
              <div class="lab-ar">&rarr;</div>
              <div class="lab-out is-abstain">Other</div>
            </div>
          </div>
          <div id="gm-note" class="say" style="margin-top:34px;font-size:29px">Chosen because it can abstain. No model output ever becomes a risk number.</div>
        </div>
      </section>

      <!-- 8 -->
      {scene_open['detectors'].format(tone='light')}
        <div class="wrap">
          <div id="dt-title" class="eyebrow">Cohort detectors &mdash; about agencies and members, never a single work</div>
          <div id="dt-grid">
{det_cards}
          </div>
        </div>
      </section>

      <!-- 9 -->
      {scene_open['queue'].format(tone='light')}
        <div class="stack">
          <div id="qu-title" class="eyebrow">What reaches a desk</div>
          <div id="qu-wrap">
            <div class="fcol" id="qc-1"><div class="ffig figure">2,50,839</div><div class="flab">Works scored</div></div>
            <div class="fcol" id="qc-2"><div class="ffig figure">48,296</div><div class="flab">Worth a look</div></div>
            <div class="fcol" id="qc-3"><div class="ffig figure is-risk">2,316</div><div class="flab">High risk</div></div>
          </div>
          <div id="qu-note" class="say" style="margin-top:56px">A morning&rsquo;s work, instead of a year&rsquo;s.</div>
        </div>
      </section>

      <!-- 10 -->
      {scene_open['why'].format(tone='dark')}
        <div style="width:1280px">
          <div><span id="wy-badge"><span class="ai-dot"></span><span class="ai-word">AI powered</span><span>&middot; gemini-flash-lite</span></span></div>
          <h2 id="wy-head" class="display">Why was this flagged?</h2>
          <div style="margin-top:44px">
            <div class="reason" id="wr-1">
              <div class="reason-text">298% above the median for this sector and district</div>
              <div class="reason-method">Peer comparison</div>
            </div>
            <div class="reason" id="wr-2">
              <div class="reason-text">100% similarity with another nearby work</div>
              <div class="reason-method">AI &middot; Sentence-BERT embeddings</div>
            </div>
            <div class="reason" id="wr-3">
              <div class="reason-text">191 days beyond expected completion</div>
              <div class="reason-method">Published dates</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 11 -->
      {scene_open['refresh'].format(tone='light')}
        <div class="wrap">
          <div id="rf-title" class="eyebrow">Every night, 01:00 IST</div>
          <div id="rf-steps">
{step_els}
          </div>
          <div id="rf-note">Scores are swapped in one transaction, so a reader never sees a half-empty table.</div>
        </div>
      </section>

      <!-- 12 -->
      {scene_open['limits'].format(tone='dark')}
        <div class="stack">
          <div id="lm-title" class="eyebrow">What it will not tell you</div>
          <div style="margin-top:34px">
{np_items}
          </div>
          <div id="lm-l1">A kasauti says which pieces are worth assaying.</div>
          <div id="lm-l2">Never which are false.</div>
          <div id="lm-mark">
            <div id="lm-logo" data-layout-allow-overflow="true">
              <span class="slash a"></span><span class="slash b"></span>
            </div>
            <div id="lm-name">Kasauti</div>
          </div>
          <div id="lm-sub">SIH26102 &middot; MoSPI</div>
        </div>
      </section>

      <!-- narration, one file per scene -->
{vo_audio}
      <audio id="bed" src="assets/music/bed.mp3" data-start="0" data-duration="{TOTAL}" data-volume="0.1"></audio>
    </div>

    <script>
      function formatIN(n) {{
        const s = Math.round(n).toString();
        if (s.length <= 3) return s;
        const last3 = s.slice(-3), rest = s.slice(0, -3);
        return rest.replace(/\\B(?=(\\d{{2}})+(?!\\d))/g, ",") + "," + last3;
      }}

      function build() {{
        const tl = gsap.timeline({{ paused: true }});
        // Entrances are always `from`, never a CSS transform plus a tween on
        // the same property - that pairing is a lint error and the two start
        // values fight.
        const rise = (t, at, o) => tl.from(t, Object.assign(
          {{ y: 30, opacity: 0, duration: 0.55, ease: "power3.out" }}, o || {{}}), at);
        const seq = (sel, at, step, o) =>
          gsap.utils.toArray(sel).forEach((el, i) => rise(el, at + i * step, o));

        // 1 problem
        rise("#s-problem .eyebrow", {at('problem', 0.1)}, {{ y: 16 }});
        const c = {{ v: 0 }}, cEl = document.getElementById("pb-count");
        tl.to(c, {{ v: 250839, duration: 2.1, ease: "power2.out",
          onUpdate: () => {{ cEl.textContent = formatIN(c.v); }} }}, {at('problem', 0.35)});
        tl.from("#pb-count", {{ opacity: 0, duration: 0.4 }}, {at('problem', 0.35)});
        rise("#pb-money", {at('problem', 3.1)}, {{ y: 20 }});
        rise("#pb-line", {at('problem', 5.6)}, {{ y: 22, duration: 0.7 }});

        // 2 what
        rise("#wh-eyebrow", {at('what', 0.2)}, {{ y: 16 }});
        rise("#wh-head", {at('what', 0.7)}, {{ y: 38, duration: 0.75 }});
        rise("#wh-sub", {at('what', 3.4)}, {{ y: 20 }});

        // 3 provenance
        rise("#pv-title", {at('provenance', 0.15)}, {{ y: 14 }});
        rise("#pv-n1", {at('provenance', 0.8)}, {{ y: 26 }});
        rise("#pv-a1", {at('provenance', 5.4)}, {{ y: 0, duration: 0.4 }});
        rise("#pv-n2", {at('provenance', 5.9)}, {{ y: 26 }});
        rise("#pv-a2", {at('provenance', 10.8)}, {{ y: 0, duration: 0.4 }});
        rise("#pv-n3", {at('provenance', 11.3)}, {{ y: 26 }});
        rise("#pv-note", {at('provenance', 14.6)}, {{ y: 18 }});

        // 4 score - one row per named component, as the line names them
        rise("#sc-title", {at('score', 0.15)}, {{ y: 14 }});
        [0, 1, 2, 3, 4].forEach((i) => {{
          const row = "#sc-r" + (i + 1), t = {at('score', 1.5)} + i * 1.25;
          rise(row, t, {{ y: 22, duration: 0.45 }});
          tl.fromTo(row + " .bar-fill", {{ scaleX: 0 }},
            {{ scaleX: Number(document.querySelector(row + " .bar-fill").dataset.w),
               duration: 0.55, ease: "power2.out" }}, t + 0.1);
        }});
        seq("#sc-bands .band", {at('score', 8.6)}, 0.3, {{ y: 18, duration: 0.5 }});

        // 5 forest - the population settles first, then what it isolates
        rise("#fo-plot", {at('forest', 0.15)}, {{ y: 24, duration: 0.6 }});
        rise("#fo-side .eyebrow", {at('forest', 0.4)}, {{ y: 14 }});
        rise("#fo-name", {at('forest', 0.8)}, {{ y: 24 }});
        rise("#fo-desc", {at('forest', 1.4)}, {{ y: 20 }});
        tl.from("#fo-plot .pt:not(.is-out)", {{ opacity: 0, duration: 0.5,
          stagger: {{ each: 0.012, from: "random" }}, ease: "power1.out" }}, {at('forest', 1.0)});
        tl.from("#fo-plot .pt.is-out", {{ opacity: 0, scale: 0.3, duration: 0.5,
          stagger: 0.12, ease: "power3.out" }}, {at('forest', 6.2)});

        // 6 bert
        rise("#bt-title", {at('bert', 0.15)}, {{ y: 14 }});
        rise("#bt-name", {at('bert', 0.5)}, {{ y: 22 }});
        rise("#bt-a", {at('bert', 1.6)}, {{ y: 24 }});
        rise("#bt-b", {at('bert', 2.3)}, {{ y: 24 }});
        rise("#bt-mid", {at('bert', 4.6)}, {{ y: 0, scale: 0.9, duration: 0.6 }});
        rise("#bt-note", {at('bert', 7.4)}, {{ y: 18 }});

        // 7 gemini
        rise("#gm-title", {at('gemini', 0.15)}, {{ y: 14 }});
        rise("#gm-name", {at('gemini', 0.5)}, {{ y: 24 }});
        seq(".lab", {at('gemini', 1.6)}, 1.1, {{ y: 22, duration: 0.5 }});
        rise("#gm-note", {at('gemini', 6.4)}, {{ y: 18 }});

        // 8 detectors - one card per line of the list
        rise("#dt-title", {at('detectors', 0.15)}, {{ y: 14 }});
        seq(".dcard", {at('detectors', 2.6)}, 1.35, {{ y: 26, duration: 0.5 }});

        // 9 queue
        rise("#qu-title", {at('queue', 0.15)}, {{ y: 14 }});
        rise("#qc-1", {at('queue', 0.6)}, {{ y: 26 }});
        rise("#qc-2", {at('queue', 1.3)}, {{ y: 26 }});
        rise("#qc-3", {at('queue', 3.1)}, {{ y: 26, duration: 0.6 }});
        rise("#qu-note", {at('queue', 5.2)}, {{ y: 18 }});

        // 10 why
        rise("#wy-badge", {at('why', 0.15)}, {{ y: 14 }});
        rise("#wy-head", {at('why', 0.6)}, {{ y: 26 }});
        seq(".reason", {at('why', 2.0)}, 1.5, {{ y: 22, duration: 0.5 }});

        // 11 refresh
        rise("#rf-title", {at('refresh', 0.1)}, {{ y: 14 }});
        seq(".step", {at('refresh', 0.7)}, 0.62, {{ y: 22, duration: 0.5 }});
        rise("#rf-note", {at('refresh', 3.3)}, {{ y: 16 }});

        // 12 limits
        rise("#lm-title", {at('limits', 0.15)}, {{ y: 14 }});
        seq(".np", {at('limits', 1.4)}, 0.85, {{ y: 18, duration: 0.45 }});
        rise("#lm-l1", {at('limits', 8.4)}, {{ y: 22, duration: 0.6 }});
        rise("#lm-l2", {at('limits', 9.9)}, {{ y: 24, duration: 0.6 }});
        rise("#lm-mark", {at('limits', 12.4)}, {{ y: 24, duration: 0.6 }});
        rise("#lm-sub", {at('limits', 13.1)}, {{ y: 14, duration: 0.5 }});

        // Music sits far under the narration - it is a floor, not a bed.
        const bed = document.getElementById("bed");
        tl.fromTo(bed, {{ volume: 0 }}, {{ volume: 0.1, duration: 1.2 }}, 0);
        tl.to(bed, {{ volume: 0.16, duration: 2 }}, {at('limits', 8.0)});
        tl.to(bed, {{ volume: 0, duration: 2.2 }}, {round(TOTAL - 2.4, 2)});

        window.__timelines["main"] = tl;
      }}

      if (document.fonts && document.fonts.ready) document.fonts.ready.then(build);
      else build();
    </script>
  </body>
</html>
"""

OUT.write_text(HTML)
print(f"wrote {OUT}")
print(f"{len(SCENES)} scenes, total {TOTAL}s = {TOTAL/60:.2f} min")
for s in SCENES:
    print(f"  {s['key']:12} start {s['start']:7.2f}  vo {s['voDur']:6.2f}  scene {s['dur']:6.2f}")
