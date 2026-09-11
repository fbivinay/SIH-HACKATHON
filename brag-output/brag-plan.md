# Brag Plan: Kasauti

## What is this app?

Kasauti reads every MPLADS work India has published — 250,839 of them across two
Lok Sabha terms — scores each one against comparable works using three AI models,
and hands officials a ranked list of what to verify. It is impressive because it
is real: real data, real reconciliation against the ministry's own dashboard, and
a section on the site that says what it refuses to claim.

## The angle

**Nobody has read them all.** That is the actual problem: a quarter of a million
public-works records, ₹19,804 crore, and no human path through it. The video
opens on that number, then shows the system that did read them — and, at the end,
shows the thing that separates it from every other dashboard: it tells you *why*
a work was flagged, and it says what it cannot tell you.

The angle is restraint. This is a tool for a ministry, judged by a ministry. No
hype, no "revolutionise", no invented capability. The touchstone metaphor carries
the whole thing: a kasauti says which pieces are worth assaying, never which are
false. That refusal *is* the product claim.

## Hook (first 2-3 seconds)

Black. A single number counts up hard to **2,50,839**, monospaced, huge. Under
it, one line arrives: **Nobody has read them all.** Then the count sits there,
silent, for a beat before the cut. No logo yet — the number earns the next
twenty seconds, not the brand.

## Key moments (the middle)

- **The score, taken apart.** The five weighted components arriving one by one on
  the beat — Cost 25%, Delay 25%, Duplication 20%, Agency 15%, Compliance 15% —
  with the weights visible. Not "AI-powered analysis": the actual arithmetic.
- **The funnel.** 2,50,839 works → 48,296 worth a look → 2,316 high risk. Three
  numbers, each one smaller, the last one in the risk red. This is the whole
  value proposition in three figures: a quarter-million records reduced to a
  morning's work.
- **Why it was flagged.** The real panel from the work page: the `AI POWERED ·
  GEMINI-FLASH-LITE` badge, then reasons arriving each tagged with the method
  that produced it — Isolation Forest, Sentence-BERT, peer comparison,
  Herfindahl-Hirschman. Every flag is arguable. That is the point.

## Outro / punchline

The touchstone line, held long enough to read properly:

> A kasauti says which pieces are worth assaying. **Never which are false.**

Then the wordmark lands on the final strong beat. No call to action, no URL
shouting. The restraint is the closing argument.

## User flow worth showing

Entry → key action → result, as an official actually moves through it:

1. **Open the queue** — 48,296 flagged works, ranked, the highest scores first.
2. **Open one work** — score 85, the five components broken out with their bars.
3. **Read why** — each reason with the model that produced it, so the flag can be
   argued with rather than obeyed.

Scenes 3, 4 and 5 are this flow. The landing page is only the reveal in Scene 2.

## Tone

- Preset: `polished`
- Creative direction: *institutional confidence — a touchstone, not a verdict*
- Interpretation: Slow cuts, generous holds, no bounce or overshoot in the
  motion. Type does the work; the palette stays monochrome and lets the one red
  number carry all the weight. Nothing accelerates for excitement's sake. Where
  most launch videos would cut faster, this one holds a beat longer — the
  confidence is in not rushing.

## Format: landscape — 1920x1080
## Duration: 24 seconds

## Visual identity (from the project)

