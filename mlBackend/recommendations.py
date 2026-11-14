"""OncoFlow recommendation engine: regional (macro) + patient (micro) actions.

Uses ``artifacts/oncoflow_bundle.joblib`` SHAP drivers for wellbeing-services
counties and maps them to Finland's National Cancer Strategy 2026–2035.
Patient recommendations combine the county baseline with agent intake fields,
calibrated to Prof. Outi Kuitunen's Finnish lung-cancer pathway benchmarks
(155 days total: 50d patient, 41d primary care, 58d specialist care).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent
ARTIFACT_PATH = _ROOT / "artifacts" / "oncoflow_bundle.joblib"

TargetLevel = Literal["doctor_micro", "department_macro"]

# Prof. Outi Kuitunen lung-cancer pathway benchmarks (Finland, days).
KUITUNEN_BENCHMARKS = {
    "patient_days": 50.0,
    "primary_care_days": 41.0,
    "specialist_care_days": 58.0,
    "total_days": 155.0,
}

# Features where higher values indicate pressure / inequity for cancer outcomes.
HIGH_IS_BAD = {
    "gp_wait_over_7d_pct",
    "gp_wait_over_3mo_pct",
    "pop_75plus_living_alone_pct",
}

# Features where lower values indicate gaps (education, geriatric assessment, screening invites).
LOW_IS_BAD = {
    "higher_education_pct",
    "pop_75plus_rai_assessed_pct",
    "cr_3620_proportion_of_women_invited_to_cervical_cance",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_",
}

SCREENING_FEATURES = {
    "cr_3620_proportion_of_women_invited_to_cervical_cance",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_",
}

# Strategy 2026–2035 intervention catalogue keyed by driver family.
FEATURE_LABELS: dict[str, str] = {
    "gp_wait_over_7d_pct": "GP wait over 7 days",
    "gp_wait_over_3mo_pct": "GP wait over 3 months",
    "gp_outpatient_visits_per_1000": "GP outpatient visits",
    "higher_education_pct": "higher education share",
    "pop_75plus_living_alone_pct": "75+ living alone",
    "pop_75plus_rai_assessed_pct": "75+ RAI assessment coverage",
    "cr_3620_proportion_of_women_invited_to_cervical_cance": "cervical screening invitations",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_": "breast screening invitations",
}

STRATEGY_INTERVENTIONS: dict[str, dict[str, Any]] = {
    "gp_wait": {
        "action": (
            "Expand the personal-physician model and add primary-care physician "
            "capacity so cancer-suspect symptoms are seen within days, not weeks "
            "(National Cancer Strategy 2026–2035, sub-objective 2.5)."
        ),
        "responsible_actor": (
            "Wellbeing services county primary healthcare leadership; "
            "FICAN coordination"
        ),
        "justification_template": (
            "{feature_label} is among this county’s top pressure points "
            "(currently {value:.1f}%). Long GP waits delay early detection; "
            "strategy 2.5 calls for straightforward primary-care access and "
            "standardised cancer-suspicion referral criteria."
        ),
        "expected_impact": (
            "Shorter waits to see a GP for cancer-suspect symptoms; "
            "higher share of cancers diagnosed at stages I–II."
        ),
        "success_metrics": [
            "Median days from first contact to GP assessment for cancer-suspect symptoms",
            "Share of residents waiting >7 days / >3 months for non-urgent primary care",
            "Proportion of cancer-suspect referrals meeting national pathway criteria",
        ],
    },
    "education_literacy": {
        "action": (
            "Deploy a targeted, multichannel cancer-symptom and screening awareness "
            "campaign for lower-education and linguistic-minority residents "
            "(strategy sub-objective 1.3 on health literacy)."
        ),
        "responsible_actor": (
            "Wellbeing services county communications & prevention; "
            "FICAN; Cancer Society of Finland"
        ),
        "justification_template": (
            "The county’s {feature_label} is relatively low ({value:.1f}%), which "
            "points to socioeconomic and health-literacy risk. Strategy 1.3 links "
            "limited literacy to delayed care-seeking and weaker screening participation."
        ),
        "expected_impact": (
            "Fewer avoidable delays from symptom to first contact; "
            "narrower education-linked gaps in screening and outcomes."
        ),
        "success_metrics": [
            "Screening participation by education / mother-tongue stratum",
            "Share of residents recognising key cancer alarm symptoms (survey)",
            "Median patient delay from symptom onset to first contact",
        ],
    },
    "living_alone_75plus": {
        "action": (
            "Strengthen outreach and care-navigation for people aged 75+ living alone, "
            "including proactive symptom checks and social-care linkage into cancer pathways "
            "(strategy equality theme: older people; sub-objectives 3.3–3.4)."
        ),
        "responsible_actor": (
            "Wellbeing services county home care / older-people services; "
            "primary healthcare"
        ),
        "justification_template": (
            "Elevated {feature_label} ({value:.1f}%) concentrates frailty and delayed "
            "help-seeking. Strategy emphasises functional-capacity–guided care and early "
            "psychosocial / social-work support for older adults."
        ),
        "expected_impact": (
            "Earlier presentation among isolated older adults; fewer late-stage diagnoses "
            "in the 75+ cohort."
        ),
        "success_metrics": [
            "Time from symptom onset to first contact among 75+ living alone",
            "Share of 75+ cancer patients with a named care coordinator",
            "Stage I–II diagnosis rate in 75+ residents",
        ],
    },
    "rai_g8": {
        "action": (
            "Scale RAI / functional-capacity assessment coverage for 75+ and introduce "
            "the G8 screening tool in all units treating older cancer patients, feeding "
            "results into primary-care referrals (strategy sub-objective 3.4)."
        ),
        "responsible_actor": (
            "Wellbeing services county geriatric and oncology services; "
            "City of Helsinki / HUS where applicable"
        ),
        "justification_template": (
            "Low {feature_label} ({value:.1f}%) indicates incomplete geriatric assessment. "
            "Strategy 3.4 requires G8 screening, geriatric assessment for abnormal results, "
            "and functional-capacity data already in primary care."
        ),
        "expected_impact": (
            "Treatment plans matched to frailty rather than chronological age; safer "
            "diagnostics and fewer avoidable complications in frail patients."
        ),
        "success_metrics": [
            "75+ RAI assessment coverage",
            "Share of older cancer patients screened with G8",
            "Share of counties offering primary-care consult to a geriatric oncology team",
        ],
    },
    "screening_invitation": {
        "action": (
            "Close invitation and organisation gaps in national breast and cervical "
            "screening: apply screening quality manuals, fix invitation-list coverage, "
            "and target under-reached groups so every county approaches ≥80% participation "
            "(strategy sub-objectives 2.3–2.4)."
        ),
        "responsible_actor": (
            "Wellbeing services county screening organiser; Finnish Cancer Registry; "
            "national cancer screening steering group / FICAN"
        ),
        "justification_template": (
            "A gap in {feature_label} (currently {value:.1f}%) signals uneven organised "
            "screening reach. Strategy 2.3–2.4 require high-quality, equitable invitation "
            "of the target population and ≥80% participation in each wellbeing services county."
        ),
        "expected_impact": (
            "Higher early detection via organised screening; more cancers found at "
            "stages I–II."
        ),
        "success_metrics": [
            "Invitation coverage of eligible target population (%)",
            "Screening participation rate by county (target ≥80%)",
            "Share of screen-detected vs symptomatic cancers",
        ],
    },
}

FEATURE_TO_FAMILY: dict[str, str] = {
    "gp_wait_over_7d_pct": "gp_wait",
    "gp_wait_over_3mo_pct": "gp_wait",
    "higher_education_pct": "education_literacy",
    "pop_75plus_living_alone_pct": "living_alone_75plus",
    "pop_75plus_rai_assessed_pct": "rai_g8",
    "cr_3620_proportion_of_women_invited_to_cervical_cance": "screening_invitation",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_": "screening_invitation",
}


@dataclass
class Recommendation:
    """Structured OncoFlow recommendation for UI / agent consumers."""

    target_level: TargetLevel
    action: str
    responsible_actor: str
    justification: str
    expected_impact: str
    success_metrics: list[str]
    driver_feature: str | None = None
    shap_value: float | None = None
    region_name: str | None = None
    pathway_days: dict[str, float] | None = None
    priority: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_bundle(path: Path | str = ARTIFACT_PATH) -> dict[str, Any]:
    """Load the trained OncoFlow artifact bundle."""
    bundle = joblib.load(path)
    required = {"pipeline", "explainer", "features", "latest_county_table"}
    missing = required - set(bundle)
    if missing:
        raise KeyError(f"oncoflow_bundle missing keys: {sorted(missing)}")
    return bundle


def _county_row(bundle: Mapping[str, Any], region: str | int) -> pd.Series:
    table: pd.DataFrame = bundle["latest_county_table"]
    if isinstance(region, (int, np.integer)) or (
        isinstance(region, str) and region.isdigit()
    ):
        rid = int(region)
        hits = table.loc[table["region_id"] == rid]
        key = f"region_id={rid}"
    else:
        hits = table.loc[table["region_name"].str.casefold() == str(region).casefold()]
        if hits.empty:
            hits = table.loc[
                table["region_name"].str.contains(str(region), case=False, regex=False)
            ]
        key = f"region_name={region!r}"
    if hits.empty:
        available = table["region_name"].tolist()
        raise ValueError(f"No county match for {key}. Available: {available}")
    return hits.iloc[0]


def _feature_frame(bundle: Mapping[str, Any], row: pd.Series) -> pd.DataFrame:
    features: list[str] = list(bundle["features"])
    return pd.DataFrame([{f: row.get(f) for f in features}], columns=features)


def _imputed_matrix(bundle: Mapping[str, Any], X: pd.DataFrame) -> np.ndarray:
    return bundle["pipeline"].named_steps["imputer"].transform(X)


def county_shap_drivers(
    bundle: Mapping[str, Any],
    region: str | int,
    *,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Return top-|SHAP| feature contributions for a county's latest profile."""
    row = _county_row(bundle, region)
    features: list[str] = list(bundle["features"])
    X = _feature_frame(bundle, row)
    Xi = _imputed_matrix(bundle, X)
    shap_values = np.asarray(bundle["explainer"].shap_values(Xi))[0]

    table: pd.DataFrame = bundle["latest_county_table"]
    medians = {
        f: float(pd.to_numeric(table[f], errors="coerce").median(skipna=True))
        for f in features
    }

    drivers: list[dict[str, Any]] = []
    for feature, value, shap_v in zip(features, Xi[0], shap_values):
        median = medians.get(feature, float("nan"))
        if feature in HIGH_IS_BAD:
            adverse = bool(value >= median) if np.isfinite(median) else True
        elif feature in LOW_IS_BAD:
            adverse = bool(value <= median) if np.isfinite(median) else True
        else:
            adverse = False
        drivers.append(
            {
                "feature": feature,
                "value": float(value),
                "shap_value": float(shap_v),
                "abs_shap": float(abs(shap_v)),
                "national_median": median,
                "adverse_direction": adverse,
                "family": FEATURE_TO_FAMILY.get(feature),
            }
        )
    drivers.sort(key=lambda d: d["abs_shap"], reverse=True)
    return drivers[:top_n]


