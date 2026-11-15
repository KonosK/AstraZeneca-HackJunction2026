import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {Captions} from "../components/Captions";
import {FilmGrain} from "../components/FilmGrain";
import {MacBrowserFrame} from "../components/MacBrowserFrame";
import {CALL_CUES, CALL_MONTAGE_DURATION_SEC} from "../data/callCaptions";
import {COLORS, TIMING} from "../theme";

export const DemoSequence1: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Start call as soon as Maisa is on screen, while keeping the full montage in-scene
  const callAudioFrom = Math.min(
    Math.round(5.8 * fps),
    Math.max(0, TIMING.demo1 - Math.ceil(CALL_MONTAGE_DURATION_SEC * fps) - 1),
  );

  const baselineScale = interpolate(frame, [0, 5.5 * fps], [1.02, 1.14], {
    extrapolateRight: "clamp",
  });
  const maisaEnter = spring({
    frame: frame - Math.round(5.5 * fps),
    fps,
    config: {damping: 18, stiffness: 70},
  });

  return (
    <AbsoluteFill style={{background: COLORS.bg}}>
      <Sequence durationInFrames={Math.round(5.8 * fps)}>
        <MacBrowserFrame
          url="127.0.0.1:8001/simulation · Without SILTA"
          scale={baselineScale}
          translateY={interpolate(frame, [0, 5.5 * fps], [10, -24], {
            extrapolateRight: "clamp",
          })}
        >
          <OffthreadVideo
            src={staticFile("screen/baseline.mp4")}
            style={{width: "100%", height: "100%", objectFit: "cover"}}
          />
          <AbsoluteFill
            style={{
              justifyContent: "flex-start",
              alignItems: "flex-start",
              padding: 36,
            }}
          >
            <div
              style={{
                background: "rgba(7,19,26,0.78)",
                border: "1px solid rgba(224,106,106,0.45)",
                borderRadius: 14,
                padding: "14px 18px",
                color: COLORS.text,
                fontFamily: "Sora, sans-serif",
                fontSize: 26,
              }}
            >
              Fragmented baseline ·{" "}
              <span style={{color: COLORS.danger}}>78 fictional days</span>
            </div>
          </AbsoluteFill>
        </MacBrowserFrame>
      </Sequence>

      <Sequence from={Math.round(5.5 * fps)}>
        <MacBrowserFrame
          url="127.0.0.1:8001/patient · Maisa · Call My Phone"
          scale={interpolate(maisaEnter, [0, 1], [1.06, 1.18])}
          translateY={interpolate(maisaEnter, [0, 1], [28, -36])}
        >
          <OffthreadVideo
            src={staticFile("screen/maisa_call.mp4")}
            style={{width: "100%", height: "100%", objectFit: "cover"}}
          />
          <AbsoluteFill
            style={{
              justifyContent: "flex-start",
              alignItems: "flex-end",
              padding: 36,
            }}
          >
            <div
              style={{
                background: "rgba(80, 60, 120, 0.82)",
                borderRadius: 14,
                padding: "12px 18px",
                color: "white",
                fontFamily: "Sora, sans-serif",
                fontSize: 24,
                boxShadow: "0 0 30px rgba(126,100,200,0.35)",
              }}
            >
              Call My Phone · live speakerphone
            </div>
          </AbsoluteFill>
        </MacBrowserFrame>
      </Sequence>

      <Sequence from={callAudioFrom}>
        <AbsoluteFill>
          <Audio src={staticFile("audio/call_montage.mp3")} volume={0.95} />
          <Captions cues={CALL_CUES} />
        </AbsoluteFill>
      </Sequence>

      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};
