"""Outbound + inbound ElevenLabs phone intake → OncoFlow patient analysis (in-memory)."""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Any

import httpx

from mlBackend.api import PatientAnalyzeRequest, analyze_patient, get_regions_df

_lock = threading.Lock()
_state: dict[str, Any] = {
    "conversation_id": None,  # last observed / displayed conversation
    "active_conversation_id": None,  # outbound call we must finish first
    "call_status": "idle",  # idle | calling | in_progress | processing | done | error | incomplete
    "latest_call_status": "idle",
    "latest_call_message": None,
    "processed_conversation_ids": set(),
    "seeded": False,
    "latest": None,
    "error": None,
    "to_number": None,
}

DEFAULT_REGION = "Lapland wellbeing services county"
SILTA_DIRECT_NUMBER = "+16412766024"
MIN_USER_TURNS = 2
MIN_CALL_SECS = 15
INCOMPLETE_MESSAGE = (
    "Call ended early before check-up completion — nothing sent to Apotti"
)
HANDOFF_PATTERNS = (
    r"sending your checkup summary",
    r"care team now",
    r"sending .+ care team",
    r"care team",
    r"check-?up summary",
    r"share (this|the) (check|summary)",
    r"summary (with|to) (your |the )?doctor",
    r"approve agent to send",
    r"whenever you are ready",
    r"enough for (this |the )?check",
    r"wrap(?:ping)? up",
    r"human review",
)
SYMPTOM_PATTERNS = (
    r"\bcough\b",
    r"\bbreath",
    r"\bfatigue\b",
    r"\btired\b",
    r"\bpain\b",
    r"\bweight\b",
    r"\bappetite\b",
    r"\bchest\b",
    r"\blung\b",
    r"\bsymptom",
    r"\bsever",
    r"\blump\b",
    r"\bear\b",
    r"\bneck\b",
    r"\bswell",
    r"\btender\b",
    r"\bfirm\b",
    r"\bworr",
    r"\bconcern",
    r"\bnause",
    r"\bdizz",
    r"\bfever\b",
    r"\b/\s*10\b",
    r"\bout of (?:ten|10)\b",
    r"\b\d\s*(?:out of|/)\s*10\b",
    r"\b(?:severity|scale).{0,20}\b([0-9]|10)\b",
)

EXTRACT_SYSTEM = (
    "Extract structured synthetic patient intake fields from a phone checkup transcript. "
    "Return ONLY JSON with keys: region_name, age, symptom_severity_score, public_care_track, "
    "already_referred_to_specialist, care_phase, needs_interpreter, travel_time_to_care_minutes, "
    "symptom_onset_days, primary_symptom_cluster, smoking_status, lives_alone, sex, education_band, "
    "g8_frailty_score, language, missing_staging_fields (array of strings), comorbidity_flags "
    "(array of short strings for red flags / barriers), notes (short summary). "
    "Use null for unknowns. Never invent a diagnosis or referral. "
    "g8_frailty_score only if a formal assessed number was spoken; otherwise null. "
    "primary_symptom_cluster one of: unknown, respiratory, breast, gi, gyn, heme, other. "
    "smoking_status one of: unknown, never, former, current. "
    "care_phase one of: pre_contact, primary_care, diagnostics, mdt, treatment. "
    "If region is Lapland / vague, use 'Lapland wellbeing services county'."
)


def elevenlabs_key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "").strip()


def agent_id() -> str:
    return os.getenv("ELEVENLABS_AGENT_ID", "").strip()


def phone_number_id() -> str:
    return os.getenv("ELEVENLABS_PHONE_NUMBER_ID", "").strip()


def snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "call_status": _state["call_status"],
            "latest_call_status": _state["latest_call_status"],
            "latest_call_message": _state["latest_call_message"],
            "conversation_id": _state["conversation_id"],
            "active_conversation_id": _state["active_conversation_id"],
            "to_number": _state["to_number"],
            "error": _state["error"],
            "source": "phone_call" if _state["latest"] else None,
            "patient": (_state["latest"] or {}).get("patient"),
            "intake": (_state["latest"] or {}).get("intake"),
            "notes": (_state["latest"] or {}).get("notes"),
            "transcript": (_state["latest"] or {}).get("transcript"),
            "silta_direct_number": SILTA_DIRECT_NUMBER,
        }


