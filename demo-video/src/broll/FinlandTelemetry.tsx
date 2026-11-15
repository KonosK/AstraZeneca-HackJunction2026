import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {COLORS} from "../theme";

/** Procedural stand-in for fal Shot 3 — glowing Finland county telemetry. */
export const FinlandTelemetry: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = 0.55 + 0.45 * Math.sin(frame / 12);

  const counties = [
    {x: 980, y: 220, r: 18, c: COLORS.cyan},
    {x: 940, y: 300, r: 22, c: COLORS.teal},
    {x: 1000, y: 360, r: 20, c: COLORS.amber},
    {x: 920, y: 430, r: 26, c: COLORS.cyan},
    {x: 1040, y: 470, r: 18, c: COLORS.teal},
    {x: 960, y: 540, r: 24, c: COLORS.amber},
    {x: 1080, y: 560, r: 16, c: COLORS.cyan},
    {x: 1000, y: 620, r: 28, c: COLORS.teal},
    {x: 940, y: 680, r: 20, c: COLORS.amber},
    {x: 1060, y: 700, r: 18, c: COLORS.cyan},
    {x: 980, y: 760, r: 22, c: COLORS.teal},
  ];

  const rot = interpolate(frame, [0, 300], [0, 8]);

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 40%, #0C2C34 0%, #060F14 55%, #04080C 100%)",
      }}
    >
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{position: "absolute", inset: 0}}
      >
        <defs>
          <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1FA6A0" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#0C4F55" stopOpacity="0.15" />
          </linearGradient>
        </defs>
        <g transform={`rotate(${rot} 1000 540)`}>
          {/* Stylized Finland silhouette (abstract topographic glass) */}
          <path
            d="M980 160 C1020 180, 1060 240, 1050 320 C1080 380, 1100 460, 1090 540 C1110 620, 1080 720, 1040 800 C1000 880, 940 900, 900 840 C860 760, 880 660, 870 560 C850 460, 880 360, 900 280 C920 210, 940 160, 980 160 Z"
            fill="url(#glass)"
            stroke={COLORS.cyan}
            strokeWidth={2}
            opacity={0.85}
          />
          {counties.map((c, i) => {
            const on = ((frame + i * 9) % 60) < 28;
            return (
              <g key={i}>
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={c.r}
                  fill={c.c}
                  opacity={on ? 0.35 * pulse : 0.12}
                />
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={4}
                  fill={COLORS.text}
                  opacity={0.9}
                />
              </g>
            );
          })}
        </g>
        <text
          x={320}
          y={860}
          fill={COLORS.muted}
          fontFamily="Sora, sans-serif"
          fontSize={22}
        >
          23 wellbeing services counties · synthetic telemetry
        </text>
      </svg>
    </AbsoluteFill>
  );
};
