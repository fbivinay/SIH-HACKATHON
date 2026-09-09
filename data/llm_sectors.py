"""Classify the works the keyword rules could not, using a language model.

WHY THIS EXISTS
---------------
sectors.py reads a work's description with ordered keyword rules and gets 79.8%
of works into a named sector. The remaining 50,720 (20.2%) land in 'Other', and
that bucket is not noise - it is the second largest sector in the data.

The rules miss them because they are English keywords and the descriptions
frequently are not:

    146x  Muktidham Nirman                  cremation ground construction
    139x  Rangmanch Nirman                  stage construction
     76x  knowledge improvement of student's.

Transliterated Hindi, ungrammatical English, and phrasings no keyword list
anticipates. Extending the rules cannot reach this: 74.3% of the unclassified
works have a description that occurs exactly once, and the 1,000 commonest
phrases cover only 12.3% of them. It is a genuine long tail of 37,703 unique
strings.

WHY NOT EMBEDDINGS, WHICH ARE FREE AND ALREADY HERE
---------------------------------------------------
scoring.py already runs all-MiniLM-L6-v2 locally, so zero-shot classification
by nearest sector embedding costs nothing. Measured, it does not work, and the
reason is structural rather than a tuning problem:

    Muktidham Nirman   -> Religious & Cultural  0.35   correct
    public utility     -> Water                 0.51   wrong, and more confident

An embedding model always returns a nearest neighbour. It cannot abstain, so a
string carrying no information still lands somewhere, often with a higher
similarity than a correct answer. No threshold separates the two. The ability
to answer "Other, this text does not say" is the thing worth paying for, and
only a generative model has it.

WHAT IT IS ALLOWED TO AFFECT
----------------------------
A sector is not cosmetic: cost_risk compares a work against the median of its
(district, sector) peers, so a label change moves a score. That makes this the
one place in the system where a model's output reaches a risk score, and it is
fenced accordingly:

  * The keyword rules run first and always win. This only ever sees text they
    returned Other for.
  * The reply is constrained to the eleven existing sectors or Other. It cannot
    invent a sector, and Other is an allowed answer, so an uninformative
    description stays uninformative.
  * Labels are cached on disk against the normalised description, so a run is
    reproducible and a bad batch can be deleted without re-scoring anything.
  * Every failure - no key, no package, a bad response, a rate limit - returns
    Other. The pipeline never depends on this working.
"""

import json
import os
import pathlib
import time

from sectors import OTHER, SECTOR_RULES, normalize

SECTOR_NAMES = [name for name, _ in SECTOR_RULES]
ALLOWED = SECTOR_NAMES + [OTHER]

# Committed on purpose. It is derived data, but it is the only thing the model
# run produced, and committing it means a clone, a CI run or the nightly
# workflow gets the labels with no key and no network. Deleting it costs a
# re-run, not correctness.
CACHE_PATH = pathlib.Path(__file__).with_name("sector_cache.json")

# The free tier is Flash-only at 10-15 requests/minute and 100-1,000 requests
# per day, so the batch size - not the token budget - decides whether a run
# finishes. 150 descriptions of ~20 tokens is ~4k tokens in, far under the
# 250k/minute ceiling, and turns 42,098 strings into ~280 requests.
BATCH_SIZE = 150
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
# 15 requests/minute is the tightest published free-tier rate.
MIN_SECONDS_BETWEEN_CALLS = 4.5

PROMPT = (
    "You are labelling public works from India's MPLADS scheme by the kind of "
    "asset built. Descriptions are often transliterated Hindi or ungrammatical "
    "English.\n\n"
    "Reply with one sector per numbered description, using EXACTLY these names:\n"
    + "\n".join(f"- {s}" for s in SECTOR_NAMES) +
    f"\n- {OTHER}\n\n"
    f"Use {OTHER} when the text genuinely does not say what was built - "
    "'public utility', 'As Per Attachment', a reference number. Do not guess. "
    f"{OTHER} is a correct answer, not a failure.\n\n"
    "Some guidance on the vocabulary that recurs:\n"
    "- muktidham, shamshan, ghat, mandir, rangmanch, mancha -> Religious & Cultural\n"
    "- hymast, minimast, high mast, MML, solar light -> Street Lighting\n"
    "- yatri pratikshalaya, bus stop shelter, panchayat bhavan -> Community Buildings\n"
    "- nirman means construction and does not by itself indicate a sector\n"
)


