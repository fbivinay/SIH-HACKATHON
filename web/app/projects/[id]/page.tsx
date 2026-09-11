import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import ReviewTrail from "@/components/ReviewTrail";
import {
  formatCount,
  formatINR,
  isNearDuplicate,
  riskLevelClass,
  riskLevelLabel,
  workStatusLabel,
} from "@/lib/format";

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
  // The segment is either a serial id or a work_key. Both resolve here, so a
  // link shared today still opens tomorrow: the loader reassigns every id on
  // each nightly refresh, and work_key is what does not move.
  const decoded = decodeURIComponent(id);
  const isSerial = /^\d+$/.test(decoded);

  let p;
  try {
    p = isSerial ? await api.project(Number(decoded)) : await api.projectByKey(decoded);
  } catch {
    notFound();
  }

  const components = [
    { label: "Cost", value: p.cost_risk },
    { label: "Delay", value: p.delay_risk },
    { label: "Duplication", value: p.duplicate_risk },
    { label: "Agency", value: p.agency_risk },
    { label: "Compliance", value: p.compliance_risk },
  ];

  const scorePending = p.overall_risk_score === null;
  const hasReasons = p.flagged_reasons && p.flagged_reasons.length > 0;

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <Link href="/projects" className="text-xs link-quiet">
        &larr; Back to works
      </Link>

      <h1 className="section-head mt-4">{p.work_name}</h1>
      <div className="eyebrow mt-2">{p.sector ?? p.category}</div>
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
      {p.description && p.description.trim() !== p.work_name.trim() && (
        <p className="mt-3 text-sm text-[color:var(--ink)]/80 max-w-2xl">{p.description}</p>
      )}

      {/* Score hero */}
      <div className="stat-card stat-card--neutral mt-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="stat-card__label">Overall risk score</div>
          <div className="stat-card__value" style={{ fontSize: "2.5rem" }}>
            {scorePending ? "—" : p.overall_risk_score!.toFixed(0)}
            <span className="text-base font-normal text-[color:var(--muted)]">/100</span>
          </div>
          <div className="stat-card__note">
            {scorePending
              ? "Risk scoring for this work has not run yet."
              : "Blended from the five components below, each weighted as shown."}
          </div>
        </div>
        <span className={riskLevelClass(p.risk_level)} style={{ fontSize: "0.8rem", padding: "0.35rem 0.8rem" }}>
          {riskLevelLabel(p.risk_level)}
        </span>
      </div>

      {/* Component breakdown */}
      <section className="mt-6">
        <h2 className="text-[0.95rem] font-medium mb-3">
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
          <div className="stat-card__label">Cost deviation</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {p.cost_deviation_pct === null ? "—" : `${p.cost_deviation_pct.toFixed(0)}%`}
          </div>
        </div>
        <div className="stat-card stat-card--neutral">
          <div className="stat-card__label">Work status</div>
          <div className="stat-card__value" style={{ fontSize: "1.15rem" }}>
            {workStatusLabel(p.work_status)}
          </div>
        </div>
      </section>

      {/* Why flagged — the core of this screen */}
      <section className="mt-6">
        <h2 className="text-[0.95rem] font-medium mb-3">
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

      {p.work_key && (
        <p className="mt-6 text-[0.78rem]" style={{ color: "var(--ink-3)" }}>
          Permanent link to this work:{" "}
          <Link className="link-quiet" href={`/projects/${encodeURIComponent(p.work_key)}`}>
            /projects/{p.work_key}
          </Link>
          <br />
          The numeric address changes on every refresh; this one does not.
        </p>
      )}

      <ReviewTrail workKey={p.work_key} />

      {p.similar_work_id && isNearDuplicate(p.max_similarity_score) && (
        <p className="mt-6 text-sm">
          Reads as a near-duplicate of{" "}
          <Link className="link-quiet" href={`/projects/${p.similar_work_id}`}>
            work #{p.similar_work_id}
          </Link>{" "}
          <span style={{ color: "var(--ink-3)" }}>
            (description similarity {Number(p.max_similarity_score).toFixed(2)}; two works
            can legitimately share a description, so this is a prompt to check, not a
            finding)
          </span>
        </p>
      )}
    </main>
  );
}
