# Thriver Care / SILTA — Junction 2026

**Goal:** deliver the strongest truthful, demonstrable entry for AstraZeneca's Equal Care Across Finland challenge, reusing the existing OncoFlow FastAPI/ML/recommendation backend and the dashboard source that the team supplies. Do not start a different product or rewrite teammate ML.

## Authority and conflicts
1. `docs/00_CHALLENGE.pdf` — official mandatory judging requirements.
2. `docs/02_INTEGRATION.md` — API contracts, architecture, boundaries, provenance, clinical safeguards. API Python code is authoritative for *existing actual behavior*.
3. `docs/01_DESIGN.md` — four visual worlds, global bubble, identity and interactions; the original logo and bubble reference assets take precedence over approximations.
4. `docs/03_BRIEF.md` — scoring and source leads, verify claims.
5. Actual uploaded dashboard source code — reuse/adapt as appropriate, do not assume it is already wired.
If architecture/document conflicts, protect data truthfulness and safety and log the decision in `docs/decisions.md`.

## Build boundaries
- Existing `mlBackend/` belongs to teammate. Preserve its public contract and pretrained model; do not retrain or silently patch clinical/recommendation behavior. Compatibility/environment fixes are allowed; substantive fixes require owner review.
- No actual EHR/Kanta/Maisa/Apotti production access, patient data, referrals or clinical authorizations. Use clearly marked synthetic FHIR/demo data.
- County incidence index != inequality/outcome measurement or patient cancer probability. SHAP != causality. Days projections are heuristics, not measured impact. Mark all these visibly.
- The default journey MUST run without external LLM, ElevenLabs, proprietary provider credentials or network model services. Deterministic agent orchestration and existing backend are the main deliverable.
- Provider adapters for Gemini and ElevenLabs are optional and must not be blocking. Do not claim ElevenLabs integration works without real calls and credentials.
- Do not invent medical facts, URLs, metrics, source citations, vendor UI screenshots, original logo, or API success. Unknown/missing information stays unknown.
- Avoid dependency churn, extra infrastructure, or unnecessary token-heavy tasks; act on the single build brief end to end.

## UI and delivery
- Four routes: Simulation, Patient (Maisa-like), Doctor (Apotti/Epic-like), Dashboard, with ONE fixed top-center floating navigation bubble.
- Original logo lives in `assets/brand/` (if supplied). Bubble reference in `assets/references/` (if supplied). Do not draw a fake logo if absent: use clear text wordmark and report missing asset.
- Existing dashboard source supplied in `dashboard-source/` or pre-existing project frontend. Identify and preserve reusable parts and visual intent; do not clobber it or create two competing apps.
- Visually test all four routes. Ensure required buttons and steps work. One synthetic end-to-end case must show regional evidence -> intake/provenance -> reviewable proposal -> county-level intervention.
- Test Python API and frontend build, integration and functional demo flow. Generate `docs/FINAL_REPORT.md` and `docs/DEMO_RUNBOOK.md` with verified outcomes and remaining blockers.
- Do not push to main, merge, deploy external services or spend money without permission. Prepare deploy configs and copy/paste setup if credentials are unavailable.
