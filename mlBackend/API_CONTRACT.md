# OncoFlow API Contract

Base URL (local): `http://127.0.0.1:8000`

```bash
.venv\Scripts\uvicorn.exe api:app --reload
.venv\Scripts\python.exe test_api.py
```

CORS: enabled for all origins (`*`).

All JSON responses are recursively sanitized: `NaN` / `±Inf` become `null` so payloads are valid with `json.dumps(..., allow_nan=False)`.

## Evidence classes

| Class | Meaning |
|-------|---------|
| `validated_thl_fcr` | Observed THL Sotkanet / Finnish Cancer Registry indicators (e.g. `observed_cancer_index_age_std`, county indicators from `data`) |
| `calibrated_projection` | Model predictions, SHAP attributions, and Kuitunen-calibrated patient pathway days — **not** measured outcomes |

## Shared 5-block response shape

`POST /analyze/region` and `POST /analyze/patient` always return these top-level keys:

1. `predictions_and_gaps`
2. `contributing_factors`
3. `recommended_interventions`
4. `supporting_evidence`
5. `confidence_and_limitations`

---

## `GET /health`

Service status + model metadata from `artifacts`.

### Response `200`

```json
{
  "status": "ok",
  "service": "OncoFlow API",
  "version": "1.0.0",
  "model": {
    "artifact_path": "artifacts/oncoflow_bundle.joblib",
    "best_model": "RandomForestRegressor",
    "target": "cancer_index_age_std",
    "features": [
      "gp_wait_over_7d_pct",
      "gp_wait_over_3mo_pct",
      "gp_outpatient_visits_per_1000",
      "higher_education_pct",
      "pop_75plus_living_alone_pct",
      "pop_75plus_rai_assessed_pct",
      "cr_3620_proportion_of_women_invited_to_cervical_cance",
      "cr_3621_proportion_of_women_invited_to_breast_cancer_"
    ],
    "n_counties": 23,
    "cv": {
      "best_model": "RandomForestRegressor",
      "mae_mean": 4.669205999999993,
      "mae_std": 1.306692622560489,
      "rmse_mean": 6.296502090961064,
      "r2_mean": -0.13815145735811496
    }
  }
}
```

---

## `GET /regions`

All **23** wellbeing services counties with latest real indicators from `data` (currently year **2024**). Missing numeric values serialize as `null`.

### Response `200` (shape; one county shown)

Full response contains `count: 23` and 23 objects in `regions`.

```json
{
  "count": 23,
  "year": 2024,
  "regions": [
    {
      "region_id": 968,
      "region_name": "Lapland wellbeing services county",
      "year": 2024,
      "indicators": {
        "gp_wait_over_7d_pct": 39.5,
        "gp_wait_over_3mo_pct": 0.6,
        "gp_outpatient_visits_per_1000": 6041.0,
        "morbidity_index_age_std": 110.6,
        "higher_education_pct": 29.2,
        "pop_75plus_living_alone_pct": 45.4,
        "pop_75plus_rai_assessed_pct": null,
        "cr_3620_proportion_of_women_invited_to_cervical_cance": 79.9,
        "cr_3621_proportion_of_women_invited_to_breast_cancer_": 83.8,
        "cancer_index_age_std": 89.9
      },
      "source": "THL Sotkanet / Finnish Cancer Registry (clean_cancer_training_data.csv)"
    }
  ]
}
```

---

## `POST /analyze/region`

Regional prediction, SHAP drivers, and `department_macro` strategy recommendations.

### Request

```json
{
  "region_name": "Lapland"
}
```

### Response `200` (exact Lapland example)

