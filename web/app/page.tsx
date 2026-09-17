import Link from "next/link";
import { api } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";
import CountUp from "@/components/CountUp";
import HeroField from "@/components/HeroField";
import ScoreMethod from "@/components/ScoreMethod";


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

  // The first screen is the hero, the term switcher and the six figures, sized
  // to fill the space between the masthead and the ticker with no slack
  // (.home-fold); the score's components and limits follow below it. The
  // models are on /provenance.
  return (
    <main className="home">
      <div className="home-fold">
      <section className="shell page-head">
        <HeroField />
        {/* The headline alone. The sentence that stood under it - the count,
            and the five things a work is scored on - is what the six figures
            and the sections below the fold say, and it cost the headline the
            room to be read across a hall. */}
        <h1 className="display display--hero">
          Every MPLADS work, checked against its peers.
        </h1>
      </section>

      <section className="shell home-figures">
        {scoringPending && (
          <div className="notice mb-5" role="status">
            <span aria-hidden="true">&#9679;</span>
            <span>
              Scoring is running across all {formatCount(data.total_projects)} works. Risk
              figures fill in when it finishes.
            </span>
          </div>
        )}
        {/* The term switcher sits with the figures it filters rather than in the
            hero, where it cost 66px of the fold and explained nothing. */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          {/* flex-1 min-w-0 so the sentence wraps inside its own column instead of
              pushing the term buttons onto a second row, which cost a whole
              card-row of the fold at 1280. */}
          <p className="flex-1 min-w-0 text-[0.95rem]" style={{ color: "var(--ink-3)" }}>
            {scope.label}
            {scope.note ? ` (${scope.note})` : ""} — figures cover this scope only, matching
            the same view on the source&rsquo;s dashboard.
          </p>
          <nav className="flex flex-none flex-wrap gap-2" aria-label="Lok Sabha term">
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
        </div>
        {/* One panel, six cells, hairlines between: the figures are one set
            for one scope, not six separate cards. The first row is the record,
            the second what the scoring made of it. Vendor payments was a
            seventh and left a hole; the source still serves it. */}
        <div className="figures-panel">
          <div className="figures">
            {stats.map((s) => (
              <div key={s.label} className={`figure${s.tone ? ` figure--${s.tone}` : ""}`}>
                <div className="figure__label">{s.label}</div>
                <div className="figure__value">
                  <CountUp text={String(s.value)} />
                </div>
                <div className="figure__note">{s.note}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      </div>

      <ScoreMethod />
    </main>
  );
}
