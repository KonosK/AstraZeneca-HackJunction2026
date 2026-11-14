import type { OverlayMetric, RegionSummary } from "../api/types";
import {
  formatNumber,
  getOverlayValue,
  shortCountyName,
} from "../lib/metrics";
import type { SortMode } from "./TopBar";
import styles from "./CountyList.module.css";

interface CountyListProps {
  regions: RegionSummary[];
  metric: OverlayMetric;
  selectedId: number | null;
  onSelect: (region: RegionSummary) => void;
  search: string;
  sort: SortMode;
  loading: boolean;
}

export function CountyList({
  regions,
  metric,
  selectedId,
  onSelect,
  search,
  sort,
  loading,
}: CountyListProps) {
  const q = search.trim().toLowerCase();
  let listed = regions.filter(
    (r) =>
      !q ||
      r.region_name.toLowerCase().includes(q) ||
      shortCountyName(r.region_name).toLowerCase().includes(q),
  );

  listed = [...listed].sort((a, b) => {
    if (sort === "name") {
      return shortCountyName(a.region_name).localeCompare(shortCountyName(b.region_name));
    }
    const av = getOverlayValue(a.indicators, metric);
    const bv = getOverlayValue(b.indicators, metric);
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return sort === "metric_desc" ? bv - av : av - bv;
  });

  return (
    <section className={`panel ${styles.panel}`} aria-label="County list">
      <div className={styles.header}>
        <h3 className="panel-title">Counties</h3>
        <span className={styles.count}>{listed.length} shown</span>
      </div>
      <div className={styles.grid} role="listbox" aria-label="Wellbeing services counties">
        {listed.map((region) => {
          const value = getOverlayValue(region.indicators, metric);
          const active = region.region_id === selectedId;
          return (
            <button
              key={region.region_id}
              type="button"
              role="option"
              aria-selected={active}
              className={`${styles.item} ${active ? styles.itemActive : ""}`}
              onClick={() => onSelect(region)}
            >
              <span className={styles.name}>{shortCountyName(region.region_name)}</span>
              <span className={styles.value}>{formatNumber(value)}</span>
            </button>
          );
        })}
        {!loading && listed.length === 0 ? (
          <p className="muted" style={{ margin: 0, padding: "4px 2px", fontSize: "0.8rem" }}>
            No counties match “{search}”.
          </p>
        ) : null}
      </div>
    </section>
  );
}
