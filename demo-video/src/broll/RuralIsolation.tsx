import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {COLORS} from "../theme";

/** Procedural Nordic cinema stand-in for fal Shot 1 (rural Lapland phone call). */
export const RuralIsolation: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drift = interpolate(frame, [0, 360], [0, -28]);
  const glow = spring({frame, fps, config: {damping: 200}});

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 30% 20%, #3A5B6A 0%, #15222A 42%, #0A1218 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -40,
          transform: `translateY(${drift}px) scale(1.08)`,
          background:
            "linear-gradient(180deg, rgba(180,210,220,0.35) 0%, transparent 38%), linear-gradient(115deg, #1C3340 0%, #0E1A22 55%, #16262F 100%)",
        }}
      />
      {/* Window light */}
      <div
        style={{
          position: "absolute",
          right: "12%",
          top: "18%",
          width: 420,
          height: 520,
          borderRadius: 8,
          background:
            "linear-gradient(180deg, rgba(255,236,200,0.55), rgba(255,210,150,0.12))",
          boxShadow: `0 0 ${80 + glow * 40}px rgba(255, 214, 160, 0.35)`,
          opacity: 0.85,
          transform: "skewX(-2deg)",
        }}
      />
      {/* Silhouette figure by window */}
      <div
        style={{
          position: "absolute",
          right: "22%",
          bottom: "12%",
          width: 160,
          height: 340,
          borderRadius: "80px 80px 40px 40px",
          background:
            "linear-gradient(180deg, rgba(20,28,34,0.95), rgba(10,14,18,0.98))",
          boxShadow: "inset -18px 0 30px rgba(255,220,170,0.12)",
        }}
      />
      {/* Phone glow in hand */}
      <div
        style={{
          position: "absolute",
          right: "18%",
          bottom: "38%",
          width: 34,
          height: 58,
          borderRadius: 8,
          background: COLORS.cyan,
          opacity: 0.35 + 0.2 * Math.sin(frame / 8),
          boxShadow: `0 0 30px ${COLORS.cyan}`,
        }}
      />
      {/* Soft snowfall particles */}
      {Array.from({length: 28}).map((_, i) => {
        const x = (i * 73) % 100;
        const y = ((frame * (0.4 + (i % 5) * 0.12) + i * 17) % 120) - 10;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: 3 + (i % 3),
              height: 3 + (i % 3),
              borderRadius: 99,
              background: "rgba(240,248,255,0.65)",
              opacity: 0.35 + (i % 4) * 0.1,
            }}
          />
        );
      })}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(7,19,26,0.15), rgba(7,19,26,0.55))",
        }}
      />
    </AbsoluteFill>
  );
};
