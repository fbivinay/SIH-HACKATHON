"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import type { StateStat } from "@/lib/api";
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

type Bounds = [[number, number], [number, number]];

// India's own extent, read off the boundary file rather than typed in, so the
// map is framed on whatever the file contains.
function boundsOf(fc: GeoJSON.FeatureCollection): Bounds {
  let s = 90, w = 180, n = -90, e = -180;
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") {
      const [lon, lat] = c as number[];
      if (lat < s) s = lat;
      if (lat > n) n = lat;
      if (lon < w) w = lon;
      if (lon > e) e = lon;
    } else if (Array.isArray(c)) c.forEach(walk);
  };
  for (const f of fc.features) {
    const g = f.geometry as { coordinates?: unknown } | null;
    if (g?.coordinates) walk(g.coordinates);
  }
  return [[s, w], [n, e]];
}

/**
 * The risk choropleth - the whole of the States page's first screen.
 *
 * It had a page of its own (/map) until 2026-09-19, when the owner folded it
 * into States: the map says where, the list below it says how much. It is
 * framed on India's own extent (fitBounds with fractional zoom), so the
 * country fills the screen at any window size instead of sitting small at a
 * fixed zoom 4.5. Clicking a state opens its desk, which is what the rows of
 * the old map table did.
 *
 * Shaded by the share of each state's works above the review threshold.
 * Average score would shade nothing: all 36 states average inside the low
 * band, so the map would be one flat colour.
 */
export default function StateMap({ stats }: { stats: StateStat[] }) {
  const router = useRouter();
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/india-states.geojson")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`status ${r.status}`))))
      .then(setGeojson)
      .catch(() => setFailed(true));
  }, []);

  const byState = useMemo(() => {
    const map = new Map<string, StateStat>();
    for (const s of stats) map.set(normalizeStateName(s.state), s);
    return map;
  }, [stats]);
  const bounds = useMemo(() => (geojson ? boundsOf(geojson) : null), [geojson]);
  const scoringPending = isAggregateScoringPending(stats, "high_risk_count");

  return (
    <div className="statemap">
      {geojson && bounds ? (
        <MapContainer
          bounds={bounds}
          boundsOptions={{ padding: [12, 12] }}
          zoomSnap={0.1}
          scrollWheelZoom={false}
          style={{ height: "100%", width: "100%" }}
        >
          {/* OpenStreetMap's own tiles, desaturated in CSS rather than swapped
              for a designed grey basemap: CARTO's light_all now requires an API
              key and watermarks "API KEY REQUIRED" across every tile without
              one. */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <GeoJSON
            data={geojson}
            style={(feature) => {
              const stat = byState.get(
                normalizeStateName((feature?.properties as Record<string, string>)?.ST_NM)
              );
              return {
                fillColor: stat && !scoringPending ? choroplethFill(stat.flagged_share) : NO_DATA_FILL,
                fillOpacity: stat ? 0.85 : 0.45,
                color: "#ffffff",
                weight: 1,
              };
            }}
            onEachFeature={(feature, layer) => {
              const label = (feature.properties as Record<string, string>)?.ST_NM ?? "Unknown";
              const stat = byState.get(normalizeStateName(label));
              if (stat) {
                layer.bindTooltip(
                  `${label} — ${formatCount(stat.flagged_count)} of ${formatCount(
                    stat.total_projects
                  )} works to verify (${stat.flagged_share === null ? "—" : `${stat.flagged_share}%`})`,
                  { sticky: true }
                );
                layer.on("click", () => router.push(`/state/${encodeURIComponent(stat.state)}`));
              } else {
                layer.bindTooltip(`${label}: no matching works`, { sticky: true });
              }
            }}
          />
        </MapContainer>
      ) : (
        <p className="statemap__status">{failed ? "The map could not be loaded." : "Loading map…"}</p>
      )}

      <div className="choro-legend statemap__legend" aria-hidden="true">
        <span className="choro-legend__title">Share of works to verify</span>
        {CHOROPLETH_STEPS.map((step) => (
          <span key={step.label} className="choro-legend__item">
            <span className="choro-legend__swatch" style={{ background: step.fill }} />
            {step.label}
          </span>
        ))}
      </div>
    </div>
  );
}
