import Link from "next/link";

/**
 * How the score is built and what it will not say.
 *
 * Both lived on the overview until the owner cut that page down to the hero
 * and the figures. They sit on /provenance with the models, because the page
 * about where the numbers come from is also the page about what they mean.
 * Renders blocks, not sections: that page is one shell.
 */
// Same weights and thresholds as data/scoring.py. Stated on the page because a
// score nobody can take apart is a score nobody should act on.
const COMPONENTS = [
  {
    name: "Cost",
    weight: "25%",
    method:
      "Sanctioned amount against the median for the same sector in the same district, blended with an isolation forest over amount, delay and spend.",
    guard: "Silent unless the district has at least 8 comparable works.",
  },
  {
    name: "Delay",
    weight: "25%",
    method:
      "Days past expected completion, taken from the recommendation and completion dates the portal publishes.",
    guard: "A work with no recorded schedule scores zero, not high.",
  },
  {
    name: "Duplication",
    weight: "20%",
    method:
      "Sentence-transformer embeddings of the work description, compared inside the same district and sector at 0.94 cosine similarity.",
    guard: "Near-identical wording is a lead, not a finding.",
  },
  {
    name: "Agency",
    weight: "15%",
    method:
      "The implementing agency's delay rate, how concentrated its payments are across vendors, and how long its oldest payment has been pending.",
    guard: "Measured per Lok Sabha term, so terms are never pooled.",
  },
  {
    name: "Compliance",
    weight: "15%",
    method:
      "Four stated rules: a recommended work with no schedule, a completed work with no completion date, a completed work with no photograph, and spend beyond the sanction — which cannot fire, because the source publishes one figure per completed work and it serves as both.",
    guard: "Each breach names the rule it breaks. The full book is on Sources.",
  },
];

const LIMITS = [
  {
    title: "It does not allege wrongdoing",
    body: "A high score means a work does not resemble its peers. That is a reason to look, and nothing more.",
  },
  {
    title: "It invents no fields",
    body: "Progress percentages, beneficiary counts, geo-tags and bill values are not published for MPLADS works, so this system does not show them.",
  },
  {
    title: "It reports, it does not forecast",
    body: "Every figure describes what the record already shows — how late a work is, how far its cost sits from its peers. The portal publishes no progress milestones, so there is nothing to project a completion date from. The closest thing to an early warning here is money committed to an agency that has paid nobody in six months, which is an observation, not a prediction.",
  },
  {
    title: "No model decides alone",
    body: "The score itself is deterministic and rule-weighted, and every flag names the record it came from. The language model only labels what a work is, so it meets the right peers; it never scores, ranks or flags anything.",
  },
];

export default function ScoreMethod() {
  return (
    <>
    <div className="mt-12">
      <div className="slab">
        <div className="text-center">
          <h2 className="section-head">What the score is made of</h2>
          <p className="lede">
            Five components, fixed weights, no black box. Every one can be read back to the
            rows it came from.
          </p>
        </div>

        <div className="mt-9 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {COMPONENTS.map((c) => (
            <div key={c.name} className="slab-card">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-[0.98rem] font-medium">{c.name}</h3>
                <span
                  className="text-[0.78rem] tabular-nums"
                  style={{ fontFamily: "var(--font-data)", color: "var(--on-slab-2)" }}
                >
                  {c.weight}
                </span>
              </div>
              <p className="mt-2 text-[0.83rem] leading-relaxed" style={{ color: "var(--on-slab-2)" }}>
                {c.method}
              </p>
              <p className="mt-2.5 text-[0.78rem] leading-relaxed" style={{ color: "var(--on-slab-2)", opacity: 0.75 }}>
                {c.guard}
              </p>
            </div>
          ))}

          <div className="slab-card flex flex-col justify-between">
            <div>
              <h3 className="text-[0.98rem] font-medium">Bands</h3>
              <p className="mt-2 text-[0.83rem] leading-relaxed" style={{ color: "var(--on-slab-2)" }}>
                Below 40 a work is low risk and stays out of the queue. 40 to 70 is medium.
                Above 70 is high, and goes to the top of the list.
              </p>
            </div>
            <Link href="/alerts" className="btn btn--solid mt-4 self-start">
              See what is flagged
            </Link>
          </div>
        </div>
      </div>
    </div>

    <div className="mt-12">
      <div className="text-center">
        <h2 className="section-head">What it will not tell you</h2>
        <p className="lede">
          The gaps matter as much as the findings, so they are stated rather than papered
          over.
        </p>
      </div>
      <div className="mt-8 grid gap-3 md:grid-cols-3">
        {LIMITS.map((l) => (
          <div key={l.title} className="card">
            <h3 className="text-[0.98rem] font-medium">{l.title}</h3>
            <p className="mt-2 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
              {l.body}
            </p>
          </div>
        ))}
      </div>
    </div>
    </>
  );
}
