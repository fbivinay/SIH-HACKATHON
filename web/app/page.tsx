import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

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
      "Four stated rules: spend beyond the sanction, a recommended work with no schedule, a completed work with no completion date, and a completed work with no photograph.",
    guard: "Each breach names the rule it breaks.",
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
    title: "The model never decides",
    body: "Scoring is deterministic and rule-weighted. Nothing an LLM writes can move a score, and every flag names the record it came from.",
  },
];

const TERMS = [
  { value: "18", label: "18th Lok Sabha", note: "2024–29" },
  { value: "17", label: "17th Lok Sabha", note: "2019–24" },
  { value: "", label: "Both terms", note: "everything on record" },
];

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  // Defaults to the 18th, because the source's own dashboard does. Pooling
  // both terms made our figures look wrong beside it while being right.
  const rawTerm = typeof sp.ls_term === "string" ? sp.ls_term : "18";
  const term = ["17", "18", ""].includes(rawTerm) ? rawTerm : "18";
  const scope = TERMS.find((t) => t.value === term) ?? TERMS[0];

  const data = await api.overview(term ? { ls_term: term } : {});

  // Risk counts are legitimately 0 (COUNT(*) FILTER, never null) until scoring
  // has run. Say so rather than presenting a wall of zeros as "nothing flagged".
  const scoringPending =
    data.total_projects > 0 &&
    data.high_risk_count === 0 &&
    data.delayed_count === 0 &&
    data.anomaly_count === 0;

  const dash = "—";
  const stats = [
    {
      label: "Works tracked",
      value: formatCount(data.total_projects),
      note: `${formatCount(data.completed_count)} completed, ${formatCount(
        data.pending_count
      )} still pending`,
    },
    {
      label: "Allocated to MPs",
      value: formatINR(data.allocated_total),
      note: `Across ${formatCount(data.mp_count)} members`,
    },
    {
      // The source's dashboard calls this "Total Expenditure". Naming it
      // vendor payments keeps it distinct from the value of completed works,
      // which is a different figure entirely.
      label: "Vendor payments",
      value: formatINR(data.vendor_payments),
      note: `${formatCount(data.payment_count)} transactions on record`,
    },
    {
      label: "Completed works value",
      value: formatINR(data.completed_works_value),
      note: "What finished works finally cost",
    },
    {
      label: "High risk",
      value: scoringPending ? dash : formatCount(data.high_risk_count),
      note: scoringPending ? "Waiting on scoring" : "Score 70 and above",
      tone: "high" as const,
    },
    {
      label: "Running late",
      value: scoringPending ? dash : formatCount(data.delayed_count),
      note: scoringPending ? "Waiting on scoring" : "More than 60 days past due",
      tone: "medium" as const,
    },
    {
      label: "Worth a look",
      value: scoringPending ? dash : formatCount(data.anomaly_count),
      note: scoringPending ? "Waiting on scoring" : "Score 40 and above",
    },
  ];

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display display--hero">
          Every MPLADS work,
          <br />
          checked against its peers.
        </h1>
        <p className="lede">
          {formatCount(data.total_projects)} works across every district in India, scored on
          cost, delay, duplication, the implementing agency and the scheme&rsquo;s own rules.
          The ones that do not fit come out ranked, with the record that flagged them.
        </p>

        <nav className="mt-6 flex flex-wrap justify-center gap-2" aria-label="Lok Sabha term">
          {TERMS.map((t) => (
            <Link
              key={t.value || "all"}
              href={t.value ? `/?ls_term=${t.value}` : "/?ls_term="}
              className="review-btn"
              aria-current={term === t.value ? "true" : undefined}
              style={term === t.value ? { color: "var(--ink)", borderColor: "var(--ink)" } : undefined}
            >
              {t.label}
            </Link>
          ))}
        </nav>
        <div className="mt-8 flex flex-wrap justify-center gap-2.5">
          <Link href="/alerts" className="btn btn--solid">
            Open the verification queue
          </Link>
          <Link href="/projects" className="btn btn--quiet">
            Browse every work
          </Link>
        </div>
      </section>

      <section className="shell">
        {scoringPending && (
          <div className="notice mb-5" role="status">
            <span aria-hidden="true">&#9679;</span>
            <span>
              Scoring is running across all {formatCount(data.total_projects)} works. Risk
              figures fill in when it finishes.
            </span>
          </div>
        )}
        <p className="mb-3 text-[0.8rem]" style={{ color: "var(--ink-3)" }}>
          {scope.label}
          {scope.note ? ` (${scope.note})` : ""} — figures below cover this scope only, so
          they line up with the same view on the source&rsquo;s own dashboard.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {stats.map((s) => (
            <div key={s.label} className={`stat-card${s.tone ? ` stat-card--${s.tone}` : ""}`}>
              <div className="stat-card__label">{s.label}</div>
              <div className="stat-card__value">{s.value}</div>
              <div className="stat-card__note">{s.note}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="shell mt-6">
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
      </section>

      <section className="shell mt-6">
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
      </section>
    </main>
  );
}
