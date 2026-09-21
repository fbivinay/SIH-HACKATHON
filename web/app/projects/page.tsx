import { Suspense } from "react";
import Link from "next/link";
import { api, alertsExportUrl } from "@/lib/api";
import Pager from "@/components/Pager";
import ProjectFilters from "@/components/ProjectFilters";
import ReviewActions from "@/components/ReviewActions";
import RiskBar from "@/components/RiskBar";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";
import CountUp from "@/components/CountUp";

export const metadata = { title: "Projects" };

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

/**
 * The queue.
 *
 * The shell - the filter bar and the download - is rendered from nothing but
 * the URL, so it is on screen immediately; the tiles and the table each wait
 * on their own request behind a <Suspense>. Before this the page awaited all
 * three before a byte of HTML left the server, which on a fresh filter was
 * two to six seconds of the previous page (measured locally 2026-09-20, where
 * a round trip to Neon is ~220ms and a cold count ~500ms).
 */
export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const filters: Record<string, string> = {};
  for (const [k, v] of Object.entries(sp)) {
    if (typeof v === "string" && v !== "") filters[k] = v;
  }
  // The URL as the reader wrote it, before the scope rules below rewrite it -
  // what a tile link keeps when it changes only the review status.
  const asWritten = new URLSearchParams(filters);
  asWritten.delete("offset");
  // One page for the whole record now that Works is gone, so the band control
  // is also the scope: nothing chosen is the review queue (score 40 and above),
  // "ALL" is every work, and a named band is that band whatever its score - a
  // LOW work sits below 40, so the queue's floor would otherwise hide it.
  const allWorks = filters.risk_level === "ALL";
  if (allWorks) delete filters.risk_level;
  else if (!filters.risk_level) filters.min_score ??= DEFAULT_MIN_SCORE;
  filters.limit = String(PAGE_SIZE);

  const offset = Number.parseInt(filters.offset ?? "0", 10) || 0;
  filters.offset = String(offset);

  // Memoised on the API for ten minutes and ~5ms warm, so the shell does not
  // wait on anything that moves.
  const filterOptions = await api.filters().catch(() => ({ states: [], risk_levels: [] }));

  // Both Suspense boundaries are keyed on the filters: a new filter set is a
  // new request, and without the key React would keep showing the old one
  // rather than its skeleton on a hard load.
  const key = new URLSearchParams(filters).toString();

  return (
    <main>
      {/* No visible heading: the owner wanted the queue to start at the top of
          the page. The h1 stays for screen readers and the document outline. */}
      <h1 className="sr-only">Projects — what to verify next</h1>

      <section className="shell pt-8 queue-screen">
        <Suspense key={`t-${key}`} fallback={<TilesSkeleton />}>
          <QueueTiles filters={filters} allWorks={allWorks} asWritten={asWritten.toString()} />
        </Suspense>

        <div className="mt-5">
          <ProjectFilters filterOptions={filterOptions} statuses={Object.keys(STATUS_LABELS)} />
        </div>

        {/* The brief asks this platform to reduce manual monitoring effort. An
            officer who narrows the queue to their district and finds work to
            inspect needs to hand that list to whoever inspects it. */}
        <div className="mt-4 flex justify-end">
          <a href={alertsExportUrl(filters)} className="btn btn--solid" download>
            Download this queue (CSV)
          </a>
        </div>

        <Suspense key={`q-${key}`} fallback={<TableSkeleton />}>
          <QueueTable filters={filters} offset={offset} />
        </Suspense>
      </section>
    </main>
  );
}

/** Five ghost tiles and a ghost table, in the shape of what is coming. */
function TilesSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3" aria-hidden="true">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="stat-card skel-card" />
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="mt-2 skel-table" role="status" aria-label="Loading the queue">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="skel-row" />
      ))}
    </div>
  );
}

