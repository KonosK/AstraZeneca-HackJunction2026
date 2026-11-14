# CODEX IMPLEMENTATION SPEC — ONCOFLOW / ASTRAZENECA JUNCTION 2026

**Status:** Approved integration plan for the final hackathon demo  
**Date:** 2026-11-14  
**Primary goal:** Ship a reliable, polished, AI-assisted demonstration of **equity-aware cancer-care navigation and regional decision support** using the EXISTING OncoFlow ML API and recommendation engine.  
**Audience:** Codex implementation agent and the two integration owners.  
**Priority:** AstraZeneca's *Equal Care Across Finland* judging criteria: Actionability **30%**, Insight **25%**, Data quality/transparency **20%**, Execution **15%**, Clarity **10%**.

> **Codex: implement this specification, not merely a mockup or plan.** First inspect the files in the actual workspace. Reuse existing code and UI wherever they exist. If a file, API route, dataset, or provider is missing, report it truthfully and implement a documented fallback rather than inventing success. Do not rewrite or retrain the teammate's ML model unless explicitly assigned. At each milestone, run relevant tests and report exact commands/results.

---

## 0. Source of truth and integration boundaries

We received and inspected the teammate's repository archive `AstraZeneca-Junction2026-main.zip` (commit identifier displayed inside archive: `5f976cdc6f1068603f71d9f667b682f8feee5c9c`). The relevant files **inside the archive** are:

- `mlBackend/api.py` — actual FastAPI route implementation, Pydantic request schemas, five-block output.
- `mlBackend/recommendations.py` — region recommendations, patient micro-interventions, and heuristic pathway-day calculations.
- `mlBackend/train_and_evaluate.py` — training procedure and the eight county-level model features.
- `mlBackend/artifacts/oncoflow_bundle.joblib` — serialized model/explainer; requires compatible dependencies.
- `mlBackend/data/clean_cancer_training_data.csv` — regional input table.
- `mlBackend/test_api.py` — bundled FastAPI smoke/integration checks.
- `mlBackend/API_CONTRACT.md` — teammate's human-readable API examples and semantics.

Also read any supplied `BRIEF.md` and challenge statement. **When documentation and executable code conflict, use executable code for current behavior; record the inconsistency and obtain owner approval for a change.** Avoid treating copied example responses as live API results.

### Ownership (do not blur these responsibilities)

| Module | Owner | What it does | What NOT to do |
|---|---|---|---|
| Regional ML + SHAP | Teammate | County-level `cancer_index_age_std` prediction and feature attribution | Never reinterpret it as a patient cancer probability |
| Recommendation engine | Teammate | `department_macro`, `doctor_micro`, heuristic `pathway_days_estimate` | Do not duplicate business rules in an LLM |
| Agent + data unification | Our Codex build | Combine fragmented, **synthetic** clinical information; track provenance/conflicts; ask for missing fields | Do not invent missing data |
| API integration adapter | Our Codex build | Validate payloads, call FastAPI, validate responses, handle errors/fallback | Do not silently fabricate API outputs |
| Demo UI | Our Codex build | Regional equity dashboard + guided case workflow + clinician review queue | Do not represent demo queue as a real health-system referral |
| Clinical decisions | Licensed professionals | Review clinical recommendations, decide referral/urgency/treatment | Do not autonomously direct care using this experimental system |

**Conceptual guardrail:** the ML predicts a **regional, age-standardized cancer incidence index** (`cancer_index_age_std`), not individual clinical risk and not directly measured healthcare inequality. SHAP explains the fitted county model, **not medical causes** or intervention effects. `pathway_days_estimate` is a rule-based projection calibrated against a published Finnish lung-cancer pathway benchmark; it is **not** an observed time for the selected patient. Keep these categories visible throughout UI and agent narration.

Do not claim the product has already proven an improvement in equity. It supports identifying potential access barriers, linking aggregate evidence to plausible interventions, and measuring future outcomes.

---

## 1. Desired user experience: two connected modes

### Mode A — **Regional Equity Intelligence** (main judging story)

1. A decision-maker selects a **real county from `GET /regions`** (e.g. Lapland).
2. UI shows observed county indicators such as primary-care waits, education %, living-alone %, and screening invitation coverage, **with their year and provenance**.
3. UI calls `POST /analyze/region` and displays model output + SHAP drivers *separately from* observed facts.
4. UI displays existing `recommended_interventions.department_macro` items: action, actor responsible, justification, success metrics, evidence/limitation labels.
5. An optional what-if input invokes the **actual** `POST /analyze/region` using allowed `what_if_overrides`. Show changes as hypothetical model projections, **not causal savings, actual deaths avoided, or proven outcomes**.
6. Highlight ONE defensible equity problem at a defined cancer-care stage and ONE county-level proposed response. The data must support the factual part of the claim. Without observed subgroup or process-delay data, label that gap as a *potential access barrier*, not a demonstrated unequal cancer outcome.

