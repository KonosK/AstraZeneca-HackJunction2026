# THRIVER CARE — CODEX MASTER DESIGN SPECIFICATION

**JUNCTION 2026 · AstraZeneca / Equal Care Across Finland**  
**Document type:** master implementation prompt — **VISUAL DESIGN, UI/UX AND FRONTEND ONLY**  
**Status:** design direction locked; separate architecture, agent inputs/outputs and API contracts will be supplied later.  
**Primary instruction:** implement the product described here, **not the old Figma mockups**.

---

## 0. Your role and non-negotiable brief

You are the **founding product designer, senior frontend engineer, interaction designer, and visual QA reviewer** of **Thriver Care**, whose core coordination engine is **SILTA**. Build a compelling, working, navigable frontend demonstration intended for a two-minute live pitch to AstraZeneca's judges and potential Finnish healthcare partners.

You are not generating a generic healthcare SaaS template. You are recreating **four deliberately different software worlds**, connected by **one floating, centered, universal navigation bubble**:

1. **Simulation** — our own highly designed, expressive, cinematic yet restrained Thriver experience.
2. **Patient** — a high-fidelity, convincing extension **inside real-looking Maisa / MyChart**, as if the user were already using the Finnish patient portal and SILTA had been added to it.
3. **Doctor** — a high-fidelity, clinically credible extension **inside real-looking Apotti / Epic Hyperspace or Hyperdrive**, as if SILTA were an embedded clinician-review module in the existing EHR.
4. **Dashboard** — our own distinctive Thriver decision-intelligence product for wellbeing services counties and national decision-makers; editorial, evidence-first, action-oriented.

**These four views must NOT share a generic component library aesthetic.** The patient and doctor tabs must each inherit their **host application's** true visual language. Simulation and dashboard can both use the Thriver palette while having their own distinct composition, type hierarchy and motion grammar. A common brand is **not** a mandate for common layouts.

The **only universally identical UI object** is the floating **central navigation bubble**. It overlays all four worlds, always in the same position, and makes it clear to judges that they can move across the demonstration's four contexts.

### Prior work explicitly rejected

- Do **not** reconstruct or implement the previous Figma screens as source-of-truth. Their layouts were rejected as too generic and inaccurate to Maisa/Apotti.
- Do **not** use earlier AI-generated collages labelled “real references” as proof of how the actual software looks. Generated collages are moodboards, **not screenshots of genuine products**.
- The supplied user screenshots of the real Maisa interface, documented public images, and official vendor documentation take precedence over any generated visualization.
- The simulation must **not** resemble the doctor interface, the Maisa portal or the dashboard.
- **Do not remove, relocate or replace the central floating navigation bubble.** This is a hard requirement.

### Design priorities in order

1. Visually faithful Maisa and Apotti host applications.
2. Truly distinctive simulation and dashboard, free of generic AI-dashboard tropes.
3. Perfectly implemented universal central floating navigation bubble.
4. Clear, convincing demonstration of the agent working, days passing, patient context, clinician review and proposed intervention.
5. Responsive behavior, accessibility, performance, code quality and visual polish.
6. Backend integration comes **after** the separate architecture specification; don't invent contracts.

---

## 1. Authoritative references — follow this precedence

1. **User's actual Thriver logo file** (`image(6).png` in the conversation/project assets, or its exact copy provided to the repository). Preserve its actual geometry, proportions and colors. The logo has an arched bridge/connection shape, an upright central stem, a coral point at left and powder-blue elements. **Do not redraw it from memory** or substitute the approximate vector in the old Figma project.
2. **User's floating navigation reference** (`image(9).png` in the conversation). The reference depicts a slim, capsule-shaped, floating, horizontally centered glass/light-grey navigation control; a noticeably larger active slot and smaller icon-only slots. Respect this silhouette and positioning.
3. **Public photographs, UI screenshots, app-store screenshots and official support guides from Maisa/Apotti/Epic**, particularly the user-provided genuine Maisa screenshot and other screenshot examples presented in the conversation.
4. **User's simulation and layout preferences**, including the earlier Gemini direction for an agent activity view with a changing day counter and agent progress — treat these as product/interaction directions, not permission for flashy visuals.
5. This document's concrete rules and acceptance checks.

