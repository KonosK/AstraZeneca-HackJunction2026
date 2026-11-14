import { useEffect, useState } from "react";
import { analyzeRegion } from "../api/client";
import type { RegionAnalyzeResponse, RegionSummary } from "../api/types";
import { featureLabel, formatNumber, shortCountyName } from "../lib/metrics";
import styles from "./CountyInspector.module.css";

/** Hide model-debug justifications (snake_case features or SHAP jargon). */
function isTechnicalStrategyText(text: string): boolean {
  if (/\bSHAP\b/i.test(text)) return true;
  if (/[a-z]+(?:_[a-z0-9]+)+/.test(text)) return true;
  return false;
}

/** Show expected_impact only when short and free of model jargon. */
function isPlainShortImpact(text: string | undefined): boolean {
  if (!text) return false;
  if (text.length > 160) return false;
  if (isTechnicalStrategyText(text)) return false;
  return true;
}

interface CountyInspectorProps {
  region: RegionSummary | null;
}

export function CountyInspector({ region }: CountyInspectorProps) {
  const [data, setData] = useState<RegionAnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!region) {
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    analyzeRegion({ region_name: region.region_name })
      .then((res) => {
        if (cancelled) return;
        setData(res);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setData(null);
        setError(err instanceof Error ? err.message : "Analyze failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [region?.region_id, region?.region_name]);

  if (!region) {
    return (
      <aside className={`panel ${styles.panel}`} aria-label="Selected county inspector">
        <div className={styles.header}>
          <h3 className="panel-title">Selected county</h3>
        </div>
        <div className={styles.empty}>
          Click a county on the map or list to load regional analysis, top drivers, and
          department strategies.
        </div>
      </aside>
    );
  }

  const pg = data?.predictions_and_gaps;
  const shap = data?.contributing_factors.shap_drivers_baseline ?? [];
  const maxAbs = Math.max(...shap.map((s) => s.abs_shap), 0.001);
  const strategies = data?.recommended_interventions.department_macro ?? [];

  return (
    <aside className={`panel ${styles.panel}`} aria-label="Selected county inspector">
      <div className={styles.header}>
        <h3 className="panel-title">{shortCountyName(region.region_name)}</h3>
        <p className={styles.meta}>
          {region.region_name}
          <br />
          Data year: {region.year} (latest in dataset)
        </p>
      </div>

      <div className={styles.body}>
        {loading && !data ? (
          <div aria-busy="true" aria-label="Loading analysis">
            <div className="skeleton" style={{ height: 72, marginBottom: 10 }} />
            <div className="skeleton" style={{ height: 120, marginBottom: 10 }} />
            <div className="skeleton" style={{ height: 160 }} />
          </div>
        ) : null}

        {error ? (
          <p role="alert" style={{ color: "var(--danger)", margin: 0, fontSize: "0.85rem" }}>
            {error}
          </p>
        ) : null}

        {data && pg ? (
          <>
            <section>
              <h4 className={styles.sectionTitle}>Cancer index</h4>
              <div className={styles.compare}>
                <div className={styles.compareCard}>
                  <span className="badge badge-validated">Validated</span>
                  <p className={styles.compareValue}>
                    {formatNumber(pg.observed_cancer_index_age_std)}
                  </p>
                  <div className="faint" style={{ fontSize: "0.72rem", marginTop: 4 }}>
                    Observed · THL / FCR
                  </div>
                </div>
                <div className={styles.compareCard}>
                  <span className="badge badge-projection">Model estimate</span>
                  <p className={styles.compareValue}>
                    {formatNumber(pg.predicted_cancer_index_age_std)}
                  </p>
                  <div className="faint" style={{ fontSize: "0.72rem", marginTop: 4 }}>
                    Estimated from indicators
                  </div>
                </div>
              </div>
              <p className={styles.gap}>
                Model score − observed:{" "}
                <strong>{formatNumber(pg.prediction_minus_observed)}</strong>
              </p>
            </section>

            <section>
              <h4 className={styles.sectionTitle}>Top drivers of the cancer index</h4>
              <p className="faint" style={{ fontSize: "0.75rem", margin: "0 0 8px" }}>
                Larger bars = stronger influence on the model’s county score. ‘Adverse’ means
                worse than the national median.
              </p>
              <ul className={styles.shapList}>
                {shap.map((d) => (
                  <li key={d.feature} className={styles.shapItem}>
                    <div className={styles.shapMeta}>
                      <span>
                        {featureLabel(d.feature)}
                        {d.adverse_direction ? (
                          <span className={styles.adverse}> · adverse</span>
                        ) : null}
                      </span>
                      <span>
                        val {formatNumber(d.value)} · impact {formatNumber(d.shap_value, 2)}
                      </span>
                    </div>
                    <div className={styles.shapBars} aria-hidden>
                      <div
                        className={`${styles.shapFill} ${d.shap_value >= 0 ? styles.shapPos : styles.shapNeg}`}
                        style={{ width: `${(d.abs_shap / maxAbs) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h4 className={styles.sectionTitle}>Department strategies</h4>
              <p className={styles.strategyNote}>
                Actions are based on this county’s top drivers, mapped to Finland’s National
                Cancer Strategy.
              </p>
              <div className={styles.strategy}>
                {strategies.length === 0 ? (
                  <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
                    No department strategies for this county.
                  </p>
                ) : (
                  strategies.map((s) => {
                    const driverLabel = s.driver_feature
                      ? featureLabel(s.driver_feature).replace(/ %$/, "")
                      : null;
                    const showJustification =
                      Boolean(s.justification) &&
                      !isTechnicalStrategyText(s.justification);
                    const showImpact =
                      Boolean(s.expected_impact) &&
                      isPlainShortImpact(s.expected_impact);

                    return (
                      <article
                        key={`${s.priority}-${s.driver_feature}`}
                        className={styles.strategyCard}
                      >
                        <p className={styles.action}>
                          <span className={styles.priority}>{s.priority}</span>
                          {" "}
                          {s.action}
                        </p>
                        <p className={styles.actor}>
                          <strong>Actor:</strong> {s.responsible_actor}
                        </p>
                        {driverLabel ? (
                          <p className={styles.driverTag}>
                            Linked to: {driverLabel}
                          </p>
                        ) : null}
                        {showJustification ? (
                          <p className={styles.justification}>{s.justification}</p>
                        ) : null}
                        {showImpact ? (
                          <p className={styles.impact}>{s.expected_impact}</p>
                        ) : null}
                      </article>
                    );
                  })
                )}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </aside>
  );
}
