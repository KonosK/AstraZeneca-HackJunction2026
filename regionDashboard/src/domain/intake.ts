/** Deterministic synthetic intake. No clinical inference or natural-language guessing. */
export const REFERENCE_DATE = "2026-11-14";
export type Value = string | number | boolean | string[] | null;
export type Field = {
  value: Value;
  status: "missing" | "candidate" | "confirmed" | "conflicted";
  source: string;
  confidence: "explicit" | "derived" | "unknown";
  ref: string;
  recordedAt?: string;
  alternative?: Value;
};
export type Intake = Record<string, Field>;
export const definitions: Record<
  string,
  {
    label: string;
    kind: "number" | "boolean" | "enum" | "text";
    options?: string[];
    required?: boolean;
  }
> = {
  region_name: { label: "County", kind: "text", required: true },
  age: { label: "Age at demo reference date", kind: "number", required: true },
  symptom_severity_score: {
    label:
      "Symptom severity (0–10, demo operator input; not validated urgency)",
    kind: "number",
    required: true,
  },
  public_care_track: {
    label: "Public care pathway?",
    kind: "boolean",
    required: true,
  },
  already_referred_to_specialist: {
    label: "Already referred to a specialist?",
    kind: "boolean",
    required: true,
  },
  care_phase: {
    label: "Current care phase",
    kind: "enum",
    options: ["pre_contact", "primary_care", "diagnostics", "mdt", "treatment"],
    required: true,
  },
  needs_interpreter: {
    label: "Interpreter needed?",
    kind: "boolean",
    required: true,
  },
  travel_time_to_care_minutes: {
    label: "Travel to care (minutes, self-reported estimate)",
    kind: "number",
  },
  symptom_onset_days: { label: "Days since symptoms began", kind: "number" },
  primary_symptom_cluster: {
    label: "Reported symptom group",
    kind: "enum",
    options: ["unknown", "respiratory", "breast", "gi", "gyn", "heme", "other"],
  },
  smoking_status: {
    label: "Smoking status",
    kind: "enum",
    options: ["unknown", "never", "former", "current"],
  },
  lives_alone: { label: "Lives alone?", kind: "boolean" },
  sex: {
    label: "Recorded sex",
    kind: "enum",
    options: ["unknown", "female", "male", "other"],
  },
  education_band: {
    label: "Education (optional)",
    kind: "enum",
    options: ["unknown", "low", "mid", "high"],
  },
  g8_frailty_score: {
    label: "Formal G8 assessment score (leave unknown if not assessed)",
    kind: "number",
  },
  language: { label: "Preferred language", kind: "text" },
};
export function emptyIntake(): Intake {
  return Object.fromEntries(
    Object.keys(definitions).map((k) => [
      k,
      {
        value: null,
        status: "missing",
        source: "Unknown",
        confidence: "unknown",
        ref: "",
      },
    ]),
  );
}
/** Map chat/LLM free text onto allowed intake values. */
export function coerceIntakeValue(key: string, value: Value): Value {
  if (value === null || value === undefined) return null;
  const def = definitions[key];
  if (!def) return value;
  if (def.kind === "number") {
    const n = typeof value === "number" ? value : Number(String(value).match(/-?\d+(?:\.\d+)?/)?.[0]);
    if (!Number.isFinite(n) || n < 0) return null;
    if (key === "symptom_severity_score") return Math.min(10, Math.round(n));
    if (key === "age") return Math.min(120, Math.round(n));
    if (key === "g8_frailty_score") return Math.min(17, Math.round(n));
    return n;
  }
  if (def.kind === "boolean") {
    if (typeof value === "boolean") return value;
    const s = String(value).toLowerCase();
    if (["yes", "true", "y", "kyllä", "joo"].includes(s)) return true;
    if (["no", "false", "n", "ei"].includes(s)) return false;
    return null;
  }
  if (def.kind === "enum" && def.options) {
    const raw = String(value).toLowerCase().trim().replace(/\s+/g, "_");
    if (def.options.includes(raw)) return raw;
    if (key === "primary_symptom_cluster") {
      if (/respir|lung|cough|breath|chest/.test(raw)) return "respiratory";
      if (/breast/.test(raw)) return "breast";
      if (/gi|stomach|bowel|abdomen|digest/.test(raw)) return "gi";
      if (/gyn|uter|ovari|pelvic/.test(raw)) return "gyn";
      if (/heme|blood|anem|lymph/.test(raw)) return "heme";
      if (/ear|lump|neck|skin|pain|other|weird/.test(raw)) return "other";
      return "unknown";
    }
    if (key === "smoking_status") {
      if (/never/.test(raw)) return "never";
      if (/former|quit|used_to|ex/.test(raw)) return "former";
      if (/current|smoke|yes/.test(raw)) return "current";
      return "unknown";
    }
    if (key === "care_phase") {
      if (/pre|first|not_yet/.test(raw)) return "pre_contact";
      if (/primary|gp|doctor/.test(raw)) return "primary_care";
      if (/diagnos|scan|test/.test(raw)) return "diagnostics";
      if (/mdt|team/.test(raw)) return "mdt";
      if (/treat/.test(raw)) return "treatment";
      return def.options.includes(String(value)) ? String(value) : "primary_care";
    }
    if (key === "sex") {
      if (/female|woman|f\b/.test(raw)) return "female";
      if (/male|man|\bm\b/.test(raw)) return "male";
      if (/other/.test(raw)) return "other";
      return "unknown";
    }
    if (key === "education_band") {
      if (/low/.test(raw)) return "low";
      if (/mid|medium/.test(raw)) return "mid";
      if (/high/.test(raw)) return "high";
      return "unknown";
    }
    return def.options[0] === "unknown" ? "unknown" : null;
  }
  if (def.kind === "text") {
    const s = String(value).trim();
    return s.length ? s.slice(0, 150) : null;
  }
  return value;
}
export function setField(
  state: Intake,
  key: string,
  value: Value,
  resolve = false,
): Intake {
  const old = state[key];
  if (!old) throw Error("Unsupported field");
  const coerced = coerceIntakeValue(key, value);
  const conflict =
    !resolve &&
    old.value !== null &&
    old.source.startsWith("FHIR") &&
    old.value !== coerced;
  return {
    ...state,
    [key]: {
      value: conflict ? old.value : coerced,
      alternative: conflict ? coerced : undefined,
      status: conflict
        ? "conflicted"
        : coerced === null
          ? "missing"
          : "candidate",
      source: conflict ? old.source : "Manual answer",
      confidence: "explicit",
      ref: "Intake form · " + REFERENCE_DATE,
    },
  };
}
export function confirmFields(state: Intake): Intake {
  if (Object.values(state).some((f) => f.status === "conflicted"))
    throw Error("Resolve conflicting answers first.");
  return Object.fromEntries(
    Object.entries(state).map(([k, f]) => [
      k,
      { ...f, status: f.value === null ? "missing" : "confirmed" },
    ]),
  );
}
/** Topics the patient checkup chat should cover before Approve. */
export const CHECKUP_CHAT_KEYS = [
  "symptom_severity_score",
  "primary_symptom_cluster",
  "symptom_onset_days",
  "travel_time_to_care_minutes",
  "lives_alone",
  "smoking_status",
] as const;

