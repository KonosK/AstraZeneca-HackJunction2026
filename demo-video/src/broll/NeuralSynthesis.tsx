import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {COLORS} from "../theme";

/** Procedural stand-in for fal Shot 2 — voice waveform → clinical data nodes. */
export const NeuralSynthesis: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 40% 50%, #0E3A42 0%, #061018 60%, #04090D 100%)",
        overflow: "hidden",
      }}
    >
      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{position: "absolute", inset: 0}}
      >
        <defs>
          <linearGradient id="stream" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={COLORS.cyan} stopOpacity="0.1" />
            <stop offset="50%" stopColor={COLORS.teal} stopOpacity="0.9" />
            <stop offset="100%" stopColor={COLORS.amber} stopOpacity="0.7" />
          </linearGradient>
          <filter id="soft">
            <feGaussianBlur stdDeviation="2.2" />
          </filter>
        </defs>
        {/* Waveform */}
        {Array.from({length: 64}).map((_, i) => {
          const h =
            18 +
            Math.abs(Math.sin(frame / 9 + i * 0.35)) * 70 +
            Math.abs(Math.sin(frame / 5 + i * 0.2)) * 40;
          return (
            <rect
              key={`w-${i}`}
              x={120 + i * 10}
              y={540 - h / 2}
              width={5}
              height={h}
              rx={2}
              fill={COLORS.cyan}
              opacity={0.35 + (i % 5) * 0.08}
            />
          );
        })}
        {/* Neural streams */}
        {Array.from({length: 7}).map((_, i) => {
          const y = 280 + i * 80;
          const phase = interpolate(frame % 90, [0, 90], [0, 1]);
          return (
            <g key={`s-${i}`} filter="url(#soft)">
              <path
                d={`M 760 ${y} C 980 ${y - 40}, 1180 ${y + 50}, 1480 ${320 + i * 70}`}
                stroke="url(#stream)"
                strokeWidth={2.5}
                fill="none"
                strokeDasharray="12 10"
                strokeDashoffset={-phase * 120 - i * 20}
                opacity={0.75}
              />
              <circle
                cx={1480}
                cy={320 + i * 70}
                r={8 + (i % 3)}
                fill={i % 2 === 0 ? COLORS.amber : COLORS.cyan}
                opacity={0.85}
              />
            </g>
          );
        })}
        {/* Data nodes label rings */}
        {["FHIR", "SHAP", "BRIEF"].map((label, i) => (
          <g key={label}>
            <circle
              cx={1580}
              cy={360 + i * 140}
              r={46}
              fill="rgba(12,79,85,0.45)"
              stroke={COLORS.cyan}
              strokeWidth={1.5}
            />
            <text
              x={1580}
              y={366 + i * 140}
              textAnchor="middle"
              fill={COLORS.text}
              fontFamily="Sora, sans-serif"
              fontSize={18}
            >
              {label}
            </text>
          </g>
        ))}
      </svg>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 70% 40%, transparent 0%, rgba(4,9,13,0.45) 70%)",
        }}
      />
    </AbsoluteFill>
  );
};
