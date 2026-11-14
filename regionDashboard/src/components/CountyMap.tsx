import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import type { OverlayMetric, RegionSummary } from "../api/types";
import { geoName } from "../data/geoJoin";
import { FINLAND_MAP_SIZE, useFinlandProjection } from "../hooks/useFinlandProjection";
import {
  extent,
  formatNumber,
  getOverlayValue,
  OVERLAY_OPTIONS,
  shortCountyName,
  valueToColor,
} from "../lib/metrics";
import styles from "./CountyMap.module.css";

interface CountyMapProps {
  regions: RegionSummary[];
  metric: OverlayMetric;
  onMetricChange: (m: OverlayMetric) => void;
  selectedId: number | null;
  onSelect: (region: RegionSummary) => void;
  search: string;
  loading: boolean;
  error: string | null;
}

export function CountyMap({
  regions,
  metric,
  onMetricChange,
  selectedId,
  onSelect,
  search,
  loading,
  error,
}: CountyMapProps) {
  const metricMeta = OVERLAY_OPTIONS.find((o) => o.value === metric);
  const { projection, geography, error: mapError } = useFinlandProjection();
  const values = regions
    .map((r) => getOverlayValue(r.indicators, metric))
    .filter((v): v is number => v != null);
  const { min, max } = extent(values);

  const q = search.trim().toLowerCase();
  const byName = new Map(regions.map((r) => [r.region_name, r]));
  const showMapBusy = loading || !projection || !geography;

  return (
    <section className={`panel ${styles.panel}`} aria-label="County choropleth map">
      <div className={styles.header}>
        <div>
          <h3 className="panel-title">County map</h3>
          <div className="muted" style={{ fontSize: "0.8rem", marginTop: 2 }}>
            {metricMeta?.label ?? metric}
          </div>
        </div>
        <div className={styles.headerMeta}>
          <label className={styles.metricLabel} htmlFor="map-metric-overlay">
            Metric
            <select
              id="map-metric-overlay"
              value={metric}
              onChange={(e) => onMetricChange(e.target.value as OverlayMetric)}
            >
              {OVERLAY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          {metricMeta?.validated ? (
            <span className="badge badge-validated">Validated THL / FCR</span>
          ) : null}
          <div className={styles.legend} aria-hidden>
            <div className={styles.legendBar} />
            <div className={styles.legendScale}>
              <span>{formatNumber(min, 1)}</span>
              <span>{formatNumber(max, 1)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.mapWrap}>
        {showMapBusy && !error && !mapError ? (
          <div className={styles.state} role="status">
            Loading counties…
          </div>
        ) : null}
        {error || mapError ? (
          <div className={styles.state} role="alert">
            {error ?? mapError}
          </div>
        ) : null}
        {!loading && !error && regions.length === 0 ? (
          <div className={styles.state}>No regions returned from API.</div>
        ) : null}

        {projection && geography ? (
          <ComposableMap
            className={styles.svg}
            projection={projection}
            width={FINLAND_MAP_SIZE.width}
            height={FINLAND_MAP_SIZE.height}
            preserveAspectRatio="xMidYMid meet"
            aria-label={`Choropleth of Finnish wellbeing counties by ${metricMeta?.label ?? metric}`}
          >
            <Geographies geography={geography}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const name = geoName(geo.properties as Record<string, unknown>);
                  const region = byName.get(name);
                  const value = region ? getOverlayValue(region.indicators, metric) : null;
                  const fill = valueToColor(value, min, max);
                  const selected = region?.region_id === selectedId;
                  const dimmed =
                    q.length > 0 &&
                    region != null &&
                    !region.region_name.toLowerCase().includes(q) &&
                    !shortCountyName(region.region_name).toLowerCase().includes(q);

                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      className={`${styles.county} ${selected ? styles.countySelected : ""}`}
                      fill={fill}
                      stroke="var(--map-stroke)"
                      strokeWidth={selected ? 1.35 : 0.55}
                      opacity={dimmed ? 0.28 : region ? 1 : 0.45}
                      tabIndex={region ? 0 : -1}
                      role="button"
                      aria-label={
                        region
                          ? `${shortCountyName(region.region_name)}, ${metricMeta?.label ?? metric}: ${formatNumber(value)}`
                          : `${shortCountyName(name) || "Unknown"}, no data`
                      }
                      aria-pressed={selected}
                      onClick={() => region && onSelect(region)}
                      onKeyDown={(e) => {
                        if (!region) return;
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onSelect(region);
                        }
                      }}
                    />
                  );
                })
              }
            </Geographies>
          </ComposableMap>
        ) : null}
      </div>
    </section>
  );
}
