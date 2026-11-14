// Authored storytelling times from the supplied simplified HTML. Not clinical estimates.
export const baselineEvents = [
  {
    day: 0,
    title: "First contact",
    detail: "A synthetic person seeks help through primary care.",
  },
  {
    day: 19,
    title: "First appointment",
    detail: "Scenario assumption: information is collected at the appointment.",
  },
  {
    day: 34,
    title: "Information sent",
    detail: "Scenario assumption: the packet needs clarification.",
  },
  {
    day: 49,
    title: "Clarification requested",
    detail: "The fictional packet returns for additional context.",
  },
  {
    day: 64,
    title: "Follow-up completed",
    detail: "The missing context is finally available in this story.",
  },
  {
    day: 78,
    title: "Next care appointment",
    detail:
      "Fictional end of the coordination pathway. No diagnosis or treatment outcome is asserted.",
  },
];
export const siltaEvents = [
  {
    day: 0,
    title: "Connect the evidence",
    detail: "SILTA brings together county context and a synthetic FHIR record.",
  },
  {
    day: 3,
    title: "Ask the patient",
    detail:
      "Pause here. Open Patient, review the short questionnaire and confirm the structured answers.",
  },
  {
    day: 7,
    title: "Review with the clinician",
    detail:
      "Pause here. Open Doctor to inspect the actual OncoFlow proposal and record a local decision.",
  },
  {
    day: 15,
    title: "Diagnostic work-up planned",
    detail:
      "The reviewed information accompanies the proposed diagnostic appointment in this illustrative pathway.",
  },
  {
    day: 23,
    title: "Care team follow-up",
    detail:
      "The care team reviews the proposed work-up and practical access needs in this illustrative pathway.",
  },
  {
    day: 32,
    title: "Next care appointment",
    detail:
      "The next care appointment is reached in this illustrative pathway. This is not a measured treatment benefit.",
  },
];
export type Decision = "accepted" | "rejected" | "more_information" | null;
export function canAdvance(
  index: number,
  mode: "baseline" | "silta",
  submitted: boolean,
  decision: Decision,
): boolean {
  if (index >= 5) return false;
  if (mode === "baseline") return true;
  if (index === 1) return submitted;
  if (index >= 2) return decision === "accepted";
  return true;
}

/** One continuous story clock; only the two human handoffs can stop it. */
export function nextScenarioDay(
  day: number,
  mode: "baseline" | "silta",
  submitted: boolean,
  decision: Decision,
): number {
  const end = mode === "baseline" ? 78 : 32;
  if (day >= end) return end;
  if (
    mode === "silta" &&
    ((day >= 3 && !submitted) || (day >= 7 && decision !== "accepted"))
  )
    return day;
  return day + 1;
}
export function scenarioStep(day: number, mode: "baseline" | "silta"): number {
  const events = mode === "baseline" ? baselineEvents : siltaEvents;
  return Math.max(
    0,
    events.findLastIndex((event) => event.day <= day),
  );
}
