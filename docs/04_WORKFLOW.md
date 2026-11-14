# THRIVER CARE / SILTA — Executive workflow and demo handoff
**Junction 2026 · AstraZeneca Equal Care Across Finland · 14 Nov 2026**

## Objective
Deliver a coherent, reliable, two-minute demonstration connecting a **synthetic individual patient journey** to **regional operational decision support**, using the existing OncoFlow backend and regional dashboard. The purpose is to identify potential access barriers, organize information, surface reviewable interventions, and support equitable care. Do not claim validated clinical efficacy or actual EHR integration.

## Source of truth
Read `AGENTS.md`, `docs/00_CHALLENGE.pdf`, `docs/01_DESIGN.md`, `docs/02_INTEGRATION.md`, `docs/03_BRIEF.md`, `mlBackend/api.py`, `mlBackend/recommendations.py`, `mlBackend/API_CONTRACT.md`, and the existing `regionDashboard/` before implementation. Existing Python behavior overrides speculative descriptions. Preserve teammate ML and recommendation code. This handoff clarifies the desired product journey; it does **not** authorize replacing established API semantics or clinical safeguards.

## End-to-end MICRO workflow
1. **Periodic check-in:** A patient opens a simulated Maisa-like portal and spends ~60 seconds describing how they feel and any symptoms. Voice and text must both work; check-in cadence is configurable, not a clinical prescription. The interface supports language selection and accessible, plain-language wording.
2. **Voice capture:** With permission, record audio and send it through a server-side ElevenLabs STT adapter when configured. Show editable transcription and require patient confirmation. ElevenLabs TTS may optionally narrate prompts. If API/network/permission fails, typed text is fully functional; do not fake successful STT or spend unnecessary credits.
3. **Longitudinal record assembly:** SILTA retrieves *available synthetic* patient history from local FHIR/demo fixtures (e.g., Patient, Encounter, Observation, Condition, ServiceRequest, QuestionnaireResponse) and current check-in. Normalize facts with source, date, uncertainty, and conflict flags. Never imply production access to Maisa, Kanta, Apotti or Epic.
4. **Gap detection:** Compare confirmed facts against the actual `POST /analyze/patient` contract and contextual question requirements. Distinguish absent, unknown, contradictory, and not applicable fields. Never infer unrecorded clinical findings or insert default severity/frailty scores.
5. **Adaptive questionnaire:** Ask a short, prioritized set of relevant questions adapted to known language, communication needs, symptom context, and previously collected information. Allow skip/unknown, correction, and free text. A new answer updates the structured record; ask again only when justified.
6. **Patient review:** Present a clear structured summary with source and missing data. Patient/demo operator confirms before analysis. Only structured, validated fields are sent to OncoFlow, not a raw transcript.
7. **Analysis:** Call the **real** `POST /analyze/patient`. Render the existing five response sections: `predictions_and_gaps`, `contributing_factors`, `recommended_interventions`, `supporting_evidence`, `confidence_and_limitations`. Distinguish regional observed metrics, regional model projections, rule-based flags, heuristic pathway days, and evidence limitations.
8. **Routing:** A transparent, deterministic policy classifies **review required**, **more information needed**, or **routine monitoring / existing care pathway**. Trigger rules and thresholds are configurable, displayed, versioned and auditable; do not invent clinical thresholds. Missing/contradictory data or explicit red flags must not be silently treated as low risk. The demo must not autonomously diagnose, triage clinically, prescribe or suppress necessary medical review. If no medically approved threshold set exists, use clearly labeled *demo-only workflow rules*, and require clinician approval before clinical deployment.
9. **Doctor inbox:** If review is required, create an **in-app draft** containing check-in, assembled timeline, provenance, uncertainties, relevant flags, projected pathway days (clearly heuristic), suggested `doctor_micro` actions, sources, and limitations. Doctor can **accept, edit, reject, request more information**. Log choice and rationale locally. No real referral or EHR write occurs.
10. **Feedback and follow-up:** Show the patient's review status and next simulated check-in; log decision status and subsequent outcome measures where available. Do not promise automated clinical follow-up or patient safety monitoring.