### Mode B — **Case Navigation Agent** (integration showcase)

1. Clinician/demo operator loads a **clearly labeled synthetic patient** via bundled local FHIR R4 fixtures or a simple form. The prototype must work without a live EHR or external credentials.
2. The agent aggregates available facts from synthetic `Patient`, `Observation`, `Condition`, `Encounter`, `ServiceRequest` and/or `QuestionnaireResponse` records as actually provided; unsupported or absent resources stay unknown.
3. It detects fields missing for the current backend request, then asks only useful, prioritized questions. The user can answer, mark as unknown, or correct an extracted field.
4. It shows a **reviewable structured intake** with field-level source and confidence. Operator explicitly confirms before running the analysis.
5. It sends this structured payload, **not the transcript**, to `POST /analyze/patient`.
6. It renders the backend's actual `doctor_micro`, `department_macro`, county SHAP, contextual indicators, projected pathway days, and `blind_spots` distinctly.
7. The clinician may **submit a local draft for review** in an in-app review queue. This is **not a real medical referral or notification** and must be labeled as such.
8. The UI links the patient navigation recommendations to the same county-level access barriers surfaced in Mode A, without implying county statistics describe this individual's diagnosis.

**Design goal:** one coherent product, not two unrelated dashboards. Use a shared county context and clearly labeled *Population / Patient / Intervention* sections.

---

## 2. Existing backend — exact integration contract

The FastAPI app is `mlBackend.api:app` when launched from repo root (`uvicorn mlBackend.api:app --host 127.0.0.1 --port 8000`) or `api:app` when launched from `mlBackend/`.

**Endpoints already present (do not invent others):**

| Method | Path | Purpose | Important notes |
|---|---|---|---|
| GET | `/health` | Model/service metadata, target/features, CV metrics | Loads model; may fail when Python package versions mismatch |
| GET | `/regions` | List of regions with latest aggregated indicators | Current dataset contains **23** region rows (latest year **2024** in supplied contract) |
| POST | `/analyze/region` | County model output + SHAP + `department_macro` | Optional feature-level what-if |
| POST | `/analyze/patient` | County context + heuristic pathway + `doctor_micro`/`department_macro` | Requires core fields; Tier B optional |

**Backend request models are defined in `api.py`, not in the LLM prompt.** Frontend/types should be generated or carefully mirrored and contract tested.

### 2.1 `POST /analyze/patient` — current accepted fields

| Key | Type | Required in Pydantic? | Agent handling |
|---|---|---|---|
| `patient_id` | string | yes | Synthetic case/session ID; **not** an actual person's national ID |
| `region_name` | string | yes | Resolve against `/regions`; send canonical county name |
| `age` | number | yes | Extract from date of birth if reliable; otherwise ask |
| `public_care_track` | boolean | no; defaults `true` | Ask/confirm unknown; do **not** quietly equate missing with public |
| `symptom_severity_score` | number 0–10 | yes | Require explicit clinician/demo-operator input or a transparent **demonstration-only** rubric; never silently fabricate 5/7; not validated urgency |
| `g8_frailty_score` | number or null | no; defaults `null` | Only if a documented G8 assessment actually exists; **never fabricate or infer from age** |
| `missing_staging_fields` | list of strings | no; defaults `[]` | Populate when cancer work-up has begun and staging completeness is truly known; `[]` does not mean confirmed complete when status unknown |
| `sex` | `female/male/other/unknown` | optional | Extract only if clinically pertinent and explicitly recorded; do not infer from name |
| `symptom_onset_days` | number >=0 or null | optional | From documented onset date or explicit answer; note uncertainty |
| `primary_symptom_cluster` | `respiratory/breast/gi/gyn/heme/other/unknown` | optional | Explicit or confidently mapped; otherwise ask |
| `smoking_status` | `never/former/current/unknown` | optional | Ask/collect; do not assume |
| `lives_alone` | boolean or null | optional | Ask when relevant; missing != false |
| `travel_time_to_care_minutes` | number >=0 or null | optional | User-provided estimate unless validated travel data exists |
| `needs_interpreter` | boolean | optional; defaults false | Confirm explicitly where relevant; missing != confirmed no |
| `education_band` | `low/mid/high/unknown` | optional | Voluntary and contextual; avoid assuming this determines medical urgency |
| `already_referred_to_specialist` | boolean | optional; defaults false | Check referral status or ask; missing != not referred |
| `care_phase` | `pre_contact/primary_care/diagnostics/mdt/treatment` | optional | Derive from evidence when possible, otherwise confirm |
| `language` | string or null | optional | From preference or documentation |
| `comorbidity_flags` | string[] | optional | Only known, documented conditions; match the backend's recognized codes where applicable |
| `agent_confidence` | number 0–1 or null | optional | Optional extraction-confidence metadata; **not** a calibrated clinical confidence/urgency score |

