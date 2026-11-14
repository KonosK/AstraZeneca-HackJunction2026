"""OncoFlow FastAPI service: regional SHAP analysis + patient triage guidance."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Literal, Mapping, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from .recommendations import (
        ARTIFACT_PATH,
        KUITUNEN_BENCHMARKS,
        _county_row,
        _feature_frame,
        county_shap_drivers,
        estimate_pathway_days,
        load_bundle,
        patient_recommendations,
        recommendations_as_dicts,
        regional_recommendations,
    )
except ImportError:  # running as a flat module (e.g. uvicorn api:app from mlBackend/)
    from recommendations import (
        ARTIFACT_PATH,
        KUITUNEN_BENCHMARKS,
        _county_row,
        _feature_frame,
        county_shap_drivers,
        estimate_pathway_days,
        load_bundle,
        patient_recommendations,
        recommendations_as_dicts,
        regional_recommendations,
    )

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "clean_cancer_training_data.csv"
BUNDLE_PATH = Path(ARTIFACT_PATH)

INDICATOR_COLUMNS = [
    "gp_wait_over_7d_pct",
    "gp_wait_over_3mo_pct",
    "gp_outpatient_visits_per_1000",
    "morbidity_index_age_std",
    "higher_education_pct",
    "pop_75plus_living_alone_pct",
    "pop_75plus_rai_assessed_pct",
    "cr_3620_proportion_of_women_invited_to_cervical_cance",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_",
    "cancer_index_age_std",
]

VALIDATED_SOURCES = [
    "THL Sotkanet (wellbeing services county indicators)",
    "Finnish Cancer Registry (screening invitation / cancer index inputs)",
]

STRATEGY_REF = "National Cancer Strategy 2026–2035"

FIVE_BLOCK_KEYS = (
    "predictions_and_gaps",
    "contributing_factors",
    "recommended_interventions",
    "supporting_evidence",
    "confidence_and_limitations",
)

app = FastAPI(
    title="OncoFlow API",
    description=(
        "Regional cancer-risk predictions with SHAP drivers and patient pathway "
        "triage calibrated to Finnish lung-cancer benchmarks."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BUNDLE: dict[str, Any] | None = None
_REGIONS_DF: pd.DataFrame | None = None


# ---------------------------------------------------------------------------
# Strict JSON sanitization
# ---------------------------------------------------------------------------


def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert NaN / ±inf (and numpy equivalents) to None for JSON null."""
    if obj is None:
        return None

    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]

    if isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())

    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        if not math.isfinite(value):
            return None
        return value

    if isinstance(obj, Mapping):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # pandas missing scalars (pd.NA, NaT) — avoid treating strings/bools as NA
    if not isinstance(obj, (str, bytes, bool, int)):
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass

    return obj


def json_ok(payload: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=sanitize_for_json(payload), status_code=status_code)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RegionAnalyzeRequest(BaseModel):
    region_name: str = Field(..., description="Wellbeing services county name or substring")


SexLiteral = Literal["female", "male", "other", "unknown"]
SymptomClusterLiteral = Literal[
    "respiratory", "breast", "gi", "gyn", "heme", "other", "unknown"
]
SmokingLiteral = Literal["never", "former", "current", "unknown"]
EducationLiteral = Literal["low", "mid", "high", "unknown"]
CarePhaseLiteral = Literal[
    "pre_contact", "primary_care", "diagnostics", "mdt", "treatment"
]


