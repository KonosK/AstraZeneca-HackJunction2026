# Evidence and clinical limitations

The supplied data are county aggregates attributed by OncoFlow to THL Sotkanet / Finnish Cancer Registry. The current API reports 23 profiles for 2024. Raw indicator IDs, denominators, extraction dates and source-validation artifacts are not included. The UI says observed **in the supplied dataset**, not independently revalidated national evidence.

Lapland has 39.5% primary-care waits over seven days in this dataset. This suggests a potential access barrier; it is not a cancer-specific waiting-time estimate or proof of unequal treatment. Incidence index differences cannot establish differences in care quality. Screening invitation coverage is not participation or completed follow-up. No subgroup or mortality effect is inferred.

The actual model reports GroupKFold mean R² -0.1381514574, MAE 4.669206 and RMSE 6.296502. It predicts regional age-standardized cancer incidence index. The negative R² limits predictive claims. Neither model output nor SHAP authorizes individual triage. SHAP is a fitted-model attribution, not a causal mechanism.

Backend pathway days are heuristic estimates. Its 155-day benchmark is attributed by supplied backend text to a Finnish lung-cancer pathway study; this source and intended G8 threshold (<14 in code) need clinical owner verification. A known backend discrepancy treats severity 0 as default 5 in some calculations; a characterization test records it. The frontend sends 0 faithfully and does not silently compensate or patch teammate behavior.

The 78/32-day simulation is an authored comparison from the supplied simplified HTML. It claims no measured benefit, stage change, treatment initiation, reduced deaths, or causal benefit. Actual heuristic values are available separately in the clinician evidence disclosure.

Goal 3 coverage: proposed focus is primary-care accessibility and support for older people living alone. Backend strategy mapping supplies proposed actors and success metrics. Access to the cited national strategy PDF was denied by the network; the exact official Goal 3 indicator identifier, numerator/denominator and mapping remain **unverified**, a material judging limitation. Do not present challenge compliance as fully proven until a domain owner checks the source.

Every patient record is synthetic. FHIR support is intentionally narrow: birth date / explicit gender / candidate county, ambulatory Encounter mapping, active ServiceRequest as a reviewable candidate, and explicit answers in a known synthetic QuestionnaireResponse. Other resources and absent clinical fields remain unknown. Formal G8 is never inferred. Empty staging fields mean not assessed, not complete.

No clinical threshold set is validated. Routing is a versioned, configurable demo workflow based on context completeness, successful analysis and human decision state. Proposed backend clinical actions require professional validation even if their prose sounds directive. No referrals, prescriptions, appointments, hospital messages or EHR writes are issued. Follow-up dates are illustrative, not safety monitoring. This prototype must never process real patient data.