These Tier B fields are already implemented in `api.py`; they are NOT inputs to the regional Random Forest/SHAP. Their effect, where present, is on backend rules/heuristic pathway estimates and contextual recommendations.

### 2.2 Minimal example request (synthetic)

```json
{
  "patient_id": "SYNTH-LAPLAND-001",
  "region_name": "Lapland wellbeing services county",
  "age": 78,
  "public_care_track": true,
  "symptom_severity_score": 7,
  "g8_frailty_score": null,
  "missing_staging_fields": [],
  "sex": "unknown",
  "symptom_onset_days": 60,
  "primary_symptom_cluster": "respiratory",
  "smoking_status": "former",
  "lives_alone": true,
  "travel_time_to_care_minutes": 95,
  "needs_interpreter": false,
  "education_band": "unknown",
  "already_referred_to_specialist": false,
  "care_phase": "primary_care",
  "language": "fi"
}
```

**Important:** this is **an illustrative demo fixture**, not an actual patient; severity score `7` and all boolean answers must be stated/confirmed by demo operator before request. The empty staging array is applicable because this example's staging work-up has not started. Do not auto-insert such values for arbitrary real user data.

### 2.3 Response shape (both POST routes)

Both return exactly these five top-level sections:

```text
predictions_and_gaps
contributing_factors
recommended_interventions
supporting_evidence
confidence_and_limitations
```

**Patient response paths the UI must consume:**

- `predictions_and_gaps.intake` — echo of normalized patient intake.
- `predictions_and_gaps.blind_spots` — backend suggestions for missing follow-up fields.
- `predictions_and_gaps.pathway_days_estimate` — projected `patient_days`, `primary_care_days`, `specialist_care_days`, `total_days`, `benchmark_total_days`, `excess_vs_benchmark_days`.
- `predictions_and_gaps.county_context.observed_cancer_index_age_std` and `...predicted_cancer_index_age_std` — **different evidence classes**.
- `predictions_and_gaps.county_context.indicators` — latest regional indicators.
- `contributing_factors.county_shap_drivers` — feature/value/SHAP, **county-level**, never patient causal factors.
- `contributing_factors.intake_risk_flags` — rule-based flags, not an individual's cancer-probability estimate.
- `recommended_interventions.doctor_micro[]` — patient-workflow recommendations.
- `recommended_interventions.department_macro[]` — regional/system recommendations.
- `supporting_evidence.*` — sources and benchmark statement.
- `confidence_and_limitations.*` — CV metrics and explicit limitations.

**Region response paths:**

- `predictions_and_gaps.observed_cancer_index_age_std`, `predicted_cancer_index_age_std`, `baseline_features`, `year`, and `what_if`.
- `contributing_factors.shap_drivers_baseline`, `shap_drivers_what_if`.
- `recommended_interventions.department_macro[]`.
- `supporting_evidence` and `confidence_and_limitations`.

**Recommendation item fields** (from `Recommendation.to_dict()`): `target_level`, `action`, `responsible_actor`, `justification`, `expected_impact`, `success_metrics`, `driver_feature`, `shap_value`, `region_name`, `pathway_days`, `priority`, `metadata`. Render these objects from the API; **do not prompt an LLM to invent recommendations or citations**.

### 2.4 Errors / runtime contract

- 400: invalid what-if key/value (region route).
- 404: county not found (both POST routes).
- 422: malformed/invalid patient request (including severity outside 0–10).
- Network failure, timeout, 5xx, or model deserialization failure: **show a real error**, offer retry, and optionally switch to an explicitly labeled offline fixture only by user choice.
- JSON numbers must be finite or `null` (backend implements sanitization).
- The service's current CORS is permissive. For a deployable demo, use a server-side BFF/proxy and restrict origins rather than exposing broad production CORS or credentials.

### 2.5 Current limitations requiring visible labeling

