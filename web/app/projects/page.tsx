import Link from "next/link";
import { api } from "@/lib/api";
import ProjectFilters from "@/components/ProjectFilters";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel } from "@/lib/format";

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
  const [projects, filterOptions] = await Promise.all([
    api.projects(filters),
    api.filters().catch(() => ({ states: [], risk_levels: [] })),
  ]);

  // Human-readable summary of what's applied, rather than raw "state=Bihar" pairs.
  const applied: string[] = [];
  if (filters.q) applied.push(`matching “${filters.q}”`);
  if (filters.state) applied.push(`in ${filters.state}`);
  if (filters.district) applied.push(`in ${filters.district}`);
  if (filters.risk_level) applied.push(`at ${riskLevelLabel(filters.risk_level)} risk`);

  return (
    <main className="shell py-8">
      <h1 className="display">Works register</h1>
      <p className="lede !mx-0 !max-w-2xl">
        {`Showing ${formatCount(projects.length)} ${projects.length === 1 ? "work" : "works"}${
          applied.length > 0 ? " " + applied.join(", ") : ""
        }, ranked by risk score (highest first).`}{" "}
        Results are capped at 200 — narrow the filters to see more specific works.
      </p>

      <div className="mt-5">
        <ProjectFilters filterOptions={filterOptions} />
      </div>

      <div className="mt-6 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Work</th>
              <th>State</th>
              <th>District</th>
              <th>Agency</th>
              <th className="text-right">Sanctioned</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-[color:var(--muted)] py-6">
                  {applied.length > 0
                    ? "No works match these filters. Try widening or clearing them."
                    : "No works available."}
                </td>
              </tr>
            )}
            {projects.map((p) => (
              <tr key={p.id}>
                <td className="max-w-[26rem]">
                  <Link href={`/projects/${p.id}`} className="link-quiet">
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
                    {p.overall_risk_score !== null ? ` · ${p.overall_risk_score.toFixed(0)}` : ""}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
