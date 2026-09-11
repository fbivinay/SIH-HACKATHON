import Link from "next/link";
import { api } from "@/lib/api";
import ProjectFilters from "@/components/ProjectFilters";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";
import CountUp from "@/components/CountUp";
import Pager from "@/components/Pager";

const PAGE_SIZE = 50;

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  // api.projects() takes Record<string, string> — flatten and drop undefined/array values.
  const filters: Record<string, string> = {};
  for (const [k, v] of Object.entries(sp)) {
    if (typeof v === "string" && v !== "") filters[k] = v;
  }

  // Fetch in parallel; a filter-options failure must not blank the whole page,
  // so fall back to an empty option set and still render the table.
  const offset = Math.max(0, Number.parseInt(filters.offset ?? "0", 10) || 0);
  filters.offset = String(offset);
  filters.limit = String(PAGE_SIZE);

  const [page, filterOptions] = await Promise.all([
    api.projects(filters),
    api.filters().catch(() => ({ states: [], risk_levels: [] })),
  ]);

  // Human-readable summary of what's applied, rather than raw "state=Bihar" pairs.
  const applied: string[] = [];
  if (filters.q) applied.push(`matching “${filters.q}”`);
  if (filters.state) applied.push(`in ${filters.state}`);
  if (filters.district) applied.push(`in ${filters.district}`);
  if (filters.risk_level) applied.push(`at ${riskLevelLabel(filters.risk_level)} risk`);

  const pageHref = (next: number) => {
    const params = new URLSearchParams(filters);
    params.delete("limit");
    if (next > 0) params.set("offset", String(next));
    else params.delete("offset");
    const qs = params.toString();
    return qs ? `/projects?${qs}` : "/projects";
  };

  return (
    <main className="shell py-8">
      <h1 className="display">Works register</h1>
      <p className="lede !mx-0 !max-w-2xl">
        {page.total === 0
          ? `No works${applied.length > 0 ? " " + applied.join(", ") : ""}.`
          : `${formatCount(offset + 1)}–${formatCount(
              Math.min(offset + page.projects.length, page.total)
            )} of ${formatCount(page.total)} works${
              applied.length > 0 ? " " + applied.join(", ") : ""
            }, ranked by risk score (highest first).`}
      </p>

      <div className="mt-5">
        <ProjectFilters filterOptions={filterOptions} />
      </div>

      {/* Every page carries live figures, not only the overview: a register
          that opens straight into a table gives a reader no sense of scale. */}
      <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Works in this view", value: formatCount(page.total), note: applied.length ? applied.join(", ") : "Every work on record" },
          { label: "Shown here", value: formatCount(page.projects.length), note: `Page ${Math.floor(offset / PAGE_SIZE) + 1}` },
          { label: "Sanctioned on this page", value: formatINR(page.projects.reduce((t, x) => t + (x.sanctioned_amount ?? 0), 0)), note: "Sum of the rows below" },
          { label: "High risk here", value: formatCount(page.projects.filter((x) => x.risk_level === "HIGH").length), note: "Score 70 and above", tone: "high" },
        ].map((c) => (
          <div key={c.label} className={`stat-card${c.tone ? ` stat-card--${c.tone}` : ""}`}>
            <div className="stat-card__label">{c.label}</div>
            <div className="stat-card__value">
              <CountUp text={String(c.value)} />
            </div>
            <div className="stat-card__note">{c.note}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Work</th>
              <th>State</th>
              <th>District</th>
              <th>Agency</th>
              <th className="num">Sanctioned</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {page.projects.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-[color:var(--muted)] py-6">
                  {applied.length > 0
                    ? "No works match these filters. Try widening or clearing them."
                    : "No works available."}
                </td>
              </tr>
            )}
            {page.projects.map((p) => (
              <tr key={p.id}>
                <td className="max-w-[26rem]">
                  <Link href={`/projects/${encodeURIComponent(p.work_key ?? String(p.id))}`} className="link-quiet">
                    {p.work_name}
                  </Link>
                </td>
                <td>{p.state}</td>
                <td>{p.district}</td>
                <td className="max-w-[16rem] truncate">{p.implementing_agency}</td>
                <td className="num">{formatINR(p.sanctioned_amount)}</td>
                <td>
                  <span className={riskLevelClass(p.risk_level)}>
                    {riskLevelLabel(p.risk_level)}
                    {p.overall_risk_score !== null ? ` ${p.overall_risk_score.toFixed(0)}` : ""}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {page.total > PAGE_SIZE && (
        <Pager
          offset={offset}
          pageSize={PAGE_SIZE}
          shown={page.projects.length}
          total={page.total}
          hrefFor={pageHref}
          label="Register pages"
        />
      )}
    </main>
  );
}