function needsCheckupChat(f: Field | undefined): boolean {
  if (!f || f.value === null || f.value === undefined) return true;
  if (f.status === "conflicted") return true;
  // Synthetic FHIR candidates still need a gentle spoken confirm.
  return f.status === "candidate" && f.source.startsWith("FHIR");
}

export function checkupChatComplete(state: Intake): boolean {
  return CHECKUP_CHAT_KEYS.every((k) => !needsCheckupChat(state[k]));
}

export function planQuestions(
  state: Intake,
  blindSpots: string[] = [],
): string[] {
  // Required form gaps (missing / conflicted only).
  const required = Object.keys(definitions).filter((k) => {
    if (!definitions[k].required) return false;
    const f = state[k];
    return !f || f.value === null || f.status === "conflicted";
  });
  // Checkup chat: cover/confirm the six core topics (including FHIR candidates).
  const checkup = CHECKUP_CHAT_KEYS.filter((k) => needsCheckupChat(state[k]));
  const optional = [...blindSpots].filter(
    (k) =>
      definitions[k] &&
      !definitions[k].required &&
      !(CHECKUP_CHAT_KEYS as readonly string[]).includes(k) &&
      state[k]?.value === null,
  );
  return [...new Set([...required, ...checkup, ...optional])].slice(0, 6);
}
export type FhirResource = {
  resourceType: string;
  id?: string;
  [key: string]: unknown;
};
export type FhirBundle = {
  resourceType: "Bundle";
  type: string;
  entry: { resource: FhirResource }[];
};
export const syntheticBundle: FhirBundle = {
  resourceType: "Bundle",
  type: "collection",
  entry: [
    {
      resource: {
        resourceType: "Patient",
        id: "SYNTH-LAPLAND-001",
        birthDate: "1948-02-10",
        gender: "male",
        address: [{ state: "Lapland wellbeing services county" }],
        communication: [{ language: { coding: [{ code: "fi" }] } }],
      },
    },
    {
      resource: {
        resourceType: "Encounter",
        id: "prior-encounter",
        status: "finished",
        period: { start: "2026-09-01" },
        class: {
          system: "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          code: "AMB",
        },
      },
    },
    {
      resource: {
        resourceType: "Encounter",
        id: "encounter-demo",
        status: "in-progress",
        class: {
          system: "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          code: "AMB",
        },
      },
    },
    {
      resource: {
        resourceType: "QuestionnaireResponse",
        id: "synthetic-intake",
        status: "completed",
        questionnaire: "urn:thriver:synthetic-intake:v1",
        item: [
          { linkId: "public_care_track", answer: [{ valueBoolean: true }] },
          {
            linkId: "already_referred_to_specialist",
            answer: [{ valueBoolean: false }],
          },
          { linkId: "needs_interpreter", answer: [{ valueBoolean: false }] },
          {
            linkId: "primary_symptom_cluster",
            answer: [{ valueString: "respiratory" }],
          },
          { linkId: "symptom_onset_days", answer: [{ valueInteger: 60 }] },
          { linkId: "smoking_status", answer: [{ valueString: "former" }] },
          { linkId: "lives_alone", answer: [{ valueBoolean: true }] },
        ],
      },
    },
  ],
};
// Only the bundled form and explicit resource mappings are supported. No absence-based inference.
export function extractFhir(bundle: unknown): Intake {
  const b = bundle as FhirBundle;
  if (
    b?.resourceType !== "Bundle" ||
    b.type !== "collection" ||
    !Array.isArray(b.entry) ||
    b.entry.length > 100
  )
    throw Error(
      "Use a synthetic FHIR R4 collection Bundle (max 100 resources).",
    );
  let state = emptyIntake();
  const put = (k: string, v: Value, ref: string, derived = false) => {
    if (!definitions[k]) return;
    const prior = state[k];
    if (prior.value !== null && prior.value !== v) {
      state[k] = { ...prior, status: "conflicted", alternative: v };
      return;
    }
    state[k] = {
      value: v,
      status: "candidate",
      source: "FHIR synthetic fixture",
      recordedAt: REFERENCE_DATE,
      confidence: derived ? "derived" : "explicit",
      ref,
    };
  };
  for (const { resource: r } of b.entry) {
    if (!r || typeof r.resourceType !== "string")
      throw Error("Invalid resource");
    const ref = r.resourceType + "/" + (r.id ?? "unknown");
    if (r.resourceType === "Patient") {
      if (
        typeof r.birthDate === "string" &&
        /^\d{4}-\d{2}-\d{2}$/.test(r.birthDate)
      ) {
        const birth = new Date(r.birthDate + "T00:00:00Z"),
          now = new Date(REFERENCE_DATE + "T00:00:00Z");
        const age =
          now.getUTCFullYear() -
          birth.getUTCFullYear() -
          (now.toISOString().slice(5, 10) < r.birthDate.slice(5) ? 1 : 0);
        if (Number.isFinite(age) && age >= 0 && age <= 120)
          put("age", age, ref + ".birthDate → age at " + REFERENCE_DATE, true);
      }
      if (
        typeof r.gender === "string" &&
        ["male", "female", "other", "unknown"].includes(r.gender)
      )
        put("sex", r.gender, ref + ".gender");
      const addresses = r.address as { state?: string }[] | undefined;
      if (addresses?.[0]?.state)
        put(
          "region_name",
          addresses[0].state,
          ref + ".address.state (candidate, confirm county)",
        );
    }
    if (
      r.resourceType === "Encounter" &&
      r.status === "in-progress" &&
      (r.class as { code?: string })?.code === "AMB"
    )
      put(
        "care_phase",
        "primary_care",
        ref + " (demo mapping AMB → primary_care)",
        true,
      );
    if (
      r.resourceType === "ServiceRequest" &&
      r.status === "active" &&
      r.intent === "order"
    )
      put(
        "already_referred_to_specialist",
        true,
        ref + " (demo order; verify specialist destination)",
        true,
      );
    if (
      r.resourceType === "QuestionnaireResponse" &&
      r.questionnaire === "urn:thriver:synthetic-intake:v1"
    ) {
      const items = r.item as {
        linkId: string;
        answer?: Record<string, Value>[];
      }[];
      if (!Array.isArray(items)) throw Error("Invalid synthetic questionnaire");
      for (const item of items) {
        const a = item.answer?.[0];
        if (!a) continue;
        const val = a.valueBoolean ?? a.valueInteger ?? a.valueString ?? null;
        if (
          typeof val === "number" ||
          typeof val === "string" ||
          typeof val === "boolean"
        )
          put(item.linkId, val, ref + ".item." + item.linkId);
      }
    }
  }
  return state;
}
export interface PatientRequest {
  patient_id: string;
  region_name: string;
  age: number;
  symptom_severity_score: number;
  public_care_track: boolean;
  already_referred_to_specialist: boolean;
  needs_interpreter: boolean;
  care_phase: string;
  g8_frailty_score: number | null;
  missing_staging_fields: string[];
  sex: string;
  primary_symptom_cluster: string;
  smoking_status: string;
  education_band: string;
  symptom_onset_days: number | null;
  travel_time_to_care_minutes: number | null;
  lives_alone: boolean | null;
  language: string | null;
  comorbidity_flags: string[];
}
export function buildPatientAnalyzeRequest(
  state: Intake,
  counties: string[],
): PatientRequest {
  const value = (k: string) => state[k]?.value;
  if (Object.values(state).some((f) => f.status === "conflicted"))
    throw Error("Resolve conflicting answers first.");
  for (const [k, def] of Object.entries(definitions)) {
    const v = value(k);
    if (def.required && (state[k]?.status !== "confirmed" || v === null))
      throw Error("Confirm " + def.label);
    if (v === null) continue;
    if (state[k]?.status !== "confirmed")
      throw Error("Confirm or clear " + def.label);
    if (
      def.kind === "number" &&
      (typeof v !== "number" || !Number.isFinite(v) || v < 0)
    )
      throw Error("Invalid " + def.label);
    if (def.kind === "boolean" && typeof v !== "boolean")
      throw Error("Invalid " + def.label);
    if (def.kind === "enum" && !def.options?.includes(String(v)))
      throw Error("Invalid " + def.label);
    if (def.kind === "text" && (typeof v !== "string" || v.length > 150))
      throw Error("Invalid " + def.label);
  }
  if (!counties.includes(String(value("region_name"))))
    throw Error("Select a canonical county from the live list.");
  if (
    Number(value("symptom_severity_score")) > 10 ||
    Number(value("age")) > 120
  )
    throw Error("Severity must be 0–10 and age 0–120.");
  if (
    value("g8_frailty_score") !== null &&
    Number(value("g8_frailty_score")) > 17
  )
    throw Error("G8 must be 0–17.");
  return {
    patient_id: "SYNTH-LAPLAND-001",
    region_name: String(value("region_name")),
    age: Number(value("age")),
    symptom_severity_score: Number(value("symptom_severity_score")),
    public_care_track: value("public_care_track") as boolean,
    already_referred_to_specialist: value(
      "already_referred_to_specialist",
    ) as boolean,
    needs_interpreter: value("needs_interpreter") as boolean,
    care_phase: String(value("care_phase")),
    g8_frailty_score: value("g8_frailty_score") as number | null,
    missing_staging_fields: [],
    sex: String(value("sex") ?? "unknown"),
    primary_symptom_cluster: String(
      value("primary_symptom_cluster") ?? "unknown",
    ),
    smoking_status: String(value("smoking_status") ?? "unknown"),
    education_band: String(value("education_band") ?? "unknown"),
    symptom_onset_days: value("symptom_onset_days") as number | null,
    travel_time_to_care_minutes: value("travel_time_to_care_minutes") as
      | number
      | null,
    lives_alone: value("lives_alone") as boolean | null,
    language: value("language") as string | null,
    comorbidity_flags: [],
  };
}