```json
{
  "predictions_and_gaps": {
    "region_id": 968,
    "region_name": "Lapland wellbeing services county",
    "year": 2024,
    "observed_cancer_index_age_std": 89.9,
    "observed_evidence_class": "validated_thl_fcr",
    "predicted_cancer_index_age_std": 92.32850000000002,
    "predicted_evidence_class": "calibrated_projection",
    "prediction_minus_observed": 2.4285,
    "baseline_features": {
      "gp_wait_over_7d_pct": 39.5,
      "gp_wait_over_3mo_pct": 0.6,
      "gp_outpatient_visits_per_1000": 6041.0,
      "higher_education_pct": 29.2,
      "pop_75plus_living_alone_pct": 45.4,
      "pop_75plus_rai_assessed_pct": null,
      "cr_3620_proportion_of_women_invited_to_cervical_cance": 79.9,
      "cr_3621_proportion_of_women_invited_to_breast_cancer_": 83.8
    }
  },
  "contributing_factors": {
    "shap_drivers_baseline": [
      {
        "feature": "cr_3621_proportion_of_women_invited_to_breast_cancer_",
        "value": 83.8,
        "shap_value": -6.008911926526025,
        "abs_shap": 6.008911926526025,
        "national_median": 83.45,
        "adverse_direction": false,
        "family": "screening_invitation"
      },
      {
        "feature": "pop_75plus_living_alone_pct",
        "value": 45.4,
        "shap_value": -1.4339526080447698,
        "abs_shap": 1.4339526080447698,
        "national_median": 44.9,
        "adverse_direction": true,
        "family": "living_alone_75plus"
      },
      {
        "feature": "cr_3620_proportion_of_women_invited_to_cervical_cance",
        "value": 79.9,
        "shap_value": -0.5651827398692926,
        "abs_shap": 0.5651827398692926,
        "national_median": 73.6,
        "adverse_direction": false,
        "family": "screening_invitation"
      },
      {
        "feature": "pop_75plus_rai_assessed_pct",
        "value": 17.299999999999997,
        "shap_value": -0.32952639669571704,
        "abs_shap": 0.32952639669571704,
        "national_median": null,
        "adverse_direction": true,
        "family": "rai_g8"
      },
      {
        "feature": "higher_education_pct",
        "value": 29.2,
        "shap_value": 0.25327042938155925,
        "abs_shap": 0.25327042938155925,
        "national_median": 30.7,
        "adverse_direction": true,
        "family": "education_literacy"
      }
    ],
    "interpretation": "Positive SHAP pushes predicted cancer_index_age_std up; adverse_direction marks pressure relative to the national median."
  },
  "recommended_interventions": {
    "department_macro": [
      {
        "target_level": "department_macro",
        "action": "Strengthen outreach and care-navigation for people aged 75+ living alone, including proactive symptom checks and social-care linkage into cancer pathways (strategy equality theme: older people; sub-objectives 3.3–3.4).",
        "responsible_actor": "Wellbeing services county home care / older-people services; primary healthcare",
        "justification": "Elevated pop_75plus_living_alone_pct (value=45.4%, SHAP=-1.434) concentrates frailty and delayed help-seeking. Strategy emphasises functional-capacity–guided care and early psychosocial / social-work support for older adults.",
        "expected_impact": "Earlier presentation among isolated older adults; fewer late-stage diagnoses in the 75+ cohort.",
        "success_metrics": [
          "Time from symptom onset to first contact among 75+ living alone",
          "Share of 75+ cancer patients with a named care coordinator",
          "Stage I–II diagnosis rate in 75+ residents"
        ],
        "driver_feature": "pop_75plus_living_alone_pct",
        "shap_value": -1.4339526080447698,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 1,
        "metadata": {
          "strategy_family": "living_alone_75plus",
          "feature_value": 45.4,
          "national_median": 44.9,
          "source": "National Cancer Strategy 2026–2035"
        }
      },
      {
        "target_level": "department_macro",
        "action": "Scale RAI / functional-capacity assessment coverage for 75+ and introduce the G8 screening tool in all units treating older cancer patients, feeding results into primary-care referrals (strategy sub-objective 3.4).",
        "responsible_actor": "Wellbeing services county geriatric and oncology services; City of Helsinki / HUS where applicable",
        "justification": "Low pop_75plus_rai_assessed_pct (value=17.3%, SHAP=-0.330) indicates incomplete geriatric assessment. Strategy 3.4 requires G8 screening, geriatric assessment for abnormal results, and functional-capacity data already in primary care.",
        "expected_impact": "Treatment plans matched to frailty rather than chronological age; safer diagnostics and fewer avoidable treatment complications in frail patients.",
        "success_metrics": [
          "pop_75plus_rai_assessed_pct coverage",
          "Share of older cancer patients screened with G8",
          "Share of counties offering primary-care consult to a geriatric oncology team"
        ],
        "driver_feature": "pop_75plus_rai_assessed_pct",
        "shap_value": -0.32952639669571704,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 2,
        "metadata": {
          "strategy_family": "rai_g8",
          "feature_value": 17.299999999999997,
          "national_median": null,
          "source": "National Cancer Strategy 2026–2035"
        }
      },
      {
        "target_level": "department_macro",
        "action": "Deploy a targeted, multichannel cancer-symptom and screening awareness campaign for lower-education and linguistic-minority residents (strategy sub-objective 1.3 on health literacy).",
        "responsible_actor": "Wellbeing services county communications & prevention; FICAN; Cancer Society of Finland",
        "justification": "Low higher_education_pct (value=29.2%, SHAP=+0.253) flags socioeconomic and health-literacy risk. Strategy 1.3 links limited literacy to delayed care-seeking and weaker screening participation.",
        "expected_impact": "Reduced patient-attributable delay toward the 50-day Kuitunen segment; narrower education-linked gaps in incidence and mortality.",
        "success_metrics": [
          "Screening participation by education / mother-tongue stratum",
          "Share of residents recognising key cancer alarm symptoms (survey)",
          "Median patient delay from symptom onset to first contact"
        ],
        "driver_feature": "higher_education_pct",
        "shap_value": 0.25327042938155925,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 3,
        "metadata": {
          "strategy_family": "education_literacy",
          "feature_value": 29.2,
          "national_median": 30.7,
          "source": "National Cancer Strategy 2026–2035"
        }
      }
    ],
    "target_level": "department_macro"
  },
  "supporting_evidence": {
    "validated_sources": [
      "THL Sotkanet (wellbeing services county indicators)",
      "Finnish Cancer Registry (screening invitation / cancer index inputs)"
    ],
    "strategy_reference": "National Cancer Strategy 2026–2035",
    "evidence_classes": {
      "validated_thl_fcr": "Observed county indicators and cancer_index_age_std from THL Sotkanet / Finnish Cancer Registry extracts.",
      "calibrated_projections": "Model predictions, SHAP contributions, and (when present) Kuitunen-calibrated pathway day estimates."
    }
  },
  "confidence_and_limitations": {
    "model": {
      "best_model": "RandomForestRegressor",
      "mae_mean": 4.669205999999993,
      "mae_std": 1.306692622560489,
      "rmse_mean": 6.296502090961064,
      "r2_mean": -0.13815145735811496
    },
    "data_year_basis": "Latest available county year in training table / Sotkanet extract",
    "distinction": {
      "validated_findings": "County indicators and observed cancer_index_age_std come from validated THL Sotkanet / Finnish Cancer Registry inputs in the training extract. Treat these as the evidence baseline.",
      "calibrated_projections": "Predicted cancer_index_age_std and SHAP attributions are model outputs from the county feature profile, not observed outcomes."
    },
    "limitations": [
      "GroupKFold CV R² can be weak; use predictions for relative prioritisation, not absolute risk labels.",
      "SHAP explains the fitted model, not causal effects.",
      "Patient pathway days are heuristic calibrations for triage support, not clinical orders.",
      "National Cancer Strategy interventions are mapped from adverse SHAP families and require local validation."
    ]
  }
}
```

