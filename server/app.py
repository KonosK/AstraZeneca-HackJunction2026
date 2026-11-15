"""Same-origin synthetic demo server. Credentials never reach the browser."""
from __future__ import annotations
import io
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError
from mlBackend.api import app as oncoflow, get_bundle, get_regions_df
from server import phone_intake

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'regionDashboard' / 'dist'
NARRATION = 'This is SILTA, a synthetic demonstration. Please tell your care team how long it takes you to reach care. Review and confirm your answer before sharing.'
_limits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()

ALLOWED_INTAKE_KEYS = {
    'region_name', 'age', 'symptom_severity_score', 'public_care_track',
    'already_referred_to_specialist', 'care_phase', 'needs_interpreter',
    'travel_time_to_care_minutes', 'symptom_onset_days', 'primary_symptom_cluster',
    'smoking_status', 'lives_alone', 'sex', 'education_band', 'g8_frailty_score',
    'language',
}
FIELD_QUESTIONS = {
    'symptom_severity_score': 'On a scale from 0 to 10, how severe do your symptoms feel right now?',
    'travel_time_to_care_minutes': 'About how many minutes does it take you to reach care?',
    'symptom_onset_days': 'About how many days have you had these symptoms?',
    'smoking_status': 'Do you currently smoke, used to smoke, or never smoked?',
    'lives_alone': 'Do you live alone?',
    'needs_interpreter': 'Do you need an interpreter for care visits?',
    'care_phase': 'Where are you in care right now — first contact, primary care, diagnostics, MDT, or treatment?',
    'primary_symptom_cluster': 'Which symptom group fits best: respiratory, breast, gi, gyn, heme, or other?',
    'public_care_track': 'Are you on the public care pathway?',
    'already_referred_to_specialist': 'Have you already been referred to a specialist?',
    'age': 'What is your age?',
    'region_name': 'Which wellbeing services county are you in?',
    'sex': 'What sex is recorded for you?',
    'education_band': 'Would you describe your education as low, mid, or high?',
    'g8_frailty_score': 'If a formal G8 frailty score was assessed, what was it? Otherwise say unknown.',
    'language': 'Which language do you prefer for care?',
}

def load_dotenv() -> None:
    path = ROOT / '.env'
    if not path.is_file():
        return
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip().lstrip('\ufeff')
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value

load_dotenv()

@asynccontextmanager
async def lifespan(app):
    get_bundle()
    get_regions_df()
    try:
        phone_intake.seed_processed_conversations()
    except Exception:
        # Phone intake is optional; never block demo startup.
        pass
    yield

app = FastAPI(title='Thriver Care synthetic demo', lifespan=lifespan)
app.mount('/api/oncoflow', oncoflow)

