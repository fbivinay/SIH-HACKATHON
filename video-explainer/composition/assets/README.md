# Assets are not committed

`brag-output/composition/assets/` holds three kinds of borrowed file, all
gitignored:

- `music/bed.mp3` — a bundled `/brag` track
  (`happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`, ende.app). The skill
  ships it, and its own README says to verify the exact licence terms before
  redistributing, so it is not committed here. **The rendered `brag.mp4`
  contains this music in its audio track** — check the licence before posting
  it anywhere public.
- `sfx/*.ogg` — Kenney.nl, CC0 (public domain). Safe, but restored the same way.
- `fonts/*.woff2` — Geist and Geist Mono, lifted from `web/.next/static/media`
  so the render does not depend on Google Fonts resolving. Regenerate with a
  `next build`.
- `vendor/gsap.min.js` — GSAP 3.14.2, fetched from jsdelivr.

Restore them:

```sh
A=~/.claude/skills/brag/assets
mkdir -p music sfx fonts vendor
cp "$A/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3" music/bed.mp3
cp "$A/sfx/interface/drop_003.ogg"             sfx/tick.ogg
cp "$A/sfx/interface/select_008.ogg"           sfx/resolve.ogg
cp "$A/sfx/impact/impactGeneric_light_000.ogg" sfx/land.ogg
cp "$A/sfx/impact/impactBell_heavy_000.ogg"    sfx/mark.ogg
W=../../../web/.next/static/media
cp "$W"/caa3a2e1cccd8315-s.p.*.woff2 fonts/geist.woff2
cp "$W"/797e433ab948586e-s.p.*.woff2 fonts/geist-mono.woff2
curl -sSL -o vendor/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js
```