### Errors

- `404` — unknown `region_name`

---

## `POST /analyze/patient`

Patient intake from the conversational agent → doctor-level triage (`doctor_micro`) plus validated county context and pathway-day projections.

**Tier A** fields keep existing required behaviour. **Tier B** fields are optional with safe defaults so older clients still work. Personal Tier B fields feed pathway-day estimation and `doctor_micro` rules only — they are **never** passed into the county ML model or SHAP (county-only).

### Request (Tier A + Tier B, Lapland-style)

```json
{
  "patient_id": "demo-001",
  "region_name": "Lapland",
  "age": 78,
  "public_care_track": true,
  "symptom_severity_score": 7,
  "g8_frailty_score": 12,
  "missing_staging_fields": ["T", "N", "M"],
  "sex": "male",
  "symptom_onset_days": 60,
  "primary_symptom_cluster": "respiratory",
  "smoking_status": "former",
  "lives_alone": true,
  "travel_time_to_care_minutes": 95,
  "needs_interpreter": false,
  "education_band": "low",
  "already_referred_to_specialist": false,
  "care_phase": "primary_care",
  "language": "fi",
  "comorbidity_flags": ["copd"],
  "agent_confidence": 0.82
}
```

| Field | Tier | Type | Default | Notes |
|-------|------|------|---------|-------|
| `patient_id` | A | string | required | Agent session / case id |
| `region_name` | A | string | required | County name or substring (e.g. `"Lapland"`) |
| `age` | A | number | required | Years |
| `public_care_track` | A | boolean | `true` | Public vs private track |
| `symptom_severity_score` | A | number | required | 0–10 |
| `g8_frailty_score` | A | number or null | `null` | `<14` = frail |
| `missing_staging_fields` | A | string[] | `[]` | e.g. `["T","N","M"]` |
| `sex` | B | `"female"` \| `"male"` \| `"other"` \| `"unknown"` | `"unknown"` | Filters irrelevant macros; breast/gyn tips |
| `symptom_onset_days` | B | number or null | `null` | ≥0; long onset nudges patient delay |
| `primary_symptom_cluster` | B | `"respiratory"` \| `"breast"` \| `"gi"` \| `"gyn"` \| `"heme"` \| `"other"` \| `"unknown"` | `"unknown"` | Targets smoking / screening tips |
| `smoking_status` | B | `"never"` \| `"former"` \| `"current"` \| `"unknown"` | `"unknown"` | + respiratory → urgency / tip |
| `lives_alone` | B | boolean or null | `null` | True (esp. age≥75) raises patient delay |
| `travel_time_to_care_minutes` | B | number or null | `null` | ≥0; >60 / >120 inflate primary/specialist |
| `needs_interpreter` | B | boolean | `false` | Literacy path + slight delay inflation |
| `education_band` | B | `"low"` \| `"mid"` \| `"high"` \| `"unknown"` | `"unknown"` | Preferred over county education % when set |
| `already_referred_to_specialist` | B | boolean | `false` | Suppresses primary inflation / fast-track |
| `care_phase` | B | `"pre_contact"` \| `"primary_care"` \| `"diagnostics"` \| `"mdt"` \| `"treatment"` | `"primary_care"` | With referral → continuity tip |
| `language` | B | string or null | `null` | Blind spot if interpreter needed |
| `comorbidity_flags` | B | string[] | `[]` | e.g. `cognitive_impairment` → geriatric tip |
| `agent_confidence` | B | number or null | `null` | 0–1 if present (echoed; not used in ML) |

