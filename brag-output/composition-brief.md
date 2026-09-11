# Hyperframes Composition Brief: Kasauti

## Objective

Create a short launch-style brag video for Kasauti, an AI-powered MPLADS
verification system built for Smart India Hackathon 2026 (SIH26102, MoSPI).

## Output

- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 24 seconds

## Source Material

- Project root: `/home/rvina/projects/SIH HACKATHON`
- Primary files read: `web/app/page.tsx`, `web/app/layout.tsx`,
  `web/app/globals.css`, `web/app/projects/[id]/page.tsx`, `data/scoring.py`,
  `README.md`, plus the live API at `/api/overview` for every figure
- Product name: **Kasauti**
- Tagline / strongest claim: *Every MPLADS work, checked against its peers.*
- Key UI moment to recreate: the work page's **Why was this flagged?** panel —
  the `AI POWERED · GEMINI-FLASH-LITE` badge above the heading, and each reason
  carrying the method that produced it underneath

Copy that must appear verbatim (all of it is on the live site or in the code):

- `Every MPLADS work, checked against its peers.`
- `AI POWERED · GEMINI FLASH LITE · ISOLATION FOREST · SENTENCE-BERT`
- `Why was this flagged?`
- `AI POWERED · GEMINI-FLASH-LITE`
- `A kasauti says which pieces are worth assaying.` / `Never which are false.`
- Component names and weights: `Cost 25%`, `Delay 25%`, `Duplication 20%`,
  `Agency 15%`, `Compliance 15%`
- `SIH26102 · MoSPI`

## Creative Direction

- Tone preset: `polished`
- Creative direction: *institutional confidence — a touchstone, not a verdict*
- Interpretation: slow cuts and generous holds. No bounce, no overshoot, no
  easing that reads as playful — `power2.out` and `power3.out` only. Type does
  all the work. Where a normal launch video would cut faster, this one holds a
  beat longer; the confidence is in not rushing.
- Angle: **Nobody has read them all.** A quarter of a million public-works
  records, ₹19,804 crore, no human path through it. Open on that number, show
  the system that did read them, and close on the thing that separates it from
  every other dashboard — it says *why* a work was flagged, and it says what it
  cannot tell you.
- Hook: a hard count-up to **2,50,839** on black, then one quiet line —
  *Nobody has read them all.* No logo until the second scene.
- Outro / punchline: *A kasauti says which pieces are worth assaying. **Never
  which are false.*** Then the wordmark on the final strong cue.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign
  - **Any hue that is not risk.** The product's own law: colour only ever means
    risk. The single exception already in the product is the two words "AI
    powered" in `#7a1a12` with a `#16704a` dot. Nothing else in this video
    gets a colour.

## Visual Identity

- Background (dark scenes): `#0b0b0c` — the product's `--slab`
- Background (light scenes): `#f1f1f2` — the product's `--ground`
- Text on dark: `#fafafa`, secondary `#b6b6bf`
- Text on light: `#0b0b0c`, secondary `#4a4a52`, tertiary `#6b6b74`
- Accent: `#a82e22` (`--risk-high`) — risk only
- AI red: `#7a1a12`; risk-low green `#16704a` (the dot)
- Display font: **Geist** — the real variable woff2 lifted from the product's
  own build into `assets/fonts/geist.woff2`. Not a Google Fonts link: the
  render must not depend on the network, and this is the exact file the site
  ships.
- Body / data font: **Geist Mono** — `assets/fonts/geist-mono.woff2`. Every
  figure in the product is monospaced with `font-variant-numeric: tabular-nums`,
  and the video must keep that or the count-up will jitter.
- Visual references from the project: the rounded card (`--radius-card: 18px`),
  the thin component bars from the score panel, the pill badge with a leading
  dot, the mono eyebrow in uppercase at `letter-spacing: 0.16em`

## Storyboard

`brag-output/brag-plan.md` is the creative contract. Scene summary:

1. **The number nobody has read** — 0.0s, 3.3s — count-up to `2,50,839` on
   black under the label `MPLADS WORKS PUBLISHED`, then *Nobody has read them
   all.*