## End-to-end MACRO workflow
1. Load real county records from `GET /regions`, with indicator definitions, dates, source provenance and missing values visible.
2. Call `POST /analyze/region` for a selected county; distinguish **observed data** from the model's predicted age-standardized cancer incidence index and SHAP associations. The existing model does **not** predict individual cancer probability, causal factors, or directly measured unequal treatment.
3. Display `department_macro` recommendations with action, responsible actor, rationale, evidence/limitations, and success metric. Identify the precise pathway stage affected when evidence supports it.
4. Optional `what_if_overrides` call shows a hypothetical model scenario, **not proven causal days saved or deaths avoided**.
5. Show how future consented, authorized and properly aggregated workflow measurements could complement public data; do **not** pretend synthetic patient check-ins are real population-level evidence.

## Four-screen demo (target 120 seconds)
- **0–15 s — Simulation:** Select one real county and one explicitly synthetic patient; introduce a potential bottleneck and start the shared scenario.
- **15–55 s — Patient:** Record or use a preloaded short sample/check-in; show ElevenLabs transcription if actually connected, editable confirmation, historical record assembly, missing-field prompt and adaptive question.
- **55–90 s — Doctor:** Confirm structured intake, call the real backend, show clearly labeled heuristic/observed/model outputs and reviewable `doctor_micro` intervention; doctor accepts/edits/requests information in local inbox.
- **90–120 s — Dashboard:** Switch to the same county, display sourced observed indicators, explain the limits of county SHAP, highlight one grounded macro intervention and its measurable success metric.
- **Fallback:** If live voice is unavailable, type the exact sample. If external model services fail, use deterministic agent. If backend fails, show an explicit error and a clearly labeled recorded fixture, never silently substitute fake live results.

## Critical implementation and acceptance criteria for Codex
- Maintain four existing planned routes (Simulation, Patient, Doctor, Dashboard), consistent shared scenario and fixed top-center navigation bubble per `docs/01_DESIGN.md`.
- Reuse `regionDashboard/` and `mlBackend/`; do not create competing dashboards or retrain the ML.
- Add a real server-side ElevenLabs integration only if configured and testable; keep key secret and typed-text fallback. Do not claim integration success without a real call.
- Patient record merge has provenance, missingness, conflict handling, corrections and explicit confirmation.
- Personalized questions respond to confirmed context; do not invent symptoms, history or questionnaire answers.
- Routing logic has visible reasons and configurable **demo-only** thresholds unless clinically validated; default to review when uncertainty matters.
- Doctor actions persist in local demo state and have an audit trail. No clinical system writes.
- Macro analysis works independently of micro and uses genuine public aggregated data with evidence classes and caveats.
- Validate actual API routes and response fields. Test end-to-end patient→doctor→dashboard, voice failure fallback, missing fields, backend outage, reset and responsive layouts.
- Update `docs/DEMO_RUNBOOK.md` and `docs/FINAL_REPORT.md` with actual implemented behavior, test commands/results, unresolved limitations and a precise 2-minute script.

## Scientific truthfulness — nonnegotiable
The current Random Forest predicts **regional age-standardized cancer incidence index**, not patient delay days or cancer risk. Patient pathway days are **heuristic projections**, not observed waiting times or verified intervention effects. County SHAP drivers are **model associations**, not proven causes. No patient-level data is supplied by AstraZeneca; all micro cases are synthetic. Clinical safety rules and thresholds are not validated merely because they work in the demo. The primary challenge objective is **evidence-based, actionable regional equity improvement**, not an impressive patient chatbot.

## First instruction to Codex
Compare this workflow against the existing code and specifications. Implement missing user-facing links and state transitions in the current repository without overriding backend ownership or falsifying capabilities. Report which steps already work, which are implemented, and which remain demo-only or blocked. Prioritize one reliable, complete vertical slice over feature breadth.
