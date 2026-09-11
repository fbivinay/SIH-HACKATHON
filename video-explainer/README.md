# The two-minute explainer

`kasauti-explainer.mp4` — 2:17, 1920x1080, narrated. Twelve scenes covering the
whole system: the problem, what it does, where the data comes from and how that
is reconciled, the five score components, each of the three AI models and what
each one refuses to do, the cohort detectors, the review queue, the flagged-work
panel, the nightly refresh, and what it will not tell you.

## How it is built

Narration first, visuals second. `narration.txt` holds one segment per scene;
`vo/` holds the generated speech; `build.py` measures those files and emits
`composition/index.html` with every scene held exactly as long as its line.

That order matters. The first script was written to 142 words per minute,
measured from a single short sentence, and came out at 2:45 — number-heavy copy
reads slower. Timing the scenes off the *rendered* audio instead of a word
count is what keeps picture and voice together.

Numbers are spelled out in `narration.txt` ("two lakh fifty thousand") so the
model says them correctly; the screen shows the digits.

## Rebuilding

Needs `ffmpeg` and the Kokoro venv (`~/.venvs/kokoro`, created with
`uv venv --python 3.12` then `uv pip install kokoro-onnx soundfile`).

```sh
export HYPERFRAMES_PYTHON=~/.venvs/kokoro/bin/python
H=npx\ hyperframes

# 1. Regenerate any narration segment you edited
$H tts "$(cat vo/03-provenance.txt)" --voice am_michael --out vo/03-provenance.wav
ffmpeg -y -i vo/03-provenance.wav -b:a 96k composition/assets/vo/03-provenance.mp3

# 2. Re-emit the composition against the new lengths
python3 build.py

# 3. Gate, then render
cd composition && $H check && $H render
```

Voice is `am_michael`. Three others were auditioned (`af_heart`, `bf_emma`,
`bm_george`); samples are gone but regenerate in seconds.

## Assets

`composition/assets/` is gitignored — see the README there. The music bed is a
bundled `/brag` track whose licence has not been verified for redistribution,
and it is in this video's audio track.