def _schema(count):
    """One sector per input, in order. Constraining the reply is what stops the
    model inventing a twelfth sector or returning prose."""
    return {
        "type": "object",
        "properties": {
            "sectors": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {"type": "string", "enum": ALLOWED},
            }
        },
        "required": ["sectors"],
    }


def load_cache(path=CACHE_PATH):
    """Labels keyed by normalised description. Missing or corrupt reads as
    empty - a damaged cache must cost a re-run, not a crash."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def save_cache(cache, path=CACHE_PATH):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
    tmp.replace(path)


class GeminiClassifier:
    """The Gemini backend. Constructed lazily so importing this module never
    requires the package or a key."""

    def __init__(self, api_key=None, model=MODEL):
        from google import genai  # imported here: absence must degrade, not raise

        self.genai = genai
        self.model = model
        self.client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self._last_call = 0.0

    def classify(self, descriptions):
        from google.genai import types

        # Free-tier RPM is the binding constraint; pace rather than retry.
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

        numbered = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(descriptions))
        resp = self.client.models.generate_content(
            model=self.model,
            contents=numbered,
            config=types.GenerateContentConfig(
                system_instruction=PROMPT,
                response_mime_type="application/json",
                response_json_schema=_schema(len(descriptions)),
                temperature=0,
            ),
        )
        sectors = json.loads(resp.text)["sectors"]
        if len(sectors) != len(descriptions):
            raise ValueError(f"asked for {len(descriptions)} labels, got {len(sectors)}")
        # Belt and braces: the schema constrains this, but a label outside the
        # set would silently create a twelfth sector and a peer group of one.
        return [s if s in ALLOWED else OTHER for s in sectors]


def classify_missing(descriptions, client=None, cache=None, batch_size=BATCH_SIZE,
                     progress=print):
    """Label every description the keyword rules could not.

    `client` is injectable so the tests can run the whole path offline. Returns
    {normalised description: sector} covering only what was newly classified;
    the caller merges it with the cache.
    """
    from sectors import classify_sector

    cache = load_cache() if cache is None else cache
    pending = []
    seen = set()
    for text in descriptions:
        # The rules are re-run here rather than trusted from the caller. Passing
        # the whole column by mistake would otherwise send 250,839 descriptions
        # to a 1,000-request-a-day free tier, and the bill for that mistake on a
        # paid tier is worse.
        if classify_sector(text) != OTHER:
            continue
        key = normalize(text)
        if not key or key in cache or key in seen:
            continue
        seen.add(key)
        pending.append((key, text))

    if not pending:
        return {}
    if client is None:
        progress(f"llm_sectors: {len(pending)} descriptions unlabelled, no client "
                 f"configured - leaving them as {OTHER}.")
        return {}

    fresh = {}
    for start in range(0, len(pending), batch_size):
        chunk = pending[start:start + batch_size]
        try:
            labels = client.classify([text for _, text in chunk])
        except Exception as err:  # noqa: BLE001 - one bad batch must not lose the rest
            progress(f"llm_sectors: batch at {start} failed ({err}); "
                     f"leaving {len(chunk)} as {OTHER}")
            continue
        for (key, _), label in zip(chunk, labels):
            fresh[key] = label
        progress(f"llm_sectors: {min(start + batch_size, len(pending))}/{len(pending)}")
    return fresh


def apply(descriptions, cache=None):
    """Sector per description, rules first and the cache only for their gaps."""
    cache = load_cache() if cache is None else cache
    from sectors import classify_sector

    out = []
    for text in descriptions:
        sector = classify_sector(text)
        if sector == OTHER:
            sector = cache.get(normalize(text), OTHER)
        out.append(sector)
    return out
