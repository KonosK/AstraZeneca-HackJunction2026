import { useEffect, useRef, useState } from "react";
const narration =
  "This is SILTA, a synthetic demonstration. Please tell your care team how long it takes you to reach care. Review and confirm your answer before sharing.";
export function VoiceInput({
  text,
  onText,
  language,
}: {
  language: string;
  text: string;
  onText: (s: string) => void;
}) {
  const [status, setStatus] = useState("Ready for text or voice"),
    [recording, setRecording] = useState(false),
    [busy, setBusy] = useState(false),
    [consent, setConsent] = useState(false),
    [seconds, setSeconds] = useState(0),
    [narrating, setNarrating] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    chunks = useRef<Blob[]>([]),
    audio = useRef<HTMLAudioElement | null>(null),
    url = useRef<string | null>(null),
    token = useRef<string>("");
  const stopTracks = () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  };
  useEffect(
    () => () => {
      if (recorder.current?.state === "recording") {
        recorder.current.onstop = null;
        recorder.current.stop();
      }
      stopTracks();
      audio.current?.pause();
      if (url.current) URL.revokeObjectURL(url.current);
    },
    [],
  );
  useEffect(() => {
    if (!recording) return;
    const id = setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, [recording]);
  useEffect(() => {
    if (seconds >= 20 && recorder.current?.state === "recording")
      recorder.current.stop();
  }, [seconds]);
  async function headers() {
    if (!token.current) {
      const r = await fetch("/api/session");
      if (!r.ok) throw Error("Voice service unavailable. Continue with text.");
      token.current = (await r.json()).token;
    }
    return { "X-Silta-CSRF": token.current };
  }
  async function providerError(r: Response) {
    let detail = "Voice provider unavailable";
    try {
      detail = (await r.json()).detail || detail;
    } catch {
      /* plain server error */
    }
    throw Error(detail + ". Your text remains editable.");
  }
  async function checkSetup() {
    setStatus("Checking this server’s voice setup…");
    try {
      const r = await fetch("/api/voice/status", {
        signal: AbortSignal.timeout(5000),
      });
      if (!r.ok)
        throw Error(
          "Could not check voice setup. Use the demo sample or type a reply.",
        );
      const info = await r.json();
      setStatus(
        info.configured
          ? "The server detects an ElevenLabs key. Record a short synthetic answer to test provider access; this check does not validate the key or credits."
          : "No ElevenLabs key is configured on this server. Configure it in the PowerShell window running Python, then restart the backend. Or use Fill demo check-in.",
      );
    } catch (e) {
      setStatus(
        e instanceof Error
          ? e.message
          : "Setup check failed. Continue with text.",
      );
    }
  }
  async function checkProvider() {
    setBusy(true);
    setStatus("Checking ElevenLabs account access without generating audio…");
    try {
      const response = await fetch("/api/voice/check", {
        method: "POST",
        headers: await headers(),
        signal: AbortSignal.timeout(30000),
      });
      if (!response.ok) await providerError(response);
      const info = await response.json();
      setStatus(
        info.message +
          (typeof info.remaining_characters === "number"
            ? ` Account characters remaining: ${info.remaining_characters}.`
            : ""),
      );
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Could not verify provider access. Use the sample or text.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function record() {
    if (!consent) {
      setStatus("Consent is required to send synthetic audio to ElevenLabs.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatus(
        "Recording requires a supported browser and HTTPS. Use text below.",
      );
      return;
    }
    try {
      audio.current?.pause();
      setNarrating(false);
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      chunks.current = [];
      setSeconds(0);
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "";
      const rec = new MediaRecorder(
        stream.current,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = rec;
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      rec.onerror = () => {
        stopTracks();
        setRecording(false);
        setStatus("Recording failed. Use text.");
      };
      rec.onstop = async () => {
        stopTracks();
        setRecording(false);
        setBusy(true);
        setStatus("Transcribing with ElevenLabs…");
        try {
          const blob = new Blob(chunks.current, { type: rec.mimeType });
          if (!blob.size) throw Error("No audio captured");
          const r = await fetch("/api/voice/stt", {
            method: "POST",
            headers: { ...(await headers()), "Content-Type": blob.type },
            body: blob,
            signal: AbortSignal.timeout(35000),
          });
          if (!r.ok) await providerError(r);
          const b = await r.json();
          onText(b.text);
          setStatus("Transcription ready. Correct, then confirm.");
        } catch (e) {
          setStatus(
            e instanceof Error ? e.message : "Transcription failed. Use text.",
          );
        } finally {
          setBusy(false);
        }
      };
      rec.start();
      setRecording(true);
      setStatus("Recording synthetic answer (maximum 20 seconds)…");
    } catch (e) {
      stopTracks();
      setStatus(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Microphone permission denied. Type your answer below."
          : "Microphone unavailable. Type your answer below.",
      );
    }
  }
  async function speak() {
    if (!consent) {
      setStatus("Consent is required to use ElevenLabs narration.");
      return;
    }
    setBusy(true);
    setStatus("Preparing ElevenLabs narration…");
    try {
      const r = await fetch("/api/voice/tts", {
        method: "POST",
        headers: { ...(await headers()), "Content-Type": "application/json" },
        body: JSON.stringify({ text: narration }),
        signal: AbortSignal.timeout(35000),
      });
      if (!r.ok) await providerError(r);
      if (url.current) URL.revokeObjectURL(url.current);
      url.current = URL.createObjectURL(await r.blob());
      audio.current = new Audio(url.current);
      audio.current.onended = () => setNarrating(false);
      audio.current.onerror = () => {
        setNarrating(false);
        setStatus("Audio playback failed. Read or type your reply.");
      };
      await audio.current.play();
      setNarrating(true);
      setStatus("SILTA narration playing. It does not provide a diagnosis.");
    } catch (e) {
      setStatus(
        e instanceof Error
          ? e.message
          : "Narration unavailable. Read the question.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="voice-task" aria-label="Patient response">
      <h3>
        {language === "fi"
          ? "Miten voit tänään?"
          : "How are you feeling today?"}
      </h3>
      <p>
        {language === "fi"
          ? "Kerro voinnistasi ja mahdollisista oireista. Kuinka kauan matka hoitoon kestää?"
          : "Describe how you feel and any symptoms. Also, how long does it take you to reach care? Travel can be a practical access barrier."}
      </p>

      <details className="voice-options">
        <summary>Optional voice · ElevenLabs</summary>
        <p className="small">
          Record a synthetic answer or listen to the English prompt. Text and
          the demo preset work without a key.
        </p>
        <button onClick={checkSetup} disabled={busy || recording}>
          Check voice setup
        </button>
        <button onClick={checkProvider} disabled={busy || recording}>
          Verify provider access
        </button>
        <label className="consent">
          <input
            type="checkbox"
            checked={consent}
            disabled={busy || recording}
            onChange={(e) => setConsent(e.target.checked)}
          />{" "}
          Optional: I consent to send this synthetic demo audio to ElevenLabs.
          Never use real patient data.
        </label>
        <div className="button-row">
          <button onClick={speak} disabled={busy || recording || narrating}>
            Listen to SILTA
          </button>
          <button
            onClick={() =>
              recording ? recorder.current?.stop() : void record()
            }
            disabled={busy}
          >
            {recording ? `Stop recording · ${seconds}s` : "Record voice answer"}
          </button>
          {narrating && (
            <button
              onClick={() => {
                audio.current?.pause();
                setNarrating(false);
                setStatus("Narration stopped.");
              }}
            >
              Stop narration
            </button>
          )}
        </div>
      </details>
      {status !== "Ready for text or voice" && (
        <p role="status" className="voice-status">
          {status}
        </p>
      )}
      <label>
        Editable answer preview
        <textarea
          aria-label="Editable answer preview"
          value={text}
          maxLength={1000}
          onChange={(e) => onText(e.target.value)}
          placeholder="Type here, or record a synthetic answer. For example: about 95 minutes."
        />
      </label>
      <p className="small">
        Review or edit your reply before sending. Audio is not submitted as a
        clinical fact; only confirmed structured fields reach the model.
      </p>
    </section>
  );
}
