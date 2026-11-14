import type { PatientRequest } from "../domain/intake";
import type {
  RegionAnalyzeResponse,
  ShapDriver,
  StrategyRecommendation,
} from "./types";
export interface PatientResponse {
  predictions_and_gaps: {
    patient_id: string;
    region_name: string;
    year: number;
    intake: PatientRequest;
    blind_spots: string[];
    pathway_days_estimate: Record<string, number>;
    county_context: {
      observed_cancer_index_age_std: number | null;
      predicted_cancer_index_age_std: number;
      indicators: Record<string, number | null>;
    };
  };
  contributing_factors: {
    county_shap_drivers: ShapDriver[];
    intake_risk_flags: Record<string, boolean | string[]>;
    blind_spots: string[];
  };
  recommended_interventions: {
    doctor_micro: StrategyRecommendation[];
    department_macro: StrategyRecommendation[];
  };
  supporting_evidence: Record<string, unknown>;
  confidence_and_limitations: RegionAnalyzeResponse["confidence_and_limitations"];
}
const obj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
export function decodeFiveBlocks(
  data: unknown,
): Record<string, Record<string, unknown>> {
  if (!obj(data)) throw Error("Invalid analysis response");
  for (const k of [
    "predictions_and_gaps",
    "contributing_factors",
    "recommended_interventions",
    "supporting_evidence",
    "confidence_and_limitations",
  ])
    if (!obj(data[k])) throw Error("Invalid analysis section: " + k);
  const rec = data.recommended_interventions as Record<string, unknown>;
  for (const key of ["doctor_micro", "department_macro"]) {
    if (key === "doctor_micro" && rec[key] === undefined) continue;
    if (!Array.isArray(rec[key])) throw Error("Invalid recommendations");
    for (const item of rec[key] as unknown[])
      if (
        !obj(item) ||
        typeof item.action !== "string" ||
        typeof item.responsible_actor !== "string" ||
        typeof item.justification !== "string" ||
        !Array.isArray(item.success_metrics) ||
        !item.success_metrics.every((s) => typeof s === "string")
      )
        throw Error("Invalid recommendation fields");
  }
  return data as Record<string, Record<string, unknown>>;
}
export function decodePatient(data: unknown): PatientResponse {
  const b = decodeFiveBlocks(data),
    p = b.predictions_and_gaps;
  if (
    typeof p.patient_id !== "string" ||
    typeof p.region_name !== "string" ||
    !obj(p.intake) ||
    !Array.isArray(p.blind_spots) ||
    !p.blind_spots.every((x) => typeof x === "string") ||
    !obj(p.pathway_days_estimate) ||
    !obj(p.county_context) ||
    !Array.isArray(b.recommended_interventions.doctor_micro)
  )
    throw Error("Invalid patient response");
  for (const k of [
    "patient_days",
    "primary_care_days",
    "specialist_care_days",
    "total_days",
  ])
    if (
      typeof p.pathway_days_estimate[k] !== "number" ||
      !Number.isFinite(p.pathway_days_estimate[k])
    )
      throw Error("Invalid pathway estimate");
  if (
    !Array.isArray(b.confidence_and_limitations.limitations) ||
    !obj(b.confidence_and_limitations.model)
  )
    throw Error("Invalid model limitations");
  return data as PatientResponse;
}
