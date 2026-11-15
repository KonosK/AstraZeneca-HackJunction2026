import { useEffect, useRef, useState } from "react";
import {
  analyzePatient,
  fetchHealth,
  fetchRegions,
  setRecordedMode,
} from "./api/client";
import type {
  HealthResponse,
  RegionAnalyzeResponse,
  RegionSummary,
} from "./api/types";
import type { PatientResponse } from "./api/patient";
import {
  buildPatientAnalyzeRequest,
  checkupChatComplete,
  coerceIntakeValue,
  confirmFields,
  definitions,
  emptyIntake,
  extractFhir,
  planQuestions,
  setField,
  syntheticBundle,
  type Intake,
  type Value,
} from "./domain/intake";
import {
  baselineEvents,
  siltaEvents,
  canAdvance,
  nextScenarioDay,
  scenarioStep,
  type Decision,
} from "./domain/scenario";
import { featureLabel, formatNumber, shortCountyName } from "./lib/metrics";
import { RegionalDashboard } from "./views/RegionalDashboard";
import {
  CheckupChat,
  type ChatMessage,
} from "./views/CheckupChat";
import { routeReview, DEFAULT_POLICY } from "./domain/routing";
import "./demo.css";
type Route = "simulation" | "patient" | "doctor" | "dashboard";
const routes: Route[] = ["simulation", "patient", "doctor", "dashboard"];
const displayAnswer = (v: Value) =>
  v === null
    ? "Unknown"
    : typeof v === "boolean"
      ? v
        ? "Yes"
        : "No"
      : String(v).replaceAll("_", " ");