def _macro_from_driver(
    driver: Mapping[str, Any],
    *,
    region_name: str,
    priority: int,
) -> Recommendation | None:
    family = driver.get("family")
    if not family or family not in STRATEGY_INTERVENTIONS:
        return None
    if not driver.get("adverse_direction", False):
        return None

    spec = STRATEGY_INTERVENTIONS[family]
    feature = driver["feature"]
    feature_label = FEATURE_LABELS.get(feature, feature.replace("_", " "))
    return Recommendation(
        target_level="department_macro",
        action=spec["action"],
        responsible_actor=spec["responsible_actor"],
        justification=spec["justification_template"].format(
            feature_label=feature_label,
            value=driver["value"],
        ),
        expected_impact=spec["expected_impact"],
        success_metrics=list(spec["success_metrics"]),
        driver_feature=feature,
        shap_value=float(driver["shap_value"]),
        region_name=region_name,
        priority=priority,
        metadata={
            "strategy_family": family,
            "feature_value": driver["value"],
            "shap_value": float(driver["shap_value"]),
            "national_median": driver["national_median"],
            "source": "National Cancer Strategy 2026–2035",
        },
    )


def regional_recommendations(
    bundle: Mapping[str, Any],
    region: str | int,
    *,
    top_n: int = 5,
    max_actions: int = 4,
) -> list[Recommendation]:
    """Map top adverse SHAP drivers to department-level strategy interventions."""
    row = _county_row(bundle, region)
    region_name = str(row["region_name"])
    drivers = county_shap_drivers(bundle, region, top_n=top_n)

    recs: list[Recommendation] = []
    seen_families: set[str] = set()
    priority = 1
    for driver in drivers:
        family = driver.get("family")
        if family in seen_families:
            continue
        rec = _macro_from_driver(driver, region_name=region_name, priority=priority)
        if rec is None:
            continue
        seen_families.add(str(family))
        recs.append(rec)
        priority += 1
        if len(recs) >= max_actions:
            break
    return recs


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _intake_str(intake: Mapping[str, Any], key: str, default: str = "unknown") -> str:
    raw = intake.get(key, default)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().casefold()


