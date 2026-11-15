import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {NeuralSynthesis} from "../broll/NeuralSynthesis";
import {FilmGrain} from "../components/FilmGrain";
import {COLORS} from "../theme";

/**
 * Layer card entrances are paced to the VO (~19.7s / 25.6s / 32.7s absolute).
 * Architecture scene begins ~9.6s absolute after the hook fade.
 */
const LAYERS = [
  {
    title: "Layer 1",
    subtitle: "Inclusive Voice & Chat Intake",
    tag: "Micro",
    detail: "Maisa-like phone & chat checkup · human-review consent",
    delay: 280,
  },
  {
    title: "Layer 2",
    subtitle: "Apotti Clinician Copilot",
    tag: "Micro",
    detail: "Structured brief · proposals for clinician review only",
    delay: 460,
  },
  {
    title: "Layer 3",
    subtitle: "23-County Random Forest + SHAP",
    tag: "Macro",
    detail: "County intelligence · associations, not causality",
    delay: 680,
  },
] as const;

export const ArchitectureReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill>
      <NeuralSynthesis />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(7,19,26,0.55), rgba(7,19,26,0.82))",
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          gap: 22,
          padding: 80,
        }}
      >
        <div
          style={{
            fontFamily: "Sora, sans-serif",
            fontSize: 22,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: COLORS.cyan,
            marginBottom: 12,
            opacity: interpolate(frame, [0, 20], [0, 1], {
              extrapolateRight: "clamp",
            }),
          }}
        >
          Three-layer architecture
        </div>
        {LAYERS.map((layer, i) => {
          const enter = spring({
            frame: frame - layer.delay,
            fps,
            config: {damping: 16, stiffness: 100},
          });
          const y = interpolate(enter, [0, 1], [50, 0]);
          const pulse = interpolate(
            (frame + i * 20) % 50,
            [0, 25, 50],
            [0.35, 1, 0.35],
          );
          return (
            <div
              key={layer.title}
              style={{
                width: 1180,
                opacity: enter,
                transform: `translateY(${y}px)`,
                borderRadius: 22,
                padding: "22px 28px",
                background: COLORS.glass,
                border: "1px solid rgba(126,224,214,0.22)",
                backdropFilter: "blur(14px)",
                boxShadow: `0 0 ${20 + pulse * 30}px rgba(31,166,160,${0.12 * pulse})`,
                display: "grid",
                gridTemplateColumns: "160px 1fr auto",
                alignItems: "center",
                gap: 18,
              }}
            >
              <div
                style={{
                  fontFamily: "Sora, sans-serif",
                  color: COLORS.amber,
                  fontSize: 22,
                  fontWeight: 600,
                }}
              >
                {layer.title}
              </div>
              <div>
                <div
                  style={{
                    fontFamily: "Fraunces, serif",
                    fontSize: 36,
                    color: COLORS.text,
                    lineHeight: 1.15,
                  }}
                >
                  {layer.subtitle}
                </div>
                <div
                  style={{
                    marginTop: 6,
                    fontFamily: "Sora, sans-serif",
                    fontSize: 18,
                    color: COLORS.muted,
                  }}
                >
                  {layer.detail}
                </div>
              </div>
              <div
                style={{
                  fontFamily: "Sora, sans-serif",
                  fontSize: 14,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: COLORS.cyan,
                  border: "1px solid rgba(126,224,214,0.35)",
                  borderRadius: 999,
                  padding: "8px 14px",
                }}
              >
                {layer.tag}
              </div>
              <div
                style={{
                  gridColumn: "1 / -1",
                  height: 3,
                  borderRadius: 99,
                  background: `linear-gradient(90deg, transparent, ${COLORS.cyan}, ${COLORS.amber}, transparent)`,
                  opacity: pulse * 0.7,
                  transform: `translateX(${interpolate(frame + i * 10, [0, 80], [-200, 200])}px)`,
                }}
              />
            </div>
          );
        })}
      </AbsoluteFill>
      <FilmGrain opacity={0.07} />
    </AbsoluteFill>
  );
};