const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
type ReminderCadence = "weekly" | "monthly" | "quarterly";
const REMINDER_LABELS: Record<ReminderCadence, string> = {
  weekly: "every week",
  monthly: "every month",
  quarterly: "every 3 months",
};
function nextReminderLabel(cadence: ReminderCadence): string {
  const d = new Date();
  if (cadence === "weekly") d.setDate(d.getDate() + 7);
  else if (cadence === "monthly") d.setMonth(d.getMonth() + 1);
  else d.setMonth(d.getMonth() + 3);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
function Icon({ name }: { name: Route }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {name === "simulation" ? (
        <>
          <path d="M5 4v16M5 7h7l3 5h5M5 17h7l3-5" />
          <circle cx="20" cy="12" r="2" />
        </>
      ) : name === "patient" ? (
        <>
          <rect x="7" y="2" width="10" height="20" rx="3" />
          <path d="M11 18h2" />
        </>
      ) : name === "doctor" ? (
        <>
          <path d="M5 3v6a5 5 0 0 0 10 0V3M4 3h3m6 0h3M10 14v3a4 4 0 0 0 8 0v-3" />
          <circle cx="18" cy="11" r="3" />
        </>
      ) : (
        <>
          <path d="M3 20h18M6 16v-4m5 4V8m5 8V4M4 7l5-3 5 1 6-3" />
        </>
      )}
    </svg>
  );
}
function Limitations({
  data,
}: {
  data: PatientResponse | RegionAnalyzeResponse;
}) {
  return (
    <details className="evidence-details">
      <summary>Evidence, model performance & limitations</summary>
      <p>
        Regional incidence index ≠ patient risk or measured inequality. SHAP
        describes model contributors, not causes. Pathway days are heuristic
        estimates, not measured patient timelines.
      </p>
      <p>
        GroupKFold CV R²{" "}
        {formatNumber(data.confidence_and_limitations.model.r2_mean, 3)} · MAE{" "}
        {formatNumber(data.confidence_and_limitations.model.mae_mean, 2)}
      </p>
      <ul>
        {data.confidence_and_limitations.limitations.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>
      <pre>{JSON.stringify(data.supporting_evidence, null, 2)}</pre>
    </details>
  );
}
function routeFromPath(): Route {
  return routes.find((r) => location.pathname === "/" + r) || "simulation";
}
export default function App() {
  const [route, setRoute] = useState<Route>(routeFromPath),
    [regions, setRegions] = useState<RegionSummary[]>([]),
    [selected, setSelected] = useState<RegionSummary | null>(null),
    [health, setHealth] = useState<HealthResponse | null>(null),
    [apiError, setApiError] = useState(""),
    [loading, setLoading] = useState(true),
    [retry, setRetry] = useState(0);
  const [intake, setIntake] = useState<Intake>(emptyIntake),
    [patient, setPatient] = useState<PatientResponse | null>(null),
    [patientError, setPatientError] = useState(""),
    [analyzing, setAnalyzing] = useState(false),
    [submitted, setSubmitted] = useState(false),
    [note, setNote] = useState(""),
    [noteConfirmed, setNoteConfirmed] = useState(false);
  const [chatStarted, setChatStarted] = useState(false),
    [chatMessages, setChatMessages] = useState<ChatMessage[]>([]),
    [chatDraft, setChatDraft] = useState(""),
    [chatBusy, setChatBusy] = useState(false),
    [chatReady, setChatReady] = useState(false);
  const [patientTab, setPatientTab] = useState<"checkup" | "reminders">(
      "checkup",
    ),
    [reminderEmail, setReminderEmail] = useState(""),
    [reminderCadence, setReminderCadence] =
      useState<ReminderCadence>("monthly"),
    [reminderSaved, setReminderSaved] = useState<{
      email: string;
      cadence: ReminderCadence;
      nextLabel: string;
    } | null>(null);
  const [decision, setDecision] = useState<Decision>(null),
    [reviewNote, setReviewNote] = useState(""),
    [audit, setAudit] = useState<string[]>([]),
    [editing, setEditing] = useState(false),
    [selectedProposals, setSelectedProposals] = useState<number[]>([]);
  const [mode, setMode] = useState<"baseline" | "silta">("baseline"),
    [step, setStep] = useState(0),
    [day, setDay] = useState(0),
    [playing, setPlaying] = useState(false),
    [status, setStatus] = useState(""),
    [recorded, setRecorded] = useState(false);
  const generation = useRef(0),
    main = useRef<HTMLElement | null>(null);
  function activateRecordedReplay(enabled: boolean) {
    invalidate();
    setRecordedMode(enabled);
    setRecorded(enabled);
    setSelected(null);
    setStep(0);
    setDay(0);
    setPlaying(false);
    setLoading(true);
    setRetry((n) => n + 1);
  }
  function navigate(next: Route) {
    history.pushState({}, "", `/${next}`);
    setRoute(next);
    setPlaying(false);
    window.scrollTo(0, 0);
  }
  useEffect(() => {
    const pop = () => {
      setRoute(routeFromPath());
      setPlaying(false);
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  useEffect(() => {
    document.title = title(route) + " · Thriver Care";
    main.current?.focus();
  }, [route]);
  useEffect(() => {
    let active = true;
    Promise.all([fetchRegions(), fetchHealth()])
      .then(([r, h]) => {
        if (!active) return;
        setRegions(r.regions);
        setHealth(h);
        setSelected(
          (s) =>
            s ??
            r.regions.find((x) => x.region_name.startsWith("Lapland")) ??
            r.regions[0],
        );
        setApiError("");
      })
      .catch((e) => {
        if (active) setApiError(String(e.message));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [retry]);
  function invalidate() {
    generation.current++;
    setAnalyzing(false);
    setPlaying(false);
    if (mode === "silta" && day >= 3) {
      setDay(3);
      setStep(1);
    }
    setPatient(null);
    setSelectedProposals([]);
    setSubmitted(false);
    setDecision(null);
    setAudit([]);
    setPatientError("");
    setStatus(
      "Answers changed. Previous analysis and review are invalid; confirm and run again.",
    );
  }
  function chooseRegion(r: RegionSummary) {
    if (r.region_id === selected?.region_id) return;
    invalidate();
    setSelected(r);
    setStep(0);
    setDay(0);
    setPlaying(false);
    setIntake((s) => setField(s, "region_name", r.region_name, true));
  }
  function reset() {
    invalidate();
    setIntake(emptyIntake());
    setNote("");
    setNoteConfirmed(false);
    setChatStarted(false);
    setChatMessages([]);
    setChatDraft("");
    setChatBusy(false);
    setChatReady(false);
    setPatientTab("checkup");
    setReminderEmail("");
    setReminderCadence("monthly");
    setReminderSaved(null);
    setReviewNote("");
    setEditing(false);
    setStep(0);
    setDay(0);
    setPlaying(false);
    setStatus("Demo reset. No synthetic answers or review decisions retained.");
  }
  function startCheckupChat() {
    invalidate();
    let s = extractFhir(syntheticBundle);
    if (selected) s = setField(s, "region_name", selected.region_name, true);
    setIntake(s);
    setNote("");
    setNoteConfirmed(false);
    setChatStarted(true);
    setChatDraft("");
    setChatReady(false);
    setPatientTab("checkup");
    setChatMessages([
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "Hi — this is SILTA with your synthetic cancer checkup. How are you today, and how have you been feeling?",
      },
    ]);
    setStatus("SILTA checkup chat started.");
  }
  async function sendCheckupChat() {
    const text = chatDraft.trim();
    if (!text || chatBusy) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };
    const history = [...chatMessages, userMsg];
    setChatMessages(history);
    setChatDraft("");
    setChatBusy(true);
    setPatientError("");
    try {
      const snapshot = Object.fromEntries(
        Object.entries(intake).map(([k, f]) => [k, f.value]),
      );
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          intake_snapshot: snapshot,
          pending_fields: planQuestions(intake),
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw Error(detail || `Agent chat failed (${res.status})`);
      }
      const data = (await res.json()) as {
        reply: string;
        field_updates?: { key: string; value: Value }[];
        ready_to_submit?: boolean;
        mode?: string;
        model?: string | null;
        error?: string;
      };
      let nextIntake = intake;
      if (data.field_updates?.length) {
        nextIntake = intake;
        for (const upd of data.field_updates) {
          if (!(upd.key in definitions)) continue;
          nextIntake = setField(nextIntake, upd.key, upd.value, true);
        }
        setIntake(nextIntake);
        setPatient(null);
        setSubmitted(false);
        setDecision(null);
      }
      // Only unlock Approve after a fuller checkup, not after 1–2 answers.
      setChatReady(
        Boolean(data.ready_to_submit) && checkupChatComplete(nextIntake),
      );
      setChatMessages((msgs) => [
        ...msgs,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply || "Thanks — please continue.",
        },
      ]);
      const spoken = history
        .filter((m) => m.role === "user")
        .map((m) => m.content)
        .join(" ");
      setNote(spoken);
    } catch (e) {
      setPatientError((e as Error).message);
    } finally {
      setChatBusy(false);
    }
  }
  async function submitCheckIn() {
    setPatientError("");
    const run = ++generation.current;
    try {
      const transcript = chatMessages
        .filter((m) => m.role === "user")
        .map((m) => m.content)
        .join(" ");
      const checkInNote = note.trim() || transcript;
      if (!checkInNote)
        throw Error("Chat with SILTA first, then confirm and send.");
      if (!chatStarted) throw Error("Start the SILTA checkup chat first.");
      setNote(checkInNote);
      let cleaned = intake;
      for (const key of Object.keys(definitions)) {
        const current = cleaned[key]?.value;
        if (current === null || current === undefined) continue;
        const coerced = coerceIntakeValue(key, current);
        if (coerced !== current)
          cleaned = setField(cleaned, key, coerced, true);
      }
      setIntake(cleaned);
      const confirmedIntake = confirmFields(cleaned);
      const body = buildPatientAnalyzeRequest(
        confirmedIntake,
        regions.map((r) => r.region_name),
      );
      const canonical = regions.find((r) => r.region_name === body.region_name);
      if (canonical && canonical.region_id !== selected?.region_id) {
        setSelected(canonical);
        setStep(0);
        setDay(0);
      }
      setAnalyzing(true);
      const response = await analyzePatient(body);
      if (run !== generation.current) return;
      setIntake(confirmedIntake);
      setNoteConfirmed(true);
      setPatient(response);
      setSubmitted(true);
      setSelectedProposals([]);
      setAudit([
        `${new Date().toISOString()} · Patient/demo operator · explicitly confirmed check-in and structured record; SILTA analysis received and submitted to the local simulated inbox`,
      ]);
      setStatus("Check-in sent to the local review inbox.");
    } catch (e) {
      if (run === generation.current) setPatientError((e as Error).message);
    } finally {
      if (run === generation.current) setAnalyzing(false);
    }
  }
  const events = mode === "baseline" ? baselineEvents : siltaEvents,
    event = events[step],
    allowed = canAdvance(step, mode, submitted, decision);
  function resumeSimulation() {
    if (mode !== "silta") {
      setMode("silta");
      setDay(3);
      setStep(1);
    }
    navigate("simulation");
    setPlaying(true);
  }
  useEffect(() => {
    if (!playing || route !== "simulation") return;
    const timer = setTimeout(() => {
      const next = nextScenarioDay(day, mode, submitted, decision);
      if (next === day) {
        setPlaying(false);
        return;
      }
      setDay(next);
      setStep(scenarioStep(next, mode));
      if (
        next === (mode === "baseline" ? 78 : 32) ||
        (mode === "silta" &&
          ((next === 3 && !submitted) ||
            (next === 7 && decision !== "accepted")))
      )
        setPlaying(false);
    }, 120);
    return () => clearTimeout(timer);
  }, [playing, route, day, mode, submitted, decision]);
  function recordDecision(next: Exclude<Decision, null>) {
    if (next === "accepted" && !selectedProposals.length) return;
    const label =
      next === "accepted"
        ? "Accepted selected proposals"
        : next === "rejected"
          ? "Rejected"
          : "More information requested";
    setDecision(next);
    const actions =
      next === "accepted"
        ? selectedProposals
            .map(
              (i) => patient?.recommended_interventions.doctor_micro[i]?.action,
            )
            .filter(Boolean)
        : [];
    setAudit((a) => [
      ...a,
      `${new Date().toISOString()} · Demo reviewer · ${label}${reviewNote ? " · " + reviewNote : ""}${actions.length ? " · " + actions.join(" | ") : ""} · local decision only`,
    ]);
    setStatus("Local review saved.");
    if (next === "accepted") {
      if (mode !== "silta" || day < 7) {
        setMode("silta");
        setDay(7);
        setStep(2);
      }
      navigate("simulation");
      setPlaying(true);
    } else if (mode === "silta" && day >= 7) {
      setDay(7);
      setStep(2);
      setPlaying(false);
    }
  }
  const routing = routeReview(intake, !!patient, decision === "accepted");
  const name = selected
    ? shortCountyName(selected.region_name)
    : "Loading county";
  const selector = (
    <label className="county-select">
      County context
      <select
        aria-label="County context"
        value={selected?.region_id ?? ""}
        onChange={(e) => {
          const r = regions.find((x) => x.region_id === Number(e.target.value));
          if (r) chooseRegion(r);
        }}
        disabled={!regions.length}
      >
        {regions.length === 0 ? (
          <option>Waiting for API</option>
        ) : (
          regions.map((r) => (
            <option key={r.region_id} value={r.region_id}>
              {shortCountyName(r.region_name)}
            </option>
          ))
        )}
      </select>
    </label>
  );
  const brand = (
    <span className="brand">
      <img src="/brand/thriver-logo-on-light.svg" alt="" />
      thriver<span>care</span>
    </span>
  );
  return (
    <>
      <nav className="floating-nav" aria-label="Demo views">
        {routes.map((r) => (
          <a
            key={r}
            href={"/" + r}
            aria-label={title(r)}
            title={title(r)}
            aria-current={route === r ? "page" : undefined}
            onClick={(e) => {
              if (!e.metaKey && !e.ctrlKey) {
                e.preventDefault();
                navigate(r);
              }
            }}
          >
            <Icon name={r} />
            <span>{title(r)}</span>
          </a>
        ))}
      </nav>
      <main ref={main} tabIndex={-1} className={`world ${route}`}>
        {recorded && (
          <div className="recorded-banner" role="status">
            <strong>DEMO FIXTURE — NOT LIVE MODEL RESPONSE</strong> · Recorded
            14 November 2026 · Lapland judge case only. No current inference.
            <button onClick={() => activateRecordedReplay(false)}>
              Return to live backend
            </button>
          </div>
        )}
        {apiError && (
          <div className="error-banner" role="alert">
            <strong>Backend offline / unavailable.</strong> {apiError} No model
            outputs are being fabricated.{" "}
            <button
              onClick={() => {
                setLoading(true);
                setRetry((n) => n + 1);
              }}
            >
              Retry connection
            </button>
            <button onClick={() => activateRecordedReplay(true)}>
              Use explicitly recorded demo
            </button>
          </div>
        )}
        {route === "simulation" && (
          <>
            <header className="sim-header">
              {brand}
              <span className="eyebrow">
                Junction 2026 / Equal care across Finland
              </span>
              {selector}
            </header>
            <div className="sim-intro compact-intro">
              <h1>Follow the care pathway</h1>
              <p>Synthetic case 001 · {name}</p>
            </div>
            <div className="scenario-switch" role="group" aria-label="Scenario">
              <button
                aria-pressed={mode === "baseline"}
                onClick={() => {
                  setMode("baseline");
                  setStep(0);
                  setDay(0);
                  setPlaying(false);
                }}
              >
                Without SILTA
              </button>
              <button
                aria-pressed={mode === "silta"}
                onClick={() => {
                  setMode("silta");
                  setStep(0);
                  setDay(0);
                  setPlaying(false);
                }}
              >
                With SILTA
              </button>
            </div>
            <div className="scenario-layout">
              <section className="story-stage">
                <div className="story-top">
                  <span className="eyebrow">
                    {mode === "baseline"
                      ? "Fragmented coordination"
                      : "Human-reviewed coordination"}
                  </span>
                  <span className="scenario-label">Illustrative scenario</span>
                </div>
                <div className="day-display">
                  <span>DAY</span>
                  <strong data-testid="day">
                    {day.toString().padStart(2, "0")}
                  </strong>
                  <small>
                    of {mode === "baseline" ? 78 : 32} fictional days
                  </small>
                </div>
                <progress
                  className="story-progress"
                  aria-label="Pathway progress"
                  max={mode === "baseline" ? 78 : 32}
                  value={day}
                />
                <h2>{event.title}</h2>
                <p className="event-detail">{event.detail}</p>
                {mode === "silta" && step === 1 && (
                  <div className="checkpoint">
                    <strong>
                      {submitted
                        ? "Patient context received"
                        : "Waiting for the patient"}
                    </strong>
                    <p>
                      {submitted
                        ? "Confirmed intake and analysis are ready; see the mode label. Continue to clinician review."
                        : "Open the patient portal and talk with SILTA in the checkup chat, then confirm and send."}
                    </p>
                    <button
                      className="primary"
                      onClick={() => {
                        navigate("patient");
                      }}
                    >
                      Open SILTA checkup chat →
                    </button>
                  </div>
                )}
                {mode === "silta" && step === 2 && (
                  <div className="checkpoint">
                    <strong>
                      {decision === "accepted"
                        ? "Clinician review accepted"
                        : decision === "rejected"
                          ? "Proposal rejected"
                          : decision === "more_information"
                            ? "More context needed"
                            : "Waiting for the clinician"}
                    </strong>
                    <p>
                      Only a local, explicit acceptance unlocks this
                      illustrative faster pathway. Rejection does not count as
                      an approval.
                    </p>
                    <button
                      className="primary"
                      onClick={() => navigate("doctor")}
                    >
                      Open Doctor review →
                    </button>
                  </div>
                )}
                {step === 5 && (
                  <div className="checkpoint finish">
                    <strong>
                      {mode === "silta"
                        ? "Scenario complete · day 32"
                        : "Scenario complete · day 78"}
                    </strong>
                    <p>
                      {mode === "silta"
                        ? "46 fewer fictional days in this authored story. This difference is not an model prediction, measured benefit or treatment claim."
                        : "Replay with SILTA to see the patient and clinician handoffs. The same synthetic case is used."}
                    </p>
                    {mode === "baseline" && (
                      <button
                        className="primary"
                        onClick={() => {
                          setMode("silta");
                          setStep(0);
                          setDay(0);
                        }}
                      >
                        Compare with SILTA →
                      </button>
                    )}
                    <button onClick={() => navigate("dashboard")}>
                      See county evidence →
                    </button>
                  </div>
                )}
                <div className="timeline-controls">
                  {allowed && (
                    <button onClick={() => setPlaying((v) => !v)}>
                      {playing
                        ? "Pause"
                        : day === 0
                          ? "Start simulation"
                          : "Continue simulation"}
                    </button>
                  )}
                  <button onClick={reset}>Reset</button>
                </div>
              </section>
              <aside className="pathway">
                <span className="eyebrow">
                  Pathway /{" "}
                  {mode === "baseline" ? "without SILTA" : "with SILTA"}
                </span>
                <ol>
                  {events.map((e, i) => (
                    <li
                      key={i}
                      className={
                        i === step ? "current" : i < step ? "complete" : ""
                      }
                    >
                      <span className="event-dot">
                        {i < step ? "✓" : i + 1}
                      </span>
                      <div>
                        <small>Day {e.day}</small>
                        <strong>{e.title}</strong>
                        <span>
                          {i === step
                            ? playing
                              ? "In progress"
                              : "Paused here"
                            : i < step
                              ? "Step shown"
                              : "Coming next"}
                        </span>
                      </div>
                    </li>
                  ))}
                </ol>
                <div className="agent-note">
                  <span className="eyebrow">What SILTA actually does</span>
                  <p>
                    Collects explicit context → asks for missing fields → calls
                    SILTA analysis → prepares a human-reviewable proposal.
                  </p>
                  <p>No autonomous referral. No invented diagnosis.</p>
                </div>
              </aside>
            </div>
            <footer className="sim-footer">
              <span>
                Observed county evidence and an illustrative care story are
                different kinds of information.
              </span>
              <button onClick={() => navigate("dashboard")}>
                Explore {name} evidence ↗
              </button>
            </footer>
          </>
        )}
        {route === "patient" && (
          <>
            <header className="maisa-header">
              <span className="maisa-wordmark">
                maisa<span>Patient portal · simulated</span>
              </span>
              <span>English demo · Synthetic person</span>
            </header>
            <div className="host-grid">
              <aside className="patient-sidebar">
                <strong>Welcome, Demo patient</strong>
                <button
                  type="button"
                  className={
                    patientTab === "checkup" ? "host-selected" : "host-nav"
                  }
                  onClick={() => setPatientTab("checkup")}
                >
                  Checkup chat
                </button>
                <button
                  type="button"
                  className={
                    patientTab === "reminders" ? "host-selected" : "host-nav"
                  }
                  onClick={() => setPatientTab("reminders")}
                >
                  Reminders
                  {reminderSaved ? " · on" : ""}
                </button>
                <span className="host-muted">Messages · demo</span>
                <span className="host-muted">Appointments · no records</span>
                <div className="host-safe">
                  This is a reconstructed portal, not your health record.
                </div>
              </aside>
              <section className="patient-content">
                <div className="patient-mobile-tabs" role="tablist" aria-label="Patient sections">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={patientTab === "checkup"}
                    className={patientTab === "checkup" ? "active" : ""}
                    onClick={() => setPatientTab("checkup")}
                  >
                    Checkup
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={patientTab === "reminders"}
                    className={patientTab === "reminders" ? "active" : ""}
                    onClick={() => setPatientTab("reminders")}
                  >
                    Reminders
                  </button>
                </div>
                {patientTab === "reminders" ? (
                  <>
                    <div className="patient-compact-title">
                      <span className="eyebrow">{name} · Synthetic case 001</span>
                      <h1>Check-in reminders</h1>
                    </div>
                    <div className="patient-extension checkup-reminder-panel">
                      {reminderSaved ? (
                        <div className="checkup-reminder-saved" role="status">
                          <strong>Reminders on</strong>
                          <p>
                            SILTA will nudge {reminderSaved.email}{" "}
                            {REMINDER_LABELS[reminderSaved.cadence]} to talk with
                            the agent again and stay safe — next ping{" "}
                            {reminderSaved.nextLabel}.
                          </p>
                          <div className="button-row">
                            <button
                              type="button"
                              onClick={() => {
                                setReminderEmail(reminderSaved.email);
                                setReminderCadence(reminderSaved.cadence);
                                setReminderSaved(null);
                              }}
                            >
                              Change reminder
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setReminderSaved(null);
                                setStatus("Reminder cleared.");
                              }}
                            >
                              Turn off
                            </button>
                          </div>
                        </div>
                      ) : (
                        <form
                          className="checkup-reminder-form"
                          onSubmit={(e) => {
                            e.preventDefault();
                            const email = reminderEmail.trim();
                            if (!email || !email.includes("@")) {
                              setStatus("Enter an email to save the reminder.");
                              return;
                            }
                            const nextLabel = nextReminderLabel(reminderCadence);
                            setReminderSaved({
                              email,
                              cadence: reminderCadence,
                              nextLabel,
                            });
                            setAudit((a) => [
                              `Email reminder · ${REMINDER_LABELS[reminderCadence]} · next ${nextLabel}`,
                              ...a,
                            ]);
                            setStatus(
                              `Reminder saved (${REMINDER_LABELS[reminderCadence]}).`,
                            );
                          }}
                        >
                          <p>
                            Get optional email nudges to check in with SILTA
                            again — weekly, monthly, or every few months.
                          </p>
                          <label className="checkup-reminder-field">
                            <span>Email</span>
                            <input
                              type="email"
                              autoComplete="email"
                              placeholder="you@example.com"
                              value={reminderEmail}
                              onChange={(e) => setReminderEmail(e.target.value)}
                              required
                            />
                          </label>
                          <fieldset className="checkup-reminder-cadence">
                            <legend>How often</legend>
                            {(
                              [
                                ["weekly", "Weekly"],
                                ["monthly", "Monthly"],
                                ["quarterly", "Every 3 months"],
                              ] as const
                            ).map(([value, label]) => (
                              <label key={value}>
                                <input
                                  type="radio"
                                  name="reminder-cadence"
                                  checked={reminderCadence === value}
                                  onChange={() => setReminderCadence(value)}
                                />
                                {label}
                              </label>
                            ))}
                          </fieldset>
                          <div className="button-row">
                            <button className="primary" type="submit">
                              Save reminder
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="patient-compact-title">
                      <span className="eyebrow">{name} · Synthetic case 001</span>
                      <h1>SILTA checkup chat</h1>
                    </div>
                    {submitted && patient ? (
                      <div className="patient-extension success" role="status">
                        <h2>Checkup sent</h2>
                        <div className="checkup-report">
                          {(() => {
                            const intakeSnap =
                              patient.predictions_and_gaps.intake;
                            const pathway =
                              patient.predictions_and_gaps
                                .pathway_days_estimate;
                            return (
                              <>
                                <p>
                                  Your checkup summary went to the local demo
                                  care inbox for{" "}
                                  {shortCountyName(
                                    patient.predictions_and_gaps.region_name,
                                  )}
                                  . Clinical next steps stay with your clinician
                                  — nothing here is medical advice.
                                </p>
                                <p>
                                  <strong>Summary:</strong> you reported
                                  severity{" "}
                                  {String(
                                    intakeSnap.symptom_severity_score ?? "—",
                                  )}
                                  /10
                                  {intakeSnap.travel_time_to_care_minutes !=
                                  null
                                    ? ` · about ${intakeSnap.travel_time_to_care_minutes} min to care`
                                    : ""}
                                  {intakeSnap.primary_symptom_cluster &&
                                  intakeSnap.primary_symptom_cluster !==
                                    "unknown"
                                    ? ` · ${String(intakeSnap.primary_symptom_cluster).replaceAll("_", " ")} symptoms`
                                    : ""}
                                  . Illustrative pathway estimate ≈{" "}
                                  {formatNumber(pathway.total_days, 0)} days
                                  (heuristic, not measured time).
                                </p>
                              </>
                            );
                          })()}
                        </div>
                        <div className="button-row">
                          <button className="primary" onClick={resumeSimulation}>
                            Continue simulation →
                          </button>
                          <button
                            onClick={() => {
                              startCheckupChat();
                              setStatus("Checkup chat restarted.");
                            }}
                          >
                            New checkup
                          </button>
                          <button
                            type="button"
                            onClick={() => setPatientTab("reminders")}
                          >
                            Reminders →
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="patient-extension compact-checkin">
                        <CheckupChat
                          messages={chatMessages}
                          draft={chatDraft}
                          busy={chatBusy || analyzing}
                          started={chatStarted}
                          onDraftChange={setChatDraft}
                          onSend={() => void sendCheckupChat()}
                          onStart={startCheckupChat}
                        />
                        {chatStarted && chatReady && (
                          <>
                            <p className="small consent-copy">
                              SILTA is ready. Approving lets the agent send this
                              checkup summary to the local demo inbox — not a
                              real referral.
                            </p>
                            <button
                              className="primary submit-checkin"
                              disabled={analyzing || chatBusy || !!apiError}
                              onClick={() => void submitCheckIn()}
                            >
                              {analyzing
                                ? "SILTA is sending…"
                                : "Approve agent to send"}
                            </button>
                          </>
                        )}
                        {patientError && (
                          <div className="error-box" role="alert">
                            {patientError}
                            <div className="button-row">
                              <button onClick={() => void submitCheckIn()}>
                                Retry analysis
                              </button>
                              <button
                                onClick={() => activateRecordedReplay(true)}
                              >
                                Use recorded demo
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </section>
            </div>
          </>
        )}
        {route === "doctor" && (
          <>
            <header className="ehr-header">
              <strong>
                APOTTI <span>Clinical workspace · reconstructed demo</span>
              </strong>
              <span>Demo reviewer / no live EHR</span>
            </header>
            <div className="ehr-toolbar">
              Work queue <span>›</span> Review assistance <span>›</span>{" "}
              SYNTH-LAPLAND-001
            </div>
            <div className="doctor-grid">
              <aside className="workqueue">
                <h2>Review inbox</h2>
                <div className="queue-item">
                  <strong>Synthetic case 001</strong>
                  <span>
                    {decision
                      ? decision.replace("_", " ")
                      : submitted
                        ? "Ready for review"
                        : "Awaiting patient confirmation"}
                  </span>
                  <small>{name}</small>
                </div>
                <p>Operational queue only. No clinical urgency score.</p>
              </aside>
              <section className="chart">
                <div className="patient-banner">
                  <div>
                    <strong>DEMO PATIENT · Synthetic</strong>
                    <span>
                      Age {intake.age.value ?? "unknown"} · {name}
                    </span>
                  </div>
                  <span className="pill">
                    {decision ? decision.replace("_", " ") : "Not reviewed"}
                  </span>
                </div>
                <div className="chart-tabs">
                  <strong>Overview</strong>
                  <span>Documents: synthetic only</span>
                  <span>Orders: none</span>
                </div>
                <div className="silta-review">
                  <span className="eyebrow">SILTA / review assistance</span>
                  <h1>Review this case</h1>
                  {!submitted || !patient ? (
                    <div className="empty-state">
                      <h2>No submitted case yet</h2>
                      <p>
                        Complete the patient questionnaire, confirm structured
                        answers, run the real analysis and send the local review
                        draft.
                      </p>
                      <button onClick={() => navigate("patient")}>
                        Open SILTA checkup chat →
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="model-review-summary">
                        <section>
                          <span className="eyebrow">
                            Regional model index · {name}
                          </span>
                          <strong>
                            {formatNumber(
                              patient.predictions_and_gaps.county_context
                                .predicted_cancer_index_age_std,
                            )}
                          </strong>
                          <span>
                            Observed:{" "}
                            {formatNumber(
                              patient.predictions_and_gaps.county_context
                                .observed_cancer_index_age_std,
                            )}{" "}
                            · Not individual cancer risk
                          </span>
                        </section>
                        <section>
                          <span className="eyebrow">
                            County model contributors · SHAP
                          </span>
                          {patient.contributing_factors.county_shap_drivers
                            .slice(0, 3)
                            .map((driver) => (
                              <p key={driver.feature}>
                                {featureLabel(driver.feature)}{" "}
                                <strong>
                                  {formatNumber(driver.shap_value, 2)}
                                </strong>
                              </p>
                            ))}
                          <span>Model associations, not proven causes</span>
                        </section>
                      </div>
                      <details>
                        <summary>Patient reply & workflow context</summary>
                        <p>{noteConfirmed ? note : "No confirmed reply."}</p>
                        <p>
                          Travel:{" "}
                          {String(
                            intake.travel_time_to_care_minutes.value ??
                              "Unknown",
                          )}{" "}
                          minutes · care phase:{" "}
                          {displayAnswer(intake.care_phase.value)}. Patient
                          report, not a measured clinical interval.
                        </p>
                        <p>
                          {routing.status}: {routing.reason}
                        </p>
                        <pre>{JSON.stringify(DEFAULT_POLICY, null, 2)}</pre>
                      </details>
                      <div className="proposal-heading">
                        <h2>Select proposals for review</h2>
                        <span>{selectedProposals.length} selected</span>
                      </div>
                      <p className="small">
                        Original model/rule proposals. Select only those you
                        endorse in this synthetic case; they are not clinical
                        orders.
                      </p>
                      <div className="proposal-list">
                        {patient.recommended_interventions.doctor_micro.map(
                          (proposal, index) => (
                            <article key={index} className="proposal-option">
                              <label>
                                <input
                                  type="checkbox"
                                  checked={selectedProposals.includes(index)}
                                  aria-label={`Select proposal ${index + 1}`}
                                  onChange={(e) => {
                                    setSelectedProposals((current) =>
                                      e.target.checked
                                        ? [...current, index]
                                        : current.filter((i) => i !== index),
                                    );
                                    if (decision === "accepted")
                                      setDecision(null);
                                  }}
                                />
                                <span>
                                  {proposal.action.split(":")[0].split(". ")[0]}
                                </span>
                              </label>
                              <details>
                                <summary>Action, owner & evidence</summary>
                                <p>{proposal.action}</p>
                                <p>
                                  <strong>Owner:</strong>{" "}
                                  {proposal.responsible_actor}
                                </p>
                                <p>
                                  <strong>Success metric:</strong>{" "}
                                  {proposal.success_metrics?.join(" · ") ||
                                    "Not supplied"}
                                </p>
                                <p>{proposal.justification}</p>
                              </details>
                            </article>
                          ),
                        )}
                      </div>
                      <p className="small">
                        Unknown / not assessed:{" "}
                        {patient.predictions_and_gaps.blind_spots
                          .map((k) => definitions[k]?.label ?? k)
                          .join("; ") || "No follow-up fields flagged"}
                        . Missing labs, diagnosis, allergies and staging are not
                        invented.
                      </p>
                      <details className="agent-trace">
                        <summary>How SILTA built this review</summary>
                        <ol>
                          <li>
                            <strong>Assemble:</strong> compatible local FHIR
                            resources and explicit answers, with field-level
                            provenance. No live EHR retrieval.
                          </li>
                          <li>
                            <strong>Reconcile:</strong> missing values stay
                            unknown and conflicts require explicit resolution;
                            questions come from the deterministic field planner.
                          </li>
                          <li>
                            <strong>Confirm & validate:</strong> the patient
                            approves the editable reply and structured record
                            once. Raw audio and transcript are not sent to the
                            model.
                          </li>
                          <li>
                            <strong>Analyze:</strong> the existing backend
                            returns its five response sections and{" "}
                            {
                              patient.recommended_interventions.doctor_micro
                                .length
                            }{" "}
                            rule-based patient proposals.{" "}
                            {recorded
                              ? "This session explicitly replays a recorded response."
                              : "This session received a live model response."}
                          </li>
                          <li>
                            <strong>Route & review:</strong> {routing.status}.
                            The professional selects proposals; this prototype
                            does not decide that a person can safely avoid
                            medical care.
                          </li>
                        </ol>
                      </details>
                      <details>
                        <summary>Confirmed intake & field provenance</summary>
                        <dl className="provenance">
                          {Object.entries(intake).map(([k, f]) => (
                            <div key={k}>
                              <dt>{definitions[k].label}</dt>
                              <dd>
                                {String(f.value ?? "Unknown")} · {f.status} ·{" "}
                                {f.source} · {f.ref}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                      <details>
                        <summary>
                          Heuristic pathway estimate — not the simulation clock
                        </summary>
                        <p>
                          {
                            patient.predictions_and_gaps.pathway_days_estimate
                              .total_days
                          }{" "}
                          days. Backend rule-based estimate, not observed time
                          or a predicted benefit from SILTA. The supplied
                          lung-cancer benchmark is not universal.
                        </p>
                        <pre>
                          {JSON.stringify(
                            patient.predictions_and_gaps.pathway_days_estimate,
                            null,
                            2,
                          )}
                        </pre>
                        <p>
                          Known backend issue: severity 0 may be treated as 5
                          internally. G8 cutoff requires clinical owner review.
                        </p>
                      </details>
                      <details>
                        <summary>
                          Analysis contributors & rule flags — not individual
                          cancer risk
                        </summary>
                        <p>
                          County observed incidence index:{" "}
                          {formatNumber(
                            patient.predictions_and_gaps.county_context
                              .observed_cancer_index_age_std,
                          )}
                          . Regional model projection:{" "}
                          {formatNumber(
                            patient.predictions_and_gaps.county_context
                              .predicted_cancer_index_age_std,
                          )}
                          . These are not this person’s probability of cancer.
                        </p>
                        <p>
                          SHAP contributors to the county model, not proven
                          causes:
                        </p>
                        {patient.contributing_factors.county_shap_drivers.map(
                          (d) => (
                            <p key={d.feature}>
                              {featureLabel(d.feature)} · SHAP{" "}
                              {formatNumber(d.shap_value, 2)}
                            </p>
                          ),
                        )}
                        <p>
                          Backend heuristic flags, not clinically validated
                          urgency categories:
                        </p>
                        <pre>
                          {JSON.stringify(
                            patient.contributing_factors.intake_risk_flags,
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                      <Limitations data={patient} />
                      {editing && (
                        <label>
                          Local review note
                          <textarea
                            aria-label="Local review note"
                            value={reviewNote}
                            maxLength={500}
                            onChange={(e) => setReviewNote(e.target.value)}
                          />
                          <button
                            onClick={() => {
                              setEditing(false);
                              setAudit((a) => [
                                ...a,
                                `${new Date().toISOString()} · Demo reviewer · local review note edited`,
                              ]);
                            }}
                          >
                            Save local note
                          </button>
                        </label>
                      )}
                      <div className="decision-controls">
                        <button
                          className="primary"
                          disabled={!selectedProposals.length}
                          onClick={() => recordDecision("accepted")}
                        >
                          Accept selected & continue
                        </button>
                        <button onClick={() => setEditing((v) => !v)}>
                          Edit review note
                        </button>
                        <button onClick={() => recordDecision("rejected")}>
                          Reject
                        </button>
                        <button
                          onClick={() => recordDecision("more_information")}
                        >
                          Request more information
                        </button>
                      </div>
                      {decision && (
                        <p className="small" role="status">
                          Local decision: {decision.replace("_", " ")}. No
                          external order or referral.
                        </p>
                      )}
                    </>
                  )}
                  <details className="audit">
                    <summary>Local audit trail ({audit.length})</summary>
                    {audit.length ? (
                      audit.map((a, i) => <p key={i}>{a}</p>)
                    ) : (
                      <p>No review actions recorded.</p>
                    )}
                  </details>
                </div>
              </section>
            </div>
          </>
        )}
        {route === "dashboard" && (
          <RegionalDashboard
            health={health}
            regions={regions}
            year={selected?.year ?? regions[0]?.year ?? null}
            regionsLoading={loading}
            regionsError={apiError || null}
            selected={selected}
            onSelect={chooseRegion}
          />
        )}
        {status && (
          <div className="sr-only" role="status">
            {status}
          </div>
        )}
      </main>
    </>
  );
}
