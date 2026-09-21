import { api } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";
import HeroField from "@/components/HeroField";
import FiguresBoard from "@/components/FiguresBoard";
import { TERMS } from "@/lib/terms";
import ScoreMethod from "@/components/ScoreMethod";
import WatchScreen from "@/components/WatchScreen";


// Built once and served from the edge, not rendered per request: nothing here
// reads the request. The term a link asks for (?ls_term=) is picked up in the
// browser by FiguresBoard - every scope is already on the page - which is what
// lets this page be static, prefetched in full by every link to it, and open
// instantly. Measured before: 0.35s to first byte, rendered on every visit.
export default async function OverviewPage() {

  // Every scope, not just the one asked for. Three cached reads cost nothing
  // a warm page can feel, and they are what lets the switcher change the
  // figures with no network in the way at all - see components/FiguresBoard.
  // The fourth screen's three reads alongside: none may take the overview
  // down, so each falls back to nothing and its card is simply left out.
  const [all, trends, forecast, compliance] = await Promise.all([
    Promise.all(TERMS.map((t) => api.overview(t.value ? { ls_term: t.value } : {}))),
    api.trends().catch(() => null),
    api.lateForecast().catch(() => null),
    api.compliance().catch(() => null),
  ]);
  const scopes = TERMS.map((t, i) => ({ term: t.value, ...figures(all[i]) }));

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

      {/* Defaults to the 18th, because the source's own dashboard does:
          pooling both terms made our figures look wrong beside it while being
          right. */}
      <FiguresBoard scopes={scopes} initial="18" />
      </div>

      <ScoreMethod />

      {/* The fourth screen: trends, the one forecast, early warnings and the
          compliance rules - the parts of the brief that are about time. */}
      <WatchScreen trends={trends} forecast={forecast} compliance={compliance} />
    </main>
  );
}

// One scope's six figures, formatted here so the client component is only a
// switch and never a second place where money or counts are formatted.
function figures(data: Awaited<ReturnType<typeof api.overview>>) {
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

  return {
    stats,
    pendingNote: scoringPending
      ? `Scoring is running across all ${formatCount(data.total_projects)} works. Risk figures fill in when it finishes.`
      : null,
  };
}
