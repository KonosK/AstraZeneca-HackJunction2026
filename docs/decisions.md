# Integration decisions

- 14 November 2026: Preserve `mlBackend/` source, model and CSV byte-for-byte. New integration is a separate Python module and an extension of the existing React app. No retraining.
- New user workflow and clarification override any demand for visually dense host replicas. Patient and clinician shells are deliberately reduced reconstructions with explicit demo labels; meaningful new SILTA content remains obvious.
- Preserve all four path-based routes and the supplied floating capsule silhouette. SVG copied verbatim from supplied brand asset; no generated logo.
- Supplied simplified HTML contributes workflow structure and 78/32 illustrative time points only. Its claims about stage progression, 85% improvement, deaths avoided, screening results, transport coordination and actual EHR synchronization are **not adopted**.
- Human gates: at scenario day 3 require confirmed patient intake, actual analysis (or explicitly recorded replay), preview and local submission. At day 7 require explicit clinician acceptance. Rejection/more information never advances the accelerated branch.
- No clinically approved routing policy exists. Version `demo-workflow-v1` checks missing/contradictory context and human review state; no clinical risk thresholds, severity-based automatic referral or autonomous suppression of review.
- `what_if_overrides` is described in documents but absent from the actual request model/route. Omit the what-if feature rather than invent API success.
- The default journey uses deterministic rules and text. The attached ElevenLabs override authorizes a real optional adapter; a live auth rejection is a blocker for successful voice validation, not for the text workflow.
- Existing cloud draft/publication settings are untouched, respecting the user's explicit instruction. Repository startup scripts document the new server; nothing is published, pushed, merged or externally deployed.