If you discover an inconsistency, prefer **authentic host-product screenshots for host interfaces**, and prefer **this specification + the original navigation/logo references** for Thriver-owned UI.

### Official and public sources to investigate before styling host interfaces

**Maisa**

- Official Maisa FAQ with examples of mobile and web layouts: https://ukk.maisa.fi/en/ukk/what-is-maisa/
- Official HUS guide and instruction videos: https://www.hus.fi/en/e-services/instruction-videos-for-Maisa
- Maisa as client portal of Apotti: https://www.apotti.fi/en/client-portal-maisa/
- Publicly distributed Maisa app screenshots: https://play.google.com/store/apps/details?id=fi.maisa.maisa
- Real public photo of Maisa login: https://www.hel.fi/en/news/receive-messages-and-letters-digitally-directly-in-maisa

**Apotti / Epic clinician environment**

- Apotti ecosystem and sandbox / SMART-on-FHIR integration documentation: https://www.apotti.fi/en/the-apotti-ecosystem/
- Epic developer documentation: https://fhir.epic.com/
- Use publicly shared screenshots of Epic Hyperspace/Hyperdrive, clinician charts, worklists and referral review views, giving precedence to source-verified screenshots over random illustrations.

**Important constraint:** We are implementing a high-fidelity **prototype replica of the visible reference interfaces**, with a SILTA extension. Match actual publicly visible layout, assets and colors as closely as feasible. Do not assert that we have production access, a commercial integration, access to non-public Epic assets or authorization from Apotti/HUS. If an exact internal control is not visible in the references, preserve the faithful surrounding structure and mark the unknown rather than fabricating it as a verified detail. Avoid scraping private systems or using real patient data.

### Mandatory research artifact

Create `docs/visual-reference-audit.md` containing, for each of the **patient and doctor** views:

- 2–5 specific genuine visual references (URLs and short descriptions), preferably official screenshots / guides;
- source date or date accessed where available;
- observed navigation, font characteristics, spacing density, card/table treatment, colors and hierarchy;
- which host elements are reproduced faithfully, which are reconstructed, and which are SILTA additions;
- discrepancies/uncertainties that cannot be verified.

Do **not** skip reference research and produce an invented “inspired by” interface. If web access is not available to Codex, use the user-provided screenshots and available project assets, record the limitation and avoid claiming pixel-perfect accuracy.

---

## 2. Product identity / brand assets

### Thriver Care palette

| Token | Hex | Role |
|---|---|---|
| `brand.midnight` | `#101828` | Primary ink / deep Thriver surfaces / authority |
| `brand.powder` | `#CBE9F3` | Lightness / approachable intelligence / selective panels |
| `brand.coral` | `#FF654F` | Contrast / major action / timeline intervention marker |
| `neutral.glacier` | `#F5F8F7` | Calm background, only where appropriate |
| `neutral.white` | `#FFFFFF` | Neutral surfaces |

The first **two colors are principal**; coral is **contrast/accent**, not a blanket CTA or alert fill. Add neutral greys and accessible feedback colors only when necessary. This is **Thriver's palette**, **not** the Maisa or Epic palette.

### Brand placement

- Simulation: our logo and brand prominently, but with sophisticated restraint.
- Dashboard: our brand visibly, with editorial rather than marketing treatment.
- Patient/Maisa: the **real Maisa identity remains dominant**. Thriver logo/mark only appears inside the *specific embedded SILTA card or flow*, and may carry an understated “Powered by Thriver Care” label.
- Doctor/Apotti: the **real Apotti/Epic host identity remains dominant**. Thriver mark appears only within the clinician assistant / smart panel.
- Universal bubble: it belongs to the **demo shell**, not to the host patient or doctor application's native navigation.

### Typeface directive