async function QueueTiles({
  filters,
  allWorks,
  asWritten,
}: {
  filters: Record<string, string>;
  allWorks: boolean;
  asWritten: string;
}) {
  // The same filters the table uses, minus paging - the tiles describe the
  // queue below them, not the whole country.
  const summary = await api
    .alertSummary({
      ...Object.fromEntries(
        // Nor the review status: the tiles ARE the status filter, and
        // counting under it would read "Escalated 3" beside "Verified 0"
        // the moment Escalated was pressed.
        Object.entries(filters).filter(
          ([k]) => k !== "limit" && k !== "offset" && k !== "status"
        )
      ),
      // The summary endpoint defaults its floor to 40, so outside the queue
      // the tiles would still count only the queue: "All works" read
      // 48,296 in scope and "Low" read 0. Say 0 explicitly there.
      min_score: filters.min_score ?? "0",
    })
    .catch(() => null);

  if (!summary) return null;

  const tiles = [
        {
          label: "Awaiting review",
          status: "pending",
          value: formatCount(summary.pending),
          note: `${formatINR(summary.pending_sanctioned_amount)} sanctioned`,
          tone: "high" as const,
        },
        {
          label: "Escalated",
          status: "escalated",
          value: formatCount(summary.escalated),
          note: "Sent for physical verification",
          tone: "medium" as const,
        },
        {
          label: "Verified",
          status: "verified",
          value: formatCount(summary.verified),
          note: "Checked, found in order",
          tone: "low" as const,
        },
        {
          label: "Dismissed",
          status: "dismissed",
          value: formatCount(summary.dismissed),
          note: "Flag did not hold",
          tone: "neutral" as const,
        },
        {
          label: "In scope",
          status: "",
          value: formatCount(summary.in_scope),
          note: filters.min_score
            ? `Score ${filters.min_score} and above — ${formatCount(summary.high)} high, ${formatCount(
                summary.medium
              )} medium`
            : allWorks
              ? `Every work — ${formatCount(summary.high)} high, ${formatCount(
                  summary.medium
                )} medium, ${formatCount(summary.in_scope - summary.high - summary.medium)} low`
              : `Every ${riskLevelLabel(filters.risk_level ?? "").toLowerCase()} work`,
      tone: "accent" as const,
    },
  ];

  return (
    <>
      {/* Scores are NULL until scoring.py has run over a fresh load, and the
          queue's min_score filter excludes NULLs - so an unscored database
          produces an empty page that looks broken. Say what is happening. */}
      {summary.in_scope === 0 && (
        <div className="notice mb-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            No work has a risk score yet — the scoring pass has not finished since the
            last data load. The queue fills in as soon as it does.
          </span>
        </div>
      )}
      {/* Each tile is the filter it counts: press "Escalated" and the table
          lists the escalated works, under every other filter already set, so
          the number on the tile and the rows below it are the same set.
          Pressing the tile that is already on takes it off, like a decision
          button; "In scope" is every status. */}
      <nav className="grid grid-cols-2 lg:grid-cols-5 gap-3" aria-label="Filter by review status">
        {tiles.map((t) => {
          const on = (filters.status ?? "") === t.status;
          const next = new URLSearchParams(asWritten);
          if (t.status && !on) next.set("status", t.status);
          else next.delete("status");
          const qs = next.toString();
          return (
            <Link
              key={t.label}
              href={qs ? `/projects?${qs}` : "/projects"}
              scroll={false}
              aria-current={on ? "true" : undefined}
              className={`stat-card stat-card--${t.tone} stat-card--link`}
            >
              <div className="stat-card__label">{t.label}</div>
              <div className="stat-card__value">
                <CountUp text={String(t.value)} />
              </div>
              <div className="stat-card__note">{t.note}</div>
            </Link>
          );
        })}
      </nav>
    </>
  );
}

