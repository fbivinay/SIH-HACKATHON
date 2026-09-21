/**
 * The three models, what each decides and what it does not.
 *
 * Lived on the overview until the owner asked for the opening screen to carry
 * no AI section; the masthead still says "AI-powered" on every page. It sits
 * on /provenance, between the reconciliation and the detectors, because that
 * is the page about where the figures come from and the models are part of
 * that answer. Renders a block, not a section: the page is one shell.
 */
// What actually runs. Named on the page because the
// brief asks for an AI-powered system and a visitor could not previously tell
// what was intelligent about this one - the methods were described in the
// component table, in language that never said "model".
//
// Every entry here was checked against the source before being written. Nothing
// is called AI that is really a sum.
// Three short points each (owner's call, 2026-09-21): what it does, what that
// catches, and the limit of what it may decide - the last is the one that
// must never be cut.
const MODELS = [
  {
    name: "Isolation Forest",
    kind: "Unsupervised anomaly detection · scikit-learn",
    points: [
      "Learns what an ordinary work looks like from sanctioned amount, delay and spend ratio together.",
      "Catches works that look normal on each measure but odd in combination.",
      "Can only raise a work's cost component - it never flags a work on its own.",
    ],
  },
  {
    name: "Sentence-BERT embeddings",
    kind: "Neural language model · all-MiniLM-L6-v2, runs locally",
    points: [
      "Compares work descriptions by meaning, not by the words they share.",
      "“CC road” and “cement concrete road” land together, where a keyword match misses them.",
      "Flags near-duplicates above 0.94 similarity in the same district and sector.",
    ],
  },
  {
    name: "Gemini",
    kind: "Large language model · sector labelling only",
    points: [
      "Gives a sector to the 41,691 descriptions the keyword rules could not place.",
      "May answer “unclear”, and did so 5,167 times rather than guess.",
      "Never scores or flags a work - it only decides which works are compared together.",
    ],
  },
];

export default function WhereTheAI() {
  return (
    <div className="mt-12">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div>
          <h2 className="section-head flex items-center gap-3 flex-wrap">
            <span className="ai-badge"><b className="ai-word">AI powered</b></span>
            Where the AI is
          </h2>
          <p className="lede !mx-0 !max-w-2xl !mt-1">
            Three models run over every work. Each one is named here with what it
            decides and what it does not, because a system that cannot say where its
            intelligence sits is asking to be taken on trust.
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {MODELS.map((m) => (
          <article key={m.name} className="card model-card">
            <h3 className="model-card__name">{m.name}</h3>
            <p className="model-card__kind">{m.kind}</p>
            <ul className="model-card__points">
              {m.points.map((pt) => (
                <li key={pt}>{pt}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </div>
  );
}
