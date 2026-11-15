/* Timed against public/audio/call_montage.mp3 (Whisper-verified). */
import type {CaptionCue} from "../components/Captions";

export const CALL_MONTAGE_DURATION_SEC = 29.04;

/** Frame cues at 30fps — local to the call-audio Sequence. */
export const CALL_CUES: CaptionCue[] = [
  {
    start: 0,
    end: 240,
    text: "Hello, this is SILTA from the Thriver Care cancer checkup service…",
  },
  {
    start: 240,
    end: 420,
    text: "A painful lump that stayed about the same for a week is worth a clinician look.",
  },
  {
    start: 480,
    end: 630,
    text: "Would it be all right if I share this checkup summary with your care team for human review only?",
  },
  {
    start: 630,
    end: 690,
    text: "Yeah, that's fine.",
  },
  {
    start: 690,
    end: 840,
    text: "Thank you. I am sending your checkup summary to your care team now.",
  },
];
