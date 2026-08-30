import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { formatCount, formatINR, riskLevelClass, riskLevelLabel, workStatusLabel } from "@/lib/format";

function RiskMeter({ label, value }: { label: string; value: number | null }) {
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value));
  const color =
    value === null
      ? "var(--risk-pending)"
      : value >= 70
        ? "var(--risk-high)"
        : value >= 40
          ? "var(--risk-medium)"
          : "var(--risk-low)";
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs mb-1">
        <span className="font-medium text-[color:var(--ink)]">{label}</span>
        <span
          className="font-data tabular-nums"
          style={{ fontFamily: "var(--font-data)", color: value === null ? "var(--muted)" : color }}
        >
          {value === null ? "—" : value.toFixed(0)}
        </span>
      </div>
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ background: "var(--paper)", border: "1px solid var(--line)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value === null ? 0 : pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const projectId = Number(id);
  if (!Number.isInteger(projectId)) notFound();

  let p;
  try {
    p = await api.project(projectId);
  } catch {
    notFound();
  }

  const components = [
    { label: "Cost", value: p.cost_risk },
    { label: "Delay", value: p.delay_risk },
    { label: "Duplicate", value: p.duplicate_risk },
    { label: "Agency", value: p.agency_risk },
    { label: "Compliance", value: p.compliance_risk },
  ];

  const scorePending = p.overall_risk_score === null;
  const hasReasons = p.flagged_reasons && p.flagged_reasons.length > 0;

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <Link href="/projects" className="text-xs link-quiet">
        &larr; Back to projects
      </Link>

      <div className="eyebrow mt-4">
        {p.category} · Work #{p.id}
      </div>
      <h1
        className="mt-1 text-xl sm:text-2xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {p.work_name}
      </h1>
      <p className="mt-1.5 text-sm text-[color:var(--muted)]">
        {p.state} / {p.district} — {p.implementing_agency}
        {p.mp_name && (
          <>
            {" "}
            &middot; {p.mp_name}
            {p.constituency ? ` (${p.constituency})` : ""}
          </>
        )}
      </p>
      {p.description && (
        <p className="mt-3 text-sm text-[color:var(--ink)]/80 max-w-2xl">{p.description}</p>
      )}

      {/* Score hero */}
      <div className="stat-card stat-card--neutral mt-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="stat-card__label">Overall Risk Score</div>
          <div className="stat-card__value" style={{ fontSize: "2.5rem" }}>
            {scorePending ? "—" : p.overall_risk_score!.toFixed(0)}
            <span className="text-base font-normal text-[color:var(--muted)]">/100</span>
          </div>
          <div className="stat-card__note">
            {scorePending
              ? "Risk scoring for this work has not run yet."
              : "overall_risk_score, blended from the five components below."}
          </div>
        </div>
        <span className={riskLevelClass(p.risk_level)} style={{ fontSize: "0.8rem", padding: "0.35rem 0.8rem" }}>
          {riskLevelLabel(p.risk_level)}
        </span>
      </div>

      {/* Component breakdown */}
      <section className="mt-6">
        <h2 className="text-sm font-semibold mb-3" style={{ fontFamily: "var(--font-display)" }}>
          Risk components
        </h2>
        <div className="stat-card grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
          {components.map((c) => (
            <RiskMeter key={c.label} label={c.label} value={c.value} />
          ))}
        </div>
      </section>

      {/* Supporting facts */}
      <section className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="stat-card stat-card--accent">
          <div className="stat-card__label">Sanctioned</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {formatINR(p.sanctioned_amount)}
          </div>
        </div>
        <div className="stat-card stat-card--medium">
          <div className="stat-card__label">Delay</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {p.delay_days === null ? "—" : `${formatCount(p.delay_days)}d`}
          </div>
        </div>
        <div className="stat-card stat-card--medium">
          <div className="stat-card__label">Cost Deviation</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {p.cost_deviation_pct === null ? "—" : `${p.cost_deviation_pct.toFixed(0)}%`}
          </div>
        </div>
        <div className="stat-card stat-card--neutral">
          <div className="stat-card__label">Work Status</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {workStatusLabel(p.work_status)}
          </div>
        </div>
      </section>

      {/* Why flagged — the core of this screen */}
      <section className="mt-6">
        <h2 className="text-sm font-semibold mb-3" style={{ fontFamily: "var(--font-display)" }}>
          Why was this flagged?
        </h2>
        <div className="stat-card">
          {scorePending ? (
            <p className="text-sm text-[color:var(--muted)]">
              Risk indicators are not available yet — this work has not been through the
              scoring pass.
            </p>
          ) : hasReasons ? (
            <ul className="list-disc pl-5 space-y-1.5 text-sm text-[color:var(--ink)]">
              {p.flagged_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm" style={{ color: "var(--risk-low)" }}>
              No risk indicators flagged for this work.
            </p>
          )}
        </div>
      </section>

      {p.similar_work_id && (
        <p className="mt-6 text-sm">
          Similar to{" "}
          <Link className="link-quiet" href={`/projects/${p.similar_work_id}`}>
            work #{p.similar_work_id}
          </Link>
        </p>
      )}
    </main>
  );
}
