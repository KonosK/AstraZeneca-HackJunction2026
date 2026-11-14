import type { Intake } from "./intake";
export interface RoutingPolicy {
  version: string;
  requireReviewForNewCase: boolean;
  blockOnUncertainty: boolean;
}
export const DEFAULT_POLICY: RoutingPolicy = {
  version: "demo-workflow-v1",
  requireReviewForNewCase: true,
  blockOnUncertainty: true,
};
export function routeReview(
  state: Intake,
  analyzed: boolean,
  accepted: boolean,
  policy = DEFAULT_POLICY,
) {
  const required = [
    "region_name",
    "age",
    "symptom_severity_score",
    "public_care_track",
    "care_phase",
    "already_referred_to_specialist",
    "needs_interpreter",
  ];
  const uncertain =
    Object.values(state).some((f) => f.status === "conflicted") ||
    required.some((k) => state[k]?.status !== "confirmed");
  if (uncertain && policy.blockOnUncertainty)
    return {
      status: "More information needed",
      reason:
        "Missing, unconfirmed or contradictory workflow context. No low-risk inference.",
      policy: policy.version,
    };
  if (!analyzed)
    return {
      status: "More information needed",
      reason: "Real OncoFlow analysis has not completed.",
      policy: policy.version,
    };
  if (accepted)
    return {
      status: "Existing care pathway / demo follow-up",
      reason:
        "Human acceptance recorded locally. This does not establish clinical safety or authorize care.",
      policy: policy.version,
    };
  return {
    status: "Review required",
    reason: policy.requireReviewForNewCase
      ? "New synthetic case: require a human decision. No clinical score threshold is used."
      : "No approved clinical threshold set: fall back to human review.",
    policy: policy.version,
  };
}