def _intake_float(intake: Mapping[str, Any], key: str) -> float | None:
    raw = intake.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def _intake_bool(intake: Mapping[str, Any], key: str, default: bool | None = None) -> bool | None:
    if key not in intake:
        return default
    raw = intake.get(key)
    if raw is None:
        return default
    return bool(raw)


def estimate_pathway_days(
    county_row: Mapping[str, Any] | pd.Series,
    intake: Mapping[str, Any],
) -> dict[str, float]:
    """Calibrate Kuitunen pathway segments using county baseline + intake fields.

    Base: patient 50d, primary care 41d, specialist 58d (total 155d).
    Multipliers reflect GP wait pressure, public track, age/frailty, symptom
    severity, incomplete staging, and optional Tier B personal fields.
    Personal fields never enter the county ML / SHAP path.
    """
    b = KUITUNEN_BENCHMARKS
    wait7 = float(pd.to_numeric(county_row.get("gp_wait_over_7d_pct"), errors="coerce") or 40.0)
    wait3m = float(
        pd.to_numeric(county_row.get("gp_wait_over_3mo_pct"), errors="coerce") or 1.0
    )
    edu = float(pd.to_numeric(county_row.get("higher_education_pct"), errors="coerce") or 30.0)
    alone = float(
        pd.to_numeric(county_row.get("pop_75plus_living_alone_pct"), errors="coerce") or 45.0
    )

    age = float(intake.get("age") or 65)
    public_track = bool(intake.get("public_care_track", True))
    severity = float(intake.get("symptom_severity_score") or 5)  # 0–10
    g8 = intake.get("g8_frailty_score")
    g8_score = float(g8) if g8 is not None and str(g8) != "" else None
    missing_staging = intake.get("missing_staging_fields") or []
    if isinstance(missing_staging, str):
        missing_staging = [s.strip() for s in missing_staging.split(",") if s.strip()]
    n_missing = len(list(missing_staging))

    # Tier B (optional)
    education_band = _intake_str(intake, "education_band", "unknown")
    lives_alone = _intake_bool(intake, "lives_alone", None)
    travel_min = _intake_float(intake, "travel_time_to_care_minutes")
    needs_interpreter = bool(intake.get("needs_interpreter", False))
    smoking_status = _intake_str(intake, "smoking_status", "unknown")
    symptom_cluster = _intake_str(intake, "primary_symptom_cluster", "unknown")
    symptom_onset_days = _intake_float(intake, "symptom_onset_days")
    already_referred = bool(intake.get("already_referred_to_specialist", False))

    # Patient delay: literacy/isolation inflate; high severity should shorten if acted on.
    patient_mult = 1.0
    if education_band == "low":
        patient_mult += 0.12
    elif education_band == "high":
        patient_mult -= 0.08
    elif education_band == "mid":
        patient_mult += 0.0
    else:
        # Fall back to county higher_education_pct when band unknown.
        patient_mult += _clamp((30.0 - edu) / 40.0, -0.15, 0.25)

    if age >= 75:
        patient_mult += 0.08 + _clamp((alone - 45.0) / 40.0, 0.0, 0.12)
    if lives_alone is True:
        patient_mult += 0.10 if age >= 75 else 0.05

    # Long-standing symptoms nudge patient delay up; very recent + severe → don't inflate.
    if symptom_onset_days is not None:
        if symptom_onset_days > 50:
            patient_mult += _clamp((symptom_onset_days - 50.0) / 100.0, 0.0, 0.20)
        elif symptom_onset_days <= 14 and severity >= 7:
            patient_mult -= 0.06

    if needs_interpreter:
        patient_mult += 0.08

    patient_mult -= _clamp((severity - 5.0) / 20.0, -0.05, 0.20)
    patient_days = b["patient_days"] * _clamp(patient_mult, 0.55, 1.55)

    # Primary care: GP waits + public track dominate; severity/frailty need fast-track.
    primary_mult = 1.0
    primary_mult += _clamp((wait7 - 40.0) / 50.0, -0.15, 0.35)
    primary_mult += _clamp(wait3m / 5.0, 0.0, 0.20)
    if public_track:
        primary_mult += 0.12
    else:
        primary_mult -= 0.08
    # Unrecognised mild symptoms linger; clear severe symptoms should trigger fast track.
    if severity < 4:
        primary_mult += 0.15
    elif severity >= 7:
        primary_mult -= 0.10
    if g8_score is not None and g8_score < 14:
        # Frail (G8 < 14): needs geriatric assessment — adds coordination unless pathway exists.
        primary_mult += 0.08

    if travel_min is not None:
        if travel_min > 120:
            primary_mult += 0.12
        elif travel_min > 60:
            primary_mult += 0.06

    if needs_interpreter:
        primary_mult += 0.05

    # Smoking + respiratory: urgency compresses primary when severity high.
    if (
        smoking_status in {"current", "former"}
        and symptom_cluster == "respiratory"
        and severity >= 6
    ):
        primary_mult -= 0.08

    # Already past GP gate — do not inflate primary the same way.
    if already_referred:
        primary_mult = min(primary_mult, 1.0)
        primary_mult -= 0.10

    primary_days = b["primary_care_days"] * _clamp(primary_mult, 0.50, 1.70)

    # Specialist: staging gaps and frailty work-up stretch imaging / MDT intervals.
    specialist_mult = 1.0
    specialist_mult += 0.06 * n_missing
    if age >= 75:
        specialist_mult += 0.05
    if g8_score is not None and g8_score < 14:
        specialist_mult += 0.10
    if public_track:
        specialist_mult += 0.05
    if severity >= 8:
        specialist_mult -= 0.08  # urgent pathway compression
    if travel_min is not None:
        if travel_min > 120:
            specialist_mult += 0.08
        elif travel_min > 60:
            specialist_mult += 0.04
    specialist_days = b["specialist_care_days"] * _clamp(specialist_mult, 0.55, 1.65)

    total = patient_days + primary_days + specialist_days
    return {
        "patient_days": round(patient_days, 1),
        "primary_care_days": round(primary_days, 1),
        "specialist_care_days": round(specialist_days, 1),
        "total_days": round(total, 1),
        "benchmark_total_days": b["total_days"],
        "excess_vs_benchmark_days": round(total - b["total_days"], 1),
    }