- Background: `#0b0b0c` (the product's `--slab`, its dark ground)
- Surface / ground: `#f1f1f2` (`--ground`), white `#ffffff` for cards
- Text on dark: `#fafafa` (`--on-slab`), secondary `#b6b6bf` (`--on-slab-2`)
- Text on light: `#0b0b0c` (`--ink`), secondary `#4a4a52` (`--ink-2`)
- Accent (risk high): `#a82e22` — **the only hue in the system**, and it means
  exactly one thing: risk
- AI red: `#7a1a12` for the words "AI powered"; risk low green `#16704a` for the
  dot beside them
- Display font: Geist (600/650 weight, tight letter-spacing -0.035em)
- Body / data font: Geist Mono — every figure in the product is monospaced with
  tabular numerals, and the video must keep that
- Strongest visual element: the score card — five labelled bars with a number
  at the right of each, and one red figure

**Colour law, inherited from the product:** colour only ever means risk. Nothing
in this video earns a hue except the risk figures and the two words "AI powered".

## Share copy (draft)

2,50,839 MPLADS works. Nobody has read them all — so we built something that
did. Kasauti scores every published work against its peers and tells you exactly
why each flag exists. A touchstone, not a verdict.

## Audio direction

- Role: sparse professional bed — present, never driving
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (110 BPM, the
  slowest of the five bundled tracks, which suits the unhurried cutting)
- Music treatment: start at 0s, low bed around 0.5 gain, quick fade-in over the
  first 0.4s, fade out over the final 1.2s under the wordmark
- Music cue guidance: preset cue file read (`cues/…vol-12….music-cues.md`).
  Beat grid at ~0.545s spacing from 0.56s. **Strong cues used for major
  moments:** 8.74s (score components complete), 13.11s (the red high-risk
  figure lands), 17.47s (the AI badge appears), 22.93s (wordmark lands).
  Sequential reveals ride the beat grid between those.
- Audio-reactive treatment: subtle — the dark ground's vignette and the card
  presence may breathe very slightly with RMS. No waveform, no equalizer, no
  scaling of text.
- SFX posture: sparse. Four cues at most across 23 seconds, each matched to a
  real visual event, never decorative.
- Audio-coupled moments: the opening count-up ticking to its landing; the five
  components arriving one per beat; the funnel's three figures; the wordmark hit.
- Restraint rule: no whooshes on cuts, no risers, no impact on every text
  reveal. If a sound cannot be justified by something moving on screen, it does
  not go in. This is an audit tool, not a trailer.

## Storyboard

### Scene 1 — The number nobody has read — 3.3s
Black ground `#0b0b0c`. A monospaced figure counts up hard from 0 to **2,50,839**
and settles, huge and centred, in `#fafafa`. Beneath it, after the count lands,
one line arrives quietly in `#b6b6bf`: **Nobody has read them all.** Small
mono label above the number: `MPLADS WORKS PUBLISHED`. Hold in silence for a
beat before the cut — the pause is the hook, not the number.
Sequential/interaction: yes — count-up runs 0.4→2.1s, then the line fades in at
2.4s and holds.
Audio intent: bed enters almost unnoticed; the count feels like something being
totalled, not celebrated.
Audio-coupled idea: counter ticks — one soft interface tick as the figure settles.
Music: low, sparse, just establishing.
Transition mood: clean → Scene 2

### Scene 2 — Kasauti — 3.8s
Cut to the light ground `#f1f1f2`. The wordmark and the product's own hero line,
exactly as the site states it: **Every MPLADS work, checked against its peers.**
Above it, the real eyebrow from the page — a green dot, then `AI POWERED` in
`#7a1a12`, then `· GEMINI FLASH LITE · ISOLATION FOREST · SENTENCE-BERT` in grey
mono. The headline arrives as one settling line, no letter-by-letter.
Sequential/interaction: yes — eyebrow at 3.5s, headline at 3.9s, sub-line at 4.6s.
Audio intent: the bed opens up slightly; the product arrives.
Audio-coupled idea: none — let the type land in the music.
Music: bed continues, first real melodic figure.
Transition mood: soft → Scene 3

### Scene 3 — What the score is made of — 4.4s
Dark ground. Title in mono: `OVERALL RISK SCORE`. Five rows arrive one per beat,
each a label, a weight and a bar that draws: **Cost 25% · Delay 25% ·
Duplication 20% · Agency 15% · Compliance 15%.** As the fifth lands on the strong
cue at 8.74s, a single figure resolves at the right: **85**, in risk red
`#a82e22`. The point being made: the score is arithmetic anyone can check, not
a black box.
Sequential/interaction: yes — five rows on the beat grid at 7.09, 7.64, 8.19,
8.74, and the score resolving on 8.74's strong cue.
Audio intent: each row lands with the beat; the music does the rhythm, not an SFX.
Audio-coupled idea: beat-aligned reveal, one row per beat; one soft tick on the
score landing.
Music: strong cue at 8.74s carries the score.
Transition mood: clean → Scene 4

### Scene 4 — A quarter-million, down to a morning — 4.2s
Light ground. Three figures across the frame, arriving left to right, each with
its mono label beneath: **2,50,839** `WORKS SCORED` → **48,296** `WORTH A LOOK`
→ **2,316** `HIGH RISK`. The first two in ink; the third in risk red, landing on
the strong cue at 13.11s and holding. A thin rule connects them, drawing left to
right as they arrive, so the reduction reads as one movement.
Sequential/interaction: yes — figures at 11.46s, 12.02s, 13.11s (the red one on
the strong cue), rule drawing between them.
Audio intent: three steps down; the last one lands with weight.
Audio-coupled idea: card-by-card sequence on the beat; one restrained impact on
the red figure.
Music: strong cue 13.11s.
Transition mood: clean → Scene 5

### Scene 5 — Why was this flagged? — 4.5s
Dark ground, the real panel from a work page. First the badge: a green dot and
`AI POWERED · GEMINI-FLASH-LITE`, landing on the strong cue at 17.47s. Then the
heading **Why was this flagged?** Then three reasons arriving one per beat, each
with the method that produced it in mono grey beneath — exactly as the product
renders them:
- *298% above the median for this sector and district* — `PEER COMPARISON`
- *100% similarity with another nearby work* — `AI · SENTENCE-BERT`
- *191 days beyond expected completion* — `PUBLISHED DATES`

This is the scene that must not be rushed: each line holds long enough to read.
Sequential/interaction: yes — badge 15.84s, heading 16.38s, reasons at 17.47s,
18.56s, 19.66s.
Audio intent: quieter here; the bed steps back so the reading has room.
Audio-coupled idea: beat-aligned reveal, one reason per beat.
Music: strong cues 17.47s and 18.56s.
Transition mood: soft → Scene 6

### Scene 6 — A touchstone, not a verdict — 3.8s
Black. The line, centred, in two weights so the refusal carries:

> A kasauti says which pieces are worth assaying.
> **Never which are false.**

Held for a full beat. Then the wordmark — logo and **Kasauti** — resolves on the
final strong cue at 22.93s, with `SIH26102 · MoSPI` small in mono beneath it.
Music fades out under it. Last frame is the wordmark, still.
Sequential/interaction: yes — first line 20.19s, second line 21.28s, wordmark
22.37→22.93s.
Audio intent: the bed thins and resolves; the wordmark lands into near-silence.
Audio-coupled idea: one dry, low hit on the wordmark — the only hard sound in
the video.
Music: fade out from 22.0s.
Transition mood: end.

---

**Scene starts and durations** (the sum was mis-added at 23.0s on the first
pass; it is 24.0, still inside the 15–25s law):

| # | Scene | Start | Duration |
|---|---|---|---|
| 1 | The number nobody has read | 0.0 | 3.3 |
| 2 | Kasauti | 3.3 | 3.8 |
| 3 | What the score is made of | 7.1 | 4.4 |
| 4 | A quarter-million, down to a morning | 11.5 | 4.2 |
| 5 | Why was this flagged? | 15.7 | 4.5 |
| 6 | A touchstone, not a verdict | 20.2 | 3.8 |

**Total 24.0s.** ✓ (15–25s)

**Strong-cue locks — four, as the brief allows:** score resolves on 10.93s,
the red high-risk figure lands on 13.11s, the first flagged reason on 17.47s,
the wordmark on 22.93s. Everything else rides the ~0.545s beat grid.

## Every figure in this video is real

Pulled from the running API at plan time, not written from memory:

| Figure | Value | Source |
|---|---|---|
| Works scored | 250,839 | `/api/overview` → `total_projects` |
| Worth a look (≥ 40) | 48,296 | `/api/overview` → `anomaly_count` |
| High risk (≥ 70) | 2,316 | `/api/overview` → `high_risk_count` |
| Allocated | ₹19,804 Cr | `/api/overview` → `allocated_total` |
| Component weights | 25/25/20/15/15 | `data/scoring.py` → `RISK_WEIGHTS` |
| Bands | LOW <40, MED 40–70, HIGH ≥70 | `data/scoring.py` |
| Work-page reasons | 298%, 100%, 191 days | `/projects/12524`, live |

If a number cannot be traced to the record, it does not appear in the video —
which is the same rule the product itself runs on.
