import test from "node:test";
import assert from "node:assert/strict";
import {
  emptyIntake,
  extractFhir,
  syntheticBundle,
  setField,
  confirmFields,
  buildPatientAnalyzeRequest,
  planQuestions,
} from "../regionDashboard/src/domain/intake.ts";
import {
  canAdvance,
  nextScenarioDay,
  scenarioStep,
} from "../regionDashboard/src/domain/scenario.ts";
import { routeReview } from "../regionDashboard/src/domain/routing.ts";
import {
  decodePatient,
  decodeFiveBlocks,
} from "../regionDashboard/src/api/patient.ts";
const county = "Lapland wellbeing services county";
function ready(severity = 7) {
  return confirmFields(
    setField(
      setField(
        extractFhir(syntheticBundle),
        "symptom_severity_score",
        severity,
        true,
      ),
      "travel_time_to_care_minutes",
      95,
      true,
    ),
  );
}
test("FHIR age uses fixed reference date, explicit sex and AMB mapping", () => {
  const s = extractFhir(syntheticBundle);
  assert.equal(s.age.value, 78);
  assert.equal(s.sex.value, "male");
  assert.equal(s.care_phase.value, "primary_care");
  assert.equal(s.g8_frailty_score.value, null);
  assert.equal(s.travel_time_to_care_minutes.value, null);
  assert.equal(s.age.status, "candidate");
});
test("missing required fields prevent payload, no guessed score", () =>
  assert.throws(
    () => buildPatientAnalyzeRequest(emptyIntake(), [county]),
    /Confirm/,
  ));
test("FHIR candidates require explicit confirmation", () =>
  assert.throws(
    () => buildPatientAnalyzeRequest(extractFhir(syntheticBundle), [county]),
    /Confirm/,
  ));
test("planner prioritizes required fields and caps at two", () => {
  const p = planQuestions(emptyIntake());
  assert.deepEqual(p, ["region_name", "age"]);
});
test("confirmed fields are not asked again", () =>
  assert.ok(!planQuestions(ready()).includes("age")));
test("canonical county required; substring is rejected", () =>
  assert.throws(
    () =>
      buildPatientAnalyzeRequest(
        confirmFields(setField(ready(), "region_name", "Lapland", true)),
        [county],
      ),
    /canonical/,
  ));
for (const v of [0, 10])
  test("severity boundary preserved " + v, () =>
    assert.equal(
      buildPatientAnalyzeRequest(ready(v), [county]).symptom_severity_score,
      v,
    ),
  );
for (const v of [-1, 11, NaN])
  test("invalid severity rejected " + v, () =>
    assert.throws(() => buildPatientAnalyzeRequest(ready(v), [county])),
  );
test("unknowns stay null/unknown; staging absent does not claim completeness", () => {
  const r = buildPatientAnalyzeRequest(ready(), [county]);
  assert.equal(r.g8_frailty_score, null);
  assert.equal(r.education_band, "unknown");
  assert.deepEqual(r.missing_staging_fields, []);
  assert.equal("transcript" in r, false);
});
test("FHIR vs manual contradiction is not silently overwritten", () => {
  const s = setField(ready(), "already_referred_to_specialist", true);
  assert.equal(s.already_referred_to_specialist.status, "conflicted");
  assert.equal(s.already_referred_to_specialist.value, false);
  assert.throws(() => confirmFields(s), /conflicting/);
  assert.equal(
    setField(s, "already_referred_to_specialist", true, true)
      .already_referred_to_specialist.status,
    "candidate",
  );
});
test("correction requires confirmation again", () =>
  assert.throws(
    () =>
      buildPatientAnalyzeRequest(setField(ready(), "age", 80, true), [county]),
    /Confirm/,
  ));
test("unsupported enum and nonboolean clinical defaults rejected", () => {
  assert.throws(() =>
    buildPatientAnalyzeRequest(
      confirmFields(setField(ready(), "care_phase", "magic", true)),
      [county],
    ),
  );
  assert.throws(() =>
    buildPatientAnalyzeRequest(
      confirmFields(setField(ready(), "public_care_track", "yes", true)),
      [county],
    ),
  );
});
test("invalid bundle rejected", () =>
  assert.throws(() => extractFhir({ resourceType: "Patient" })));
test("contradictory FHIR resources retain conflict", () => {
  const s = extractFhir({
    ...syntheticBundle,
    entry: [
      ...syntheticBundle.entry,
      {
        resource: {
          resourceType: "ServiceRequest",
          id: "x",
          status: "active",
          intent: "order",
        },
      },
    ],
  });
  assert.equal(s.already_referred_to_specialist.status, "conflicted");
});
test("unknown required booleans cannot be defaulted", () =>
  assert.throws(
    () =>
      buildPatientAnalyzeRequest(
        confirmFields(setField(ready(), "needs_interpreter", null, true)),
        [county],
      ),
    /Confirm/,
  ));
test("patient gate requires submission, clinician gate requires acceptance", () => {
  assert.equal(canAdvance(1, "silta", false, null), false);
  assert.equal(canAdvance(1, "silta", true, null), true);
  for (const d of [null, "rejected", "more_information"] as const)
    assert.equal(canAdvance(2, "silta", true, d), false);
  assert.equal(canAdvance(2, "silta", true, "accepted"), true);
  assert.equal(canAdvance(5, "silta", true, "accepted"), false);
  assert.equal(canAdvance(2, "baseline", false, null), true);
});
test("routing uncertainty is never low risk", () => {
  assert.equal(
    routeReview(emptyIntake(), false, false).status,
    "More information needed",
  );
  assert.equal(routeReview(ready(), true, false).status, "Review required");
  assert.match(routeReview(ready(), true, true).status, /Existing care/);
});
test("runtime decoding rejects missing sections and malformed recommendations", () => {
  assert.throws(() => decodePatient({}));
  assert.throws(() =>
    decodeFiveBlocks({
      predictions_and_gaps: {},
      contributing_factors: {},
      recommended_interventions: { department_macro: [{ action: "fake" }] },
      supporting_evidence: {},
      confidence_and_limitations: {},
    }),
  );
});

test("continuous baseline reaches day 78 without human gates", () => {
  let day = 0;
  for (let n = 0; n < 100; n++)
    day = nextScenarioDay(day, "baseline", false, null);
  assert.equal(day, 78);
  assert.equal(scenarioStep(day, "baseline"), 5);
});
test("continuous SILTA clock stops at patient and clinician handoffs", () => {
  let day = 0;
  for (let n = 0; n < 10; n++) day = nextScenarioDay(day, "silta", false, null);
  assert.equal(day, 3);
  for (let n = 0; n < 10; n++) day = nextScenarioDay(day, "silta", true, null);
  assert.equal(day, 7);
  assert.equal(nextScenarioDay(day, "silta", true, "rejected"), 7);
  assert.equal(nextScenarioDay(day, "silta", true, "more_information"), 7);
  for (let n = 0; n < 50; n++)
    day = nextScenarioDay(day, "silta", true, "accepted");
  assert.equal(day, 32);
});
