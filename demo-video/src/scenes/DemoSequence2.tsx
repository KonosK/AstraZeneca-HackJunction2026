import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {FilmGrain} from "../components/FilmGrain";
import {MacBrowserFrame} from "../components/MacBrowserFrame";
import {COLORS} from "../theme";

export const DemoSequence2: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const punch = spring({
    frame: frame - 12,
    fps,
    config: {damping: 16, stiffness: 90},
  });
  const toDash = spring({
    frame: frame - 10 * fps,
    fps,
    config: {damping: 18, stiffness: 70},
  });

  return (
    <AbsoluteFill style={{background: COLORS.bg}}>
      <Sequence durationInFrames={Math.round(10.2 * fps)} layout="none">
        <MacBrowserFrame
          url="127.0.0.1:8001/doctor · APOTTI clinical workspace"
          scale={interpolate(punch, [0, 1], [1.04, 1.2])}
          translateY={interpolate(frame, [0, 10 * fps], [18, -54], {
            extrapolateRight: "clamp",
          })}
        >
          <Sequence durationInFrames={Math.round(4.5 * fps)}>
            <AbsoluteFill>
              <OffthreadVideo
                src={staticFile("screen/apotti_brief.mp4")}
                style={{width: "100%", height: "100%", objectFit: "cover"}}
              />
            </AbsoluteFill>
          </Sequence>
          <Sequence from={Math.round(4.5 * fps)}>
            <AbsoluteFill>
              <OffthreadVideo
                src={staticFile("screen/apotti_proposals.mp4")}
                style={{width: "100%", height: "100%", objectFit: "cover"}}
              />
            </AbsoluteFill>
          </Sequence>
          <Callout
            title="Structured clinical brief"
            body="SHAP county contributors · fast-track proposals for human review"
            top={40}
            left={40}
          />
        </MacBrowserFrame>
      </Sequence>

      <Sequence from={Math.round(10 * fps)} layout="none">
        <MacBrowserFrame
          url="127.0.0.1:8001/dashboard · 23-County RF + SHAP"
          scale={interpolate(toDash, [0, 1], [1.1, 1.0])}
          translateY={interpolate(toDash, [0, 1], [-28, 0])}
        >
          <Sequence durationInFrames={Math.round(6 * fps)}>
            <AbsoluteFill>
              <OffthreadVideo
                src={staticFile("screen/dashboard_map.mp4")}
                style={{width: "100%", height: "100%", objectFit: "cover"}}
              />
            </AbsoluteFill>
          </Sequence>
          <Sequence from={Math.round(6 * fps)}>
            <AbsoluteFill>
              <OffthreadVideo
                src={staticFile("screen/dashboard_strategy.mp4")}
                style={{width: "100%", height: "100%", objectFit: "cover"}}
              />
            </AbsoluteFill>
          </Sequence>
          <Callout
            title="Lapland Strategy §3.4"
            body="County drivers mapped to National Cancer Strategy Goal 3"
            top={40}
            right={40}
          />
        </MacBrowserFrame>
      </Sequence>
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

const Callout: React.FC<{
  title: string;
  body: string;
  top?: number;
  left?: number;
  right?: number;
}> = ({title, body, top = 40, left, right}) => (
  <AbsoluteFill style={{pointerEvents: "none"}}>
    <div
      style={{
        position: "absolute",
        top,
        left,
        right,
        maxWidth: 520,
        padding: "16px 20px",
        borderRadius: 16,
        background: "rgba(7,19,26,0.78)",
        border: "1px solid rgba(126,224,214,0.28)",
        backdropFilter: "blur(10px)",
        color: COLORS.text,
        fontFamily: "Sora, sans-serif",
      }}
    >
      <div style={{fontSize: 22, fontWeight: 600, color: COLORS.cyan}}>
        {title}
      </div>
      <div style={{marginTop: 6, fontSize: 18, color: COLORS.muted}}>
        {body}
      </div>
    </div>
  </AbsoluteFill>
);
