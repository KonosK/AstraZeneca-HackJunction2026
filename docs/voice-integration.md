# ElevenLabs integration and live status

Official Python SDK `elevenlabs==2.78.0` is used only on the server. STT: `speech_to_text.convert`, model `scribe_v2`. TTS: `text_to_speech.convert`, `eleven_multilingual_v2`, configurable voice ID, fixed synthetic prompt. The application never introduces another clinical decision agent.

Browser flow: explicit consent → microphone permission → MediaRecorder (20-second cap) → server STT → editable preview → explicit preview confirmation → manually confirmed structured intake → analysis. Speech is never guessed into medical fields. Text check-in works without audio, provider credentials or any external language model. English and Finnish question prompts are available; structured review and fixed TTS narration are English.

Safety controls: same-origin requests, origin allowlist, HttpOnly/SameSite CSRF cookie plus header, private production Basic-auth gate, six voice attempts/minute/IP/process, 4 MB audio cap, 25-second SDK timeout, no automatic SDK retries, fixed TTS text, generic sanitized errors, no-store responses, no application audio/transcript persistence. SDK logging disabled where supported; provider retention/account settings must still be reviewed by the owner. Single-process demo limiter is not a distributed production quota service.

## Actual validation

The environment contains `ELEVENLABS_API_KEY` and the domain `api.elevenlabs.io` is allowed. A real SDK TTS attempt failed. Read-only provider subscription/voices/models requests returned HTTP 400 with machine status **`api_key_id_used_as_api_key`**. The service is rejecting the configured credential as a key identifier rather than the secret API key. Values were not logged or copied to source. Credit balance could not be verified. Live STT was not attempted after this confirmed authentication failure. No successful real STT or TTS is claimed.

Browser tests exercise recording using generated synthetic audio and an explicitly mocked STT response, editing and confirmation, provider failure, denied microphone permission and the complete text fallback. Server tests exercise the official adapter boundary, safe errors, authorization, rate limits, upload limits and missing-key behavior. Mocked tests are not live-provider evidence.

## Owner action

Replace the existing secret value securely in environment/hosting settings with the actual ElevenLabs secret API key, not the key's identifier. Keep the binding name `ELEVENLABS_API_KEY` and HTTPS destination `api.elevenlabs.io`; do not paste the value into chat or a `VITE_` variable. No duplicate secret or new domain grant is indicated by the current evidence. After the value propagates, retry one short synthetic TTS and STT pair, confirm account credit availability, and update this status with actual results.

## Local Windows setup and presence check

See `WINDOWS.md` for a short Python environment path, a masked PowerShell key prompt, backend restart and browser checks. Cloud secrets are not automatically present on a local Windows computer. `GET /api/voice/status` returns only configured/unconfigured, provider name, unchecked provider access and text-fallback availability. The UI's **Check voice setup** therefore does not imply a valid key or available credits. **Fill demo check-in** loads a synthetic editable sample independently of voice configuration and never confirms or submits it automatically.
