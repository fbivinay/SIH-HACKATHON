import Link from "next/link";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/api";
import ProjectFilters from "@/components/ProjectFilters";
import ReviewActions from "@/components/ReviewActions";
import ReviewerName from "@/components/ReviewerName";
import RiskBar from "@/components/RiskBar";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";

// Each row carries its full evidence, which is the point of the page and also
// about 280px. Fifty of them was a 14,000px scroll.
const PAGE_SIZE = 25;

// Below 40 a work is LOW (RISK_LEVEL_THRESHOLDS in data/scoring.py) and there
// is nothing to triage, so the queue starts there rather than at every work.
const DEFAULT_MIN_SCORE = "40";

const STATUS_LABELS: Record<string, string> = {
  pending: "Not yet reviewed",
  escalated: "Escalated",
  verified: "Verified",
  dismissed: "Dismissed",
};

function reviewedLine(a: Alert): string | null {
  if (a.review_status === "pending") return null;
  const who = a.review_reviewer?.trim() || "an unnamed reviewer";
  const when = a.review_updated_at
    ? new Date(a.review_updated_at).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;
  return `${STATUS_LABELS[a.review_status]} by ${who}${when ? ` on ${when}` : ""}`;
}

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const filters: Record<string, string> = {};
  for (const [k, v] of Object.entries(sp)) {
    if (typeof v === "string" && v !== "") filters[k] = v;
  }
  filters.min_score ??= DEFAULT_MIN_SCORE;
  filters.limit = String(PAGE_SIZE);

  const offset = Number.parseInt(filters.offset ?? "0", 10) || 0;
  filters.offset = String(offset);

  const [page, filterOptions, summary] = await Promise.all([
    api.alerts(filters),
    api.filters().catch(() => ({ states: [], risk_levels: [] })),
    // The same filters the table uses, minus paging - the tiles describe the
    // queue below them, not the whole country.
    api
      .alertSummary(
        Object.fromEntries(
          Object.entries(filters).filter(([k]) => k !== "limit" && k !== "offset")
        )
      )
      .catch(() => null),
  ]);

  const tiles = summary
    ? [
        {
          label: "Awaiting review",
          value: formatCount(summary.pending),
          note: `${formatINR(summary.pending_sanctioned_amount)} sanctioned`,
          tone: "high" as const,
        },
        {
          label: "Escalated",
          value: formatCount(summary.escalated),
          note: "Sent for physical verification",
          tone: "medium" as const,
        },
        {
          label: "Verified",
          value: formatCount(summary.verified),
          note: "Checked, found in order",
          tone: "low" as const,
        },
        {
          label: "Dismissed",
          value: formatCount(summary.dismissed),
          note: "Flag did not hold",
          tone: "neutral" as const,
        },
        {
          label: "In scope",
          value: formatCount(summary.in_scope),
          note: `Score ${filters.min_score} and above — ${formatCount(
            summary.high
          )} high, ${formatCount(summary.medium)} medium`,
          tone: "accent" as const,
        },
      ]
    : [];

  // Scores are NULL until scoring.py has run over a fresh load, and the queue's
  // min_score filter excludes NULLs - so an unscored database produces an empty
  // page that looks broken. Say what is actually happening instead.
  const scoringPending = summary !== null && summary.in_scope === 0 && page.total === 0;

  const shownTo = Math.min(offset + page.alerts.length, page.total);
  const prevOffset = Math.max(0, offset - PAGE_SIZE);
  const nextOffset = offset + PAGE_SIZE;
  const pageHref = (o: number) => {
    const params = new URLSearchParams(filters);
    params.delete("limit");
    if (o > 0) params.set("offset", String(o));
    else params.delete("offset");
    const qs = params.toString();
    return qs ? `/alerts?${qs}` : "/alerts";
  };

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">What to verify next</h1>
        <p className="lede">
          Works scoring above the review threshold, highest first, each carrying the record
          that flagged it. A decision here says what a reviewer concluded. It never moves
          the score.
        </p>
      </section>

      <section className="shell">

      {scoringPending && (
        <div className="notice mb-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            No work has a risk score yet — the scoring pass has not finished since the
            last data load. The queue fills in as soon as it does.
          </span>
        </div>
      )}

      {tiles.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {tiles.map((t) => (
            <div key={t.label} className={`stat-card stat-card--${t.tone}`}>
              <div className="stat-card__label">{t.label}</div>
              <div className="stat-card__value">{t.value}</div>
              <div className="stat-card__note">{t.note}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5">
        <ProjectFilters filterOptions={filterOptions} statuses={Object.keys(STATUS_LABELS)} />
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <ReviewerName />
      </div>

      <p className="mt-4 text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
        {page.total === 0
          ? "No works match these filters."
          : `Showing ${formatCount(offset + 1)}–${formatCount(shownTo)} of ${formatCount(
              page.total
            )}`}
      </p>

      <div className="mt-2 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Work</th>
              <th>Where</th>
              <th className="num">Sanctioned</th>
              <th>Risk</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {page.alerts.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8" style={{ color: "var(--ink-3)" }}>
                  Nothing in the queue for these filters.
                </td>
              </tr>
            )}
            {page.alerts.map((a, i) => {
              const reviewed = reviewedLine(a);
              return (
                <tr key={a.id} className={a.review_status !== "pending" ? "is-reviewed" : undefined}>
                  <td className="rank">{formatCount(offset + i + 1)}</td>
                  <td className="max-w-[30rem]">
                    <Link
                      href={`/projects/${encodeURIComponent(a.work_key ?? String(a.id))}`}
                      className="link-quiet"
                    >
                      {a.work_name}
                    </Link>
                    <div className="cell-sub">
                      {a.sector ? `${a.sector} — ` : ""}
                      {a.implementing_agency}
                    </div>
                    {a.flagged_reasons.length > 0 && (
                      <ul className="reason-list">
                        {a.flagged_reasons.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td className="whitespace-nowrap">
                    {a.district}
                    <div className="cell-sub">{a.state}</div>
                  </td>
                  <td className="num">{formatINR(a.sanctioned_amount)}</td>
                  <td className="min-w-[11rem]">
                    <span className={riskLevelClass(a.risk_level)}>
                      {riskLevelLabel(a.risk_level)}
                      {a.overall_risk_score !== null
                        ? ` ${a.overall_risk_score.toFixed(0)}`
                        : ""}
                    </span>
                    <div className="mt-1.5">
                      <RiskBar p={a} />
                    </div>
                  </td>
                  <td className="min-w-[15rem]">
                    <ReviewActions workKey={a.work_key} current={a.review_status} />
                    {reviewed && <div className="cell-sub">{reviewed}</div>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {page.total > PAGE_SIZE && (
        <nav className="pager" aria-label="Queue pages">
          {offset > 0 ? (
            <Link href={pageHref(prevOffset)} className="pager__link">
              ← Previous
            </Link>
          ) : (
            <span className="pager__link is-disabled">← Previous</span>
          )}
          {nextOffset < page.total ? (
            <Link href={pageHref(nextOffset)} className="pager__link">
              Next →
            </Link>
          ) : (
            <span className="pager__link is-disabled">Next →</span>
          )}
        </nav>
      )}
      </section>
    </main>
  );
}