- **Do not use Inter, Geist, a default shadcn look or the first font offered by a UI kit for the two Thriver-owned tabs.**
- Art direction: modern Swiss editorial / neo-grotesque, crisp counters, honest proportions, tightly controlled tracking; think **Helvetica Neue / Helvetica Now / Neue Haas Grotesk**.
- If Helvetica is available and properly licensed in the implementation environment, use it for Thriver headings and core UI. Otherwise use **Instrument Sans** or **Archivo** as a deliberate open alternative; adjust `letter-spacing`, line height and weight to approximate the intentional Helvetica-like voice. Don't claim the fallback *is* Helvetica.
- Patient/Maisa and Doctor/Apotti must **follow their respective actual host typography**. Do not force Helvetica or our chosen display type onto them.
- Hero typography can be large, but be disciplined: compact paragraph width, precise line breaks, not endless 48px headings everywhere.

### The logo

- Locate the **exact supplied transparent logo** from user assets. Copy as `public/brand/thriver-care-mark.png` or use its exact source SVG if present, preserving original geometry.
- Provide both light- and dark-background placement by changing the surrounding background rather than editing/reinterpreting the logo.
- No emojis as logo. No generated substitute. No invented extra curves, glows or pulsating effects on the brand mark.
- Retain the original image within repo history; if vectorizing is needed, keep the raster original and verify a vector version visually before switching.

---

## 3. The universal central floating navigation bubble — CRITICAL

The user explicitly requires **navigation between ALL FOUR applications via a CENTRAL FLOATING BUBBLE**. The bubble is persistent in every route, even though the route bodies have intentionally different visual identities.

### Reference and anatomy

The reference is a low-profile, off-white / very light grey horizontal capsule centered along the **top of the viewport**. It contains exactly four navigation targets:

1. **Simulation** — flow/timeline/agent icon.
2. **Patient** — smartphone icon.
3. **Doctor** — stethoscope icon.
4. **Dashboard** — analytics/chart icon.

A longer **active pill segment** slides horizontally under or around the selected item, while inactive slots are compact and primarily icon-only. The active item may display an icon and short text such as `Simulation`; the labels of inactive items appear on hover/focus or as accessible tooltip. Match the screenshot's overall proportions and understated styling.

### Geometry and visual styling

At desktop width ~1440px:

- `position: fixed; top: 18–28px; left: 50%; transform: translateX(-50%);`
- `z-index` above every app and embedded panel, but **not** above focused confirmation dialogs when a modal needs to take precedence.
- Total width approximately **310–355px**, height **56–64px**. `border-radius: 9999px`.
- Outer material: soft near-white translucent fill (`rgba(247,247,247,.86)` or tuned), very subtle gray hairline, small soft shadow and cautious `backdrop-filter: blur(...)`.
- Active segment: pale neutral grey, not huge saturated branding; width around **110–138px**, more generous than inactive slots.
- Inactive icons: **18–21px**, desaturated dark-gray. Active icon/text high contrast. Real SVG icon set such as Lucide, used consistently *only inside the bubble*.
- Keep padding and gaps measured, not a series of identical random 16/24/32px values.
- On a dark simulation background the bubble remains readable and recognizably the **same object**; allow only subtle dynamic contrast adaptation if strictly necessary.

### Navigation behavior

