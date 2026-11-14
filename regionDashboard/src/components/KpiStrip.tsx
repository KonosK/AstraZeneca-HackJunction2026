import type { HealthResponse, RegionSummary } from "../api/types";
import { countyWithMax, formatNumber, median, shortCountyName } from "../lib/metrics";
import styles from "./KpiStrip.module.css";

interface KpiStripProps {
  regions: RegionSummary[];
  health: HealthResponse | null;
  loading: boolean;
}

export function KpiStrip({ regions, health, loading }: KpiStripProps) {
  const cancerValues = regions
    .map((r) => r.indicators.cancer_index_age_std)
    .filter((v): v is number => v != null);
  const medCancer = median(cancerValues);
  const worstWait = countyWithMax(regions, (r) => r.indicators.gp_wait_over_7d_pct);
  const mae = health?.model.cv.mae_mean;

  if (loading) {
    return (
      <div className={styles.strip} aria-busy="true" aria-label="Loading KPIs">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`panel ${styles.card}`}>
            <div className="skeleton" style={{ height: 28, width: "40%" }} />
            <div className="skeleton" style={{ height: 14, width: "70%", marginTop: 10 }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.strip} role="region" aria-label="Regional KPIs">
      <article className={`panel ${styles.card}`}>
        <p className={styles.value}>{regions.length}</p>
        <p className={styles.label}>Counties loaded</p>
      </article>

      <article className={`panel ${styles.card}`}>
        <p className={styles.value}>{formatNumber(medCancer, 1)}</p>
        <p className={styles.label}>Median observed cancer index</p>
        <p className={styles.sub}>Validated THL / FCR · age-std</p>
      </article>

      <article className={`panel ${styles.card}`}>
        <p className={styles.value}>
          {worstWait ? formatNumber(worstWait.value, 1) : "—"}
          {worstWait ? "%" : ""}
        </p>
        <p className={styles.label}>Highest GP wait &gt;7d</p>
        <p className={styles.sub}>
          {worstWait ? shortCountyName(worstWait.region.region_name) : "No data"}
        </p>
      </article>

      <article className={`panel ${styles.card}`}>
        <p className={styles.value}>{formatNumber(mae ?? null, 2)}</p>
        <p className={styles.label}>Model MAE (CV mean)</p>
        <p className={styles.sub}>{health?.model.best_model ?? "from /health"}</p>
      </article>
    </div>
  );
}
