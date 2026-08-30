import { api } from "@/lib/api";
import { formatCount, isAggregateScoringPending, riskLevelClass, riskLevelLabel, riskScoreToLevel } from "@/lib/format";

export default async function AnalysisPage() {
  const agencies = await api.agencies();
  const scoringPending = isAggregateScoringPending(agencies, "anomaly_count");

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="eyebrow">Implementing agencies</div>
      <h1
        className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Agency Analysis
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
        {formatCount(agencies.length)} implementing agencies, ranked by average risk score.
      </p>

      {scoringPending && (
        <div className="notice mt-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            Risk scoring is running across all works. Delayed/anomaly counts and average
            risk will populate once it completes.
          </span>
        </div>
      )}

      <div className="mt-6 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Agency</th>
              <th className="text-right">Works</th>
              <th className="text-right">Delayed</th>
              <th className="text-right">Anomalies</th>
              <th className="text-right">Avg Risk</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {agencies.map((a) => (
              <tr key={a.implementing_agency}>
                <td className="max-w-[24rem] truncate">{a.implementing_agency}</td>
                <td className="num">{formatCount(a.total_projects)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(a.delayed_count)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(a.anomaly_count)}</td>
                <td className="num">{scoringPending ? "—" : a.avg_risk_score.toFixed(1)}</td>
                <td>
                  <span className={riskLevelClass(scoringPending ? null : riskScoreToLevel(a.avg_risk_score))}>
                    {scoringPending ? "Pending" : riskLevelLabel(riskScoreToLevel(a.avg_risk_score))}
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
