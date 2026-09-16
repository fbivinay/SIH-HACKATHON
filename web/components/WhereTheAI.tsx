/**
 * The three models, what each decides and what it does not.
 *
 * Lived on the overview until the owner asked for the opening screen to carry
 * no AI section; the masthead still says "AI-powered" on every page. It sits
 * on /provenance, between the reconciliation and the detectors, because that
 * is the page about where the figures come from and the models are part of
 * that answer. Renders a block, not a section: the page is one shell.
 */
// What actually runs, with the file that runs it. Named on the page because the
// brief asks for an AI-powered system and a visitor could not previously tell
// what was intelligent about this one - the methods were described in the
// component table, in language that never said "model".
//
// Every entry here was checked against the source before being written. Nothing
// is called AI that is really a sum.
const MODELS = [
  {
    name: "Isolation Forest",
    kind: "Unsupervised anomaly detection · scikit-learn",
    does:
      "Learns what an ordinary MPLADS work looks like across sanctioned amount, delay and spend ratio together, then scores how far each work sits from that shape. It catches works that are unremarkable on every single measure but odd in combination — which a threshold on any one column cannot see.",
    decides: "Raises the cost component when it disagrees with the peer median.",
    where: "data/scoring.py",
  },
  {
    name: "Sentence-BERT embeddings",
    kind: "Neural language model · all-MiniLM-L6-v2, runs locally",
    does:
      "Turns every work description into a 384-dimension vector, so two works are compared by what they mean rather than by the words they share. “Construction of CC road” and “Cement concrete road construction” land in the same place; a keyword match would miss it.",
    decides: "Flags near-duplicate sanctions above 0.94 similarity in the same district and sector.",
    where: "data/scoring.py",
  },
  {
    name: "Gemini",
    kind: "Large language model · sector labelling only",
    does:
      "Reads the 41,691 descriptions the keyword rules could not classify and assigns each a sector, so a school building is compared against school buildings. It is allowed to answer “unclear”, and did so 5,167 times rather than guess — which is exactly why a generative model was used instead of a nearest-match classifier.",
    decides:
      "Nothing directly. It only decides which works are a work’s peers — and because cost is judged against those peers, a wrong label makes a comparison wrong.",
    where: "data/llm_sectors.py",
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
            <p className="model-card__does">{m.does}</p>
            <p className="model-card__decides">
              <span>Decides</span>
              {m.decides}
            </p>
            <code className="model-card__where">{m.where}</code>
          </article>
        ))}
      </div>
    </div>
  );
}
