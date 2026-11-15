# SILTA Cinema — Remotion launch film

Isolated Remotion project for the Junction 2026 cinematic demo (~115s, 1920×1080, 30fps).

Does **not** modify the main Thriver Care / SILTA app. No PDF slides are used.

## Assets

| Path | Source |
|------|--------|
| `public/screen/*.mp4` | Cropped highlights from the live Chrome screen recording |
| `public/audio/call_montage.mp3` | Energy-ranked + Whisper-verified highlights from the speakerphone call |
| `public/audio/vo_*.mp3` | ElevenLabs executive narration (Jamie) |
| `src/broll/*` | Procedural Nordic cinema scenes (fal credits were exhausted) |

## Commands

```bash
npm run dev      # Studio preview
npm run render   # → final_silta_cinema.mp4
```

## Chapters

1. Kinetic opening over rural isolation B-roll  
2. Animated 3-layer architecture reveal  
3. Demo: 78-day baseline → Maisa **Call My Phone** + live call captions  
4. Demo: Apotti brief/proposals → 23-county RF+SHAP dashboard  
5. Evidence outro + Apple-style logo lockup  
