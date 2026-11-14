/** OncoFlow regional API types (fields used by the dashboard). */

export type EvidenceClass = "validated_thl_fcr" | "calibrated_projection";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  model: {
    artifact_path: string;
    best_model: string;
    target: string;
    features: string[];
    n_counties: number;
    cv: {
      best_model?: string;
      mae_mean?: number | null;
      mae_std?: number | null;
      rmse_mean?: number | null;
      r2_mean?: number | null;
    };
  };
}

export interface RegionIndicators {
  gp_wait_over_7d_pct: number | null;
  gp_wait_over_3mo_pct: number | null;
  gp_outpatient_visits_per_1000: number | null;
  morbidity_index_age_std: number | null;
  higher_education_pct: number | null;
  pop_75plus_living_alone_pct: number | null;
  pop_75plus_rai_assessed_pct: number | null;
  cr_3620_proportion_of_women_invited_to_cervical_cance: number | null;
  cr_3621_proportion_of_women_invited_to_breast_cancer_: number | null;
  cancer_index_age_std: number | null;
}

export interface RegionSummary {
  region_id: number;
  region_name: string;
  year: number;
  indicators: RegionIndicators;
  source: string;
}

export interface RegionsResponse {
  count: number;
  year: number | null;
  regions: RegionSummary[];
}

export interface ShapDriver {
  feature: string;
  value: number | null;
  shap_value: number;
  abs_shap: number;
  national_median: number | null;
  adverse_direction: boolean;
  family: string | null;
}

export interface StrategyRecommendation {
  target_level: string;
  action: string;
  responsible_actor: string;
  justification: string;
  expected_impact?: string;
  success_metrics?: string[];
  driver_feature: string | null;
  shap_value: number | null;
  region_name: string;
  pathway_days: unknown;
  priority: number;
  metadata?: Record<string, unknown>;
}

export interface RegionAnalyzeResponse {
  predictions_and_gaps: {
    region_id: number;
    region_name: string;
    year: number;
    observed_cancer_index_age_std: number | null;
    observed_evidence_class: EvidenceClass | string;
    predicted_cancer_index_age_std: number;
    predicted_evidence_class: EvidenceClass | string;
    prediction_minus_observed: number | null;
    baseline_features: Record<string, number | null>;
  };
  contributing_factors: {
    shap_drivers_baseline: ShapDriver[];
    interpretation: string;
  };
  recommended_interventions: {
    department_macro: StrategyRecommendation[];
    target_level: string;
  };
  supporting_evidence: {
    validated_sources: string[];
    strategy_reference: string;
    evidence_classes: Record<string, string>;
  };
  confidence_and_limitations: {
    model: {
      best_model?: string;
      mae_mean?: number | null;
      mae_std?: number | null;
      rmse_mean?: number | null;
      r2_mean?: number | null;
    };
    data_year_basis: string;
    distinction: {
      validated_findings: string;
      calibrated_projections: string;
    };
    limitations: string[];
  };
}

export interface RegionAnalyzeRequest {
  region_name: string;
}

/** Map overlay metrics available from GET /regions (validated indicators). */
export type OverlayMetric =
  | "observed_cancer_index"
  | "gp_wait_over_7d_pct"
  | "higher_education_pct"
  | "screening_breast"
  | "screening_cervical";
