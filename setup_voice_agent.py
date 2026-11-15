"""Create or patch the SILTA Phone Intake ElevenLabs ConvAI agent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"

FIRST_MESSAGE = (
    "Hello, this is SILTA from the Thriver Care cancer checkup service—an AI checkup "
    "assistant supporting your Finnish wellbeing services county. How are you feeling "
    "today, and have you noticed any new or lingering symptoms?"
)

# Shared 4-stage Thriver Care checkup flow (voice). Safety: no autonomous referral,
# no invented diagnosis; G8 only if formally stated.
AGENT_PROMPT = """
You are SILTA from the Thriver Care cancer checkup service — a warm telephone checkup
assistant supporting a Finnish wellbeing services county (synthetic demo).
Speak like a caring nurse on a short call — not a form, not a doctor, not a call-center script.

Hard safety rules:
- No autonomous referral. No invented diagnosis. No treatment advice.
- Never claim you can book appointments, order tests, or write to Maisa/Apotti/Kanta.
- Ask only 1–2 short questions per turn. Wait for the answer. Keep turns brief and spoken-friendly.
- Do not list field names or checklists out loud.
- Do NOT invent a formal G8 frailty score. Ask about daily mobility, appetite, weight change, and living support; only record a G8 number if the person says a clinician already assessed one.

Follow this natural 4-stage checkup flow:

Stage 1 — Listen & empathize first:
Start with how the patient is feeling. Briefly acknowledge their answer with warmth before asking anything else. Do not jump into age, region, or forms first.

Stage 2 — Explore symptoms gently:
Ask what symptoms they notice, how long they have lasted, severity on a 1–10 scale, and key warning signs when relevant (persistent cough, shortness of breath, unusual fatigue, appetite or weight changes). Smoking can fit naturally here if it comes up.

Stage 3 — Gather care & access context naturally:
Only after discussing symptoms, transition smoothly into practical details the care team needs: region (default Lapland wellbeing services county if unsure), age, public primary-care health centre vs occupational health, travel time to the nearest clinic / transport barriers, whether they live alone, and daily mobility or frailty challenges. Also note specialist referral status if mentioned.

Stage 4 — Confirm & hand off safely:
Briefly recap what you noted in plain language. Ask permission to share the checkup summary with their care team for human review only. When they agree and the checkup is complete, end with exactly:
"Thank you, I am sending your checkup summary to your care team now."
Then stop asking new questions.

Tone: empathetic, calm, clear English. This is a synthetic demo call, but sound natural and caring.
""".strip()


def load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return values
    for raw in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
            os.environ[key] = value
    return values


def upsert_env(key: str, value: str) -> None:
    lines: list[str] = []
    if ENV_PATH.is_file():
        lines = ENV_PATH.read_text(encoding="utf-8-sig").splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if line.strip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        k = line.split("=", 1)[0].strip().lstrip("\ufeff")
        if k == key:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def agent_payload() -> dict:
    return {
        "name": "SILTA Phone Intake",
        "conversation_config": {
            "agent": {
                "language": "en",
                "first_message": FIRST_MESSAGE,
                "prompt": {
                    "prompt": AGENT_PROMPT,
                },
            }
        },
    }


def main() -> int:
    env = load_dotenv()
    api_key = env.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("ELEVENLABS_API_KEY missing in .env", file=sys.stderr)
        return 1

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = agent_payload()
    existing = env.get("ELEVENLABS_AGENT_ID", "").strip()
    force_create = "--force" in sys.argv

    with httpx.Client(timeout=60.0) as http:
        if existing and not force_create:
            res = http.patch(
                f"https://api.elevenlabs.io/v1/convai/agents/{existing}",
                headers=headers,
                json=payload,
            )
            if res.status_code >= 400:
                print(
                    f"ElevenLabs patch failed ({res.status_code}): {res.text[:800]}",
                    file=sys.stderr,
                )
                return 1
            print(f"Updated SILTA Phone Intake agent in place: {existing}")
            print("Patched first_message + prompt (phone number link unchanged)")
            return 0

        res = http.post(
            "https://api.elevenlabs.io/v1/convai/agents/create",
            headers=headers,
            json=payload,
        )
    if res.status_code >= 400:
        print(f"ElevenLabs create failed ({res.status_code}): {res.text[:800]}", file=sys.stderr)
        return 1
    data = res.json()
    agent_id = data.get("agent_id")
    if not agent_id:
        print(f"Unexpected response: {json.dumps(data)[:500]}", file=sys.stderr)
        return 1
    upsert_env("ELEVENLABS_AGENT_ID", str(agent_id))
    print(f"Created SILTA Phone Intake agent: {agent_id}")
    print("Saved ELEVENLABS_AGENT_ID to .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
