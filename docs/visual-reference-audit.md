# Visual reference audit — 14 November 2026

## Supplied and inspected

- `assets/brand/thriver-logo.svg`: actual supplied vector, copied unchanged into frontend public/brand. Its source geometry and colors are preserved.
- `assets/references/Captura de pantalla 2026-11-14 182747.png`: actual supplied floating capsule reference, visually inspected. Pale capsule, larger active segment and compact inactive icons reproduced. The expected filename `floating-bubble-reference.png` is absent; the supplied screenshot is its usable substitute.
- No genuine Maisa or internal Apotti screenshot was supplied. No authenticated EHR access was attempted. The attached simplified HTML is a workflow reference, not evidence of authentic EHR appearance or scientific effects.

## Patient references attempted

| URL | Intended reference | Access result |
| --- | --- | --- |
| https://ukk.maisa.fi/en/ukk/what-is-maisa/ | Official FAQ / visible portal patterns | Proxy tunnel 403 |
| https://www.hus.fi/en/e-services/instruction-videos-for-Maisa | Official HUS instructions | Proxy tunnel 403 |

## Clinician references attempted

| URL | Intended reference | Access result |
| --- | --- | --- |
| https://www.apotti.fi/en/the-apotti-ecosystem/ | Official integration / ecosystem context | Proxy tunnel 403 |
| https://fhir.epic.com/ | Public Epic integration documentation, not an internal chart screenshot | Proxy tunnel 403 |

These URLs were supplied by the design specification. Their current content could not be inspected, so none is claimed as a visually verified screenshot. No page-level observation, publication date or pixel-perfect fidelity is asserted.

## Actual reconstruction and uncertainty

Patient: restrained lavender/indigo header, simple portal task and reduced sidebar, based on the supplied written design direction. The `maisa` text is a reconstruction, not a downloaded official logo. The questionnaire, voice controls, source summary and local submission confirmation are SILTA additions. No MyChart/Epic asset is fabricated.

Doctor: blue-gray toolbar, synthetic patient banner, single inbox and compact review pane, based on the supplied written direction. The APOTTI wordmark is plain text. All chrome is reconstructed; no internal Epic layout is claimed authentic. No fabricated lab values, allergies, diagnoses or live order buttons. SILTA adds confirmed context, actual backend proposal, optional evidence disclosures and local decision controls.

Simulation and dashboard: Archivo (bundled OFL font), midnight/powder/coral brand treatment. Simulation emphasizes one paused story; dashboard retains the teammate map, geo join, metric utilities and county list. Shared information state does not impose shared host styling.

Screenshots in `docs/evidence/screenshots/` cover all four views at 1440, 1280 and 390 px plus questionnaire/submission/review/final states. Automated checks assert capsule bounds remain identical across routes and no page-wide horizontal overflow. Visual inspection confirms the intentionally reduced host density; comparison against genuine host screenshots remains unverified.

To complete authentic-reference research, an owner can provide genuine screenshots or allow `ukk.maisa.fi`, `www.hus.fi`, `www.apotti.fi`, and `fhir.epic.com` in environment network settings. No draft network changes were made.
