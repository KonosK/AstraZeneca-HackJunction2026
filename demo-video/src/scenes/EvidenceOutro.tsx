import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {FinlandTelemetry} from "../broll/FinlandTelemetry";
import {FilmGrain} from "../components/FilmGrain";
import {COLORS} from "../theme";

const STATS = [
  {label: "23 Wellbeing Services Counties", delay: 10},
  {label: "THL & Finnish Cancer Registry Data", delay: 55},
  {
    label: "National Cancer Strategy 2026–2035 · Goal 3",
    delay: 100,
  },
] as const;

export const EvidenceOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const logo = spring({
    frame: frame - 220,
    fps,
    config: {damping: 14, stiffness: 80},
  });

  return (
    <AbsoluteFill>
      <FinlandTelemetry />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(7,19,26,0.35), rgba(7,19,26,0.82))",
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          gap: 20,
          padding: 80,
        }}
      >
        {STATS.map((stat) => {
          const enter = spring({
            frame: frame - stat.delay,
            fps,
            config: {damping: 16, stiffness: 95},
          });
          return (
            <div
              key={stat.label}
              style={{
                opacity: enter,
                transform: `translateY(${interpolate(enter, [0, 1], [36, 0])}px) scale(${interpolate(enter, [0, 1], [0.96, 1])})`,
                padding: "20px 36px",
                borderRadius: 18,
                background: COLORS.glass,
                border: "1px solid rgba(126,224,214,0.25)",
                backdropFilter: "blur(12px)",
                color: COLORS.text,
                fontFamily: "Fraunces, serif",
                fontSize: 40,
                textAlign: "center",
                maxWidth: 1280,
              }}
            >
              {stat.label}
            </div>
          );
        })}

        <div
          style={{
            marginTop: 48,
            opacity: logo,
            transform: `scale(${interpolate(logo, [0, 1], [0.92, 1])})`,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontFamily: "Sora, sans-serif",
              fontSize: 64,
              fontWeight: 700,
              letterSpacing: "-0.03em",
              color: COLORS.text,
            }}
          >
            SILTA <span style={{color: COLORS.amber}}>×</span> Thriver Care
          </div>
          <div
            style={{
              marginTop: 14,
              fontFamily: "Sora, sans-serif",
              fontSize: 24,
              color: COLORS.cyan,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
            }}
          >
            Equal care across Finland
          </div>
          <div
            style={{
              marginTop: 28,
              width: 72,
              height: 3,
              marginLeft: "auto",
              marginRight: "auto",
              background: `linear-gradient(90deg, ${COLORS.teal}, ${COLORS.amber})`,
              opacity: logo,
            }}
          />
        </div>
      </AbsoluteFill>
      <FilmGrain opacity={0.08} />
    </AbsoluteFill>
  );
};
