"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { api, StateStat } from "@/lib/api";
import {
  formatCount,
  isAggregateScoringPending,
  normalizeStateName,
  choroplethFill,
  CHOROPLETH_STEPS,
  NO_DATA_FILL,
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
    // Ordered by the quantity the map is shaded by, so the table reads as the
    // map's index rather than a second, differently-ranked list.
    () => (stats ? [...stats].sort((a, b) => (b.flagged_share ?? -1) - (a.flagged_share ?? -1)) : []),
    [stats]
  );

  return (
    <main className="shell py-8">
      <h1 className="display">Risk by state</h1>
      <p className="lede !mx-0 !max-w-2xl">
        {stats ? `${formatCount(stats.length)} states and union territories` : "Loading state figures…"}
        , shaded by the share of each state&rsquo;s works that sit above the review
        threshold. Average score would shade nothing: all 36 states average inside the
        low band, so the map would be one flat colour.
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
            {/* OpenStreetMap's own tiles, desaturated in CSS rather than
                swapped for a designed grey basemap: CARTO's light_all now
                requires an API key and watermarks "API KEY REQUIRED" across
                every tile without one. Greying the tile pane gets the same
                result - a quiet basemap the red choropleth can sit on top of -
                with no key, no vendor and the original attribution intact. */}
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
                    known && !scoringPending ? choroplethFill(stat!.flagged_share) : NO_DATA_FILL,
                  fillOpacity: known ? 0.85 : 0.45,
                  color: "#ffffff",
                  weight: 1,
                };
              }}
              onEachFeature={(feature, layer) => {
                const name = normalizeStateName((feature?.properties as Record<string, string>)?.ST_NM);
                const stat = byState.get(name);
                const label = (feature.properties as Record<string, string>)?.ST_NM ?? "Unknown";
                if (stat) {
                  layer.bindTooltip(
                    `${label} — ${formatCount(stat.flagged_count)} of ${formatCount(
                      stat.total_projects
                    )} works to verify (${
                      stat.flagged_share === null ? "—" : `${stat.flagged_share}%`
                    })`
                  );
                } else {
                  layer.bindTooltip(`${label}: no matching works`);
                }
              }}
            />
          </MapContainer>
        </div>
      )}

      {geojson && stats && (
        <div className="choro-legend" aria-hidden="true">
          <span className="choro-legend__title">Share of works to verify</span>
          {CHOROPLETH_STEPS.map((step) => (
            <span key={step.label} className="choro-legend__item">
              <span className="choro-legend__swatch" style={{ background: step.fill }} />
              {step.label}
            </span>
          ))}
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
              <th className="num">Works</th>
              <th className="num">To verify</th>
              <th className="num">Share</th>
              <th className="num">High risk</th>
              <th className="num">Avg score</th>
            </tr>
          </thead>
          <tbody>
            {stats === null && (
              <tr>
                <td colSpan={6} className="text-center text-[color:var(--muted)] py-6">
                  Loading…
                </td>
              </tr>
            )}
            {sorted.map((s) => (
              <tr key={s.state}>
                <td>{s.state}</td>
                <td className="num">{formatCount(s.total_projects)}</td>
                <td className="num">{scoringPending ? "—" : formatCount(s.flagged_count)}</td>
                <td className="num">
                  {scoringPending || s.flagged_share === null ? "—" : `${s.flagged_share}%`}
                </td>
                <td className="num">{scoringPending ? "—" : formatCount(s.high_risk_count)}</td>
                <td className="num">{scoringPending ? "—" : s.avg_risk_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
