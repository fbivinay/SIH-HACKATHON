import { api } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

export default async function OverviewPage() {
  const data = await api.overview();

  // Risk-derived counts are legitimately 0 (not null — COUNT(*) FILTER) until the
  // scoring pass has run across all works. Surface that instead of letting a
  // dashboard full of zeros read as "nothing flagged."
  const scoringPending =
    data.total_projects > 0 &&
    data.high_risk_count === 0 &&
    data.delayed_count === 0 &&
    data.anomaly_count === 0;

  const cards: Array<{
    label: string;
    value: string;
    note?: string;
    tone: "neutral" | "accent" | "low" | "medium" | "high";
  }> = [
    {
      label: "Total Works Tracked",
      value: formatCount(data.total_projects),
      note: "Recommended + completed",
      tone: "neutral",
    },
    {
      label: "Total Expenditure",
      value: formatINR(data.total_expenditure),
      note: `₹${data.total_expenditure.toLocaleString("en-IN")}`,
      tone: "accent",
    },
    {
      label: "High-Risk Works",
      value: scoringPending ? "—" : formatCount(data.high_risk_count),
      note: scoringPending ? "Pending scoring" : "risk_level = HIGH",
      tone: "high",
    },
    {
      label: "Delayed Works",
      value: scoringPending ? "—" : formatCount(data.delayed_count),
      note: scoringPending ? "Pending scoring" : "> 60 days behind schedule",
      tone: "medium",
    },
    {
      label: "Anomalies Flagged",
      value: scoringPending ? "—" : formatCount(data.anomaly_count),
      note: scoringPending ? "Pending scoring" : "overall_risk_score > 40",
      tone: "accent",
    },
  ];

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="eyebrow">Dataset snapshot</div>
      <h1
        className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Programme Overview
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
        Live figures from {formatCount(data.total_projects)} MPLADS works recorded across
        India&rsquo;s states and districts.
      </p>

      {scoringPending && (
        <div className="notice mt-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            Risk scoring is running across all {formatCount(data.total_projects)} works.
            High-risk, delay, and anomaly counts will populate once it completes — figures
            below show &ldquo;&mdash;&rdquo; until then.
          </span>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {cards.map((c) => (
          <div key={c.label} className={`stat-card stat-card--${c.tone}`}>
            <div className="stat-card__label">{c.label}</div>
            <div className="stat-card__value">{c.value}</div>
            {c.note && <div className="stat-card__note">{c.note}</div>}
          </div>
        ))}
      </div>
    </main>
  );
}
