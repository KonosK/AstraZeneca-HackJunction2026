"""Same-origin synthetic demo server. Credentials never reach the browser."""
from __future__ import annotations
import io
import base64
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
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
        return FileResponse(DIST / 'index.html')
    if path in ('favicon.svg', 'icons.svg', 'finland-wellbeing-counties.geojson'):
        return FileResponse(DIST / path)
    raise HTTPException(404, 'Not found')
