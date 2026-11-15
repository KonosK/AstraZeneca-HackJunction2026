"""Same-origin synthetic demo server. Credentials never reach the browser."""
from __future__ import annotations
import io
import base64
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
    yield

app = FastAPI(title='Thriver Care synthetic demo', lifespan=lifespan)
app.mount('/api/oncoflow', oncoflow)

def allowed_origins():
    origins = {s.strip().rstrip('/') for s in os.getenv('APP_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8001,http://localhost:8001').split(',') if s.strip()}
    public_url = os.getenv('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
    if public_url.startswith('https://'):
        origins.add(public_url)
    for name in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
        host = os.getenv(name, '').strip()
        if host and '/' not in host and host.endswith('.vercel.app'):
            origins.add('https://' + host)
    return origins

@app.middleware('http')
async def protect_voice(request: Request, call_next):
    if (os.getenv('APP_ENV') == 'production' or os.getenv('VERCEL') == '1') and request.url.path != '/healthz':
        password = os.getenv('DEMO_ACCESS_TOKEN', '')
        authorized = False
        try:
            scheme, encoded = request.headers.get('authorization', '').split(' ', 1)
            user, supplied = base64.b64decode(encoded, validate=True).decode().split(':', 1)
            authorized = scheme.lower() == 'basic' and user == 'demo' and bool(password) and secrets.compare_digest(supplied, password)
        except (ValueError, UnicodeDecodeError):
            pass
        if not authorized:
            return JSONResponse({'detail': 'Private synthetic demo access required'}, status_code=401, headers={'WWW-Authenticate': 'Basic realm="Thriver synthetic demo"'})
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

def agent_system_prompt(body: AgentChatRequest) -> str:
    pending = [k for k in body.pending_fields if k in ALLOWED_INTAKE_KEYS]
    must_have = [k for k in pending if k in CHECKUP_MUST]
    snap = body.intake_snapshot or {}
    known_must = [k for k in CHECKUP_MUST if snap.get(k) not in (None, '', 'unknown')]
    return (
        'You are SILTA doing a warm, natural synthetic cancer-care checkup call — '
        'like a caring nurse checking in, not a form or intake clerk. '
        'Speak in short, human messages. Ask about ONE thing at a time. '
        'Cover a real checkup before finishing: (1) how bad symptoms feel 0-10, '
        '(2) what kind of symptoms (cough, breath, pain area, etc.), '
        '(3) roughly how long this has gone on, (4) travel time to care, '
        '(5) whether they live alone, (6) smoking (never / used to / now). '
        'If the intake snapshot already has a value from records, gently confirm it '
        'in plain language instead of skipping that topic. '
        'Education band is optional — ask once gently only if the chat already feels easy; never pressure. '
        'Do NOT ask the patient for a G8 frailty score number; leave g8 unknown unless they explicitly '
        'report a formal assessed score. '
        'Do NOT list missing fields, field labels, checklists, or say you need County/Age/etc. '
        'Do NOT sound like you are extracting data. Never invent diagnoses, referrals, or treatment advice. '
        'Silently map anything useful into field_updates. '
        'Set ready_to_submit=true ONLY when all six checkup topics above are known or clearly confirmed '
        '(travel may be "cannot estimate" — then set travel_time_to_care_minutes to a best-effort number '
        'or omit and keep going until they give minutes or say they truly cannot). '
        'Never mark ready after only one or two answers. Otherwise ready_to_submit=false and continue. '
        'When ready, tell them gently the checkup can be sent for care-team review (demo only). '
        'CRITICAL: output ONLY one JSON object, no markdown, no analysis, no chain-of-thought. '
        'The "reply" value is spoken aloud to the patient — 1-3 short caring sentences, never field names, '
        'never "intake snapshot", never planning notes. Put all structure in field_updates / ready_to_submit. '
        'JSON shape: '
        '{"reply":"string","field_updates":[{"key":"field","value":...}],"ready_to_submit":false}. '
        f'Allowed keys: {sorted(ALLOWED_INTAKE_KEYS)}. '
        f'Internal still-open checkup topics (never read aloud as a list): {must_have or ["none"]}. '
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
    return out[:8]

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
    soft = {
        'symptom_severity_score': 'How rough does it feel right now, from 0 to 10?',
        'primary_symptom_cluster': 'What bothers you most — cough, breathing, pain somewhere else?',
        'symptom_onset_days': 'About how long have you been feeling this way?',
        'travel_time_to_care_minutes': 'How long does it usually take you to get to care?',
        'lives_alone': 'Are you living on your own at the moment?',
        'smoking_status': 'Do you smoke now, used to, or never?',
    }
    confirm = {
        'primary_symptom_cluster': 'Just to check — is it still mainly {v} symptoms?',
        'symptom_onset_days': 'Does about {v} days sound right for how long this has been going on?',
        'lives_alone': 'I have you living on your own — is that still right?',
        'smoking_status': 'On smoking, I have {v} — still accurate?',
    }
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
    remaining = [k for k in order if k not in {u['key'] for u in updates}]
    if remaining:
        key = remaining[0]
        prior = snap.get(key)
        if key in confirm and prior not in (None, '', 'unknown') and key not in {u['key'] for u in updates}:
            reply = confirm[key].format(v=prior)
        else:
            reply = soft.get(key, 'How have you been feeling otherwise?')
        if updates:
            reply = 'Thanks for telling me. ' + reply
        ready = False
    else:
        reply = (
            'Thanks for talking this through with me. I think we have enough for this '
            'checkup — you can send it to your care team for review whenever you are ready.'
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
            return result
        last_fail = result
    return last_fail if last_fail is not None else fallback_agent(body)

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

if DIST.is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
    app.mount('/fixtures', StaticFiles(directory=DIST / 'fixtures'), name='fixtures')
    app.mount('/brand', StaticFiles(directory=DIST / 'brand'), name='brand')

@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith('api/'):
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