1. The model's **target** is a regional cancer incidence index. It cannot be used as a patient risk score or a direct inequity measurement.
2. The provided `API_CONTRACT.md` sample reports **GroupKFold mean R² approximately -0.138**, indicating the current regional model should not be marketed as a reliably accurate predictive decision-maker. Re-check live `/health`; show actual metrics if displayed.
3. SHAP values are model attributions, not proven causes.
4. A regional percentage of university education is not an individual's health literacy score; ecological associations cannot be transferred to individuals.
5. The Kuitunen 50 / 41 / 58 = 155-day benchmark is for a Finnish **lung-cancer pathway**. Do not present it as universal for all cancer types.
6. Current pathway-day multipliers and `doctor_micro` actions are **heuristics requiring clinical validation**. They do not authorize urgent referral.
7. The backend uses a G8 threshold described as `<14`; do not silently change teammate code. Raise a review item to validate the intended criterion against the clinical source before deploying clinical-language thresholds.
8. Observed screening-invitation coverage ≠ screening participation/completed follow-up.
9. Individual-level sex/education/interpreter/living-alone fields drive recommendations, **not** regional Random Forest training.

---

## 3. Architecture and preferred repository layout

If the final-project repo already has a frontend, **extend it rather than replacing it**. If no frontend exists, use **Next.js + TypeScript** (a proven stable stack available in the environment) with a clean design system. Use a Python FastAPI process for the existing backend; do not port its trained model to JavaScript.

Suggested logical structure (adapt naming to existing repo):

```text
/
  mlBackend/                         # existing teammate code — OWNED BY TEAMMATE
  web/                               # Next.js/TypeScript demo (if no frontend exists)
    app/
      page.tsx                       # landing / single coherent experience
      api/oncoflow/[...path]/route.ts # optional BFF, or narrower typed routes
      api/agent/route.ts             # optional LLM orchestration, never browser-side keys
    components/
      regional/                      # county metrics, SHAP, recommendations, what-if
      intake/                        # synthetic FHIR import, provenance, questions, review
      results/                       # projections, recommendations, evidence/limitations
      review/                        # local draft clinician-review queue
    lib/
      oncoflow/client.ts             # timeout, errors, requests and response validation
      oncoflow/schemas.ts            # types / Zod; mirror real API
      agent/field-mapping.ts         # synthetic FHIR -> candidate fields
      agent/intake-state.ts          # question planner and confirmation
      agent/evidence-provenance.ts   # source/conflict objects and review flags
      agent/review-routing.ts        # NONclinical demo workflow rules
    fixtures/
      synthea/                       # labeled synthetic, local FHIR JSON
      api/                           # static demo responses only for explicit offline mode
    tests/
  docs/
    integration-notes.md
    clinical-limitations.md
    demo-runbook.md
    dependency-lock.md
```

**Important dependency rule:** the *agent orchestration layer* must function without any LLM API: deterministic question planner + actual API integration first. Optional Gemini/NVIDIA/other models can improve natural language extraction only **behind a provider abstraction with timeout and a non-LLM fallback**. Sponsor technologies are optional; do not jeopardize Sunday's demo for a speculative prize.

**Data flow:**

```text
Local synthetic FHIR + manual clinician input
    -> deterministic extraction and provenance ledger
    -> missing/conflicting-field question planner
    -> human confirmation of required values
    -> validate PatientAnalyzeRequest
    -> existing POST /analyze/patient
    -> strictly parsed 5-block response
    -> clinician-readable explanation + local review draft

GET /regions -> county selector -> POST /analyze/region -> observed indicator panel
          -> SHAP panel (model attribution) -> macro interventions
          -> optional POST /analyze/region what-if (projection only)
```

---

## 4. Agent data model — do not lose provenance

Create a separate **internal intake state** instead of letting the LLM directly compose API request JSON. Recommended TS shapes (adapt as necessary):

```ts
type FieldSource = "fhir" | "manual" | "derived" | "demo_fixture";
type FieldStatus = "missing" | "candidate" | "confirmed" | "conflicted";
type FieldRecord<T> = {
  value: T | null;
  status: FieldStatus;
  source: FieldSource | null;
  sourceRef?: string;        // FHIR resource id or explicit intake question
  recordedAt?: string;
  confidence?: number;       // extraction confidence, not clinical certainty
  notes?: string;
};

type IntakeState = {
  caseId: string;
  synthetic: true;
  fields: Record<string, FieldRecord<unknown>>;
  pendingQuestions: string[];
  conflicts: string[];
  analysisStatus: "not_ready" | "ready" | "analyzing" | "analyzed" | "error";
};
```

