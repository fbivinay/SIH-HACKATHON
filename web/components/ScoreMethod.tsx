import Link from "next/link";

/**
 * How the score is built and what it will not say.
 *
 * The overview, below the first screen: the owner wants the figures to own
 * the opening screen and this to follow it, not to leave the page.
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

// Four limits, four points each (owner's call, 2026-09-21: the four that
// matter most, and no "Read more"). A limit stated in one line reads as a
// disclaimer, and a limit itself has to be checkable. Every point here is
// either a rule in data/scoring.py, an entry in COMPLIANCE_BLIND_SPOTS in
// api/main.py, or the forecast's rule (/api/forecast/late) - none of it is
// written fresh for this page. The rest of the
// blind spots are on Sources, which the lede above the cards says.
const LIMITS = [
  {
    title: "It does not allege wrongdoing",
    points: [
      "A score is a comparison, not a finding: it says a work does not resemble works like it.",
      "Its peers are the works in the same district and the same sector, within one Lok Sabha term.",
      "Each component names the rows it came from, so any flag can be read back to the record and argued with.",
      "What a pattern across an agency or a member shows is reported at that grain, never folded into one work's score.",
    ],
  },
  {
    title: "It invents no fields",
    points: [
      "No progress percentage is published for an MPLADS work, so none is shown.",
      "No beneficiary count is published, so the system cannot say who a work served.",
      "No geo-tag is published, so nothing here can place a work on the ground.",
      "No bill value or invoice is published, so spending is only ever the totals the source gives.",
    ],
  },
  {
    title: "It forecasts only from the record",
    points: [
      "The one forecast - works likely to run late - is each agency's own overdue share, applied to its works due next.",
      "It never enters a work's score: it describes an agency's backlog, not anything wrong with a work.",
      "Delay is days past the completion date the source itself publishes; a work with no schedule scores zero, not high.",
      "No progress milestones are published, so nothing here projects a completion date for any single work.",
    ],
  },
  {
    title: "No model decides alone",
    points: [
      "The score is deterministic and rule-weighted: the same record scores the same way on every run.",
      "No model chooses those weights, and no model output becomes a risk number.",
      "Gemini is asked for a sector only where the keyword rules could not decide one.",
      "It is allowed to answer \u201cOther\u201d, and did so 5,167 times rather than guess - which is why a model that can abstain was used instead of a nearest-match classifier.",
    ],
  },
];

export default function ScoreMethod() {
  return (
    <>
    {/* The second screen, exactly: the slab fills the space between the masthead
        and the ticker, so one page down lands on the whole of it rather than
        three quarters of it with the rest below (owner's call). */}
    <section className="shell score-screen">
      <div className="slab">
        <div className="text-center">
          <h2 className="section-head">What the score is made of</h2>
          <p className="lede">
            Five components, fixed weights, no black box. Every one can be read back to the
            rows it came from.
          </p>
        </div>

        <div className="score-grid mt-9 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
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
            <Link href="/projects" className="btn btn--solid mt-4 self-start">
              See what is flagged
            </Link>
          </div>
        </div>
      </div>
    </section>

    {/* The third screen, the same way: see .limits-screen. */}
    <section className="shell limits-screen">
      {/* One revealable block, so the heading and the lede under it arrive
          together on the way down. The heading alone was marked, and the lede
          sat still while the title rose past it. */}
      <div className="text-center section-intro">
        <h2 className="section-head">What it will not tell you</h2>
        <p className="lede">
          The gaps matter as much as the findings, so they are stated rather than papered
          over. Four more blind spots, the rule book behind every compliance flag and the
          detectors that describe an agency rather than a work are all on{" "}
          <Link href="/provenance" className="link-quiet">
            Sources
          </Link>
          .
        </p>
      </div>
      <div className="limits-grid mt-8 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {LIMITS.map((l) => (
          <div key={l.title} className="card">
            <h3 className="text-[0.98rem] font-medium">{l.title}</h3>
            <ul className="limit-points">
              {l.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
    </>
  );
}
