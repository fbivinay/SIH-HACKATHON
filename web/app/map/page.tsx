"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { api, StateStat } from "@/lib/api";
import {
  formatCount,
  isAggregateScoringPending,
  normalizeStateName,
  riskLevelClass,
  riskLevelLabel,
  riskScoreColorHex,
  riskScoreToLevel,
} from "@/lib/format";

const MapContainer = dynamic(() => import("react-leaflet").then((m) => m.MapContainer), {
  ssr: false,
});
const TileLayer = dynamic(() => import("react-leaflet").then((m) => m.TileLayer), { ssr: false });
const GeoJSON = dynamic(() => import("react-leaflet").then((m) => m.GeoJSON), { ssr: false });

export default function MapPage() {
  const [stats, setStats] = useState<StateStat[] | null>(null);
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [geojsonFailed, setGeojsonFailed] = useState(false);

  useEffect(() => {
    api.mapStates().then(setStats);
    fetch("/india-states.geojson")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`status ${r.status}`))))
      .then(setGeojson)
      .catch(() => setGeojsonFailed(true));
  }, []);

  const byState = useMemo(() => {
    const map = new Map<string, StateStat>();
    for (const s of stats ?? []) map.set(normalizeStateName(s.state), s);
    return map;
  }, [stats]);

  const scoringPending = stats ? isAggregateScoringPending(stats, "high_risk_count") : false;
  const sorted = useMemo(
    () => (stats ? [...stats].sort((a, b) => b.avg_risk_score - a.avg_risk_score) : []),
    [stats]
  );

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="eyebrow">Geographic distribution</div>
      <h1
        className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Risk by State
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-[color:var(--muted)]">
        {stats ? `${formatCount(stats.length)} states and union territories` : "Loading state figures…"}
        , ranked by average risk score.
      </p>

      {scoringPending && (
        <div className="notice mt-5" role="status">
          <span aria-hidden="true">&#9679;</span>
          <span>
            Risk scoring is running across all works. State averages and the choropleth
            shading below will populate once it completes.
          </span>
        </div>
      )}

      {geojson && stats && (
        // Wait for stats too, not just geojson: onEachFeature (tooltip text) is bound
        // once at layer creation by react-leaflet and does not re-run on prop changes
        // (only `style` is reactively re-applied via layer.setStyle). Mounting after
        // both requests resolve keeps tooltips and fill color in sync in both the
        // null/pending and populated states.
        <div className="mt-6 mb-6 data-table-wrap" style={{ height: 480 }}>
          <MapContainer
            center={[22.5, 80]}
            zoom={4.5}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <GeoJSON
              data={geojson}
              style={(feature) => {
                const name = normalizeStateName((feature?.properties as Record<string, string>)?.ST_NM);
                const stat = byState.get(name);
                const known = Boolean(stat);
                return {
                  fillColor:
                    known && !scoringPending ? riskScoreColorHex(stat!.avg_risk_score) : "#e5e7eb",
                  fillOpacity: known ? 0.7 : 0.4,
                  color: "#374151",
                  weight: 1,
                };
              }}
              onEachFeature={(feature, layer) => {
                const name = normalizeStateName((feature?.properties as Record<string, string>)?.ST_NM);
                const stat = byState.get(name);
                const label = (feature.properties as Record<string, string>)?.ST_NM ?? "Unknown";
                if (stat) {
                  layer.bindTooltip(
                    `${label}: ${formatCount(stat.total_projects)} works, avg score ${
                      scoringPending ? "—" : stat.avg_risk_score.toFixed(1)
                    }`
                  );
                } else {
                  layer.bindTooltip(`${label}: no matching works`);
                }
              }}
            />
          </MapContainer>
        </div>
      )}

      {!(geojson && stats) && !geojsonFailed && (
        <p className="mt-6 mb-2 text-sm text-[color:var(--muted)]">Loading map…</p>
      )}

      <div className="mt-6 data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>State</th>
              <th className="text-right">Works</th>
              <th className="text-right">High Risk</th>
              <th className="text-right">Avg Score</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {stats === null && (
              <tr>
                <td colSpan={5} className="text-center text-[color:var(--muted)] py-6">
                  Loading…
                </td>
              </tr>
            )}
            {sorted.map((s) => (
              <tr key={s.state}>
                <td>{s.state}</td>
                <td className="num">{formatCount(s.total_projects)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(s.high_risk_count)}</td>
                <td className="num">{scoringPending ? "—" : s.avg_risk_score.toFixed(1)}</td>
                <td>
                  <span className={riskLevelClass(scoringPending ? null : riskScoreToLevel(s.avg_risk_score))}>
                    {scoringPending ? "Pending" : riskLevelLabel(riskScoreToLevel(s.avg_risk_score))}
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