**Invariants:**

- Every populated medical/social field is traceable to a source or a clearly labeled synthetic fixture.
- A low-confidence extracted value remains `candidate` until confirmed.
- Contradictions (e.g. FHIR says already referred, dialogue says not referred) create `conflicted` status; do not silently overwrite. Prefer current verified records, with explicit user review.
- Unknown values must remain `unknown`/`null` where API supports them; don't quietly rely on dangerous defaults (`false`, `true`, `primary_care`, or 5).
- Capture only data needed for this demonstration; do not persist real patient identifiers or transcripts to logging/analytics.
- If patient is in `pre_contact`, absent TNM should not be displayed as missing required staging; ask/track this only when relevant to diagnostics/MDT.

### 4.1 Synthetic FHIR connector (no real EHR authorization implied)

Support **a local upload or bundled fixture** with a valid FHIR R4 `Bundle`. For the hackathon, parse only the fields we can substantiate from available resources:

- `Patient.birthDate` -> age (use demonstrator's reference date consistently); sex only where appropriately represented and explicitly documented; address locality -> *candidate* county, resolve and confirm.
- `Observation` -> documented screening/assessment values, **only if correctly coded and units confirmed** (e.g., G8 if an actual G8 observation exists).
- `Condition` -> recorded comorbidity flags, subject to an explicit mapping table; don't fabricate diagnoses.
- `Encounter` / `ServiceRequest` -> possible current care phase and specialist referral status, subject to confirmation.
- `QuestionnaireResponse` -> self-reported smoking, living alone, education, interpreter need, and symptom onset only if *explicitly represented* in a known synthetic form.

Do not build a fake Kanta connector. Call this **FHIR R4-compatible synthetic demonstration / interoperability prototype**. Document which resources are supported and what remains manual.

### 4.2 Missing-question policy

Before the first API call, collect/confirm **required** values:

1. `region_name` (from actual county list), `age`, explicit `symptom_severity_score` (the latter marked *demo-only heuristic unless clinician-confirmed*).
2. Confirm `care_phase`, `already_referred_to_specialist`, and `public_care_track` before generating referral-related recommendations.
3. Ask high-value contextual questions when appropriate: onset days, primary symptom cluster, travel time, lives alone, interpreter/language, smoking, education.
4. Ask G8 only as "Has a formal G8 assessment been completed? If so, what score?". If unknown, send `null`. Do not synthesize test scores.
5. Query backend; use returned `predictions_and_gaps.blind_spots` for optional follow-up and permit **re-analysis** after changes.

**Question-selection requirements:**

- At most one or two clear questions per agent turn; prefer multiple-choice choices where they reduce friction.
- Group related questions, show progress, allow "Unknown / skip".
- Never ask for fields already confirmed; never repeat a resolved question.
- Questions should be care-phase-sensitive. Avoid asking staging before work-up or a G8 score as if it were mandatory for every age.
- The agent can explain *why* it asks about a field (e.g., travel barriers) without assuming a diagnosis.
- Every correction updates `IntakeState` and invalidates stale analysis results until rerun.

### 4.3 Submit only validated payload, not source materials

Write `buildPatientAnalyzeRequest(intakeState)` as a **pure, tested function**. The function:

1. Checks all required fields and boolean defaults that may change recommendations.
2. Validates exact enums and numerical bounds (do not send extra internal metadata in body).
3. Uses canonical `region_name` from `/regions` to avoid ambiguous substring matching.
4. Maps unknown optional values to backend-supported `null`/`unknown`, not false certainty.
5. Emits just the backend fields listed in section 2.1.
6. Rejects an unconfirmed severity score instead of inserting a fake value.

For UI/agent orchestration, call ML through a single typed integration client. **Never** call Python/SHAP directly from the LLM.

---

## 5. Handling clinician review and urgency — safety-critical distinction

**Do NOT implement autonomous clinical referral/triage based on `predicted_cancer_index_age_std`, SHAP, county indicators, `pathway_days_estimate`, or an invented 'patient risk percentage'.** Those outputs are not clinically validated individual urgency scores. Likewise, backend flag `high_symptom_severity: severity >= 6` is an internal heuristic flag, not established triage guidance.

Implement a **review-assistance workflow**, not autonomous medical orders:

- A `ReviewDraft` contains the case ID (synthetic), date/time, confirmed intake fields, actual API response references, recommendations, limitations, and a human-readable brief.
- Available statuses: `draft`, `needs_clinician_review`, `reviewed` (demo-local state only).
- `Send for clinical review` opens a preview; requires an explicit click; then records locally in a clearly labeled **simulated clinician inbox**.
- Use operational prioritization only for the demo (e.g. unreviewed case, missing critical information, conflicts, or a *clinician-entered* priority). Name it `review_priority`, not `cancer_risk` or `clinical_urgency_probability`.
- If the project later adds clinician-approved, externally validated urgency rules, gate them behind configuration, provenance and human approval. They are **out of scope** for this hackathon.
- If a user describes immediately dangerous symptoms, do not rely on model-based threshold logic. Show a general advisory to seek appropriate local emergency care instead of producing a precise autonomous triage category.

**Every intervention should be presented as a proposal for professional/local-system review, not as a medical order.** Avoid presenting the doctor's decisions as already completed.

---

## 6. Evidence, equity and explainability UX

Each data element should be typed and labeled by evidence class. At minimum render:

| Visual element | Source / type | Mandatory label |
|---|---|---|
| County waits, screening invitations, education %, living alone % | observed county data (`/regions` or `county_context.indicators`) | **Observed county data**, year; source claimed by supplied dataset |
| Regional model prediction | `predicted_cancer_index_age_std` | **Model projection — incidence index, not patient risk** |
| SHAP drivers | `shap_drivers_baseline` or `county_shap_drivers` | **Model contributors, not proven causes** |
| What-if scenario | `predictions_and_gaps.what_if` | **Hypothetical model projection; no causal estimate** |
| Patient pathway days | `pathway_days_estimate` | **Heuristic estimate; not a measured patient timeline** |
| Patient micro recommendations | `doctor_micro` | **Proposed action; clinician review required** |
| System interventions | `department_macro` | **Proposed county-level intervention, local validation required** |

When the backend returns `confidence_and_limitations`, **surface its limitations and CV metrics** (may use collapsed disclosure, but never suppress). Distinguish unverified assumptions from verified data even when the backend prose seems confident. Do not state an indicator's source URL exists in the response if only a source name is returned.

**Equity story:** show barriers along care stages:

- Detection: screening invitation/participation distinction, symptom recognition/education/language (only what is documented).
- Access/primary care: waits, travel burden, whether referral exists.
- Diagnostics/MDT: documented staging gaps, continuity (only when the patient's work-up is actually underway).
- Treatment initiation: any documented actual delays; otherwise clearly label projected timelines.

For every showcased intervention, display `responsible_actor`, `justification`, and **at least one measurable `success_metric`**. Do not make statistical statements about sex/education gaps unless data actually supports subgroup comparisons; sex-specific screening invitation indicators do not on their own prove sex inequity.

**Sources and traceability:** annotate the demo's source material with URLs where verified, dates, measure definitions and geography. Start from the existing `BRIEF.md` references and original repository dataset; do not invent missing denominator, study result or validated outcome. For an unsupported claim, use `UNKNOWN` or explain data limitation rather than silently filling it.

---

## 7. Implementation tickets — execute in this order

### P0 — Verify backend and lock its contract (before frontend polish)

- [ ] Locate the live `mlBackend` code and the `.joblib` artifact; confirm content hash/version where possible.
- [ ] Create a reproducible Python environment compatible with saved model (check Python, pandas, scikit-learn, SHAP, numpy, joblib, FastAPI, Pydantic, Uvicorn). Prefer teammate's working versions; **do not make up a lockfile**. Document actual tested versions in `docs/dependency-lock.md`.
- [ ] Run `python -m mlBackend.test_api` from repo root and log actual pass/fail. The artifact has previously exhibited scikit-learn/pandas deserialization incompatibility in a different environment; fix compatibility or regenerate under the teammate's approved environment, **without silently changing model semantics**.
- [ ] Start API and confirm `GET /health`, `GET /regions`, `POST /analyze/region`, `POST /analyze/patient` in the actual environment.
- [ ] Save **actual** sanitized example responses as test fixtures only after successful calls; don't use doc examples as evidence that endpoint works.
- [ ] Mirror API schemas in TypeScript + runtime validation (`zod` or equivalent). Handle extras/optional response fields robustly.
- [ ] In the API client, implement timeouts, robust 400/404/422/5xx handling, health status and retry (bounded retries only for safe idempotent reads/analysis).

**Exit:** four live endpoint checks pass; model loads; request/response shape tests pass; version mismatch resolved or explicitly identified as a demo blocker.

### P1 — Build the minimal integrated demo (non-LLM first)

- [ ] County selector driven by `/regions` (no invented counties or figures).
- [ ] Regional analysis view driven by actual `POST /analyze/region`.
- [ ] Guided synthetic patient intake with `IntakeState`, provenance, conflicts, confirmation.
- [ ] Load at least one local FHIR R4-compatible synthetic Bundle fixture and show extracted facts/unknowns.
- [ ] Dynamic question planner gets required fields first; optional `blind_spots` after analysis.
- [ ] `buildPatientAnalyzeRequest` and actual `POST /analyze/patient` call.
- [ ] Render `doctor_micro` and `department_macro` directly from backend with responsible actors and success metrics.
- [ ] Clear separation of observed facts, ML projections, SHAP, heuristic day estimates.
- [ ] Local clinician-review **draft** and manual simulated submission.

**Exit:** one clean path from synthetic data to county analysis, patient analysis and simulated review in a fresh browser session.

### P2 — Robustness + clinical guardrails + clearer decision support

- [ ] Demonstrate correction/conflict resolution and that changing region recomputes, not displays stale results.
- [ ] Validate exact API enum constraints, unknown handling, severity 0/10 bounds, 404 region, 422 response.
- [ ] Show loading, empty state, backend offline message, explicit fixture-only offline mode.
- [ ] Optional non-causal regional what-if; label projection clearly.
- [ ] Short evidence drawer, limitations, source metadata and actual model CV output.
- [ ] Add automated end-to-end and unit tests; remove broken demo actions and dead buttons.

**Exit:** deterministic demo path works with no external model provider; no fabricated source or urgent clinical claim.

### P3 — Optional intelligence and visual polish ONLY if P0–P2 are green

- [ ] Add LLM-based extraction from **synthetic** natural-language notes behind a server-side provider interface and a deterministic fallback; validate every proposed value against schema before confirmation.
- [ ] Optional voice input if it does not introduce reliability/deployment risk.
- [ ] Strong visual hierarchy, responsive design, one-click preset for judge demo.
- [ ] Freeze implementation, record demo video/screenshots, rehearsed two-minute narrative.

**Non-goals for Sunday:** official Kanta/EHR write integration; processing real patient data; autonomous clinical referrals; implementing a new ML algorithm; training an individual cancer-risk model; claiming predicted reductions in mortality from what-if deltas; using Gemini Decisions API purely as a technological flex.

---

## 8. Concrete tests / acceptance criteria

Build fast automated tests (unit + BFF integration + UI smoke). Minimum cases:

| ID | Test | Expected result |
|---|---|---|
| T01 | `/regions` resolves Lapland from actual returned county list | Stable canonical county used in POST requests |
| T02 | Required fields missing (`region`, `age`, severity) | Agent asks; no ML POST is sent |
| T03 | FHIR and manually entered referral status conflict | `conflicted`; explicit resolution required |
| T04 | `symptom_severity_score` = 0 and = 10 | Valid values are preserved exactly; not changed by falsy defaults in frontend |
| T05 | `symptom_severity_score` outside 0–10 | Client rejects; backend 422 where applicable |
| T06 | Unknown G8 / education / lives alone | `null` / `unknown`; no inference or fake score |
| T07 | No staging work-up yet | Empty staging not interpreted as clinical deficiency |
| T08 | Confirmed intake -> `POST /analyze/patient` | Parses the five actual sections; no transcript sent |
| T09 | Updated answers / county | Prior result marked stale, fresh API call required |
| T10 | Backend `blind_spots` | Questions only for missing, relevant fields; allow skip |
| T11 | Regional analysis | Observed and predicted values visually distinct; SHAP labeled noncausal |
| T12 | What-if | Calls backend and displays projection / no claims of real-world effect |
| T13 | API 404 / 422 / network down | Clear recovery message, no fake success |
| T14 | Offline fixture mode | Explicit `DEMO FIXTURE — NOT LIVE MODEL RESPONSE` label |
| T15 | Review queue | Requires human click; no actual real-world referral/e-mail |
| T16 | No LLM API key | Entire scripted demo still works deterministically |
| T17 | Evidence and recommendation cards | Real API action, owner, justification, metric, limitations shown |
| T18 | End-to-end two-minute run | Single scripted narrative from county barrier to case + review |

**Special regression:** current backend `estimate_pathway_days` uses `or` defaults for several numeric fields, so `symptom_severity_score=0` may be internally treated as default 5 in some calculations. This is a **backend discrepancy to flag to the owner**, not something to hide or compensate for by changing submitted values. Write a regression test and coordinate any change. Likewise, confirm published G8 threshold and model CV numbers before claiming clinical validation.

**Testing commands (adjust to installed scripts, do not claim success before actually running):**

```bash
# Backend (from root after setting up a compatible environment)
python -m mlBackend.test_api
uvicorn mlBackend.api:app --host 127.0.0.1 --port 8000

# Frontend examples only if a Next.js app is created
cd web
npm install
npm run dev
npm run build
npm run test        # create the script if needed
```

---

## 9. Judge-ready demo script (target: under 2 minutes)

**0–20s — Problem:** “Finland has a national cancer strategy, but care accessibility differs by local circumstances. Decision-makers need to know where barriers occur and what action to take.” No unproven numerical disparity claims.

**20–45s — County:** Select Lapland from `/regions`; show observed primary-care waiting indicator and other actual county indicators, with dates. Explain one **potential access barrier** supported by those figures. Open the backend-generated `department_macro` intervention and identify the responsible authority and a measurable success metric.

**45–70s — Fragmentation:** Load a synthetic FHIR case with incomplete information. Show the agent reconciling fragments and asking for one meaningful missing value (e.g., travel time or symptom onset). Confirm structured intake; demonstrate that no medical detail was invented.

**70–100s — Action:** Call `POST /analyze/patient`. Show county context, the distinct pathway heuristic (labeled), and one `doctor_micro` recommendation. Highlight *why the rule suggested the intervention*, not a claim about true causes of cancer risk. State that the intervention is a proposal for clinician review.

**100–115s — Accountability:** Click “Prepare clinician review”; show the **simulated** review draft and relevant evidence/limitations. This is not a real hospital integration.

**115–120s — Outcome:** “One system connects regional evidence, fragmented patient context, and actionable, reviewable care improvements. Next, counties can test whether measured pathway gaps actually shrink.”

Also prepare an alternative path if the API stops responding: rehearse an **explicitly labeled fixture-based replay** and explain honestly what is recorded vs live; never silently substitute a stub.

---

## 10. Delivery checklist and definition of done

Deliver to the team:

1. **Runnable final project** with documented setup. Preserve existing `mlBackend` untouched unless agreed integration fixes are needed.
2. **README** describing architecture, requirements, backend/frontend commands, env variables, demo fixtures, and setup from clean clone.
3. **Verified API compatibility report**: tested versions, endpoint checks, any failing tests, exact sample output paths, error handling.
4. **Test results**: command + pass/fail counts (do not fabricate).
5. **Demo runbook**: initial conditions, exact clicks, synthetic data case, backup mode, under-two-minute narrative.
6. **Evidence/limitations note**: regional incidence target vs equity, observed vs projected, heuristic pathways, no autonomous care.
7. **Change summary** distinguishing teammate backend, agent integration, frontend and optional additions.

Final acceptance requires **ALL**:

- [ ] Real existing backend responds in the tested environment.
- [ ] Both regional and patient flows invoke the real API, not hard-coded values.
- [ ] The agent extracts, asks, confirms, and transmits structured data with provenance.
- [ ] Patient Tier B fields affect only the existing rule/heuristic path; no fake “personal SHAP risk” is shown.
- [ ] No clinical referral is automated or misrepresented; simulated review is clearly labeled.
- [ ] No fabricated patient data, scientific claims, citations, predicted equity gains, or source URLs.
- [ ] The UI tells a coherent county-to-patient story in <2 minutes.
- [ ] No fragile external AI API is required for the main demo.
- [ ] Actual test results, remaining known limitations, and deployment instructions are documented.

---

## 11. Decision authority and change control

- The **teammate** owns regional ML, SHAP logic, and current `doctor_micro`/`department_macro` generation. Propose fixes with tests rather than rewriting on your own.
- Our **integration team** owns intake/FHIR orchestration, canonical county resolution, frontend, field provenance, API client, and simulated review UI.
- If scientific or clinical validity concerns are found, **surface them and avoid the unsupported claim**. Do not mask them with visual polish or stronger model language.
- If development time is tight, **cut P3 and the what-if view before cutting P0/P1**. Regional evidence + one successful synthetic patient flow + actionable intervention is the non-negotiable working demo.

**Codex final report format:**

```text
IMPLEMENTED
- ...

VERIFIED
- command; result ...

BLOCKERS / UNVERIFIED
- ...

DEMO WALKTHROUGH
- ...

FILES CHANGED
- ...

REMAINING CLINICAL / SCIENTIFIC LIMITATIONS
- ...
```

**Go build the integrated demo. Keep it auditable, operationally honest, and easy for AstraZeneca's nontechnical judges to understand.**
