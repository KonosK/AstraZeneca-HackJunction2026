# B-roll

fal.ai MiniMax H3 Max text-to-video was selected for photorealistic Nordic shots, but the connected fal account had **balance_exhausted** at generation time.

Procedural Remotion cinema scenes in `src/broll/` are used instead:

1. `RuralIsolation` — Lapland morning / phone-by-window
2. `NeuralSynthesis` — voice waveform → clinical nodes
3. `FinlandTelemetry` — glowing county telemetry map

To swap in real AI clips later: place `shot1.mp4`, `shot2.mp4`, `shot3.mp4` here and wire them via `<OffthreadVideo src={staticFile('broll/shotN.mp4')} />`.