class PatientAnalyzeRequest(BaseModel):
    # Tier A (required behaviour preserved)
    patient_id: str
    region_name: str
    age: float
    public_care_track: bool = True
    symptom_severity_score: float = Field(
        ..., ge=0, le=10, description="Agent symptom severity score 0–10"
    )
    g8_frailty_score: Optional[float] = Field(
        default=None, description="G8 frailty score; <14 indicates frailty"
    )
    missing_staging_fields: list[str] = Field(default_factory=list)

    # Tier B (optional; safe defaults for older clients)
    sex: Optional[SexLiteral] = "unknown"
    symptom_onset_days: Optional[float] = Field(
        default=None, ge=0, description="Days since symptom onset if known"
    )
    primary_symptom_cluster: Optional[SymptomClusterLiteral] = "unknown"
    smoking_status: Optional[SmokingLiteral] = "unknown"
    lives_alone: Optional[bool] = None
    travel_time_to_care_minutes: Optional[float] = Field(
        default=None, ge=0, description="One-way travel time to usual care site"
    )
    needs_interpreter: bool = False
    education_band: Optional[EducationLiteral] = "unknown"
    already_referred_to_specialist: bool = False
    care_phase: Optional[CarePhaseLiteral] = "primary_care"
    language: Optional[str] = None
    comorbidity_flags: list[str] = Field(default_factory=list)
    agent_confidence: Optional[float] = Field(
        default=None, ge=0, le=1, description="Agent confidence 0–1 if present"
    )


# ---------------------------------------------------------------------------
# Startup / data helpers
# ---------------------------------------------------------------------------


def get_bundle() -> dict[str, Any]:
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = load_bundle(BUNDLE_PATH)
    return _BUNDLE


def get_regions_df() -> pd.DataFrame:
    """Latest real indicators per county from clean_cancer_training_data.csv."""
    global _REGIONS_DF
    if _REGIONS_DF is None:
        df = pd.read_csv(DATA_PATH)
        latest = (
            df.sort_values("year")
            .groupby("region_name", as_index=False)
            .tail(1)
            .sort_values("region_id")
            .reset_index(drop=True)
        )
        _REGIONS_DF = latest
    return _REGIONS_DF


@app.on_event("startup")
def _startup() -> None:
    get_bundle()
    get_regions_df()


def _series_to_indicator_dict(row: Mapping[str, Any] | pd.Series) -> dict[str, Any]:
    out: dict[str, Any] = {}
    keys = set(row.index) if isinstance(row, pd.Series) else set(row)
    for col in INDICATOR_COLUMNS:
        if col not in keys:
            continue
        val = row[col]
        if pd.isna(val):
            out[col] = None
        elif isinstance(val, (int, float, np.floating, np.integer)):
            out[col] = float(val)
        else:
            out[col] = val
    return out


def _predict_row(bundle: Mapping[str, Any], row: pd.Series) -> float:
    X = _feature_frame(bundle, row)
    return float(bundle["pipeline"].predict(X)[0])


def _cv_summary(bundle: Mapping[str, Any]) -> dict[str, Any]:
    best = bundle.get("best_model")
    metrics = next(
        (m for m in bundle.get("cv_metrics", []) if m.get("model") == best),
        None,
    )
    if metrics is None:
        return {"best_model": best}
    return {
        "best_model": best,
        "mae_mean": metrics.get("mae_mean"),
        "mae_std": metrics.get("mae_std"),
        "rmse_mean": metrics.get("rmse_mean"),
        "r2_mean": metrics.get("r2_mean"),
    }