- Use router-backed real navigation between `/simulation`, `/patient`, `/doctor`, `/dashboard` (or alias to the project's actual routing scheme if the later architecture specifies otherwise).
- Bubble stays anchored at the top-center throughout navigation; active highlight moves with a short restrained spring or **180–240ms** ease-out.
- Correct focus order, mouse hover, keyboard support, tooltips, labels, accessible names and `aria-current="page"`.
- **Never obstruct primary content.** Reserve breathing room at the top of every view, including the phone/clinical replica. If necessary, host the replica in a demo viewport under the bubble rather than injecting the bubble as native Maisa/Epic UI.
- On narrow screens, shrink to **icon-only four equal target widths**, maintaining touch targets ≥44px; preserve centered floating positioning.
- Respect `prefers-reduced-motion`; animated sliding becomes an instant state change.
- Never replace this with a sidebar, top tabs, a nav bar spanning screen width or four cards.

### Visual acceptance test

Capture all four routes and superimpose the bounding box of the bubble: **its position, dimensions and outer styling must match on every route**. Route content is allowed — indeed required — to change radically.

---

## 4. Simulation application — Thriver's expressive flagship

**This is its own world.** Do not borrow a Maisa layout, an Epic/EHR table system or the dashboard's charts. It should feel like a purposeful interactive story about care coordination, not a 2026 AI admin template.

### Art direction

- Rich **Midnight** base, restrained powder-blue surfaces and a few signal-coral interventions, with exceptionally careful typography and off-axis composition.
- Intentional imbalance: one dominant visual, editorial negative space, a carefully aligned but **not formulaic** supporting panel.
- A controlled sense of time and flow. The agent is not represented as an anthropomorphic robot, glittery brain, neural-network node cloud or gratuitous “AI magic” sphere.
- Mild spatial depth may use **one** carefully graded ambient glow, very subtle translucency or a shallow soft gradient. Never multiple glowing cards and nested glass panels.
- Restrained depth, mostly flat surfaces and 1px hairlines. Prefer structure and typographic precision over rounded 24px tiles everywhere.
- Use our original logo tastefully. Bring through the central bubble.

### Required screen content

- A clearly identified simulated cancer care case, source/evidence provenance and current step in the care pathway.
- A **visible running day counter**, stepping through the timeline deliberately (not an arbitrary number rolling infinitely).
- A main **care-pathway timeline** from triggering event through referral, clinical information exchange, clinical decision and relevant next steps. Clearly mark baseline hypothetical days vs proposed/simulated outcome. User may pause, replay, advance and inspect individual steps.
- An **agent activity state machine** showing real meaning in each transition. Example visual state labels: `Monitoring`, `Evidence found`, `Gap identified`, `Patient context requested`, `Response received`, `Clinician review needed`, `Approved` / `Rejected` / `Needs more information` — exact states and transitions later align to the technical input/output contract.
- On the right or within a strategically placed side panel, a compact, understandable **“SILTA is doing X”** activity view. Each step states what was observed, what has been checked and what is waiting for human action.
- A decision-centered comparison (e.g. baseline vs intervention) is possible but must be **explicitly labelled simulation** unless supported by traceable evidence. Numbers such as 24 → 10 days are **not verified clinical results** by default.
- A meaningful way to transition contextually to Patient and Doctor views, without bypassing the global floating bubble.
- User can understand the central insight and the proposed fix in <2 minutes.

### Desired motion

- Days advance as timeline events are committed; a highlight moves across the path, completed steps become quiet, current action becomes visually emphasized.
- Animated agent activity: modest line/dot progress, compact status transitions, log rows revealing as states resolve. Preserve progress and completed items; do not fake thinking with infinite random phrases.
- Normal transition: **180–280ms**; a deliberate day jump can be **350–650ms**, only if it improves comprehension. Avoid decorative constant motion.
- **Controls:** play/pause, reset, next event and optional speed choice. No automation loops that make judging impossible.
- Audio is never auto-played; if a realistic patient voice demo exists, require explicit user interaction.
- All animation must be deterministic with seeded demo events when the real orchestration is not yet supplied.

### Do NOT build

- A generic 3 KPI cards + table + chatbot layout.
- Giant equal-width cards with identical radii and padding everywhere.
- A flat shadcn UI clone.
- Glowing neural networks, purple sci-fi visuals, endless cursors/spinners, random loading percentages.
- A fake live agent calling fake hospital APIs while claiming real integrations.

---

## 5. Patient application — exact-in-spirit Maisa extension

### Objective

Create the experience of a patient **already using Maisa**, the actual Finnish client/patient portal built on **MyChart by Epic**, who receives **one additional SILTA-enabled task** inside their familiar portal. **Do not design a new patient app called Thriver.**

**Highest fidelity mandate:** recreate the **documented, publicly visible Maisa UI** as faithfully as the available references allow, then insert the new workflow in a natural host-native position. Exact match where verified; no visually speculative redesign of the whole host.

### Real-world host details to honor

- The real Maisa **logo** and, where visible, the **MyChart by Epic** co-branding; use legitimate public-source assets or an accurate static reconstruction only where necessary.
- Existing **lavender / indigo / blue** interface treatment, host header structure, light/white content surfaces and simple utilitarian controls. **Do not impose the Thriver midnight/powder/coral palette over the entire portal.**
- Actual user-facing patterns: `Tapahtumat` (events/appointments), `Valikko` (menu), `Viestit` (messages), `Tutkimustulokset` (test results), questionnaires / forms, recent notifications, patient/account avatar.
- On mobile, faithfully honor the host's **real mobile/home screen**; on desktop, if a matching genuine desktop reference is available, honor that separately instead of stretching a phone UI to 1440px.
- Design in Finnish where it improves authenticity, with an English demo language mode if useful for the judges. Do not randomly mix untranslated Finnish, English and Spanish strings in the same flow.
- Dense enough to look like an everyday government-connected healthcare portal, not a premium wellness app.

### Required new SILTA extension (not a redesign)

Surface the new experience at three natural points, using the application's established UI conventions:

1. **Maisa home / events** — an ordinary-looking additional card, event/task notification or alert: `Your care team needs one detail to progress your referral` (content configurable).
2. **Questionnaire / task detail** — a host-styled page or panel allowing a question to be answered. Add the SILTA/ElevenLabs voice capability as a feature *within that task*, not a new full-screen dark Thriver destination.
3. **Submission status** — consent/preview, editable transcription, confirmation of what was actually shared, a record of when it was sent, and a clear understanding that a clinician reviews it.

### ElevenLabs / voice UI

- Show a native-looking voice affordance (microphone, listening state, recording timer, subtle waveform, transcription preview). A text alternative is always available.
- Distinct flow: **Ask permission → record or type → review transcription → correct/confirm → submit → clear status**.
- For audio output, make it explicit that the agent voice is a tool assisting communication, not a physician providing diagnosis.
- Text must explain what is being requested and why, without exposing internal prompt chains or revealing patient data in unsafe contexts.
- Visual state labels map to future voice agent events; the later architecture document will supply exact event names and payload shapes.
- Keep copy honest: until integrated, show demo/synthetic status in the surrounding **demo shell**, not as a deceptive claim that Maisa has deployed SILTA.

### Patient acceptance test

If Thriver's module were visually hidden, **the remaining view must immediately look like Maisa**. The extension should occupy a small, believable portion of the original layout rather than replace its information architecture. The bubble stays visible above the viewport as a non-native demo control.

---

## 6. Doctor application — high-fidelity Apotti / Epic host

### Objective

Present the view of a Finnish healthcare professional already working **inside the Apotti clinical system**, built using Epic technology (Hyperspace/Hyperdrive context). Add one *embedded, reviewable SILTA panel*, not a fake standalone doctor SaaS portal.

**Highest fidelity mandate:** replicate authentic publicly visible Epic/Apotti layout characteristics as closely as source material supports. Do not soften its workflow into the same large, beautifully spaced cards as the simulation or dashboard. It should feel like **real clinical workflow software**.

### Host UI features to match

- Compact, information-dense layout; restrained navy/blue-gray UI chrome and white/grey work surfaces **based on actual available reference screenshots**, not an invented gradient.
- Actual chart-like organization: patient search/worklist, patient banner and identifiers, allergies/alerts, history, lab results, imaging, documents, referral status, tabs, dense rows and compact controls.
- Clinical hierarchy and utilitarian spacing: information density and quickly scannable table rows, not oversized headings and 40px gaps.
- Native-feeling sidebar/toolbar and work queue / referral detail. Avoid a generic doctor profile sidebar with marketing-style stat tiles.
- Restrained Thriver visuals **inside the one embedded extension only**; host typography and colors prevail everywhere else.

### The SILTA clinical panel — required information hierarchy

One compact pane or embedded review drawer with the following, in this order:

1. **Why this was flagged** — the specific coordination gap in the care pathway; no causal claim beyond the evidence.
2. **Available evidence** — each relevant source, date/time, source system, what it supports and what is not verified.
3. **Missing or uncertain information** — surfaced explicitly, separate from available facts.
4. **Patient reply** — what the patient actually reported through the voice or text task, plus transcript if applicable, timestamp and review state; never silently turn an uncertain transcript into accepted clinical fact.
5. **Proposed next action** — an actionable, physician-reviewable draft: e.g. check missing attachment, request further context, prepare a referral packet, contact appropriate unit. **The actual proposed actions are driven by the future architecture contract**, not hardcoded guesses.
6. **Human decision controls** — `Accept`, `Edit`, `Reject` or `Request more information` with confirmation where appropriate. Show what will change **before** committing.
7. **Audit / provenance** — who reviewed, when, what was changed and which sources were used. Show a useful empty state if not yet reviewed.

### Interaction and safety rules

- Treat all displayed patient records as clearly synthetic demo data. Use realistic clinical vocabulary, dates and formatting, but fictitious identities.
- No automatically executed external actions merely because an agent recommended them. Clinical decisions and dispatch are explicit human gates.
- Do not pretend the frontend has live EHR access or read patient-level data from real production systems. Mock a credible embedded view while waiting for the technical integration spec.
- Review states must actually change in the demo UI: pending → editing → approved/rejected/request more info. A static “Approve” button with no feedback is insufficient.

### Doctor acceptance test

If the SILTA pane were hidden, it must read **as an Epic/Apotti-like clinical workspace**, not a Thriver dashboard with a dark sidebar. The content must be legible and information dense. The independent demo bubble remains centered at the top of the browser viewport.

---

## 7. Dashboard application — Thriver decision intelligence

**A fourth, independent world.** This is not the simulation with different cards. The dashboard should be a highly usable, credible control room for Finnish wellbeing services counties, public-health leadership and AstraZeneca mentors. Its role is to turn findings into **owners, interventions and measurable follow-up**.

### Art direction

- An **editorial data-product aesthetic**: precise labels, disciplined tables, small multiples, compact geographic/regional comparisons, interesting typographic hierarchy, restrained brand voice.
- Strong Thriver identity (Midnight + Powder Blue with Coral as deliberate intervention emphasis), yet most analytical surfaces remain quiet, white/light and legible.
- Distinct from both simulation's cinematic narrative and Epic's clinical-density environment.
- Avoid decorative maps, random bar charts, generic health metrics, fake NPS numbers, fake confidence percentages or “AI insights” without provenance.

### Required dashboard anatomy

1. **Executive statement:** one important, verified or explicitly simulated finding, said plainly.
2. **Where the gap exists:** geography / region, stage of cancer care pathway, time period, subgroup if evidenced.
3. **Evidence quality:** data publisher, exact dataset/year, denominator/numerator where appropriate, completeness, comparability and limitations. Explicit tag distinguishing `VERIFIED`, `MENTOR`, `INFERENCE`, `SCENARIO`, `UNKNOWN` when relevant.
4. **Recommendation:** an intervention a real organization can perform, implementation owner, reasonable next step and intended measure of success.
5. **Simulation/impact panel:** if numbers are projections, clearly show assumptions and do **not** present them as observed clinical effects.
6. **Drill-down:** select region and inspect evidence and the timeline stage. If only one genuinely supported disparity exists, present **one excellent insight** rather than filling the page with invented regional comparisons.
7. **Demo walkthrough connection:** an obvious link to replay simulation or open the relevant actor view, in addition to the bubble.

### Judge-ready outcome

A nontechnical decision-maker should answer in <2 minutes:

> Where is the inequity, where does it emerge in the pathway, why is the finding trustworthy, who should do what, and how do we monitor whether it works?

The official challenge puts priority on **actionability (30%), insight (25%), data/transparency (20%), working execution (15%), clarity (10%)**. Express these priorities visually: action and evidence before spectacle.

---

## 8. Shared user journey, without shared visual styling

Suggested high-level narrative for demo mode:

1. **Simulation:** SILTA detects a coordination gap and prepares a next step; the day counter progresses.
2. **Patient:** show how a small request appears natively in Maisa; patient answers with voice/text and reviews the transcript.
3. **Doctor:** show the resulting evidence and context in Apotti; clinician accepts, edits or rejects a proposed action.
4. **Dashboard:** show how aggregate/pathway information can help a local decision-maker identify and address the underlying delay.

Keep each screen navigable independently using the floating central bubble. Preserve coherent **demo scenario state** (same synthetic case and event order) across the tabs, but **do not** make the tabs visually match. A consistent *scenario* is not the same thing as consistent *UI styling*.

For demo rehearsal, support a reset to a known scripted state. All controls presented as interactive should actually respond: there must be no visually prominent dead CTA.

---

## 9. Visual craft — explicit anti-“AI slop” rules

These rules are more important than any UI framework defaults:

- **No unthinking spacing grids.** You may use an 8px baseline for implementation consistency, but deliberately introduce editorial density, asymmetric proportions, controlled breathing space and content-driven breaks. E.g. 52px chapter indent, 19px metadata separation, 70px narrative gap **when purposeful**.
- **No repeated generic card composition** across all four applications. Every screen needs a plausible native layout rationale.
- **No overuse of border radius:** radius should express context (bubble extremely rounded, ordinary host buttons as in actual screenshots, Thriver surfaces comparatively restrained). Do not blindly give all panels `rounded-2xl`.
- **No universal shadcn visual defaults**; using Radix/shadcn for behavior is fine if appearance is rewritten to fit the target world.
- **No gradient-on-every-card, rainbow glows, floating blobs, synthetic human avatars, generic AI sparkles or purple startup gradients**.
- **No uniform hero centered on all tabs**; simulation, patient app, clinician system and executive dashboard demand different information hierarchies.
- **No placeholder lorem ipsum, “Lorem AI insight”, random probability badges** or fabricated clinical results.
- Crisp typography: modest line lengths, intentional weights, consistent punctuation, baseline alignment and useful hierarchy.
- Charts must have precise labels, units, context, accessible alternatives and visible synthetic/verified status.
- Prefer a thoughtful icon system to emojis. Icon styles must match the **host** in Maisa/Apotti, not the floating nav's icon set.
- Maintain excellent contrast and accessible 44px touch targets where appropriate, while allowing compact professional data tables.
- Use `prefers-reduced-motion`, proper focus management, semantic landmarks, keyboard-accessible navigation and meaningful empty/loading/error states.

---

## 10. Frontend build and handoff instructions for Codex

### Build now

Implement the UI and *frontend-only* deterministic demo behavior in the repository:

- Four accessible routes / views and the global navigation bubble.
- Realistic synthetic fixtures representing one end-to-end storyline.
- Simulation day clock, timeline and agent activity states with play/pause/reset/step interaction.
- Maisa-integrated patient question/voice/text UI and submit/review flow.
- Apotti-integrated clinician review UI with evidence, missing context, patient response and human decision controls.
- Dashboard with provenance and action-oriented views, using **verified aggregate values only where actual public sources and definitions can be supplied**, otherwise an unmistakable synthetic/demo label.
- Strong responsive states: desktop 1440×900, laptop 1280, mobile 390×844; patient screen may be framed as a real mobile UI within a larger desktop demo surface as long as host navigation remains authentic.
- Favicon/brand mark from the exact original image, only where native to Thriver.
- Screenshots or baseline visual tests capturing all routes and main interaction states.
- Concise `docs/design-decisions.md` explaining why each world looks different, the source used and any inevitable approximations.

### Do NOT invent now

- Agent orchestration algorithm, endpoint names, tool signatures, request/response schemas, FHIR mappings, ElevenLabs credentials, backend auth rules, or data access paths.
- Production data connectors or claims of live Maisa/Apotti integration.
- Clinical performance figures, regional differences or patient outcomes not tied to evidence.
- A new product name or new palette.

The exact **inputs, outputs, actions, events, API contracts and architecture** will arrive separately from the architecture/evaluation discussion. **Treat that later document as authoritative for behavior and data flow.** This design document remains authoritative for **visual language, navigation, information architecture and interaction principles**. When the two documents conflict, preserve safety, truthfulness and data provenance; record the conflict and resolve it in a small decision note rather than silently replacing the visual direction.

### Suggested separation of concerns (not an imposed architecture)

- `ui/demo-shell`: only global floating bubble and shared scenario/session state.
- `ui/simulation`: expressive Thriver-specific components and timeline motion.
- `ui/maisa`: host-faithful Maisa facade plus a small `SiltaPatientExtension` module.
- `ui/apotti`: host-faithful clinician facade plus `SiltaClinicianExtension` module.
- `ui/dashboard`: independent Thriver intelligence and evidence views.
- `assets/brand`: original logo.
- `assets/references` or `docs/references`: URL list and evidence behind the host visual reconstructions.
- `domain/demo-fixtures`: synthetic cases and deterministic event sequences, replaceable later with typed adapters.

It's fine to share underlying state management, routing, date formatting and accessible primitives **in code**. Don't let that force shared visual tokens or card styling where host apps differ.

---

## 11. QA — the implementation is NOT ready until these pass

### Visual fidelity

- [ ] Centered floating capsule nav is visible and functional in **all four** tabs, same outer location/geometry, active highlight and accessible icons; never a generic top navbar.
- [ ] The original user-provided logo is used **verbatim**, not reimagined.
- [ ] The Simulation is visually distinct, purposeful and non-generic; strong typography, quiet motion and prominent care-pathway story.
- [ ] The Patient view looks immediately like **actual Maisa/MyChart**, even with the SILTA extension hidden; public reference screenshots have been compared side by side.
- [ ] The Doctor view looks immediately like **actual Apotti/Epic clinical software**, even with the SILTA extension hidden; public reference screenshots have been compared side by side.
- [ ] Dashboard is independent from Simulation and gives a clear evidence → intervention → owner flow.
- [ ] No generic identical-radius card templates or copied page shells across all apps.
- [ ] No horizontal overflow or text clipping at 390px, 1280px, 1440px.
- [ ] Screenshots recorded for main tab and at least one meaningful state per interaction.

### Functional UX

- [ ] Bubble clicks/keyboard navigate all four routes.
- [ ] Bubble remains visibly active on refresh/deep link.
- [ ] Simulation play, pause, next, reset advance deterministic day states correctly.
- [ ] Agent statuses and evidence labels update with timeline progress.
- [ ] Patient can choose voice or text, preview/edit a transcription and confirm a submission (simulated until later contracts arrive).
- [ ] Clinician can inspect evidence, accept/edit/reject/request-more-info, with UI state and audit feedback.
- [ ] Dashboard shows an attributable specific recommended action, not mere charts.
- [ ] All demo values clearly distinguish synthetic/scenario versus evidence-backed.
- [ ] Reduce-motion support and focus accessibility are verified.

### Source integrity

- [ ] `docs/visual-reference-audit.md` created with actual sources, visual comparison notes and uncertainty markers.
- [ ] No generated collage described as an actual Maisa/Apotti screenshot.
- [ ] No unauthorized internal Epic screenshots/assets or real patient data.
- [ ] No claim that the demo is deployed, authorized or connected to production Maisa/Apotti.

### Delivery response format

When finished, return:

1. Repository/branch or local path worked on, dev command and route links.
2. Four screenshots (or screenshot paths) plus one screenshot of the floating bubble across the views.
3. Reference-audit file path.
4. Implemented real interactions vs simulated interactions.
5. Exact list of missing **architecture input/output contracts**, ready for the next handoff.
6. Any unresolved fidelity differences or limitations; **do not report success if screenshots were not visually checked**.

---

## 12. Final product definition

**Thriver Care is not four pages of a generic website.** It is a unified, judge-facing demonstration that moves through **four real contexts** by means of **one central floating bubble**:

- **Our simulation** explains and animates the coordination problem.
- **The patient's actual environment** shows the smallest credible Maisa extension.
- **The clinician's actual environment** shows the smallest credible Apotti/Epic extension.
- **Our decision dashboard** translates evidence into a concrete local action.

**Design authenticity is the point.** The two host products should feel like the actual software they extend; Thriver's own two products should have distinct and unmistakable taste. The common elements are the *idea*, the *scenario*, the *logo where relevant*, and above all the **fixed central floating navigation bubble** — not a cookie-cutter design system applied everywhere.

**Start by researching and validating the two real host interfaces. Then establish the bubble and build the four worlds. Use the supplied later architecture I/O specification to wire the final agent/data behavior; until it arrives, keep a clearly labelled synthetic, working demo.**
