import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {COLORS} from "../theme";

export type CaptionCue = {
  start: number;
  end: number;
  text: string;
};

export const Captions: React.FC<{cues: CaptionCue[]}> = ({cues}) => {
  const frame = useCurrentFrame();
  const active = cues.find((c) => frame >= c.start && frame < c.end);
  if (!active) return null;

  const dur = Math.max(1, active.end - active.start);
  const local = frame - active.start;
  const fadeIn = Math.min(6, Math.floor(dur / 4));
  const fadeOut = Math.min(6, Math.floor(dur / 4));
  const opacity = interpolate(
    local,
    [0, fadeIn, Math.max(fadeIn + 1, dur - fadeOut), dur],
    [0, 1, 1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 72,
        pointerEvents: "none",
        zIndex: 20,
      }}
    >
      <div
        style={{
          opacity,
          maxWidth: 1400,
          padding: "16px 28px",
          borderRadius: 16,
          background: "rgba(7, 19, 26, 0.78)",
          border: "1px solid rgba(126, 224, 214, 0.22)",
          backdropFilter: "blur(10px)",
          color: COLORS.text,
          fontFamily: "Sora, sans-serif",
          fontSize: 28,
          lineHeight: 1.35,
          textAlign: "center",
          boxShadow: "0 18px 50px rgba(0,0,0,0.35)",
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