def _confidence_block(
    bundle: Mapping[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    """Explicitly separate validated registry findings from calibrated projections."""
    cv = _cv_summary(bundle)
    if mode == "region":
        calibrated = (
            "Predicted cancer_index_age_std and SHAP attributions are model outputs "
            "from the county feature profile, not observed outcomes."
        )
    else:
        calibrated = (
            "Pathway day estimates and doctor_micro triage actions are calibrated "
            "projections against Prof. Outi Kuitunen's Finnish lung-cancer pathway "
            "benchmarks (50 / 41 / 58 / 155 days), not measured patient timelines."
        )
    return {
        "model": cv,
        "data_year_basis": "Latest available county year in training table / Sotkanet extract",
        "distinction": {
            "validated_findings": (
                "County indicators and observed cancer_index_age_std come from "
                "validated THL Sotkanet / Finnish Cancer Registry inputs in the "
                "training extract. Treat these as the evidence baseline."
            ),
            "calibrated_projections": calibrated,
        },
        "limitations": [
            "GroupKFold CV R² can be weak; use predictions for relative prioritisation, not absolute risk labels.",
            "SHAP explains the fitted model, not causal effects.",
            "Patient pathway days are heuristic calibrations for triage support, not clinical orders.",
            "National Cancer Strategy interventions are mapped from adverse SHAP families and require local validation.",
        ],
    }


def _supporting_evidence(
    *,
    include_pathway_benchmarks: bool = False,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "validated_sources": list(VALIDATED_SOURCES),
        "strategy_reference": STRATEGY_REF,
        "evidence_classes": {
            "validated_thl_fcr": (
                "Observed county indicators and cancer_index_age_std from "
                "THL Sotkanet / Finnish Cancer Registry extracts."
            ),
            "calibrated_projections": (
                "Model predictions, SHAP contributions, and "
                "(when present) Kuitunen-calibrated pathway day estimates."
            ),
        },
    }
    if include_pathway_benchmarks:
        evidence["kuitunen_pathway_benchmarks_days"] = dict(KUITUNEN_BENCHMARKS)
        evidence["kuitunen_source"] = (
            "Prof. Outi Kuitunen Finnish lung-cancer pathway study "
            "(patient 50d + primary care 41d + specialist 58d = 155d)"
        )
    return evidence


def _patient_intake_dict(body: PatientAnalyzeRequest) -> dict[str, Any]:
    """Full Tier A + Tier B intake echoed to the agent (not fed into SHAP/ML)."""
    return {
        "patient_id": body.patient_id,
        "age": body.age,
        "public_care_track": body.public_care_track,
        "symptom_severity_score": body.symptom_severity_score,
        "g8_frailty_score": body.g8_frailty_score,
        "missing_staging_fields": list(body.missing_staging_fields),
        "sex": body.sex if body.sex is not None else "unknown",
        "symptom_onset_days": body.symptom_onset_days,
        "primary_symptom_cluster": (
            body.primary_symptom_cluster
            if body.primary_symptom_cluster is not None
            else "unknown"
        ),
        "smoking_status": (
            body.smoking_status if body.smoking_status is not None else "unknown"
        ),
        "lives_alone": body.lives_alone,
        "travel_time_to_care_minutes": body.travel_time_to_care_minutes,
        "needs_interpreter": body.needs_interpreter,
        "education_band": (
            body.education_band if body.education_band is not None else "unknown"
        ),
        "already_referred_to_specialist": body.already_referred_to_specialist,
        "care_phase": body.care_phase if body.care_phase is not None else "primary_care",
        "language": body.language,
        "comorbidity_flags": list(body.comorbidity_flags),
        "agent_confidence": body.agent_confidence,
    }


def _is_remote_county(region_name: str) -> bool:
    name = region_name.casefold()
    remote_tokens = ("lapland", "lappi", "kainuu", "north karelia", "pohjois-karjala")
    return any(token in name for token in remote_tokens)


def _patient_blind_spots(
    body: PatientAnalyzeRequest,
    *,
    region_name: str,
) -> list[str]:
    """High-value missing fields the conversational agent can ask about next."""
    spots: list[str] = []
    sex = body.sex if body.sex is not None else "unknown"
    cluster = (
        body.primary_symptom_cluster
        if body.primary_symptom_cluster is not None
        else "unknown"
    )
    smoking = body.smoking_status if body.smoking_status is not None else "unknown"
    education = body.education_band if body.education_band is not None else "unknown"

    if body.age >= 70 and body.g8_frailty_score is None:
        spots.append("g8_frailty_score")
    if body.symptom_onset_days is None:
        spots.append("symptom_onset_days")
    if sex == "unknown":
        spots.append("sex")
    if cluster == "unknown":
        spots.append("primary_symptom_cluster")
    if smoking == "unknown":
        spots.append("smoking_status")
    if body.lives_alone is None and body.age >= 70:
        spots.append("lives_alone")
    if body.travel_time_to_care_minutes is None and _is_remote_county(region_name):
        spots.append("travel_time_to_care_minutes")
    if education == "unknown":
        spots.append("education_band")
    if body.needs_interpreter and not body.language:
        spots.append("language")
    return spots


def _filter_department_macro_for_patient(
    macros: list[dict[str, Any]],
    intake: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Light re-rank/filter for patient responses only (region endpoint untouched)."""
    sex = str(intake.get("sex") or "unknown").casefold()
    if sex != "male":
        return macros

    filtered: list[dict[str, Any]] = []
    for rec in macros:
        feature = str(rec.get("driver_feature") or "")
        # Cervical screening macro is not patient-relevant for male intake.
        if "cervical" in feature.casefold():
            continue
        filtered.append(rec)

    # Re-number priorities after filtering.
    for idx, rec in enumerate(filtered, start=1):
        rec["priority"] = idx
    return filtered


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> JSONResponse:
    bundle = get_bundle()
    table = bundle["latest_county_table"]
    payload = {
        "status": "ok",
        "service": "OncoFlow API",
        "version": app.version,
        "model": {
            "artifact_path": str(BUNDLE_PATH.as_posix()),
            "best_model": bundle.get("best_model"),
            "target": bundle.get("target"),
            "features": list(bundle.get("features", [])),
            "n_counties": int(len(table)),
            "cv": _cv_summary(bundle),
        },
    }
    return json_ok(payload)


@app.get("/regions")
def list_regions() -> JSONResponse:
    df = get_regions_df()
    regions: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        indicators = {
            col: (None if pd.isna(row[col]) else float(row[col]))
            for col in INDICATOR_COLUMNS
            if col in df.columns
        }
        regions.append(
            {
                "region_id": int(row["region_id"]),
                "region_name": str(row["region_name"]),
                "year": int(row["year"]),
                "indicators": indicators,
                "source": "THL Sotkanet / Finnish Cancer Registry (clean_cancer_training_data.csv)",
            }
        )
    payload = {
        "count": len(regions),
        "year": int(df["year"].max()) if len(df) else None,
        "regions": regions,
    }
    return json_ok(payload)


@app.post("/analyze/region")
def analyze_region(body: RegionAnalyzeRequest) -> JSONResponse:
    bundle = get_bundle()
    features: list[str] = list(bundle["features"])

    try:
        baseline_row = _county_row(bundle, body.region_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    region_name = str(baseline_row["region_name"])
    region_id = int(baseline_row["region_id"])
    year = int(baseline_row["year"])
    observed = baseline_row.get("cancer_index_age_std")
    observed_f = float(observed) if observed is not None and pd.notna(observed) else None

    baseline_pred = _predict_row(bundle, baseline_row)
    baseline_features = {
        f: (None if pd.isna(baseline_row.get(f)) else float(baseline_row.get(f)))
        for f in features
    }
    shap_drivers = county_shap_drivers(bundle, body.region_name, top_n=5)
    macro_recs = recommendations_as_dicts(
        regional_recommendations(bundle, body.region_name)
    )

    gap = None
    if observed_f is not None:
        gap = round(baseline_pred - observed_f, 4)

    payload = {
        "predictions_and_gaps": {
            "region_id": region_id,
            "region_name": region_name,
            "year": year,
            "observed_cancer_index_age_std": observed_f,
            "observed_evidence_class": "validated_thl_fcr",
            "predicted_cancer_index_age_std": baseline_pred,
            "predicted_evidence_class": "calibrated_projection",
            "prediction_minus_observed": gap,
            "baseline_features": baseline_features,
        },
        "contributing_factors": {
            "shap_drivers_baseline": shap_drivers,
            "interpretation": (
                "Positive SHAP pushes predicted cancer_index_age_std up; "
                "adverse_direction marks pressure relative to the national median."
            ),
        },
        "recommended_interventions": {
            "department_macro": macro_recs,
            "target_level": "department_macro",
        },
        "supporting_evidence": _supporting_evidence(include_pathway_benchmarks=False),
        "confidence_and_limitations": _confidence_block(bundle, mode="region"),
    }
    return json_ok(payload)


@app.post("/analyze/patient")
def analyze_patient(body: PatientAnalyzeRequest) -> JSONResponse:
    bundle = get_bundle()

    try:
        county_row = _county_row(bundle, body.region_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    region_name = str(county_row["region_name"])
    region_id = int(county_row["region_id"])
    year = int(county_row["year"])

    # Full A+B intake for pathway / doctor_micro only — never into county ML/SHAP.
    intake = _patient_intake_dict(body)
    pathway = estimate_pathway_days(county_row, intake)
    micro_recs = recommendations_as_dicts(
        patient_recommendations(bundle, body.region_name, intake)
    )
    macro_recs = _filter_department_macro_for_patient(
        recommendations_as_dicts(
            regional_recommendations(bundle, body.region_name)
        ),
        intake,
    )
    shap_drivers = county_shap_drivers(bundle, body.region_name, top_n=5)
    blind_spots = _patient_blind_spots(body, region_name=region_name)

    smoking = intake.get("smoking_status") or "unknown"
    travel = body.travel_time_to_care_minutes

    observed = county_row.get("cancer_index_age_std")
    observed_f = float(observed) if observed is not None and pd.notna(observed) else None
    predicted = _predict_row(bundle, county_row)

    features: list[str] = list(bundle["features"])
    county_indicators = {
        f: (None if pd.isna(county_row.get(f)) else float(county_row.get(f)))
        for f in features
    }
    # Prefer full CSV indicators when available for validated context
    regions_df = get_regions_df()
    csv_hit = regions_df.loc[
        regions_df["region_name"].str.casefold() == region_name.casefold()
    ]
    if not csv_hit.empty:
        county_indicators = _series_to_indicator_dict(csv_hit.iloc[0])

    payload = {
        "predictions_and_gaps": {
            "patient_id": body.patient_id,
            "region_id": region_id,
            "region_name": region_name,
            "year": year,
            "intake": intake,
            "blind_spots": blind_spots,
            "pathway_days_estimate": pathway,
            "pathway_evidence_class": "calibrated_projection",
            "county_context": {
                "observed_cancer_index_age_std": observed_f,
                "observed_evidence_class": "validated_thl_fcr",
                "predicted_cancer_index_age_std": predicted,
                "predicted_evidence_class": "calibrated_projection",
                "indicators": county_indicators,
            },
            "gap_vs_kuitunen_total_days": pathway.get("excess_vs_benchmark_days"),
        },
        "contributing_factors": {
            "county_shap_drivers": shap_drivers,
            "intake_risk_flags": {
                "public_care_track": body.public_care_track,
                "high_symptom_severity": body.symptom_severity_score >= 6,
                "frail_or_older": (
                    (body.g8_frailty_score is not None and body.g8_frailty_score < 14)
                    or body.age >= 75
                ),
                "missing_staging_fields": list(body.missing_staging_fields),
                "lives_alone": body.lives_alone is True,
                "needs_interpreter": body.needs_interpreter,
                "smoking_risk": smoking in {"current", "former"},
                "high_travel": travel is not None and travel > 60,
                "already_referred": body.already_referred_to_specialist,
            },
            "blind_spots": blind_spots,
        },
        "recommended_interventions": {
            "doctor_micro": micro_recs,
            "department_macro": macro_recs,
            "primary_target_level": "doctor_micro",
        },
        "supporting_evidence": _supporting_evidence(include_pathway_benchmarks=True),
        "confidence_and_limitations": _confidence_block(bundle, mode="patient"),
    }
    return json_ok(payload)