def patient_recommendations(
    bundle: Mapping[str, Any],
    region: str | int,
    intake: Mapping[str, Any],
) -> list[Recommendation]:
    """Combine county baseline with agent intake into doctor-level actions."""
    row = _county_row(bundle, region)
    region_name = str(row["region_name"])
    pathway = estimate_pathway_days(row, intake)

    age = float(intake.get("age") or 65)
    public_track = bool(intake.get("public_care_track", True))
    severity = float(intake.get("symptom_severity_score") or 5)
    g8 = intake.get("g8_frailty_score")
    g8_score = float(g8) if g8 is not None and str(g8) != "" else None
    missing_staging = intake.get("missing_staging_fields") or []
    if isinstance(missing_staging, str):
        missing_staging = [s.strip() for s in missing_staging.split(",") if s.strip()]
    missing_staging = list(missing_staging)

    sex = _intake_str(intake, "sex", "unknown")
    education_band = _intake_str(intake, "education_band", "unknown")
    needs_interpreter = bool(intake.get("needs_interpreter", False))
    smoking_status = _intake_str(intake, "smoking_status", "unknown")
    symptom_cluster = _intake_str(intake, "primary_symptom_cluster", "unknown")
    symptom_onset_days = _intake_float(intake, "symptom_onset_days")
    already_referred = bool(intake.get("already_referred_to_specialist", False))
    care_phase = _intake_str(intake, "care_phase", "primary_care")
    travel_min = _intake_float(intake, "travel_time_to_care_minutes")
    comorbidity_flags = intake.get("comorbidity_flags") or []
    if isinstance(comorbidity_flags, str):
        comorbidity_flags = [s.strip() for s in comorbidity_flags.split(",") if s.strip()]
    comorbidity_flags = [str(c).strip().casefold() for c in comorbidity_flags]

    wait7 = float(pd.to_numeric(row.get("gp_wait_over_7d_pct"), errors="coerce") or 40.0)
    recs: list[Recommendation] = []
    priority = 1

    past_gp_gate = already_referred and care_phase in {
        "diagnostics",
        "mdt",
        "treatment",
    }
    fast_track_trigger = (
        pathway["primary_care_days"] > KUITUNEN_BENCHMARKS["primary_care_days"]
        or severity >= 6
    )

    # 1) Cancer-suspicion fast track — suppress/downgrade if already past GP gate.
    if fast_track_trigger and past_gp_gate:
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Patient is already referred / in diagnostics–MDT–treatment: prioritise "
                    "staging completeness, MDT continuity, and timed imaging/report chase "
                    "rather than a new primary-care fast-track referral (strategy 3.2 / 2.5)."
                ),
                responsible_actor="Specialist responsible physician; MDT coordinator; pathway nurse",
                justification=(
                    f"already_referred_to_specialist=true and care_phase={care_phase!r} with "
                    f"symptom_severity_score={severity:.1f} in {region_name}. Primary interval "
                    f"estimate {pathway['primary_care_days']:.1f}d is less actionable once past "
                    "the GP gate; avoid duplicate urgency framing."
                ),
                expected_impact=(
                    "Fewer duplicate primary referrals; smoother MDT / staging progression "
                    f"(current total estimate {pathway['total_days']:.1f}d)."
                ),
                success_metrics=[
                    "Days from referral to MDT decision",
                    "Staging fields complete at MDT (Y/N)",
                    "Imaging/report turnaround days",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "continuity_post_referral",
                    "public_care_track": public_track,
                    "care_phase": care_phase,
                    "downgraded_from": "primary_care_or_severity",
                },
            )
        )
        priority += 1
    elif fast_track_trigger:
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Activate a cancer-suspicion fast track: same-week assessment, "
                    "apply national referral criteria, and order urgent imaging without "
                    "waiting for a routine non-urgent slot (Kuitunen / strategy 2.5)."
                ),
                responsible_actor="Treating GP / primary-care physician; care pathway nurse",
                justification=(
                    f"Estimated primary-care interval {pathway['primary_care_days']:.1f}d "
                    f"(benchmark 41d) in {region_name} with GP wait >7d at {wait7:.1f}% "
                    f"and symptom_severity_score={severity:.1f}"
                    + (" on the public care track." if public_track else ".")
                    + " Kuitunen's Finnish lung-cancer study attributes 41 of 155 days "
                    "to primary care; delays arise from appointment access and missed symptoms."
                ),
                expected_impact=(
                    f"Compress primary-care days toward ≤41 and total pathway toward ≤155 "
                    f"(current estimate {pathway['total_days']:.1f}d)."
                ),
                success_metrics=[
                    "Days from first contact to specialist referral",
                    "Days from referral to first diagnostic imaging",
                    "Whether national cancer-suspicion referral criteria were applied (Y/N)",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "primary_care_or_severity",
                    "public_care_track": public_track,
                },
            )
        )
        priority += 1

    # 2) Patient delay / literacy counselling (interpreter / education / long onset).
    long_onset = symptom_onset_days is not None and symptom_onset_days > 50
    literacy_trigger = (
        pathway["patient_days"] > KUITUNEN_BENCHMARKS["patient_days"]
        or needs_interpreter
        or education_band == "low"
        or long_onset
    )
    if literacy_trigger:
        interpreter_bit = (
            " Arrange a professional interpreter and use plain-language materials "
            "in the patient's preferred language."
            if needs_interpreter
            else " Use plain-language, health-literacy–adapted materials (strategy 1.3)."
        )
        onset_bit = (
            f" Symptom onset reported at {symptom_onset_days:.0f} days."
            if symptom_onset_days is not None
            else ""
        )
        edu_bit = (
            f" education_band={education_band}."
            if education_band != "unknown"
            else (
                f" County higher_education_pct="
                f"{float(pd.to_numeric(row.get('higher_education_pct'), errors='coerce') or 0):.1f}%."
            )
        )
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Provide structured symptom-action counselling and a written safety-net "
                    "plan (when to re-contact, what red flags mean)."
                    + interpreter_bit
                ),
                responsible_actor="Treating clinician with practice nurse / care coordinator",
                justification=(
                    f"Estimated patient-attributable delay {pathway['patient_days']:.1f}d "
                    f"(benchmark ~50d); age={age:.0f}."
                    + edu_bit
                    + onset_bit
                    + (" needs_interpreter=true." if needs_interpreter else "")
                ),
                expected_impact=(
                    "Shorter patient delay on subsequent symptom episodes; clearer "
                    "re-contact behaviour if symptoms progress."
                ),
                success_metrics=[
                    "Documented safety-net advice in the record",
                    "Time from safety-net trigger to re-contact",
                    "Patient-reported understanding of red flags",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "patient_delay_or_literacy",
                    "needs_interpreter": needs_interpreter,
                    "education_band": education_band,
                },
            )
        )
        priority += 1

    # 3) G8 / geriatric pathway for older, frail, or cognitive-impairment flags.
    cognitive = "cognitive_impairment" in comorbidity_flags
    frail = (
        (g8_score is not None and g8_score < 14)
        or age >= 75
        or cognitive
    )
    if frail:
        g8_txt = f"{g8_score:.1f}" if g8_score is not None else "not yet scored"
        cog_bit = " comorbidity includes cognitive_impairment." if cognitive else ""
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Complete / document G8 frailty screening now; if G8 < 14 (or clinical "
                    "frailty), refer for comprehensive geriatric assessment and include "
                    "functional-capacity findings in the specialist referral (strategy 3.4)."
                ),
                responsible_actor="Treating physician; geriatric / geriatric-oncology consult",
                justification=(
                    f"Patient age={age:.0f}, G8={g8_txt}.{cog_bit} Strategy 3.4 requires G8 "
                    "in units treating older cancer patients and functional-capacity data "
                    "already in primary-care referrals. County RAI coverage is a known "
                    "regional gap."
                ),
                expected_impact=(
                    "Treatment intensity matched to function; fewer complications from "
                    "over- or under-treatment of frail patients; specialist work-up planned "
                    "with geriatric input."
                ),
                success_metrics=[
                    "G8 score recorded before treatment decision",
                    "Geriatric assessment completed when G8 < 14 (Y/N)",
                    "Functional capacity included in referral documentation (Y/N)",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "frailty_or_age",
                    "g8_frailty_score": g8_score,
                    "age": age,
                    "cognitive_impairment": cognitive,
                },
            )
        )
        priority += 1

    # 4) Staging completeness for quality / specialist interval.
    if missing_staging or pathway["specialist_care_days"] > KUITUNEN_BENCHMARKS["specialist_care_days"]:
        missing_txt = ", ".join(missing_staging) if missing_staging else "unspecified staging fields"
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Close staging documentation gaps before MDT: complete missing clinical "
                    "stage fields and ensure structured registry notification so diagnostics "
                    "are not re-ordered or delayed (strategy 3.2 / quality register)."
                ),
                responsible_actor="Specialist responsible physician; MDT coordinator",
                justification=(
                    f"Missing staging fields: {missing_txt}. Incomplete clinical notifications "
                    f"and imaging/report waits drive specialist delay "
                    f"({pathway['specialist_care_days']:.1f}d vs 58d benchmark). "
                    "Kuitunen highlights waits for imaging, reports and samples in specialised care."
                ),
                expected_impact=(
                    "Fewer repeat diagnostics; specialist interval closer to ≤58 days; "
                    "better stage capture for early-detection monitoring."
                ),
                success_metrics=[
                    "Proportion of required staging fields complete at MDT",
                    "Days from referral to treatment start",
                    "Clinical cancer notification completeness for this case",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "missing_staging_or_specialist_delay",
                    "missing_staging_fields": missing_staging,
                },
            )
        )
        priority += 1

    # 5) Targeted tips (only when relevant).
    if smoking_status in {"current", "former"} and symptom_cluster == "respiratory":
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Document smoking history (pack-years / quit date) and frame this as a "
                    "lung-suspicion pathway: prioritise urgent chest imaging and apply "
                    "national respiratory cancer-suspicion referral criteria."
                ),
                responsible_actor="Treating clinician; radiology scheduler",
                justification=(
                    f"smoking_status={smoking_status}, primary_symptom_cluster=respiratory, "
                    f"severity={severity:.1f} in {region_name}."
                ),
                expected_impact=(
                    "Faster imaging for high-risk respiratory presentations; clearer "
                    "documentation for MDT / registry."
                ),
                success_metrics=[
                    "Smoking history documented (Y/N)",
                    "Days to chest imaging",
                    "Cancer-suspicion referral criteria applied (Y/N)",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "smoking_respiratory",
                    "smoking_status": smoking_status,
                },
            )
        )
        priority += 1

    if (
        sex == "female"
        and symptom_cluster in {"breast", "gyn"}
        and care_phase in {"pre_contact", "primary_care"}
    ):
        screen_label = "breast" if symptom_cluster == "breast" else "cervical / gyn"
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    f"Use sex-appropriate framing for {screen_label} suspicion: check "
                    "organised screening invitation/participation status and chase missed "
                    "screening or symptomatic work-up without male-pathway language."
                ),
                responsible_actor="Treating GP / women's health pathway nurse",
                justification=(
                    f"sex=female, primary_symptom_cluster={symptom_cluster}, "
                    f"care_phase={care_phase}."
                ),
                expected_impact=(
                    "Earlier detection via screening chase or appropriate symptomatic referral."
                ),
                success_metrics=[
                    "Screening status documented",
                    "Days to diagnostic imaging / specialty referral",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "female_breast_or_gyn",
                    "primary_symptom_cluster": symptom_cluster,
                },
            )
        )
        priority += 1

    if travel_min is not None and travel_min > 60:
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Prefer local / telemedicine steps for early work-up where clinically "
                    "safe; bundle imaging and specialist visits to avoid unnecessary "
                    "long-distance travel."
                ),
                responsible_actor="Care pathway nurse; treating clinician",
                justification=(
                    f"travel_time_to_care_minutes={travel_min:.0f} in {region_name} "
                    f"(>{'120' if travel_min > 120 else '60'} min threshold)."
                ),
                expected_impact=(
                    "Lower travel burden and fewer missed appointments for remote patients."
                ),
                success_metrics=[
                    "Share of early steps completed locally or via telemed",
                    "Missed-appointment rate",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=priority,
                metadata={
                    "trigger": "high_travel",
                    "travel_time_to_care_minutes": travel_min,
                },
            )
        )
        priority += 1

    # 6) Always surface pathway summary if still empty (low-risk profile).
    if not recs:
        recs.append(
            Recommendation(
                target_level="doctor_micro",
                action=(
                    "Continue standard national care-pathway monitoring; re-score symptoms "
                    "and G8 at each contact and escalate if the trajectory exceeds "
                    "Kuitunen segment benchmarks."
                ),
                responsible_actor="Treating physician",
                justification=(
                    f"Estimated pathway {pathway['total_days']:.1f}d is within or near the "
                    f"155-day Finnish lung-cancer benchmark for this intake profile in "
                    f"{region_name}."
                ),
                expected_impact="Maintain timely progression and detect pathway drift early.",
                success_metrics=[
                    "Total days from symptom onset to treatment start",
                    "Segment days vs 50 / 41 / 58 benchmarks",
                ],
                region_name=region_name,
                pathway_days=pathway,
                priority=1,
                metadata={"trigger": "within_benchmark"},
            )
        )

    return recs