def allowed_origins():
    origins = {s.strip().rstrip('/') for s in os.getenv('APP_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8001,http://localhost:8001').split(',') if s.strip()}
    public_url = os.getenv('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
    if public_url.startswith('https://'):
        origins.add(public_url)
    railway_url = os.getenv('RAILWAY_STATIC_URL', '').strip().rstrip('/')
    if railway_url.startswith('https://'):
        origins.add(railway_url)
    railway_host = os.getenv('RAILWAY_PUBLIC_DOMAIN', '').strip()
    if railway_host and '/' not in railway_host:
        origins.add('https://' + railway_host)
    for name in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
        host = os.getenv(name, '').strip()
        if host and '/' not in host and host.endswith('.vercel.app'):
            origins.add('https://' + host)
    return origins

@app.middleware('http')
async def protect_voice(request: Request, call_next):
    # Public demo: no login / Basic-auth gate. Voice POSTs still use origin + CSRF + rate limits.
    if request.url.path.startswith('/api/voice') and request.method == 'POST':
        if request.headers.get('origin') not in allowed_origins():
            return JSONResponse({'detail': 'Voice origin is not allowed'}, status_code=403)
        token = request.cookies.get('silta_csrf', '')
        if len(token) < 32 or not secrets.compare_digest(token, request.headers.get('x-silta-csrf', '')):
            return JSONResponse({'detail': 'Voice session expired. Reload or use text'}, status_code=403)
        ip = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        with _lock:
            bucket = _limits[ip]
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= 6:
                return JSONResponse({'detail': 'Voice rate limit reached. Wait a minute or use text'}, status_code=429)
            bucket.append(now)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = 'microphone=(self), camera=()'
    if request.url.path.startswith('/api/voice') or request.url.path == '/api/session':
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/healthz')
def readiness():
    return {'status': 'ok'}

@app.get('/api/session')
def session():
    token = secrets.token_urlsafe(32)
    response = JSONResponse({'token': token})
    response.set_cookie('silta_csrf', token, httponly=True, samesite='strict', secure=os.getenv('COOKIE_SECURE', 'true' if os.getenv('VERCEL') == '1' or os.getenv('APP_ENV') == 'production' else 'false').lower() == 'true', max_age=3600)
    return response

@app.get('/api/voice/status')
def voice_status():
    # Presence only. No key values and no potentially paid provider request.
    return {'configured': bool(os.getenv('ELEVENLABS_API_KEY', '').strip()),
            'provider': 'ElevenLabs', 'provider_access': 'not_checked',
            'text_fallback': True}

def client():
    key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in ('\"', "'"):
        key = key[1:-1].strip()
    if not key:
        raise HTTPException(503, 'ElevenLabs is not configured. Continue with text')
    return ElevenLabs(api_key=key, timeout=25)

def provider_call(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except ApiError as exc:
        code = exc.status_code or 502
        detail = exc.body.get('detail', {}) if isinstance(exc.body, dict) else {}
        status = detail.get('status') if isinstance(detail, dict) else None
        if status == 'api_key_id_used_as_api_key':
            raise HTTPException(503, 'ElevenLabs received a key ID instead of the secret key. Create a new API key in ElevenLabs and copy its full secret value, then update ELEVENLABS_API_KEY in the backend and restart Python. Text and the demo sample still work') from None
        if status in ('quota_exceeded', 'insufficient_credits'):
            raise HTTPException(503, 'ElevenLabs credits unavailable. Continue with text') from None
        if code == 429:
            raise HTTPException(429, 'ElevenLabs rate limit or concurrency limit. Wait or use text') from None
        if code in (401, 403):
            raise HTTPException(503, 'ElevenLabs authorization or account permission unavailable. Use text') from None
        if code == 402:
            raise HTTPException(503, 'ElevenLabs credits unavailable. Use text') from None
        raise HTTPException(502, 'ElevenLabs request failed; check account credits and provider status. Use text') from None
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, 'ElevenLabs timed out. Continue with text') from None
    except Exception:
        raise HTTPException(502, 'Voice service unavailable. Continue with text') from None

@app.post('/api/voice/check')
def check_provider_access():
    # Account metadata only: no audio, synthesis, patient content or paid inference.
    def verify():
        subscription = client().user.subscription.get(request_options={'max_retries': 0})
        used = getattr(subscription, 'character_count', None)
        limit = getattr(subscription, 'character_limit', None)
        remaining = max(0, limit - used) if isinstance(limit, int) and isinstance(used, int) else None
        return {'authenticated': True, 'account_lookup': 'verified',
                'remaining_characters': remaining,
                'message': 'Account access verified. Speech permissions and successful STT/TTS still require a short synthetic test.'}
    return provider_call(verify)

@app.post('/api/voice/stt')
async def transcribe(request: Request):
    mime = request.headers.get('content-type', '').split(';')[0]
    extensions = {'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/wav': 'wav', 'audio/mpeg': 'mp3'}
    if mime not in extensions:
        raise HTTPException(415, 'Unsupported recording format. Continue with text')
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 4 * 1024 * 1024:
            raise HTTPException(413, 'Audio exceeds the 4 MB limit. Record a shorter answer or use text')
    if len(data) < 100:
        raise HTTPException(422, 'No usable recording received')
    def convert():
        c = client()
        with io.BytesIO(data) as audio:
            result = c.speech_to_text.convert(model_id='scribe_v2', file=('synthetic.' + extensions[mime], audio, mime), tag_audio_events=False, diarize=False, enable_logging=False, request_options={'max_retries': 0})
            return {'text': result.text, 'provider': 'ElevenLabs', 'synthetic_only': True}
    return await run_in_threadpool(provider_call, convert)

class Narration(BaseModel):
    text: str = Field(max_length=300)

@app.post('/api/voice/tts')
def narrate(body: Narration):
    if body.text != NARRATION:
        raise HTTPException(422, 'Only the approved synthetic-demo narration is supported')
    def convert():
        c = client()
        return b''.join(c.text_to_speech.convert(voice_id=os.getenv('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb'), text=body.text, model_id='eleven_multilingual_v2', output_format='mp3_44100_128', enable_logging=False, request_options={'max_retries': 0}))
    return Response(provider_call(convert), media_type='audio/mpeg')

class AgentMessage(BaseModel):
    role: str
    content: str = Field(max_length=4000)

class AgentChatRequest(BaseModel):
    messages: list[AgentMessage] = Field(default_factory=list, max_length=40)
    intake_snapshot: dict[str, Any] = Field(default_factory=dict)
    pending_fields: list[str] = Field(default_factory=list, max_length=20)

def gemini_model() -> str:
    return os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip() or 'gemini-3.1-flash-lite'

def gemini_key() -> str:
    return os.getenv('GEMINI_API_KEY', '').strip() or os.getenv('GOOGLE_API_KEY', '').strip()

def openrouter_model() -> str:
    return os.getenv('OPENROUTER_MODEL', 'z-ai/glm-5.3-flash').strip() or 'z-ai/glm-5.3-flash'

def openrouter_key() -> str:
    return os.getenv('OPENROUTER_API_KEY', '').strip()

CHECKUP_MUST = (
    'symptom_severity_score',
    'primary_symptom_cluster',
    'symptom_onset_days',
    'travel_time_to_care_minutes',
    'lives_alone',
    'smoking_status',
)

APPROVE_CTA = (
    "If this sounds right to you, click 'Approve agent to send' below "
    "and I will share this check-up summary with your care team."
)

MIN_CHECKUP_USER_TURNS = 4

_CLINICAL_HINT = re.compile(
    r'(tired|fatigu|exhaust|cough|breath|pain|symptom|lump|bleed|weight|nause|'
    r'weak|dizzy|fever|chest|stomach|bowel|sleep|worry|afraid|scared|drain|'
    r'ache|sore|swelling|hopeless|lonely|worse|lingering|weeks|months|'
    r'tender|firm|soft|growing|ear|neck|node)',
    re.I,
)
_DURATION_HINT = re.compile(
    r'(\d+\s*(day|days|week|weeks|month|months|year|years)|'
    r'\b(a|one|two|few|several)\s+(day|week|month)s?\b|'
    r'\b(since|ago|for a while|a while|recently|long)\b)',
    re.I,
)
_SEVERITY_HINT = re.compile(
    r'(\b([0-9]|10)\b(?:\s*/\s*10)?|severe|mild|moderate|heavy|draining|'
    r'unbearable|scale|out of|night sweats|fever|appetite|losing weight)',
    re.I,
)
_ACCESS_HINT = re.compile(
    r'(minute|mins?|hour|travel|drive|bus|health centre|health center|clinic|'
    r'occupational|työterveys|alone|on my own|by myself|partner|family)',
    re.I,
)
_WRAP_HINT = re.compile(
    r'(care team|share (this|the)|summary|wrap up|enough|whenever you are ready|'
    r'approve agent|prepare a checkup|send (this|the) check)',
    re.I,
)
_ALREADY_SENT = re.compile(
    r"(already sent|i('ve| have) sent|i('ve| have) shared|sent (it|this|the summary) (to|with))",
    re.I,
)

def agent_system_prompt(body: AgentChatRequest) -> str:
    pending = [k for k in body.pending_fields if k in ALLOWED_INTAKE_KEYS]
    must_have = [k for k in pending if k in CHECKUP_MUST]
    snap = body.intake_snapshot or {}
    known_must = [k for k in CHECKUP_MUST if snap.get(k) not in (None, '', 'unknown')]
    user_turns = sum(1 for m in body.messages if m.role == 'user')
    # Pace the *next* assistant reply after this user turn.
    next_step = max(1, min(user_turns or 1, MIN_CHECKUP_USER_TURNS))
    pacing = {
        1: (
            'NEXT REPLY = Turn 1 (Validate & characterize the symptom): Reflect with genuine warmth '
            '(e.g. "Finding a lump behind your ear can understandably feel worrying."). '
            'Then ask ONE focused clinical question about how long it has been there and whether it feels '
            'tender, soft, or firm/growing. Do NOT ask severity, travel, or Approve yet. '
            'ready_to_submit=false.'
        ),
        2: (
            'NEXT REPLY = Turn 2 (Red flags & severity): Acknowledge their answer empathetically. '
            'Ask ONE gentle question about symptom severity on a 1–10 scale and any accompanying systemic '
            'signs (unusual fatigue, night sweats, fever, or changes in appetite/weight). '
            'Do NOT ask travel/logistics or Approve yet. ready_to_submit=false.'
        ),
        3: (
            'NEXT REPLY = Turn 3 (Practical care & access context): Transition naturally by explaining why '
            'this helps their care team prepare. Ask ONE caring question about local access — how long it '
            'takes to reach their primary care health center (or if they use occupational health) and whether '
            'they manage things alone at home. Do NOT unlock Approve yet. ready_to_submit=false.'
        ),
        4: (
            'NEXT REPLY = Turn 4+ (Recap & consent gate): You now have enough for a thorough checkup. '
            'Give a brief reassuring summary of the clinical picture and practical care context you heard. '
            'Do NOT claim anything was already sent. End with exactly: '
            f'"{APPROVE_CTA}" '
            'Set ready_to_submit=true.'
        ),
    }[next_step]
    return (
        'You are SILTA from the Thriver Care cancer checkup service — a warm, patient-centered '
        'AI checkup companion supporting a Finnish wellbeing services county (synthetic demo). '
        'You conduct a thorough, empathetic 4-step clinical check-up — never wrap up after one message. '
        'No autonomous referral. No invented diagnosis. No treatment advice. '
        'Never claim you already sent or submitted anything — the patient must click '
        '"Approve agent to send" in Maisa. '
        '\n\n'
        'ACTIVE-LISTENING RULES (always): '
        '1) Reflect & validate first in plain warm human language before any question. '
        'Never use robotic acknowledgments like "Noted", "Got it", "Thanks for sharing", or "Understood". '
        '2) Exactly ONE question per bubble (one clinical focus per turn). Keep replies to 2–3 sentences max. '
        '3) Follow the hard 4-turn clinical pacing below — do not skip ahead to Approve, travel, or wrap-up early. '
        '4) Conversational weaving on Turn 3: explain why access context helps their care team; never form-fill. '
        '5) No interrogation of edge fields: never grill for a G8 frailty score. Do not re-ask profile facts '
        'already known (region/age) unless confirming briefly. Leave g8 unknown unless they volunteer a score. '
        '\n\n'
        f'HARD PACING (patient user messages so far: {user_turns}; Approve is locked until '
        f'{MIN_CHECKUP_USER_TURNS}+): '
        f'{pacing} '
        '\n\n'
        'STRUCTURED EXTRACTION (silent): map useful answers into field_updates without sounding extractive. '
        'Infer severity, onset, cluster, travel, and living support from natural language. Do not invent G8. '
        f'Set ready_to_submit=true ONLY on Turn {MIN_CHECKUP_USER_TURNS}+ after symptom plus duration/severity '
        'or care-access context, with field_updates filling any still-open checkup topics from conversation '
        'plus sensible profile defaults. While user messages < 4, ready_to_submit MUST be false. '
        '\n\n'
        'CRITICAL: output ONLY one JSON object, no markdown, no analysis, no chain-of-thought. '
        'The "reply" value is shown to the patient — warm reflective prose only. '
        'JSON shape: '
        '{"reply":"string","field_updates":[{"key":"field","value":...}],"ready_to_submit":false}. '
        f'Allowed keys: {sorted(ALLOWED_INTAKE_KEYS)}. '
        f'Internal still-open checkup topics (never read aloud): {must_have or ["none"]}. '
        f'Internal already-known checkup topics: {known_must or ["none"]}. '
        f'Internal intake snapshot: {json.dumps(snap)[:3500]}.'
    )

ENUM_OPTIONS = {
    'primary_symptom_cluster': {'unknown', 'respiratory', 'breast', 'gi', 'gyn', 'heme', 'other'},
    'smoking_status': {'unknown', 'never', 'former', 'current'},
    'care_phase': {'pre_contact', 'primary_care', 'diagnostics', 'mdt', 'treatment'},
    'sex': {'unknown', 'female', 'male', 'other'},
    'education_band': {'unknown', 'low', 'mid', 'high'},
}

def coerce_server_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in ENUM_OPTIONS:
        raw = str(value).strip().lower().replace(' ', '_')
        if raw in ENUM_OPTIONS[key]:
            return raw
        if key == 'primary_symptom_cluster':
            if re.search(r'respir|lung|cough|breath|chest', raw):
                return 'respiratory'
            if re.search(r'breast', raw):
                return 'breast'
            if re.search(r'gi|stomach|bowel|abdomen|digest', raw):
                return 'gi'
            if re.search(r'gyn|uter|ovari|pelvic', raw):
                return 'gyn'
            if re.search(r'heme|blood|anem|lymph', raw):
                return 'heme'
            return 'other'
        if key == 'smoking_status':
            if 'never' in raw:
                return 'never'
            if 'former' in raw or 'quit' in raw:
                return 'former'
            if 'current' in raw or 'smoke' in raw:
                return 'current'
            return 'unknown'
        return next(iter(ENUM_OPTIONS[key]))
    return value

def sanitize_field_updates(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get('key')
        if key not in ALLOWED_INTAKE_KEYS:
            continue
        value = coerce_server_value(key, item.get('value'))
        if value is None:
            continue
        out.append({'key': key, 'value': value})
    return out[:12]

def _user_turns(body: AgentChatRequest) -> int:
    return sum(1 for m in body.messages if m.role == 'user')

def _user_transcript(body: AgentChatRequest) -> str:
    return ' '.join(m.content.strip() for m in body.messages if m.role == 'user' and m.content.strip())

def _snap_known(snap: dict[str, Any], key: str) -> Any:
    val = snap.get(key)
    if val in (None, '', 'unknown'):
        return None
    return val

def _merge_known(snap: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    known = {k: v for k, v in snap.items() if v not in (None, '')}
    for item in updates:
        known[item['key']] = item['value']
    return known

def _infer_from_transcript(text: str) -> dict[str, Any]:
    low = text.lower()
    out: dict[str, Any] = {}
    sev_nums = re.findall(r'\b([0-9]|10)\b(?:\s*/\s*10)?', low)
    if sev_nums and re.search(r'(scale|severity|severe|bad|rate|out of|/10)', low):
        out['symptom_severity_score'] = min(10, max(0, int(sev_nums[-1])))
    elif re.search(r'(unbearable|can.?t (go on|cope)|worst|excruciating)', low):
        out['symptom_severity_score'] = 9
    elif re.search(r'(exhaust|draining|very (tired|bad|severe)|really (bad|hard|heavy)|struggle)', low):
        out['symptom_severity_score'] = 7
    elif re.search(r'(tired|fatigu|cough|pain|worry|worse|lingering|breath)', low):
        out['symptom_severity_score'] = 6
    elif re.search(r'(mild|a bit|slight|okay-ish|not too bad)', low):
        out['symptom_severity_score'] = 3

    months = re.search(r'(\d+)\s*months?', low)
    weeks = re.search(r'(\d+)\s*weeks?', low)
    days = re.search(r'(\d+)\s*days?', low)
    if months:
        out['symptom_onset_days'] = int(months.group(1)) * 30
    elif weeks:
        out['symptom_onset_days'] = int(weeks.group(1)) * 7
    elif days:
        out['symptom_onset_days'] = int(days.group(1))
    elif re.search(r'\b(a|one) month\b', low):
        out['symptom_onset_days'] = 30
    elif re.search(r'\b(a|one) week\b', low):
        out['symptom_onset_days'] = 7

    cluster = coerce_server_value('primary_symptom_cluster', low)
    if cluster and cluster != 'other':
        out['primary_symptom_cluster'] = cluster
    elif re.search(r'(tired|fatigu|exhaust|weak|energy)', low):
        out['primary_symptom_cluster'] = 'other'

    travel = re.search(r'(\d+)\s*(minutes?|mins?)\b', low)
    hours = re.search(r'(\d+(?:\.\d+)?)\s*hours?\b', low)
    if travel:
        out['travel_time_to_care_minutes'] = int(travel.group(1))
    elif hours:
        out['travel_time_to_care_minutes'] = int(float(hours.group(1)) * 60)

    if re.search(r'\blive[s]? alone\b|\bon my own\b|\bno one (at home|with me)\b', low):
        out['lives_alone'] = True
    elif re.search(r'\b(with (my |a )?(partner|spouse|wife|husband|family|kids|daughter|son)|not alone)\b', low):
        out['lives_alone'] = False

    if re.search(r'\bnever (smoked|smoke)\b|\bi don.?t smoke\b|\bnon-?smoker\b', low):
        out['smoking_status'] = 'never'
    elif re.search(r'\b(quit|used to smoke|former smoker|stopped smoking)\b', low):
        out['smoking_status'] = 'former'
    elif re.search(r'\b(still smoke|currently smoke|i smoke)\b', low):
        out['smoking_status'] = 'current'

    age = re.search(r'\b(?:i am|i\'m|age)\s*(\d{1,3})\b', low)
    if age and 18 <= int(age.group(1)) <= 120:
        out['age'] = int(age.group(1))
    return out

def _has_clinical_signal(transcript: str, known: dict[str, Any]) -> bool:
    if _CLINICAL_HINT.search(transcript or ''):
        return True
    if known.get('primary_symptom_cluster') not in (None, '', 'unknown'):
        return True
    return known.get('symptom_severity_score') not in (None, '')

def _has_checkup_depth(transcript: str, known: dict[str, Any]) -> bool:
    """Symptom plus duration/severity or care-access context."""
    if not _has_clinical_signal(transcript, known):
        return False
    has_duration = (
        known.get('symptom_onset_days') not in (None, '')
        or bool(_DURATION_HINT.search(transcript or ''))
    )
    has_severity = (
        known.get('symptom_severity_score') not in (None, '')
        or bool(_SEVERITY_HINT.search(transcript or ''))
    )
    has_access = (
        known.get('travel_time_to_care_minutes') not in (None, '')
        or isinstance(known.get('lives_alone'), bool)
        or bool(_ACCESS_HINT.search(transcript or ''))
    )
    return has_duration or has_severity or has_access

def _paced_followup(turns: int) -> str:
    if turns <= 1:
        return (
            'That sounds genuinely worrying to sit with. '
            'How long has this been with you, and does it feel tender, soft, or more firm or growing?'
        )
    if turns == 2:
        return (
            'Thank you for explaining that — living with it can take a real toll. '
            'On a gentle 1 to 10 scale, how heavy does it feel day to day, and have you noticed '
            'unusual fatigue, night sweats, fever, or changes in appetite or weight?'
        )
    if turns == 3:
        return (
            'That context helps me understand what you are carrying. '
            'To help your care team prepare, how long does it usually take you to reach your local '
            'health center, and are you mostly managing on your own at home?'
        )
    # Turn 4+ but readiness depth still missing — gather one more clinical/access detail.
    return (
        'I appreciate you walking me through this. '
        'To round out the checkup for your care team, how heavy does it feel on a 1 to 10 scale, '
        'or about how long does it take you to reach your local health center?'
    )

def _readiness_gate(body: AgentChatRequest, result: dict[str, Any], known: dict[str, Any]) -> bool:
    turns = _user_turns(body)
    # Hard lock: Approve never unlocks on user turns 1–3.
    if turns < MIN_CHECKUP_USER_TURNS:
        return False
    transcript = _user_transcript(body)
    if not _has_checkup_depth(transcript, known):
        return False
    reply = str(result.get('reply') or '')
    if bool(result.get('ready_to_submit')) or _WRAP_HINT.search(reply):
        return True
    last_user = next((m.content.strip().lower() for m in reversed(body.messages) if m.role == 'user'), '')
    if last_user and re.search(r'^(yes|yeah|yep|sure|ok|okay|please|kyllä|joo)\b', last_user):
        prior_assistant = next(
            (m.content for m in reversed(body.messages) if m.role in ('assistant', 'agent', 'silta')),
            '',
        )
        if _WRAP_HINT.search(prior_assistant or ''):
            return True
    # After 4+ turns with symptom + depth, unlock even if the model forgot the flag.
    return True

def _pick_value(*candidates: Any) -> Any:
    for value in candidates:
        if value not in (None, '', 'unknown'):
            return value
    return candidates[-1] if candidates else None

def _ensure_ready_fields(body: AgentChatRequest, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snap = body.intake_snapshot or {}
    known = _merge_known(snap, updates)
    inferred = _infer_from_transcript(_user_transcript(body))
    by_key = {u['key']: u['value'] for u in updates}
    fills = {
        'symptom_severity_score': _pick_value(
            by_key.get('symptom_severity_score'),
            known.get('symptom_severity_score'),
            inferred.get('symptom_severity_score'),
            6,
        ),
        'primary_symptom_cluster': _pick_value(
            by_key.get('primary_symptom_cluster'),
            known.get('primary_symptom_cluster'),
            inferred.get('primary_symptom_cluster'),
            'other',
        ),
        'symptom_onset_days': _pick_value(
            by_key.get('symptom_onset_days'),
            known.get('symptom_onset_days'),
            inferred.get('symptom_onset_days'),
            30,
        ),
        'travel_time_to_care_minutes': _pick_value(
            by_key.get('travel_time_to_care_minutes'),
            known.get('travel_time_to_care_minutes'),
            inferred.get('travel_time_to_care_minutes'),
            45,
        ),
        'lives_alone': _pick_value(
            by_key.get('lives_alone'),
            known.get('lives_alone') if isinstance(known.get('lives_alone'), bool) else None,
            inferred.get('lives_alone'),
            True,
        ),
        'smoking_status': _pick_value(
            by_key.get('smoking_status'),
            known.get('smoking_status'),
            inferred.get('smoking_status'),
            'unknown',
        ),
    }
    # Always re-emit checkup musts so FHIR candidates become chat-confirmed on the client.
    for key, value in fills.items():
        coerced = coerce_server_value(key, value)
        if coerced is not None:
            by_key[key] = coerced
    profile = {
        'region_name': _pick_value(by_key.get('region_name'), known.get('region_name'), 'Lapland'),
        'age': _pick_value(by_key.get('age'), known.get('age'), inferred.get('age'), 78),
        'public_care_track': _pick_value(
            by_key.get('public_care_track'),
            known.get('public_care_track') if isinstance(known.get('public_care_track'), bool) else None,
            True,
        ),
    }
    for key, value in profile.items():
        if known.get(key) in (None, '', 'unknown') or key not in known:
            coerced = coerce_server_value(key, value)
            if coerced is not None:
                by_key[key] = coerced
    by_key.pop('g8_frailty_score', None)
    return [{'key': k, 'value': v} for k, v in by_key.items()]

def _with_approve_cta(reply: str, updates: list[dict[str, Any]]) -> str:
    cluster = next(
        (u['value'] for u in updates if u['key'] == 'primary_symptom_cluster'),
        'these',
    )
    fallback = (
        f"I've been listening — carrying {cluster} concerns like this takes real strength."
    )
    text = (reply or '').strip()
    if _ALREADY_SENT.search(text) or not text:
        text = fallback
    elif text.rstrip().endswith('?'):
        # Closing should recap, not keep interrogating — drop a trailing question.
        parts = [p.strip() for p in re.split(r'(?<=[.!])\s+', text) if p.strip()]
        reflective = [p for p in parts if not p.endswith('?')]
        text = ' '.join(reflective[-2:]) if reflective else fallback
    if 'Approve agent to send' not in text:
        text = f'{text.rstrip()} {APPROVE_CTA}'
    return text.strip()

def finalize_agent_response(body: AgentChatRequest, result: dict[str, Any]) -> dict[str, Any]:
    updates = sanitize_field_updates(result.get('field_updates'))
    inferred = _infer_from_transcript(_user_transcript(body))
    known = _merge_known(body.intake_snapshot or {}, updates)
    for key, value in inferred.items():
        if key == 'g8_frailty_score':
            continue
        if known.get(key) in (None, '', 'unknown'):
            coerced = coerce_server_value(key, value)
            if coerced is None:
                continue
            updates.append({'key': key, 'value': coerced})
            known[key] = coerced
    updates = sanitize_field_updates(updates)
    known = _merge_known(body.intake_snapshot or {}, updates)
    turns = _user_turns(body)
    ready = _readiness_gate(body, result, known)
    reply = str(result.get('reply') or '').strip()
    if ready:
        updates = _ensure_ready_fields(body, updates)
        # When ready, always point at the Maisa Approve button — never claim an autonomous send.
        reply = _with_approve_cta(reply, updates)
        result = {
            **result,
            'reply': reply[:1200],
            'field_updates': updates,
            'ready_to_submit': True,
        }
    else:
        # Force-lock Approve on turns 1–3 even if the model tried to conclude early.
        premature = (
            bool(result.get('ready_to_submit'))
            or 'Approve agent to send' in reply
            or bool(_ALREADY_SENT.search(reply))
            or (turns < MIN_CHECKUP_USER_TURNS and bool(_WRAP_HINT.search(reply)))
        )
        if not reply or premature:
            reply = _paced_followup(turns)
        result = {
            **result,
            'reply': reply[:1200],
            'field_updates': updates,
            'ready_to_submit': False,
        }
    return result

def parse_agent_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start, end = text.find('{'), text.rfind('}')
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {'reply': text[:800], 'field_updates': []}

def fallback_agent(body: AgentChatRequest) -> dict[str, Any]:
    pending = [k for k in body.pending_fields if k in ALLOWED_INTAKE_KEYS]
    order = [k for k in CHECKUP_MUST if k in pending] + [k for k in pending if k not in CHECKUP_MUST]
    last = next((m.content.strip() for m in reversed(body.messages) if m.role == 'user'), '')
    snap = body.intake_snapshot or {}
    turns = _user_turns(body)
    updates: list[dict[str, Any]] = []
    if order and last:
        key = order[0]
        low = last.lower()
        yes = any(w in low for w in ('yes', 'yeah', 'yep', 'true', 'kyllä', 'joo', 'still', 'right', 'correct'))
        no = any(w in low for w in ('no', 'nope', 'false', 'ei', 'not'))
        prior = snap.get(key)
        # Affirming a known record value counts as a chat confirm.
        if prior not in (None, '', 'unknown') and yes and not no:
            updates.append({'key': key, 'value': coerce_server_value(key, prior)})
        elif key.endswith('_score') or key.endswith('_minutes') or key.endswith('_days') or key == 'age':
            nums = re.findall(r'-?\d+(?:\.\d+)?', last)
            if nums:
                updates.append({'key': key, 'value': float(nums[0]) if '.' in nums[0] else int(nums[0])})
        elif key == 'primary_symptom_cluster':
            updates.append({'key': key, 'value': coerce_server_value(key, last)})
        elif key in ('lives_alone', 'needs_interpreter', 'public_care_track', 'already_referred_to_specialist'):
            if yes and not no:
                updates.append({'key': key, 'value': True})
            elif no:
                updates.append({'key': key, 'value': False})
        elif key == 'smoking_status':
            if 'never' in low:
                updates.append({'key': key, 'value': 'never'})
            elif 'former' in low or 'used to' in low or 'quit' in low:
                updates.append({'key': key, 'value': 'former'})
            elif 'current' in low or 'smoke' in low:
                updates.append({'key': key, 'value': 'current'})
    # Pace by hard 4-turn clinical ladder; never unlock Approve before turn 4.
    if turns < MIN_CHECKUP_USER_TURNS:
        reply = _paced_followup(turns)
        ready = False
    else:
        reply = (
            'I have been listening carefully, and it sounds like we have a clear picture of '
            f'what you are dealing with. {APPROVE_CTA}'
        )
        ready = True
    return {
        'reply': reply,
        'field_updates': updates,
        'ready_to_submit': ready,
        'mode': 'fallback',
        'provider': 'deterministic',
        'model': None,
    }

def gemini_agent(body: AgentChatRequest) -> dict[str, Any] | None:
    key = gemini_key()
    if not key:
        return None
    contents: list[dict[str, Any]] = []
    for msg in body.messages[-20:]:
        role = 'model' if msg.role in ('assistant', 'agent', 'silta') else 'user'
        contents.append({'role': role, 'parts': [{'text': msg.content[:2000]}]})
    if not contents or contents[0]['role'] != 'user':
        contents.insert(0, {'role': 'user', 'parts': [{'text': 'Start the checkup.'}]})
    url = (
        f'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{gemini_model()}:generateContent'
    )
    try:
        with httpx.Client(timeout=45.0) as http:
            res = http.post(
                url,
                params={'key': key},
                headers={'Content-Type': 'application/json'},
                json={
                    'systemInstruction': {'parts': [{'text': agent_system_prompt(body)}]},
                    'contents': contents,
                    'generationConfig': {
                        'temperature': 0.3,
                        'maxOutputTokens': 400,
                        'responseMimeType': 'application/json',
                    },
                },
            )
        if res.status_code >= 400:
            detail = res.text[:240]
            return {
                **fallback_agent(body),
                'error': f'Gemini {res.status_code}',
                'detail': detail,
            }
        payload = res.json()
        parts = payload.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        content = ''.join(str(p.get('text', '')) for p in parts if isinstance(p, dict))
        parsed = parse_agent_json(content)
        return {
            'reply': str(parsed.get('reply') or 'Thanks — please continue.')[:1200],
            'field_updates': sanitize_field_updates(parsed.get('field_updates')),
            'ready_to_submit': bool(parsed.get('ready_to_submit')),
            'mode': 'gemini',
            'provider': 'google',
            'model': gemini_model(),
        }
    except Exception as exc:
        return {**fallback_agent(body), 'error': f'gemini_unavailable:{type(exc).__name__}'}

def openrouter_agent(body: AgentChatRequest) -> dict[str, Any] | None:
    key = openrouter_key()
    if not key:
        return None
    messages = [{'role': 'system', 'content': agent_system_prompt(body)}]
    for msg in body.messages[-20:]:
        role = 'assistant' if msg.role in ('assistant', 'agent', 'silta') else 'user'
        messages.append({'role': role, 'content': msg.content[:2000]})
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://127.0.0.1:8001',
        'X-Title': 'Thriver Care SILTA demo',
    }
    base_payload: dict[str, Any] = {
        'model': openrouter_model(),
        'messages': messages,
        'temperature': 0.2,
        'max_tokens': 400,
    }
    try:
        with httpx.Client(timeout=25.0) as http:
            # GLM 5.3 Flash requires reasoning; low effort keeps JSON in content.
            res = http.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json={
                    **base_payload,
                    'response_format': {'type': 'json_object'},
                    'reasoning': {'effort': 'low'},
                },
            )
            if res.status_code >= 400:
                res = http.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers=headers,
                    json={**base_payload, 'reasoning': {'effort': 'low'}},
                )
        if res.status_code >= 400:
            fb = fallback_agent(body)
            if res.status_code == 429:
                fb['reply'] = (
                    '(OpenRouter is rate-limited right now — continuing offline.) '
                    + fb['reply']
                )
            return {**fb, 'mode': 'fallback', 'error': f'OpenRouter {res.status_code}'}
        payload = res.json()
        message = payload['choices'][0]['message']
        content = message.get('content')
        if isinstance(content, list):
            content = ' '.join(
                str(part.get('text', part)) if isinstance(part, dict) else str(part)
                for part in content
            )
        if not content:
            content = message.get('reasoning') or message.get('refusal') or ''
        parsed = parse_agent_json(content if isinstance(content, str) else str(content))
        reply = str(parsed.get('reply') or '').strip()
        leak = re.search(
            r'(intake snapshot|field_updates|ready_to_submit|still-open|checkup topics|let me analyze)',
            reply,
            re.I,
        )
        if not reply or leak:
            fb = fallback_agent(body)
            updates = sanitize_field_updates(parsed.get('field_updates'))
            if updates:
                fb['field_updates'] = updates
            return {
                **fb,
                'mode': 'openrouter',
                'provider': 'openrouter',
                'model': openrouter_model(),
                'error': 'sanitized_non_patient_reply',
            }
        return {
            'reply': reply[:1200],
            'field_updates': sanitize_field_updates(parsed.get('field_updates')),
            'ready_to_submit': bool(parsed.get('ready_to_submit')),
            'mode': 'openrouter',
            'provider': 'openrouter',
            'model': openrouter_model(),
        }
    except Exception:
        return {**fallback_agent(body), 'error': 'openrouter_unavailable'}

def run_agent(body: AgentChatRequest) -> dict[str, Any]:
    last_fail: dict[str, Any] | None = None
    # OpenRouter first (faster GLM flash); Gemini only if OR missing/fails.
    for runner in (openrouter_agent, gemini_agent):
        result = runner(body)
        if result is None:
            continue
        if result.get('mode') in ('gemini', 'openrouter'):
            return finalize_agent_response(body, result)
        last_fail = result
    return finalize_agent_response(
        body,
        last_fail if last_fail is not None else fallback_agent(body),
    )

@app.get('/api/agent/status')
def agent_status():
    if openrouter_key():
        return {
            'configured': True,
            'provider': 'openrouter',
            'model': openrouter_model(),
            'fallback': True,
        }
    if gemini_key():
        return {
            'configured': True,
            'provider': 'google',
            'model': gemini_model(),
            'fallback': True,
        }
    return {
        'configured': False,
        'provider': 'deterministic',
        'model': None,
        'fallback': True,
    }

@app.post('/api/agent/chat')
def agent_chat(body: AgentChatRequest):
    if not body.messages:
        raise HTTPException(422, 'Send at least one chat message')
    return run_agent(body)

class OutboundCallRequest(BaseModel):
    to_number: str = Field(..., min_length=8, max_length=20)

@app.post('/call/outbound')
def call_outbound(body: OutboundCallRequest):
    try:
        return phone_intake.start_outbound(body.to_number)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc

@app.get('/latest-patient')
def latest_patient():
    return phone_intake.poll_and_process()

@app.get('/call/status')
def call_status():
    return phone_intake.snapshot()

if DIST.is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
    app.mount('/fixtures', StaticFiles(directory=DIST / 'fixtures'), name='fixtures')
    app.mount('/brand', StaticFiles(directory=DIST / 'brand'), name='brand')

@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith('api/') or path in ('call/outbound', 'latest-patient', 'call/status'):
        raise HTTPException(404, 'Unknown API route')
    if not DIST.is_dir():
        raise HTTPException(503, 'Build frontend or run Vite on port 5173')
    if path in ('', 'simulation', 'patient', 'doctor', 'dashboard'):
        return FileResponse(
            DIST / 'index.html',
            headers={'Cache-Control': 'no-store, max-age=0, must-revalidate'},
        )
    if path in ('favicon.svg', 'icons.svg', 'finland-wellbeing-counties.geojson'):
        return FileResponse(DIST / path)
    raise HTTPException(404, 'Not found')
