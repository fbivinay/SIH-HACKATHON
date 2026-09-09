import Link from "next/link";
import { api } from "@/lib/api";
import type { DetectorFinding } from "@/lib/api";
import { formatCount, formatINR } from "@/lib/format";

const PAGE_SIZE = 40;

function severityClass(severity: number): string {
  if (severity >= 70) return "risk-pill risk-pill--high";
  if (severity >= 40) return "risk-pill risk-pill--medium";
  return "risk-pill risk-pill--low";
}

// Each detector's evidence has its own shape, so each gets its own line rather
// than a generic key/value dump — a reviewer reads "83.6% of payments start
// with 4", not `worst_digit: 4`.
function evidenceLine(f: DetectorFinding): string | null {
  const e = f.evidence as Record<string, number | string | null>;
  const n = (k: string) => (typeof e[k] === "number" ? (e[k] as number) : null);
  switch (f.code) {
    case "D-01": {
      const amount = n("march_amount");
      return amount === null
        ? null
        : `${formatINR(amount)} of ${formatINR(n("total_amount") ?? 0)} paid in March · ${formatCount(
            n("march_payments")
          )} of ${formatCount(n("payments"))} payments · a flat year would be ${e.expected_share_pct}%`;
    }
    case "D-02":
      return `Mean absolute deviation ${e.mad} across ${formatCount(n("payments"))} payments`;
    case "D-03": {
      const idle = n("idle_amount");
      return idle === null
        ? null
        : `${formatINR(idle)} of ${formatINR(
            n("allocated_amount") ?? 0
          )} never committed to a work${e.constituency ? ` — ${e.constituency}` : ""}${
            e.state ? `, ${e.state}` : ""
          }`;
    }
    case "D-04":
      return `${formatCount(n("works_at_amount"))} of ${formatCount(
        n("works")
      )} works at one figure · ${formatCount(n("distinct_amounts"))} distinct amounts in total`;
    default:
      return null;
  }
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const filters: Record<string, string> = {};
  for (const [k, v] of Object.entries(sp)) {
    if (typeof v === "string" && v !== "") filters[k] = v;
  }
  const offset = Number.parseInt(filters.offset ?? "0", 10) || 0;
  filters.offset = String(offset);
  filters.limit = String(PAGE_SIZE);

  const [detectors, page] = await Promise.all([
    api.detectors().catch(() => []),
    api.detectorFindings(filters),
  ]);

  const active = filters.code;
  const pageHref = (next: Record<string, string | undefined>) => {
    const params = new URLSearchParams(filters);
    params.delete("limit");
    params.delete("offset");
    for (const [k, v] of Object.entries(next)) {
      if (v) params.set(k, v);
      else params.delete(k);
    }
    const qs = params.toString();
    return qs ? `/signals?${qs}` : "/signals";
  };

  const shownTo = Math.min(offset + page.findings.length, page.total);

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">Patterns, not works</h1>
        <p className="lede">
          Four detectors that read a whole population — an agency&rsquo;s year of payments,
          an MP&rsquo;s allocation — rather than a single work. None of them moves a
          work&rsquo;s risk score, because a pattern belongs to the group that produced it.
        </p>
      </section>

      <section className="shell">
        <div className="grid gap-3 md:grid-cols-2">
          {detectors.map((d) => {
            const on = active === d.code;
            return (
              <Link
                key={d.code}
                href={pageHref({ code: on ? undefined : d.code })}
                className="card block"
                aria-current={on ? "true" : undefined}
                style={on ? { borderColor: "var(--ink)" } : undefined}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <h2 className="text-[0.98rem] font-medium">
                    <span style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
                      {d.code}
                    </span>{" "}
                    {d.name}
                  </h2>
                  <span
                    className="text-[0.78rem] tabular-nums whitespace-nowrap"
                    style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                  >
                    {formatCount(d.findings)}
                  </span>
                </div>
                <p className="mt-2 text-[0.84rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
                  {d.what}
                </p>
                <p
                  className="mt-2.5 text-[0.79rem] leading-relaxed"
                  style={{ color: "var(--ink-3)" }}
                >
                  <b style={{ fontWeight: 500 }}>What it does not prove.</b> {d.limit}
                </p>
              </Link>
            );
          })}
        </div>

        <div className="mt-6 flex flex-wrap items-baseline justify-between gap-3">
          <p className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
            {page.total === 0
              ? "No findings."
              : `Showing ${formatCount(offset + 1)}–${formatCount(shownTo)} of ${formatCount(
                  page.total
                )}${active ? ` in ${active}` : " across all four"}`}
          </p>
          {active && (
            <Link href={pageHref({ code: undefined })} className="filter-clear">
              Show all detectors
            </Link>
          )}
        </div>

        <div className="mt-2 data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Finding</th>
                <th>Subject</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {page.findings.length === 0 && (
                <tr>
                  <td colSpan={3} className="text-center py-8" style={{ color: "var(--ink-3)" }}>
                    Nothing here yet. Findings are rebuilt on each scoring run.
                  </td>
                </tr>
              )}
              {page.findings.map((f) => {
                const detail = evidenceLine(f);
                return (
                  <tr key={`${f.code}-${f.subject}-${f.ls_term}-${f.period ?? ""}`}>
                    <td className="max-w-[38rem]">
                      <span
                        style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                        className="text-[0.78rem]"
                      >
                        {f.code}
                      </span>{" "}
                      {f.headline}
                      {detail && <div className="cell-sub">{detail}</div>}
                    </td>
                    <td className="max-w-[16rem]">
                      {f.subject_type === "mp"
                        ? ((f.evidence.mp_name as string) ?? f.subject)
                        : f.subject}
                      <div className="cell-sub">
                        {f.ls_term ? `${f.ls_term}th Lok Sabha` : "Term not recorded"}
                        {f.period ? `, FY ${f.period}` : ""}
                      </div>
                    </td>
                    <td>
                      <span className={severityClass(f.severity)}>{f.severity.toFixed(0)}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {page.total > PAGE_SIZE && (
          <nav className="pager" aria-label="Finding pages">
            {offset > 0 ? (
              <Link
                href={`${pageHref({})}${pageHref({}).includes("?") ? "&" : "?"}offset=${Math.max(
                  0,
                  offset - PAGE_SIZE
                )}`}
                className="pager__link"
              >
                ← Previous
              </Link>
            ) : (
              <span className="pager__link is-disabled">← Previous</span>
            )}
            {offset + PAGE_SIZE < page.total ? (
              <Link
                href={`${pageHref({})}${pageHref({}).includes("?") ? "&" : "?"}offset=${
                  offset + PAGE_SIZE
                }`}
                className="pager__link"
              >
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
