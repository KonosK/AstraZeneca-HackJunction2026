import React from "react";
import {AbsoluteFill} from "remotion";
import {COLORS} from "../theme";

export const MacBrowserFrame: React.FC<{
  children: React.ReactNode;
  url?: string;
  scale?: number;
  translateY?: number;
}> = ({
  children,
  url = "127.0.0.1:8001",
  scale = 1,
  translateY = 0,
}) => {
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background:
          "radial-gradient(ellipse at 50% 20%, #132832 0%, #060E14 70%)",
      }}
    >
      <div
        style={{
          width: 1680,
          height: 980,
          transform: `translateY(${translateY}px) scale(${scale})`,
          transformOrigin: "center center",
          borderRadius: 18,
          overflow: "hidden",
          boxShadow:
            "0 40px 100px rgba(0,0,0,0.55), 0 0 0 1px rgba(126,224,214,0.12)",
          background: COLORS.slate,
        }}
      >
        <div
          style={{
            height: 42,
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "0 16px",
            background: "linear-gradient(180deg, #24343E, #1A2730)",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <span style={dot("#FF5F57")} />
          <span style={dot("#FEBC2E")} />
          <span style={dot("#28C840")} />
          <div
            style={{
              marginLeft: 18,
              flex: 1,
              height: 24,
              borderRadius: 7,
              background: "rgba(0,0,0,0.28)",
              color: "rgba(255,255,255,0.55)",
              fontSize: 13,
              fontFamily: "Sora, sans-serif",
              display: "flex",
              alignItems: "center",
              padding: "0 12px",
            }}
          >
            {url}
          </div>
        </div>
        <div style={{position: "relative", width: "100%", height: 938}}>
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const dot = (color: string): React.CSSProperties => ({
  width: 11,
  height: 11,
  borderRadius: 99,
  background: color,
  display: "inline-block",
});