2. **Kasauti** — 3.3s, 3.8s — light ground, the AI eyebrow, the wordmark, and
   the hero line verbatim.
3. **What the score is made of** — 7.1s, 4.4s — five component rows arrive one
   per beat with weights and drawing bars; the score `85` resolves in risk red.
4. **A quarter-million, down to a morning** — 11.5s, 4.2s — `2,50,839` →
   `48,296` → `2,316`, the last in risk red, with a rule drawing between them.
5. **Why was this flagged?** — 15.7s, 4.5s — the badge, the heading, then three
   real reasons each tagged with its method. Must not be rushed: every line
   holds long enough to read.
6. **A touchstone, not a verdict** — 20.2s, 3.8s — the two-line refusal, then
   the wordmark and `SIH26102 · MoSPI`.

## Audio

- Audio role: sparse professional bed — present, never driving
- Audio arc: enters almost unnoticed under the count; opens slightly as the
  product arrives; carries the rhythm through scenes 3 and 4 so no SFX has to;
  steps back in scene 5 to leave room for reading; thins and resolves under the
  wordmark
- Music: `assets/music/bed.mp3`
  (`happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`, 110 BPM — the
  slowest of the five bundled tracks, which is why it was chosen)
- Music treatment: starts at 0s, bed at ~0.5 gain, fade in over 0.5s, fade out
  from 22.4s to silence by 24.0s under the wordmark
- Music cue guidance: bundled preset read from
  `~/.claude/skills/brag/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.md`.
  Beat grid ~0.545s from 0.56s. **Four strong-cue locks:** `10.93s` score
  resolves, `13.11s` the red high-risk figure lands, `17.47s` the first flagged
  reason, `22.93s` the wordmark. Sequential reveals ride the beat grid between
  them.
- Audio-reactive treatment: **none** — deliberately. The tone is restraint, and
  a breathing background would be the one decorative thing in a video whose
  whole argument is that nothing here is decoration. Documented as a creative
  choice, not an omission.
- Audio-coupled moments:
  - Scene 1, count settles (~2.2s) — one soft tick, the only sound under the hook
  - Scene 3, score resolves (10.93s) — a quiet select tone on the strong cue
  - Scene 4, red figure lands (13.11s) — one restrained light impact
  - Scene 6, wordmark (22.93s) — one dry bell, the only hard sound in the video
- SFX selection guidance: four cues in twenty-four seconds. Each matched to
  something actually moving on screen. No whooshes on cuts, no risers, no
  impact on every text reveal.
- SFX analysis guidance: `~/.claude/skills/brag/assets/sfx/sfx-analysis.json`
  consulted; low-brightness sounds chosen and all four mixed well under the bed
  (0.18–0.4 gain) so none of them reads as a sting.
- Exact SFX choice: `interface/drop_003` → `tick.ogg`,
  `interface/select_008` → `resolve.ogg`, `impact/impactGeneric_light_000` →
  `land.ogg`, `impact/impactBell_heavy_000` → `mark.ogg`, all copied into
  `assets/sfx/`.
- Audio files: already copied into `brag-output/composition/assets/`.

## Hyperframes Instructions

Standalone composition, single `index.html`, one paused GSAP timeline
registered at `window.__timelines["main"]`.

Requirements honoured:

- Real UI from the source project: the flagged-reason panel, the score
  components, the AI eyebrow and badge — all reproduced with the product's own
  copy, colours, radii and fonts.
- All text readable: every line a viewer must read is fast-in then held. The
  three reasons in scene 5 each hold ≥ 1.2s.
- 24 seconds, inside the 15–25s law.
- Music and four SFX included.
- Deterministic: no clocks, no `Math.random`, no network. Fonts are local
  `@font-face` files, so the render does not depend on Google Fonts resolving.
- Timeline built inside `document.fonts.ready` and registered only after the
  build completes, so text metrics are settled before any tween is measured.
- No CSS initial `transform` paired with a GSAP tween on the same property —
  every entrance uses `gsap.from`/`fromTo` so the start state lives in the tween.
- Every `<audio>` carries an `id`; no `crossorigin` anywhere.
- `npx hyperframes check` must pass with zero findings before render.
