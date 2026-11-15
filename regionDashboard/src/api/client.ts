import type {
  HealthResponse,
  RegionsResponse,
  RegionAnalyzeResponse,
  RegionAnalyzeRequest,
} from "./types";
import type { PatientRequest } from "../domain/intake";
import {
  decodeFiveBlocks,
  decodePatient,
  type PatientResponse,
} from "./patient";
let recordedMode = false;
export function setRecordedMode(enabled: boolean) {
  recordedMode = enabled;
}
export function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL || "/api/oncoflow").replace(
    /\/$/,
    "",
  );
}
export async function request<T>(
  path: string,
  init: RequestInit = {},
  decode?: (v: unknown) => T,
): Promise<T> {
  if (recordedMode) {
    const key =
      path === "/health"
        ? "health"
        : path === "/regions"
          ? "regions"
          : path === "/analyze/region"
            ? "region"
            : path === "/analyze/patient"
              ? "patient"
              : null;
    if (!key) throw Error("No recorded fixture for this operation.");
    const response = await fetch("/fixtures/" + key + ".json");
    if (!response.ok) throw Error("Recorded demo is unavailable.");
    const fixture = await response.json();
    if (init.body) {
      const body = JSON.parse(String(init.body));
      if (
        Object.keys(fixture.request).some(
          (k) => JSON.stringify(body[k]) !== JSON.stringify(fixture.request[k]),
        ) ||
        Object.keys(body).length !== Object.keys(fixture.request).length
      )
        throw Error(
          "Recorded replay supports only Lapland and the exact judge demo answers. Return to live mode to analyze changes.",
        );
    }
    return decode ? decode(fixture.response) : (fixture.response as T);
  }
  const abort = new AbortController(),
    timer = setTimeout(() => abort.abort(), 20000);
  try {
    const res = await fetch(getApiBaseUrl() + path, {
      ...init,
      signal: abort.signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    if (!res.ok) {
      let detail = "";
      try {
        const b = await res.json();
        detail =
          typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
      } catch {
        /* response may not be JSON */
      }
      throw Error(`OncoFlow ${res.status}: ${detail || res.statusText}`);
    }
    const data: unknown = await res.json();
    return decode ? decode(data) : (data as T);
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError")
      throw Error("OncoFlow timed out. Retry when the API is available.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}
export const fetchHealth = () =>
  request<HealthResponse>("/health", {}, (v) => {
    const b = v as HealthResponse;
    if (b?.status !== "ok" || !b.model?.cv)
      throw Error("Invalid health response");
    return b;
  });
export const fetchRegions = () =>
  request<RegionsResponse>("/regions", {}, (v) => {
    const b = v as RegionsResponse;
    if (
      !Array.isArray(b?.regions) ||
      b.count !== b.regions.length ||
      !b.regions.every(
        (r) =>
          typeof r.region_name === "string" &&
          typeof r.region_id === "number" &&
          typeof r.year === "number" &&
          r.indicators,
      )
    )
      throw Error("Invalid county list");
    return b;
  });
export const analyzeRegion = (body: RegionAnalyzeRequest) =>
  request<RegionAnalyzeResponse>(
    "/analyze/region",
    { method: "POST", body: JSON.stringify(body) },
    (v) => {
      const b = decodeFiveBlocks(v);
      if (
        typeof b.predictions_and_gaps.region_name !== "string" ||
        !Array.isArray(b.contributing_factors.shap_drivers_baseline)
      )
        throw Error("Invalid regional analysis");
      return v as RegionAnalyzeResponse;
    },
  );
export const analyzePatient = (body: PatientRequest) =>
  request<PatientResponse>(
    "/analyze/patient",
    { method: "POST", body: JSON.stringify(body) },
    decodePatient,
  );

export type PhoneCallStatus =
  | "idle"
  | "calling"
  | "in_progress"
  | "processing"
  | "done"
  | "error"
  | "incomplete";

export type LatestPhonePatient = {
  call_status: PhoneCallStatus;
  latest_call_status?: PhoneCallStatus | string | null;
  latest_call_message?: string | null;
  conversation_id: string | null;
  to_number: string | null;
  error: string | null;
  source: string | null;
  patient: PatientResponse | null;
  intake: Record<string, unknown> | null;
  notes: string | null;
  transcript: string | null;
  silta_direct_number?: string | null;
};

async function demoRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 30000);
  try {
    const res = await fetch(path, {
      ...init,
      signal: abort.signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    if (!res.ok) {
      let detail = "";
      try {
        const b = await res.json();
        detail =
          typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
      } catch {
        /* ignore */
      }
      throw Error(detail || `Request failed (${res.status})`);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError")
      throw Error("Request timed out.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const startOutboundCall = (to_number: string) =>
  demoRequest<{
    success: boolean;
    conversation_id: string;
    call_status: string;
    message?: string;
  }>("/call/outbound", {
    method: "POST",
    body: JSON.stringify({ to_number }),
  });

export const fetchLatestPhonePatient = async (): Promise<LatestPhonePatient> => {
  const raw = await demoRequest<LatestPhonePatient>("/latest-patient");
  let patient: PatientResponse | null = null;
  if (raw.patient) {
    try {
      patient = decodePatient(raw.patient);
    } catch {
      patient = null;
    }
  }
  return { ...raw, patient };
};
