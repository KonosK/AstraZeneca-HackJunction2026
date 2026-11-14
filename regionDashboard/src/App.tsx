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
import { VoiceInput } from "./views/VoiceInput";
import { RegionalDashboard } from "./views/RegionalDashboard";
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
    [noteConfirmed, setNoteConfirmed] = useState(false),
    [demoSample, setDemoSample] = useState(false);
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
    [session, setSession] = useState(0),
    [cadence, setCadence] = useState(7),
    [language, setLanguage] = useState("en"),
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
  function update(key: string, value: Value, resolve = false) {
    invalidate();
    setIntake((s) => setField(s, key, value, resolve));
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
  function loadFixture() {
    invalidate();
    let s = extractFhir(syntheticBundle);
    if (selected) s = setField(s, "region_name", selected.region_name, true);
    setIntake(s);
    setStatus(
      "Synthetic FHIR loaded. Confirm the extracted facts and answer the missing questions.",
    );
  }
  function preset() {
    invalidate();
    let s = extractFhir(syntheticBundle);
    if (selected) s = setField(s, "region_name", selected.region_name, true);
    s = setField(s, "symptom_severity_score", 7, true);
    s = setField(s, "travel_time_to_care_minutes", 95, true);
    s = setField(s, "language", "fi", true);
    setIntake(s);
    setNote(
      "I have felt tired and have had respiratory symptoms for about 60 days. I live alone, and it takes about 95 minutes to reach care. This is a synthetic demo case.",
    );
    setNoteConfirmed(false);
    setDemoSample(true);
    setStatus(
      "Demo operator selected fictional severity 7 and travel estimate 95 minutes. Review and confirm; these values were not inferred.",
    );
  }
  function reset() {
    invalidate();
    setIntake(emptyIntake());
    setNote("");
    setNoteConfirmed(false);
    setDemoSample(false);
    setReviewNote("");
    setEditing(false);
    setStep(0);
    setDay(0);
    setPlaying(false);
    setSession((n) => n + 1);
    setStatus("Demo reset. No synthetic answers or review decisions retained.");
  }
  async function submitCheckIn() {
    setPatientError("");
    const run = ++generation.current;
    try {
      if (!note.trim())
        throw Error("Add a check-in or use Fill demo check-in.");
      const confirmedIntake = confirmFields(intake);
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
  const pending = planQuestions(
      intake,
      patient?.predictions_and_gaps.blind_spots,
    ),
    name = selected ? shortCountyName(selected.region_name) : "Loading county";
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
                        : "Open the questionnaire, review the synthetic answers, then send a local review draft."}
                    </p>
                    <button
                      className="primary"
                      onClick={() => {
                        if (!intake.age.value) loadFixture();
                        navigate("patient");
                      }}
                    >
                      Open Patient questionnaire →
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
                <span className="host-selected">Tasks & questionnaires</span>
                <span>Messages · demo</span>
                <span>Appointments · no records</span>
                <span>Test results · no records</span>
                <div className="host-safe">
                  This is a reconstructed portal, not your health record.
                </div>
              </aside>
              <section className="patient-content">
                <div className="patient-compact-title">
                  <span className="eyebrow">{name} · Synthetic case 001</span>
                  <h1>SILTA check-in</h1>
                </div>
                {submitted ? (
                  <div className="patient-extension success" role="status">
                    <h2>
                      {decision === "accepted"
                        ? "Reviewed by your care team"
                        : decision === "more_information"
                          ? "More information requested"
                          : decision === "rejected"
                            ? "Proposal not accepted"
                            : "Sent for review"}
                    </h2>
                    <p>Your confirmed check-in is in the local demo inbox.</p>
                    <div className="button-row">
                      <button className="primary" onClick={resumeSimulation}>
                        Continue simulation →
                      </button>
                      <button
                        onClick={() => {
                          invalidate();
                          setStatus(
                            "Update your answers before sending again.",
                          );
                        }}
                      >
                        Edit check-in
                      </button>
                    </div>
                    <details>
                      <summary>Submission details</summary>
                      <p>
                        Next illustrative check-in: day {3 + cadence}. No
                        appointment or clinical follow-up is scheduled.{" "}
                        {recorded
                          ? "Recorded model fixture, not live inference."
                          : "Analysis received from the existing backend."}
                      </p>
                    </details>
                  </div>
                ) : (
                  <div className="patient-extension compact-checkin">
                    <div className="demo-fill">
                      <button
                        className="primary"
                        onClick={preset}
                        disabled={analyzing}
                      >
                        Fill demo check-in
                      </button>
                      <span>Editable synthetic sample</span>
                    </div>
                    <VoiceInput
                      language={language}
                      key={session}
                      text={note}
                      onText={(text) => {
                        setNote(text);
                        setDemoSample(false);
                        setNoteConfirmed(false);
                        invalidate();
                      }}
                    />
                    {demoSample && (
                      <span className="sample-label">
                        Synthetic sample · not a voice transcription
                      </span>
                    )}
                    <details className="checkin-options">
                      <summary>Language & check-in settings</summary>
                      <div className="checkin-settings">
                        <label>
                          Prompt language
                          <select
                            aria-label="Prompt language"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                          >
                            <option value="en">English</option>
                            <option value="fi">Suomi</option>
                          </select>
                        </label>
                        <label>
                          Demo check-in cadence
                          <select
                            aria-label="Demo check-in cadence"
                            value={cadence}
                            onChange={(e) => setCadence(Number(e.target.value))}
                          >
                            <option value={7}>Every 7 scenario days</option>
                            <option value={14}>Every 14 scenario days</option>
                            <option value={30}>Every 30 scenario days</option>
                          </select>
                        </label>
                      </div>
                    </details>
                    <details className="intake-form">
                      <summary>Review or correct record & travel time</summary>
                      {Object.keys(definitions)
                        .filter(
                          (k) =>
                            definitions[k].required ||
                            k === "travel_time_to_care_minutes",
                        )
                        .map(fieldEditor)}
                      <p className="small">
                        Severity is a fictional operator input, not clinical
                        urgency. All populated values are confirmed by the send
                        button below; conflicts must be resolved first.
                      </p>
                    </details>
                    <details>
                      <summary>Additional context & sources</summary>
                      {Object.keys(definitions)
                        .filter(
                          (k) =>
                            !definitions[k].required &&
                            k !== "travel_time_to_care_minutes",
                        )
                        .map(fieldEditor)}
                      <p>
                        Local synthetic FHIR Patient, Encounter and
                        QuestionnaireResponse · reference date 14 November 2026.
                        Unknown G8 and absent clinical findings stay unknown.
                        Staging has not been assessed.
                      </p>
                      <p>
                        Next missing context:{" "}
                        {pending.map((k) => definitions[k].label).join("; ") ||
                          "Required context available"}
                        .
                      </p>
                      <button onClick={loadFixture} disabled={analyzing}>
                        Reload synthetic FHIR
                      </button>
                      <label className="upload-label">
                        Import synthetic Bundle
                        <input
                          type="file"
                          accept=".json,application/json"
                          aria-label="Import synthetic FHIR Bundle"
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            try {
                              if (file.size > 100000)
                                throw Error("Bundle too large");
                              const next = extractFhir(
                                JSON.parse(await file.text()),
                              );
                              invalidate();
                              setIntake(next);
                            } catch (error) {
                              setPatientError((error as Error).message);
                            }
                          }}
                        />
                      </label>
                    </details>
                    <div className="record-recap">
                      <strong>
                        {intake.age.value === null
                          ? "No record loaded"
                          : `Age ${intake.age.value} · ${name}`}
                      </strong>
                      <span>
                        Travel:{" "}
                        {intake.travel_time_to_care_minutes.value ?? "unknown"}{" "}
                        min · demo severity:{" "}
                        {intake.symptom_severity_score.value ?? "not entered"}
                        /10
                      </span>
                    </div>
                    <p className="small consent-copy">
                      By confirming, you approve this editable reply and the
                      structured record above for the local simulated care-team
                      inbox. No external referral is sent.
                    </p>
                    <button
                      className="primary submit-checkin"
                      disabled={analyzing || !!apiError || !note.trim()}
                      onClick={() => void submitCheckIn()}
                    >
                      {analyzing
                        ? "Preparing SILTA review…"
                        : "Confirm & send check-in"}
                    </button>
                    {patientError && (
                      <div className="error-box" role="alert">
                        {patientError}
                        <div className="button-row">
                          <button onClick={() => void submitCheckIn()}>
                            Retry
                          </button>
                          <button onClick={() => activateRecordedReplay(true)}>
                            Use recorded demo
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
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
                        Open Patient questionnaire →
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
  function fieldEditor(key: string) {
    const def = definitions[key],
      f = intake[key];
    return (
      <div
        className={"field-row " + (f.status === "conflicted" ? "conflict" : "")}
        key={key}
      >
        <label>
          {def.label}
          {key === "region_name" ? (
            <select
              aria-label={def.label}
              value={String(f.value ?? "")}
              onChange={(e) => update(key, e.target.value)}
            >
              <option value="">Select county</option>
              {regions.map((r) => (
                <option key={r.region_id}>{r.region_name}</option>
              ))}
            </select>
          ) : def.kind === "boolean" ? (
            <select
              aria-label={def.label}
              value={f.value === null ? "" : String(f.value)}
              onChange={(e) =>
                update(
                  key,
                  e.target.value === "" ? null : e.target.value === "true",
                )
              }
            >
              <option value="">Unknown</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          ) : def.kind === "enum" ? (
            <select
              aria-label={def.label}
              value={String(f.value ?? "")}
              onChange={(e) => update(key, e.target.value || null)}
            >
              <option value="">Unknown / not recorded</option>
              {def.options?.map((v) => (
                <option key={v} value={v}>
                  {v.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label={def.label}
              type={def.kind === "number" ? "number" : "text"}
              min={def.kind === "number" ? 0 : undefined}
              max={
                key === "symptom_severity_score"
                  ? 10
                  : key === "g8_frailty_score"
                    ? 17
                    : key === "age"
                      ? 120
                      : undefined
              }
              value={f.value === null ? "" : String(f.value)}
              onChange={(e) =>
                update(
                  key,
                  e.target.value === ""
                    ? null
                    : def.kind === "number"
                      ? Number(e.target.value)
                      : e.target.value,
                )
              }
            />
          )}
        </label>
        <small>
          {f.status} · {f.source} ·{" "}
          {f.confidence === "derived"
            ? "derived, verify"
            : "explicit or unknown"}
          {f.ref && <span title={f.ref}> · {f.ref}</span>}
        </small>
        {f.status === "conflicted" && (
          <div role="alert">
            <p>
              Conflict: record “{String(f.value)}”, new answer “
              {String(f.alternative)}”. Choose explicitly.
            </p>
            <button onClick={() => update(key, f.alternative ?? null, true)}>
              Use new answer
            </button>
            <button onClick={() => update(key, f.value, true)}>
              Keep recorded value
            </button>
          </div>
        )}
      </div>
    );
  }
}