def _set(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


def _canonical_region(name: str | None) -> str:
    raw = (name or "").strip() or DEFAULT_REGION
    try:
        regions = [str(x) for x in get_regions_df()["region_name"].tolist()]
    except Exception:
        return DEFAULT_REGION
    if raw in regions:
        return raw
    low = raw.casefold()
    for r in regions:
        if low in r.casefold() or r.casefold().startswith(low.split()[0]):
            return r
    if "lapland" in low or "lappi" in low:
        return DEFAULT_REGION
    return DEFAULT_REGION if DEFAULT_REGION in regions else regions[0]


def _transcript_turns(payload: dict[str, Any]) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    transcript = payload.get("transcript") or payload.get("transcripts") or []
    if isinstance(transcript, list):
        for turn in transcript:
            if not isinstance(turn, dict):
                continue
            role = str(turn.get("role") or turn.get("speaker") or "unknown").casefold()
            text = str(turn.get("message") or turn.get("text") or turn.get("content") or "").strip()
            if text:
                turns.append({"role": role, "text": text})
    elif isinstance(transcript, str) and transcript.strip():
        turns.append({"role": "unknown", "text": transcript.strip()})
    return turns


def _transcript_text(payload: dict[str, Any]) -> str:
    parts = [f"{t['role']}: {t['text']}" for t in _transcript_turns(payload)]
    analysis = payload.get("analysis") or {}
    if isinstance(analysis, dict) and analysis.get("transcript_summary"):
        parts.append("summary: " + str(analysis["transcript_summary"]))
    return "\n".join(parts).strip()


def _user_provided_clinical_signal(user_text: str) -> bool:
    return any(re.search(pat, user_text, re.I) for pat in SYMPTOM_PATTERNS)


def _agent_confirmed_handoff(agent_text: str) -> bool:
    return any(re.search(pat, agent_text, re.I) for pat in HANDOFF_PATTERNS)


def _call_duration_secs(payload: dict[str, Any]) -> float | None:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    for src in (metadata, analysis, payload):
        if not isinstance(src, dict):
            continue
        for key in (
            "call_duration_secs",
            "duration_secs",
            "call_duration_seconds",
            "duration",
            "call_duration",
        ):
            raw = src.get(key)
            if raw is None or raw == "":
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    start = metadata.get("start_time_unix_secs")
    end = (
        metadata.get("accepted_time_unix_secs")
        or metadata.get("end_time_unix_secs")
        or metadata.get("ended_at_unix_secs")
    )
    try:
        if start is not None and end is not None:
            dur = float(end) - float(start)
            if dur >= 0:
                return dur
    except (TypeError, ValueError):
        pass
    return None


def _completion_gate(payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Return (ok, reason, debug). Reject only true early hang-ups."""
    turns = _transcript_turns(payload)
    user_turns = [t for t in turns if t["role"] in {"user", "customer", "caller"}]
    agent_turns = [t for t in turns if t["role"] in {"agent", "assistant", "silta"}]
    user_blob = "\n".join(t["text"] for t in user_turns)
    agent_blob = "\n".join(t["text"] for t in agent_turns)
    user_n = len(user_turns)
    duration = _call_duration_secs(payload)

    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    call_successful = str(
        analysis.get("call_successful")
        or metadata.get("call_successful")
        or ""
    ).casefold()
    status = str(payload.get("status") or "").casefold()
    debug = {
        "turns": user_n,
        "duration": duration,
        "status": status,
        "call_successful": call_successful or None,
    }

    if call_successful == "failure":
        return False, "Call marked unsuccessful — nothing sent to Apotti", debug

    if user_n < MIN_USER_TURNS:
        return False, INCOMPLETE_MESSAGE, debug

    if duration is not None and duration < MIN_CALL_SECS:
        return False, INCOMPLETE_MESSAGE, debug

    has_symptom = _user_provided_clinical_signal(user_blob)
    has_handoff = _agent_confirmed_handoff(agent_blob) or call_successful == "success"
    if has_symptom or has_handoff:
        return True, "", debug

    return False, INCOMPLETE_MESSAGE, debug


def _log_voice_gate(cid: str, accepted: bool, debug: dict[str, Any], reason: str = "") -> None:
    verdict = "ACCEPTED" if accepted else "INCOMPLETE"
    dur = debug.get("duration")
    dur_s = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "unknown"
    extra = f" ({reason})" if reason and not accepted else ""
    print(
        f"[SILTA Voice] Conversation {cid}: turns={debug.get('turns')}, "
        f"duration={dur_s}, status={debug.get('status')} -> {verdict}{extra}",
        flush=True,
    )


def _coerce_intake(raw: dict[str, Any]) -> dict[str, Any]:
    def num(key: str, default: float | None = None) -> float | None:
        v = raw.get(key, default)
        if v is None or v == "":
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def yn(key: str, default: bool | None = None) -> bool | None:
        v = raw.get(key, default)
        if isinstance(v, bool):
            return v
        if v is None:
            return default
        s = str(v).casefold()
        if s in ("yes", "true", "public", "health centre", "health center"):
            return True
        if s in ("no", "false", "occupational"):
            return False
        return default

    cluster = str(raw.get("primary_symptom_cluster") or "unknown").casefold().replace(" ", "_")
    if cluster not in {"unknown", "respiratory", "breast", "gi", "gyn", "heme", "other"}:
        blob = " ".join(str(x) for x in raw.values())
        if re.search(r"cough|breath|respir|chest", blob, re.I):
            cluster = "respiratory"
        else:
            cluster = "other"

    smoking = str(raw.get("smoking_status") or "unknown").casefold()
    if "never" in smoking:
        smoking = "never"
    elif "former" in smoking or "used" in smoking or "quit" in smoking:
        smoking = "former"
    elif "current" in smoking or "smoke" in smoking:
        smoking = "current"
    else:
        smoking = "unknown"

    care_phase = str(raw.get("care_phase") or "primary_care").casefold().replace(" ", "_")
    if care_phase not in {"pre_contact", "primary_care", "diagnostics", "mdt", "treatment"}:
        care_phase = "primary_care"

    age = num("age", 70) or 70
    severity = num("symptom_severity_score", 5)
    if severity is None:
        severity = 5
    severity = max(0, min(10, severity))

    g8 = num("g8_frailty_score", None)
    if g8 is not None:
        g8 = max(0, min(17, g8))

    flags = raw.get("comorbidity_flags") or []
    if not isinstance(flags, list):
        flags = []
    missing = raw.get("missing_staging_fields") or []
    if not isinstance(missing, list):
        missing = []

    public = yn("public_care_track", True)
    if public is None:
        public = True

    return {
        "patient_id": "SYNTH-PHONE-001",
        "region_name": _canonical_region(str(raw.get("region_name") or DEFAULT_REGION)),
        "age": age,
        "symptom_severity_score": severity,
        "public_care_track": public,
        "already_referred_to_specialist": bool(yn("already_referred_to_specialist", False)),
        "needs_interpreter": bool(yn("needs_interpreter", False)),
        "care_phase": care_phase,
        "g8_frailty_score": g8,
        "missing_staging_fields": [str(x) for x in missing][:12],
        "sex": str(raw.get("sex") or "unknown").casefold()
        if str(raw.get("sex") or "unknown").casefold() in {"unknown", "female", "male", "other"}
        else "unknown",
        "primary_symptom_cluster": cluster,
        "smoking_status": smoking,
        "education_band": str(raw.get("education_band") or "unknown").casefold()
        if str(raw.get("education_band") or "unknown").casefold() in {"unknown", "low", "mid", "high"}
        else "unknown",
        "symptom_onset_days": num("symptom_onset_days", None),
        "travel_time_to_care_minutes": num("travel_time_to_care_minutes", None),
        "lives_alone": yn("lives_alone", None),
        "language": str(raw.get("language") or "en")[:40],
        "comorbidity_flags": [str(x)[:80] for x in flags][:12],
        "notes": str(raw.get("notes") or "")[:1200],
    }


def _fallback_extract(transcript: str) -> dict[str, Any]:
    low = transcript.casefold()
    age_m = re.search(r"\b(?:i(?:'| a)?m|age(?:d)?|years? old)\D{0,12}(\d{1,3})\b", low)
    sev_m = re.search(r"\b(?:severity|scale|out of (?:ten|10)|/\s*10)\D{0,12}(\d{1,2})\b", low)
    days_m = re.search(r"\b(\d{1,3})\s*(?:days?|weeks?|months?)\b", low)
    travel_m = re.search(r"\b(\d{1,3})\s*(?:minutes?|mins?)\b", low)
    onset = None
    if days_m:
        n = int(days_m.group(1))
        unit = days_m.group(0)
        if "week" in unit:
            onset = n * 7
        elif "month" in unit:
            onset = n * 30
        else:
            onset = n
    flags: list[str] = []
    for label, pat in (
        ("persistent_cough", r"cough"),
        ("shortness_of_breath", r"short(?:ness)? of breath|breathless"),
        ("fatigue", r"fatigu|tired"),
        ("weight_loss", r"weight loss|lost weight"),
        ("appetite_loss", r"appetite"),
        ("transport_barrier", r"no (?:car|bus)|transport|hard to (?:get|travel)"),
    ):
        if re.search(pat, low):
            flags.append(label)
    return {
        "region_name": DEFAULT_REGION,
        "age": int(age_m.group(1)) if age_m else 70,
        "symptom_severity_score": min(10, int(sev_m.group(1))) if sev_m else 6,
        "public_care_track": "occupational" not in low,
        "already_referred_to_specialist": bool(re.search(r"referred|specialist", low)),
        "care_phase": "primary_care",
        "needs_interpreter": bool(re.search(r"interpreter", low)),
        "travel_time_to_care_minutes": int(travel_m.group(1)) if travel_m else 90,
        "symptom_onset_days": onset or 45,
        "primary_symptom_cluster": "respiratory"
        if re.search(r"cough|breath|chest|lung", low)
        else "other",
        "smoking_status": "former"
        if re.search(r"used to smoke|quit|former", low)
        else ("current" if re.search(r"smoke", low) else "unknown"),
        "lives_alone": True
        if re.search(r"live alone|on my own|by myself", low)
        else (
            False
            if re.search(r"with (?:my |a )?(?:wife|husband|partner|family|daughter|son)", low)
            else None
        ),
        "sex": "unknown",
        "education_band": "unknown",
        "g8_frailty_score": None,
        "language": "en",
        "missing_staging_fields": [],
        "comorbidity_flags": flags,
        "notes": transcript[:800],
    }


def _llm_extract(transcript: str) -> dict[str, Any]:
    or_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    gem_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    user = f"Transcript:\n{transcript[:8000]}\n\nReturn JSON only."
    if or_key:
        model = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.3-flash").strip()
        with httpx.Client(timeout=45.0) as http:
            res = http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": EXTRACT_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 700,
                    "response_format": {"type": "json_object"},
                    "reasoning": {"effort": "low"},
                },
            )
        if res.status_code < 400:
            content = res.json()["choices"][0]["message"].get("content") or "{}"
            if isinstance(content, list):
                content = " ".join(
                    str(p.get("text", p)) if isinstance(p, dict) else str(p) for p in content
                )
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
    if gem_key:
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
        with httpx.Client(timeout=45.0) as http:
            res = http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": gem_key},
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": EXTRACT_SYSTEM}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 700,
                        "responseMimeType": "application/json",
                    },
                },
            )
        if res.status_code < 400:
            parts = (
                res.json().get("candidates") or [{}]
            )[0].get("content", {}).get("parts") or []
            text = "".join(str(p.get("text") or "") for p in parts)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    return _fallback_extract(transcript)


def _run_analysis(intake: dict[str, Any]) -> dict[str, Any]:
    notes = intake.pop("notes", "")
    body = PatientAnalyzeRequest(**{k: v for k, v in intake.items() if k != "notes"})
    response = analyze_patient(body)
    if hasattr(response, "body"):
        data = json.loads(response.body)
    else:
        data = response
    return {"patient": data, "intake": intake, "notes": notes}


def _list_agent_conversations(key: str, aid: str, page_size: int = 50) -> list[dict[str, Any]]:
    with httpx.Client(timeout=30.0) as http:
        res = http.get(
            "https://api.elevenlabs.io/v1/convai/conversations",
            headers={"xi-api-key": key},
            params={
                "agent_id": aid,
                "page_size": page_size,
                "sort_direction": "desc",
            },
        )
    if res.status_code >= 400:
        return []
    data = res.json()
    rows = data.get("conversations") if isinstance(data, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _fetch_conversation(key: str, cid: str) -> dict[str, Any] | None:
    with httpx.Client(timeout=30.0) as http:
        res = http.get(
            f"https://api.elevenlabs.io/v1/convai/conversations/{cid}",
            headers={"xi-api-key": key},
        )
    if res.status_code >= 400:
        return None
    data = res.json()
    return data if isinstance(data, dict) else None


def seed_processed_conversations() -> None:
    """Mark existing agent conversations as already processed so old tests don't replay."""
    with _lock:
        if _state["seeded"]:
            return
    key = elevenlabs_key()
    aid = agent_id()
    if not key or not aid:
        with _lock:
            _state["seeded"] = True
        return
    rows = _list_agent_conversations(key, aid, page_size=100)
    # Only seed finished calls so an in-progress inbound at startup can still land in Apotti.
    ids = {
        str(r.get("conversation_id"))
        for r in rows
        if r.get("conversation_id")
        and str(r.get("status") or "").casefold()
        in {"done", "completed", "failed", "error"}
    }
    with _lock:
        _state["processed_conversation_ids"] |= ids
        _state["seeded"] = True


def start_outbound(to_number: str) -> dict[str, Any]:
    key = elevenlabs_key()
    aid = agent_id()
    pid = phone_number_id()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")
    if not aid:
        raise RuntimeError("ELEVENLABS_AGENT_ID is not configured — run setup_voice_agent.py")
    if not pid:
        raise RuntimeError("ELEVENLABS_PHONE_NUMBER_ID is not configured")
    to_number = to_number.strip()
    if not re.match(r"^\+[1-9]\d{7,14}$", to_number):
        raise ValueError("to_number must be E.164, e.g. +447700900000")

    seed_processed_conversations()
    # Clear any stale incomplete flag so the new outbound is tracked cleanly.
    _set(
        call_status="calling",
        latest_call_status="calling",
        latest_call_message=None,
        conversation_id=None,
        active_conversation_id=None,
        error=None,
        to_number=to_number,
    )
    with httpx.Client(timeout=45.0) as http:
        res = http.post(
            "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={
                "agent_id": aid,
                "agent_phone_number_id": pid,
                "to_number": to_number,
            },
        )
    detail: Any
    try:
        detail = res.json()
    except Exception:
        detail = {"raw": res.text[:800]}
    if res.status_code >= 400 or (
        isinstance(detail, dict) and detail.get("success") is False
    ):
        msg = (
            detail.get("message")
            if isinstance(detail, dict)
            else None
        ) or (
            detail.get("detail") if isinstance(detail, dict) else None
        ) or res.text[:500]
        _set(
            call_status="error",
            latest_call_status="error",
            active_conversation_id=None,
            error=str(msg),
        )
        raise RuntimeError(f"ElevenLabs outbound failed ({res.status_code}): {msg}")

    conversation_id = None
    if isinstance(detail, dict):
        conversation_id = detail.get("conversation_id")
    if not conversation_id:
        _set(
            call_status="error",
            latest_call_status="error",
            active_conversation_id=None,
            error="No conversation_id returned",
        )
        raise RuntimeError(f"Outbound call missing conversation_id: {detail}")

    _set(
        conversation_id=conversation_id,
        active_conversation_id=conversation_id,
        call_status="in_progress",
        latest_call_status="in_progress",
        latest_call_message=None,
        error=None,
    )
    print(
        f"[SILTA Voice] Outbound started conversation_id={conversation_id} to={to_number}",
        flush=True,
    )
    return {
        "success": True,
        "conversation_id": conversation_id,
        "active_conversation_id": conversation_id,
        "callSid": detail.get("callSid") if isinstance(detail, dict) else None,
        "message": detail.get("message") if isinstance(detail, dict) else "started",
        "call_status": "in_progress",
    }


def _mark_incomplete(cid: str, message: str) -> None:
    with _lock:
        _state["processed_conversation_ids"].add(cid)
        _state["conversation_id"] = cid
        if _state.get("active_conversation_id") == cid:
            _state["active_conversation_id"] = None
        _state["call_status"] = "incomplete"
        _state["latest_call_status"] = "incomplete"
        _state["latest_call_message"] = message
        _state["error"] = None
        # Intentionally leave _state["latest"] untouched — Apotti stays as-is.


def _process_done_conversation(key: str, cid: str) -> bool:
    """Fetch transcript, gate completion, then analyze. Returns True if stored."""
    with _lock:
        if cid in _state["processed_conversation_ids"]:
            return False
        _state["call_status"] = "processing"
        _state["latest_call_status"] = "processing"
        _state["latest_call_message"] = None
        _state["conversation_id"] = cid

    payload = _fetch_conversation(key, cid)
    if not payload:
        # Leave unprocessed so a later poll can retry — do NOT mark processed yet.
        with _lock:
            if _state["call_status"] == "processing":
                _state["call_status"] = "in_progress"
                _state["latest_call_status"] = "in_progress"
        return False

    status = str(payload.get("status") or "").casefold()
    if status in {"failed", "error"}:
        with _lock:
            _state["processed_conversation_ids"].add(cid)
            _state["conversation_id"] = cid
            if _state.get("active_conversation_id") == cid:
                _state["active_conversation_id"] = None
            _state["call_status"] = "error"
            _state["latest_call_status"] = "error"
            _state["latest_call_message"] = str(
                payload.get("error") or payload.get("message") or "Call failed"
            )
            _state["error"] = _state["latest_call_message"]
        print(
            f"[SILTA Voice] Conversation {cid}: turns=?, status={status} -> FAILED",
            flush=True,
        )
        return False
    if status not in {"done", "completed"}:
        # Still live — keep active_conversation_id, do not mark processed.
        with _lock:
            if _state["call_status"] == "processing":
                _state["call_status"] = "in_progress"
                _state["latest_call_status"] = "in_progress"
        return False

    ok, reason, debug = _completion_gate(payload)
    _log_voice_gate(cid, ok, debug, reason)
    if not ok:
        _mark_incomplete(cid, reason or INCOMPLETE_MESSAGE)
        return False

    transcript = _transcript_text(payload)
    try:
        raw = _llm_extract(transcript) if transcript else _fallback_extract("")
        intake = _coerce_intake(raw if isinstance(raw, dict) else {})
        if not intake.get("notes"):
            intake["notes"] = transcript[:800]
        result = _run_analysis(dict(intake))
        result["transcript"] = transcript
        with _lock:
            _state["latest"] = result
            _state["call_status"] = "done"
            _state["latest_call_status"] = "done"
            _state["latest_call_message"] = "Checkup sent to Apotti"
            _state["error"] = None
            _state["processed_conversation_ids"].add(cid)
            _state["conversation_id"] = cid
            if _state.get("active_conversation_id") == cid:
                _state["active_conversation_id"] = None
        print(
            f"[SILTA Voice] Conversation {cid}: stored latest_patient_result for Apotti",
            flush=True,
        )
        return True
    except Exception as exc:
        with _lock:
            _state["call_status"] = "error"
            _state["latest_call_status"] = "error"
            _state["latest_call_message"] = f"Failed to process call transcript: {exc}"
            _state["error"] = _state["latest_call_message"]
            _state["processed_conversation_ids"].add(cid)
            if _state.get("active_conversation_id") == cid:
                _state["active_conversation_id"] = None
        return False


def poll_and_process() -> dict[str, Any]:
    """Watch outbound active_conversation_id first, then newest agent conversations."""
    seed_processed_conversations()
    key = elevenlabs_key()
    aid = agent_id()
    if not key or not aid:
        return snapshot()

    with _lock:
        active = _state.get("active_conversation_id") or None
        displayed = _state.get("conversation_id")
        processed: set[str] = set(_state["processed_conversation_ids"])
        status = _state["call_status"]

    # 1) Always check active outbound conversation_id first.
    candidates: list[str] = []
    if active and active not in processed:
        candidates.append(str(active))

    # 2) Also scan agent conversations (inbound dials + any newer outbound).
    rows = _list_agent_conversations(key, aid, page_size=30)
    for row in rows:
        cid = str(row.get("conversation_id") or "")
        st = str(row.get("status") or "").casefold()
        if not cid or cid in processed:
            continue
        if st in {"in-progress", "initiated", "processing"}:
            # Surface live inbound/outbound progress even without outbound start.
            # Never overwrite an in-flight active outbound with a different cid.
            if active and cid != active:
                if cid not in candidates:
                    candidates.append(cid)
                continue
            if status in ("idle", "done", "error", "incomplete") or displayed == cid or active == cid:
                _set(
                    call_status="in_progress",
                    latest_call_status="in_progress",
                    latest_call_message=None,
                    conversation_id=cid,
                    error=None,
                )
            if cid not in candidates:
                candidates.append(cid)
        elif st in {"done", "completed", "failed", "error"}:
            if cid not in candidates:
                candidates.append(cid)

    for cid in candidates:
        with _lock:
            if cid in _state["processed_conversation_ids"]:
                continue
        # Only fully process terminal conversations; in-progress just updates status.
        detail = _fetch_conversation(key, cid)
        if not detail:
            continue
        st = str(detail.get("status") or "").casefold()
        if st in {"done", "completed", "failed", "error"}:
            _process_done_conversation(key, cid)
            # Keep polling other candidates only if this was not the active outbound
            # and it did not produce a stored result — still break after one process
            # attempt to keep each poll cheap.
            break
        # Not terminal yet — do not mark processed; keep waiting.
        _set(call_status="in_progress", conversation_id=cid)

    return snapshot()