### Response `200` (Lapland high-risk Tier A+B example; pathway days are calibrated projections)

```json
{
  "predictions_and_gaps": {
    "patient_id": "demo-001",
    "region_id": 968,
    "region_name": "Lapland wellbeing services county",
    "year": 2024,
    "intake": {
      "patient_id": "demo-001",
      "age": 78.0,
      "public_care_track": true,
      "symptom_severity_score": 7.0,
      "g8_frailty_score": 12.0,
      "missing_staging_fields": ["T", "N", "M"],
      "sex": "male",
      "symptom_onset_days": 60.0,
      "primary_symptom_cluster": "respiratory",
      "smoking_status": "former",
      "lives_alone": true,
      "travel_time_to_care_minutes": 95.0,
      "needs_interpreter": false,
      "education_band": "low",
      "already_referred_to_specialist": false,
      "care_phase": "primary_care",
      "language": "fi",
      "comorbidity_flags": ["copd"],
      "agent_confidence": 0.82
    },
    "blind_spots": [],
    "pathway_days_estimate": {
      "patient_days": 65.5,
      "primary_care_days": 48.8,
      "specialist_care_days": 82.4,
      "total_days": 196.7,
      "benchmark_total_days": 155.0,
      "excess_vs_benchmark_days": 41.7
    },
    "pathway_evidence_class": "calibrated_projection",
    "county_context": {
      "observed_cancer_index_age_std": 89.9,
      "observed_evidence_class": "validated_thl_fcr",
      "predicted_cancer_index_age_std": 92.32849999999999,
      "predicted_evidence_class": "calibrated_projection",
      "indicators": {
        "gp_wait_over_7d_pct": 39.5,
        "gp_wait_over_3mo_pct": 0.6,
        "gp_outpatient_visits_per_1000": 6041.0,
        "morbidity_index_age_std": 110.6,
        "higher_education_pct": 29.2,
        "pop_75plus_living_alone_pct": 45.4,
        "pop_75plus_rai_assessed_pct": null,
        "cr_3620_proportion_of_women_invited_to_cervical_cance": 79.9,
        "cr_3621_proportion_of_women_invited_to_breast_cancer_": 83.8,
        "cancer_index_age_std": 89.9
      }
    },
    "gap_vs_kuitunen_total_days": 41.7
  },
  "contributing_factors": {
    "county_shap_drivers": [
      {
        "feature": "cr_3621_proportion_of_women_invited_to_breast_cancer_",
        "value": 83.8,
        "shap_value": -6.008911926526025,
        "abs_shap": 6.008911926526025,
        "national_median": 83.45,
        "adverse_direction": false,
        "family": "screening_invitation"
      },
      {
        "feature": "pop_75plus_living_alone_pct",
        "value": 45.4,
        "shap_value": -1.4339526080447698,
        "abs_shap": 1.4339526080447698,
        "national_median": 44.9,
        "adverse_direction": true,
        "family": "living_alone_75plus"
      },
      {
        "feature": "cr_3620_proportion_of_women_invited_to_cervical_cance",
        "value": 79.9,
        "shap_value": -0.5651827398692926,
        "abs_shap": 0.5651827398692926,
        "national_median": 73.6,
        "adverse_direction": false,
        "family": "screening_invitation"
      },
      {
        "feature": "pop_75plus_rai_assessed_pct",
        "value": 17.299999999999997,
        "shap_value": -0.32952639669571704,
        "abs_shap": 0.32952639669571704,
        "national_median": null,
        "adverse_direction": true,
        "family": "rai_g8"
      },
      {
        "feature": "higher_education_pct",
        "value": 29.2,
        "shap_value": 0.25327042938155925,
        "abs_shap": 0.25327042938155925,
        "national_median": 30.7,
        "adverse_direction": true,
        "family": "education_literacy"
      }
    ],
    "intake_risk_flags": {
      "public_care_track": true,
      "high_symptom_severity": true,
      "frail_or_older": true,
      "missing_staging_fields": ["T", "N", "M"],
      "lives_alone": true,
      "needs_interpreter": false,
      "smoking_risk": true,
      "high_travel": true,
      "already_referred": false
    },
    "blind_spots": []
  },
  "recommended_interventions": {
    "doctor_micro": [
      {
        "target_level": "doctor_micro",
        "action": "Activate a cancer-suspicion fast track: same-week assessment, apply national referral criteria, and order urgent imaging without waiting for a routine non-urgent slot (Kuitunen / strategy 2.5).",
        "responsible_actor": "Treating GP / primary-care physician; care pathway nurse",
        "justification": "Estimated primary-care interval 48.8d (benchmark 41d) in Lapland wellbeing services county with GP wait >7d at 39.5% and symptom_severity_score=7.0 on the public care track. Kuitunen's Finnish lung-cancer study attributes 41 of 155 days to primary care; delays arise from appointment access and missed symptoms.",
        "expected_impact": "Compress primary-care days toward ≤41 and total pathway toward ≤155 (current estimate 196.7d).",
        "success_metrics": [
          "Days from first contact to specialist referral",
          "Days from referral to first diagnostic imaging",
          "Whether national cancer-suspicion referral criteria were applied (Y/N)"
        ],
        "driver_feature": null,
        "shap_value": null,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": {
          "patient_days": 65.5,
          "primary_care_days": 48.8,
          "specialist_care_days": 82.4,
          "total_days": 196.7,
          "benchmark_total_days": 155.0,
          "excess_vs_benchmark_days": 41.7
        },
        "priority": 1,
        "metadata": {
          "trigger": "primary_care_or_severity",
          "public_care_track": true
        }
      },
      {
        "target_level": "doctor_micro",
        "action": "Provide structured symptom-action counselling and a written safety-net plan (when to re-contact, what red flags mean) using plain-language, health-literacy–adapted materials (strategy 1.3).",
        "responsible_actor": "Treating clinician with practice nurse / care coordinator",
        "justification": "Estimated patient-attributable delay 65.5d (benchmark ~50d); age=78. education_band=low. Symptom onset reported at 60 days.",
        "expected_impact": "Shorter patient delay on subsequent symptom episodes; clearer re-contact behaviour if symptoms progress.",
        "success_metrics": [
          "Documented safety-net advice in the record",
          "Time from safety-net trigger to re-contact",
          "Patient-reported understanding of red flags"
        ],
        "driver_feature": null,
        "shap_value": null,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": {
          "patient_days": 65.5,
          "primary_care_days": 48.8,
          "specialist_care_days": 82.4,
          "total_days": 196.7,
          "benchmark_total_days": 155.0,
          "excess_vs_benchmark_days": 41.7
        },
        "priority": 2,
        "metadata": {
          "trigger": "patient_delay_or_literacy",
          "needs_interpreter": false,
          "education_band": "low"
        }
      },
      {
        "target_level": "doctor_micro",
        "action": "Complete / document G8 frailty screening now; if G8 < 14 (or clinical frailty), refer for comprehensive geriatric assessment and include functional-capacity findings in the specialist referral (strategy 3.4).",
        "responsible_actor": "Treating physician; geriatric / geriatric-oncology consult",
        "justification": "Patient age=78, G8=12.0. Strategy 3.4 requires G8 in units treating older cancer patients and functional-capacity data already in primary-care referrals. County RAI coverage is a known regional gap.",
        "expected_impact": "Treatment intensity matched to function; fewer complications from over- or under-treatment of frail patients; specialist work-up planned with geriatric input.",
        "success_metrics": [
          "G8 score recorded before treatment decision",
          "Geriatric assessment completed when G8 < 14 (Y/N)",
          "Functional capacity included in referral documentation (Y/N)"
        ],
        "driver_feature": null,
        "shap_value": null,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": {
          "patient_days": 65.5,
          "primary_care_days": 48.8,
          "specialist_care_days": 82.4,
          "total_days": 196.7,
          "benchmark_total_days": 155.0,
          "excess_vs_benchmark_days": 41.7
        },
        "priority": 3,
        "metadata": {
          "trigger": "frailty_or_age",
          "g8_frailty_score": 12.0,
          "age": 78.0
        }
      },
      {
        "target_level": "doctor_micro",
        "action": "Close staging documentation gaps before MDT: complete missing clinical stage fields and ensure structured registry notification so diagnostics are not re-ordered or delayed (strategy 3.2 / quality register).",
        "responsible_actor": "Specialist responsible physician; MDT coordinator",
        "justification": "Missing staging fields: T, N, M. Incomplete clinical notifications and imaging/report waits drive specialist delay (82.4d vs 58d benchmark). Kuitunen highlights waits for imaging, reports and samples in specialised care.",
        "expected_impact": "Fewer repeat diagnostics; specialist interval closer to ≤58 days; better stage capture for early-detection monitoring.",
        "success_metrics": [
          "Proportion of required staging fields complete at MDT",
          "Days from referral to treatment start",
          "Clinical cancer notification completeness for this case"
        ],
        "driver_feature": null,
        "shap_value": null,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": {
          "patient_days": 65.5,
          "primary_care_days": 48.8,
          "specialist_care_days": 82.4,
          "total_days": 196.7,
          "benchmark_total_days": 155.0,
          "excess_vs_benchmark_days": 41.7
        },
        "priority": 4,
        "metadata": {
          "trigger": "missing_staging_or_specialist_delay",
          "missing_staging_fields": [
            "T",
            "N",
            "M"
          ]
        }
      }
    ],
    "department_macro": [
      {
        "target_level": "department_macro",
        "action": "Strengthen outreach and care-navigation for people aged 75+ living alone, including proactive symptom checks and social-care linkage into cancer pathways (strategy equality theme: older people; sub-objectives 3.3–3.4).",
        "responsible_actor": "Wellbeing services county home care / older-people services; primary healthcare",
        "justification": "Elevated pop_75plus_living_alone_pct (value=45.4%, SHAP=-1.434) concentrates frailty and delayed help-seeking. Strategy emphasises functional-capacity–guided care and early psychosocial / social-work support for older adults.",
        "expected_impact": "Earlier presentation among isolated older adults; fewer late-stage diagnoses in the 75+ cohort.",
        "success_metrics": [
          "Time from symptom onset to first contact among 75+ living alone",
          "Share of 75+ cancer patients with a named care coordinator",
          "Stage I–II diagnosis rate in 75+ residents"
        ],
        "driver_feature": "pop_75plus_living_alone_pct",
        "shap_value": -1.4339526080447698,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 1,
        "metadata": {
          "strategy_family": "living_alone_75plus",
          "feature_value": 45.4,
          "national_median": 44.9,
          "source": "National Cancer Strategy 2026–2035"
        }
      },
      {
        "target_level": "department_macro",
        "action": "Scale RAI / functional-capacity assessment coverage for 75+ and introduce the G8 screening tool in all units treating older cancer patients, feeding results into primary-care referrals (strategy sub-objective 3.4).",
        "responsible_actor": "Wellbeing services county geriatric and oncology services; City of Helsinki / HUS where applicable",
        "justification": "Low pop_75plus_rai_assessed_pct (value=17.3%, SHAP=-0.330) indicates incomplete geriatric assessment. Strategy 3.4 requires G8 screening, geriatric assessment for abnormal results, and functional-capacity data already in primary care.",
        "expected_impact": "Treatment plans matched to frailty rather than chronological age; safer diagnostics and fewer avoidable treatment complications in frail patients.",
        "success_metrics": [
          "pop_75plus_rai_assessed_pct coverage",
          "Share of older cancer patients screened with G8",
          "Share of counties offering primary-care consult to a geriatric oncology team"
        ],
        "driver_feature": "pop_75plus_rai_assessed_pct",
        "shap_value": -0.32952639669571704,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 2,
        "metadata": {
          "strategy_family": "rai_g8",
          "feature_value": 17.299999999999997,
          "national_median": null,
          "source": "National Cancer Strategy 2026–2035"
        }
      },
      {
        "target_level": "department_macro",
        "action": "Deploy a targeted, multichannel cancer-symptom and screening awareness campaign for lower-education and linguistic-minority residents (strategy sub-objective 1.3 on health literacy).",
        "responsible_actor": "Wellbeing services county communications & prevention; FICAN; Cancer Society of Finland",
        "justification": "Low higher_education_pct (value=29.2%, SHAP=+0.253) flags socioeconomic and health-literacy risk. Strategy 1.3 links limited literacy to delayed care-seeking and weaker screening participation.",
        "expected_impact": "Reduced patient-attributable delay toward the 50-day Kuitunen segment; narrower education-linked gaps in incidence and mortality.",
        "success_metrics": [
          "Screening participation by education / mother-tongue stratum",
          "Share of residents recognising key cancer alarm symptoms (survey)",
          "Median patient delay from symptom onset to first contact"
        ],
        "driver_feature": "higher_education_pct",
        "shap_value": 0.25327042938155925,
        "region_name": "Lapland wellbeing services county",
        "pathway_days": null,
        "priority": 3,
        "metadata": {
          "strategy_family": "education_literacy",
          "feature_value": 29.2,
          "national_median": 30.7,
          "source": "National Cancer Strategy 2026–2035"
        }
      }
    ],
    "primary_target_level": "doctor_micro"
  },
  "supporting_evidence": {
    "validated_sources": [
      "THL Sotkanet (wellbeing services county indicators)",
      "Finnish Cancer Registry (screening invitation / cancer index inputs)"
    ],
    "strategy_reference": "National Cancer Strategy 2026–2035",
    "evidence_classes": {
      "validated_thl_fcr": "Observed county indicators and cancer_index_age_std from THL Sotkanet / Finnish Cancer Registry extracts.",
      "calibrated_projections": "Model predictions, SHAP contributions, and (when present) Kuitunen-calibrated pathway day estimates."
    },
    "kuitunen_pathway_benchmarks_days": {
      "patient_days": 50.0,
      "primary_care_days": 41.0,
      "specialist_care_days": 58.0,
      "total_days": 155.0
    },
    "kuitunen_source": "Prof. Outi Kuitunen Finnish lung-cancer pathway study (patient 50d + primary care 41d + specialist 58d = 155d)"
  },
  "confidence_and_limitations": {
    "model": {
      "best_model": "RandomForestRegressor",
      "mae_mean": 4.669205999999993,
      "mae_std": 1.306692622560489,
      "rmse_mean": 6.296502090961064,
      "r2_mean": -0.13815145735811496
    },
    "data_year_basis": "Latest available county year in training table / Sotkanet extract",
    "distinction": {
      "validated_findings": "County indicators and observed cancer_index_age_std come from validated THL Sotkanet / Finnish Cancer Registry inputs in the training extract. Treat these as the evidence baseline.",
      "calibrated_projections": "Pathway day estimates and doctor_micro triage actions are calibrated projections against Prof. Outi Kuitunen's Finnish lung-cancer pathway benchmarks (50 / 41 / 58 / 155 days), not measured patient timelines."
    },
    "limitations": [
      "GroupKFold CV R² can be weak; use predictions for relative prioritisation, not absolute risk labels.",
      "SHAP explains the fitted model, not causal effects.",
      "Patient pathway days are heuristic calibrations for triage support, not clinical orders.",
      "National Cancer Strategy interventions are mapped from adverse SHAP families and require local validation."
    ]
  }
}
```

### Errors

- `404` — unknown `region_name`
- `422` — validation (e.g. severity outside 0–10)

---

## Notes for frontend / agent teammates

- Prefer **substring** region match (`"Lapland"`, `"Helsinki"`) — API resolves to the full wellbeing services county name.
- Use `observed_*` + `indicators` for charts labelled as registry/Sotkanet facts.
- Use `predicted_*`, `pathway_days_estimate`, and SHAP lists as decision-support projections; surface `confidence_and_limitations.distinction` in the UI.
- Recommendation objects include `target_level`: `department_macro` (region) or `doctor_micro` (patient).
- Echoed `predictions_and_gaps.intake` includes full Tier A+B; use `blind_spots` (also under `contributing_factors`) to drive agent follow-up questions.
- Tier B personal fields never enter county SHAP / ML — only pathway heuristics and `doctor_micro` (plus light patient-only macro filtering, e.g. drop cervical screening tips when `sex=male`).