async function QueueTable({
  filters,
  offset,
}: {
  filters: Record<string, string>;
  offset: number;
}) {
  const page = await api.alerts(filters);

  // Both desks send an officer here with the queue silently scoped to their
  // place, and nothing on the page said so - now that the tiles count the
  // filtered set, an unexplained 261 is more confusing, not less.
  const scope: string[] = [];
  if (filters.q) scope.push(`matching \u201c${filters.q}\u201d`);
  if (filters.district) scope.push(`in ${filters.district}`);
  if (filters.state) scope.push(`in ${filters.state}`);
  if (filters.sector) scope.push(`in ${filters.sector}`);
  if (filters.risk_level) scope.push(`at ${filters.risk_level} risk`);
  if (filters.mp_id) scope.push("recommended by one member");
  if (filters.compliance === "breach") scope.push("that breach a compliance rule");

  const pageHref = (o: number) => {
    const params = new URLSearchParams(filters);
    params.delete("limit");
    if (o > 0) params.set("offset", String(o));
    else params.delete("offset");
    const qs = params.toString();
    return qs ? `/projects?${qs}` : "/projects";
  };

  return (
    <>
      {/* The range line above the table went on the owner's call; the pager
          under it still says where the reader is. An empty result still has
          to say so, or a blank table reads as a broken one. */}
      {page.total === 0 && (
        <p className="mt-4 text-[0.85rem]" style={{ color: "var(--ink-2)" }}>
          No works match these filters.
        </p>
      )}

      {scope.length > 0 && (
        <p className="mt-4 text-[0.82rem]" style={{ color: "var(--ink-2)" }}>
          Showing works {scope.join(", ")}.{" "}
          <Link href="/projects" className="link-quiet">
            Clear and see the whole queue
          </Link>
        </p>
      )}

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
              return (
                <tr
                  key={a.id}
                  className={`workrow${a.review_status !== "pending" ? " is-reviewed" : ""}`}
                >
                  <td className="rank">{formatCount(offset + i + 1)}</td>
                  {/* The whole row opens the work, not only its name - the
                      reasons, the place and the risk bar are all what a
                      reader is looking at when they decide to open it. Same
                      layer trick as a state card: one real link, drawing an
                      invisible sheet over the row. */}
                  <td className="max-w-[30rem] workcell">
                    <Link
                      href={`/projects/${encodeURIComponent(a.work_key ?? String(a.id))}`}
                      className="link-quiet workcell__open"
                    >
                      {a.work_name}
                    </Link>
                    <div className="cell-sub cell-sub--strong">
                      {a.sector ? `${a.sector} — ` : ""}
                      {a.implementing_agency}
                    </div>
                    {/* Two reasons, then the rest behind "Read more", so a
                        row stays the height of a row and still says everything
                        it has to say. A <details>, like the limits below the
                        overview: it opens with no JavaScript, the browser's own
                        search finds what is inside it, and it prints. */}
                    {a.flagged_reasons.length > 0 && (
                      <>
                        <ul className="reason-list">
                          {a.flagged_reasons.slice(0, 2).map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                        {a.flagged_reasons.length > 2 && (
                          <details className="reason-more workcell__above">
                            <summary>
                              <span className="reason-more__open">
                                Read more ({a.flagged_reasons.length - 2} more)
                              </span>
                              <span className="reason-more__close">Show less</span>
                            </summary>
                            <ul className="reason-list">
                              {a.flagged_reasons.slice(2).map((r) => (
                                <li key={r}>{r}</li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </>
                    )}
                  </td>
                  <td className="whitespace-nowrap">
                    <Link
                      href={`/district/${encodeURIComponent(a.state)}/${encodeURIComponent(
                        a.district
                      )}`}
                      className="link-quiet workcell__above"
                    >
                      {a.district}
                    </Link>
                    <div className="cell-sub">
                      <Link
                        href={`/state/${encodeURIComponent(a.state)}`}
                        className="link-quiet workcell__above"
                      >
                        {a.state}
                      </Link>
                    </div>
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
                  <td className="min-w-[15rem] workcell__above">
                    <ReviewActions workKey={a.work_key} current={a.review_status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {page.total > PAGE_SIZE && (
        <Pager
          offset={offset}
          pageSize={PAGE_SIZE}
          shown={page.alerts.length}
          total={page.total}
          hrefFor={pageHref}
          label="Queue pages"
          noun=""
        />
      )}
    </>
  );
}
