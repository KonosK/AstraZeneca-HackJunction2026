import type { OverlayMetric, RegionIndicators, RegionSummary } from "../api/types";

export const OVERLAY_OPTIONS: { value: OverlayMetric; label: string; validated: boolean }[] = [
  { value: "observed_cancer_index", label: "Observed cancer index (age-std)", validated: true },
  { value: "gp_wait_over_7d_pct", label: "GP wait >7 days (%)", validated: true },
  { value: "higher_education_pct", label: "Higher education (%)", validated: true },
  { value: "screening_breast", label: "Breast screening invite (%)", validated: true },
  { value: "screening_cervical", label: "Cervical screening invite (%)", validated: true },
];

export function shortCountyName(regionName: string): string {
  return regionName
    .replace(/\s+wellbeing services county$/i, "")
    .replace(/^City of\s+/i, "")
    .trim();
}

export function getOverlayValue(
  indicators: RegionIndicators,
  metric: OverlayMetric,
): number | null {
  switch (metric) {
    case "observed_cancer_index":
      return indicators.cancer_index_age_std;
    case "gp_wait_over_7d_pct":
      return indicators.gp_wait_over_7d_pct;
    case "higher_education_pct":
      return indicators.higher_education_pct;
    case "screening_breast":
      return indicators.cr_3621_proportion_of_women_invited_to_breast_cancer_;
    case "screening_cervical":
      return indicators.cr_3620_proportion_of_women_invited_to_cervical_cance;
    default:
      return null;
  }
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return Number(value).toFixed(digits);
}

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

export function countyWithMax(
  regions: RegionSummary[],
  pick: (r: RegionSummary) => number | null,
): { region: RegionSummary; value: number } | null {
  let best: { region: RegionSummary; value: number } | null = null;
  for (const region of regions) {
    const value = pick(region);
    if (value == null) continue;
    if (!best || value > best.value) best = { region, value };
  }
  return best;
}

export function featureLabel(feature: string): string {
  const map: Record<string, string> = {
    gp_wait_over_7d_pct: "GP wait >7d %",
    gp_wait_over_3mo_pct: "GP wait >3mo %",
    gp_outpatient_visits_per_1000: "GP outpatient /1000",
    higher_education_pct: "Higher education %",
    pop_75plus_living_alone_pct: "75+ living alone %",
    pop_75plus_rai_assessed_pct: "75+ RAI assessed %",
    cr_3620_proportion_of_women_invited_to_cervical_cance: "Cervical invite %",
    cr_3621_proportion_of_women_invited_to_breast_cancer_: "Breast invite %",
  };
  return map[feature] ?? feature;
}

/** Sequential teal→amber scale for choropleth (higher = warmer). */
export function valueToColor(
  value: number | null,
  min: number,
  max: number,
): string {
  if (value == null || !Number.isFinite(value) || max <= min) {
    return "var(--map-empty)";
  }
  const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
  // cool slate-teal → warm copper (health analytics, not purple)
  const stops = [
    [42, 92, 104],
    [58, 124, 118],
    [120, 148, 98],
    [186, 140, 72],
    [176, 84, 58],
  ];
  const idx = t * (stops.length - 1);
  const i = Math.floor(idx);
  const f = idx - i;
  const a = stops[i];
  const b = stops[Math.min(i + 1, stops.length - 1)];
  const r = Math.round(a[0] + (b[0] - a[0]) * f);
  const g = Math.round(a[1] + (b[1] - a[1]) * f);
  const bl = Math.round(a[2] + (b[2] - a[2]) * f);
  return `rgb(${r}, ${g}, ${bl})`;
}

export function extent(values: number[]): { min: number; max: number } {
  if (!values.length) return { min: 0, max: 1 };
  return { min: Math.min(...values), max: Math.max(...values) };
}
