import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {RuralIsolation} from "../broll/RuralIsolation";
import {FilmGrain} from "../components/FilmGrain";
import {COLORS} from "../theme";

export const OpeningHook: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const line1 = spring({
    frame: frame - 12,
    fps,
    config: {damping: 18, stiffness: 90},
  });
  const line2 = spring({
    frame: frame - 70,
    fps,
    config: {damping: 18, stiffness: 90},
  });
  const brand = spring({
    frame: frame - 140,
    fps,
    config: {damping: 16, stiffness: 80},
  });

  const line1Y = interpolate(line1, [0, 1], [40, 0]);
  const line2Y = interpolate(line2, [0, 1], [40, 0]);
  const brandY = interpolate(brand, [0, 1], [30, 0]);

  return (
    <AbsoluteFill>
      <RuralIsolation />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(7,19,26,0.78) 0%, rgba(7,19,26,0.35) 55%, rgba(7,19,26,0.55) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          paddingLeft: 120,
          paddingRight: 120,
        }}
      >
        <div
          style={{
            opacity: line1,
            transform: `translateY(${line1Y}px)`,
            color: COLORS.text,
            fontFamily: "Fraunces, serif",
            fontSize: 72,
            lineHeight: 1.12,
            maxWidth: 1100,
            fontWeight: 550,
            letterSpacing: "-0.02em",
          }}
        >
          Survival shouldn&apos;t depend on your postal code or age
        </div>
        <div
          style={{
            marginTop: 28,
            opacity: line2,
            transform: `translateY(${line2Y}px)`,
            color: COLORS.cyan,
            fontFamily: "Sora, sans-serif",
            fontSize: 28,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          Equal care across Finland
        </div>
        <div
          style={{
            marginTop: 64,
            opacity: brand,
            transform: `translateY(${brandY}px)`,
            display: "flex",
            alignItems: "baseline",
            gap: 18,
          }}
        >
          <span
            style={{
              fontFamily: "Sora, sans-serif",
              fontSize: 54,
              fontWeight: 700,
              color: COLORS.text,
              letterSpacing: "-0.03em",
            }}
          >
            SILTA
          </span>
          <span
            style={{
              fontFamily: "Sora, sans-serif",
              fontSize: 36,
              color: COLORS.amber,
            }}
          >
            ×
          </span>
          <span
            style={{
              fontFamily: "Sora, sans-serif",
              fontSize: 42,
              fontWeight: 500,
              color: COLORS.muted,
            }}
          >
            Thriver Care
          </span>
        </div>
      </AbsoluteFill>
      <FilmGrain opacity={0.1} />
    </AbsoluteFill>
  );
};
