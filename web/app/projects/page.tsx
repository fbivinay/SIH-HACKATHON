import Link from "next/link";
import { api } from "@/lib/api";
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
    if (typeof v === "string") filters[k] = v;
  }
  const projects = await api.projects(filters);

  const activeFilters = Object.entries(filters);

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="eyebrow">Works register</div>
      <h1
        className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Projects
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
        Showing {formatCount(projects.length)} of up to 200 works, ranked by risk score
        (highest first).
        {activeFilters.length > 0 && (
          <>
            {" "}
            Filtered by {activeFilters.map(([k, v]) => `${k}=${v}`).join(", ")}.
          </>
        )}
      </p>

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
                  No works match these filters.
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