def generate_recommendations(
    region: str | int,
    intake: Mapping[str, Any] | None = None,
    *,
    bundle: Mapping[str, Any] | None = None,
    artifact_path: Path | str = ARTIFACT_PATH,
    include_macro: bool = True,
    include_micro: bool = True,
) -> list[Recommendation]:
    """Generate macro and/or micro recommendations for a county (+ optional intake)."""
    b = bundle if bundle is not None else load_bundle(artifact_path)
    out: list[Recommendation] = []
    if include_macro:
        out.extend(regional_recommendations(b, region))
    if include_micro:
        if intake is None:
            raise ValueError("intake is required when include_micro=True")
        out.extend(patient_recommendations(b, region, intake))
    return out


def recommendations_as_dicts(
    recs: Iterable[Recommendation],
) -> list[dict[str, Any]]:
    return [r.to_dict() for r in recs]


def main() -> None:
    """Demo: Helsinki county macro drivers + sample high-risk patient micro actions."""
    bundle = load_bundle()
    region = "City of Helsinki"
    intake = {
        "age": 78,
        "public_care_track": True,
        "symptom_severity_score": 7,
        "g8_frailty_score": 12,
        "missing_staging_fields": ["T", "N", "M"],
    }

    print(f"Region: {region}")
    print("Top SHAP drivers:")
    for d in county_shap_drivers(bundle, region, top_n=5):
        print(
            f"  {d['feature']}: value={d['value']:.2f} shap={d['shap_value']:+.3f} "
            f"adverse={d['adverse_direction']} family={d['family']}"
        )

    recs = generate_recommendations(region, intake, bundle=bundle)
    print(f"\n{len(recs)} recommendations:")
    for r in recs:
        print(f"\n[{r.target_level}] P{r.priority}  {r.action[:100]}...")
        print(f"  actor: {r.responsible_actor}")
        if r.pathway_days:
            print(f"  pathway: {r.pathway_days}")


if __name__ == "__main__":
    main()
