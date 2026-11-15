import React from "react";
import {Audio, Sequence, AbsoluteFill, staticFile} from "remotion";
import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {loadFont as loadSora} from "@remotion/google-fonts/Sora";
import {loadFont as loadFraunces} from "@remotion/google-fonts/Fraunces";
import {OpeningHook} from "./scenes/OpeningHook";
import {ArchitectureReveal} from "./scenes/ArchitectureReveal";
import {DemoSequence1} from "./scenes/DemoSequence1";
import {DemoSequence2} from "./scenes/DemoSequence2";
import {EvidenceOutro} from "./scenes/EvidenceOutro";
import {COLORS, FPS, TIMING, VO_LAYERS_SECONDS} from "./theme";

loadSora("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
  ignoreTooManyRequestsWarning: true,
});
loadFraunces("normal", {
  weights: ["500", "600"],
  subsets: ["latin"],
  ignoreTooManyRequestsWarning: true,
});

export const SiltaCinema: React.FC = () => {
  const fadeTiming = linearTiming({durationInFrames: TIMING.fade});

  // Absolute start of evidence outro on the TransitionSeries timeline
  const outroFrom =
    TIMING.hook +
    TIMING.architecture +
    TIMING.demo1 +
    TIMING.demo2 -
    TIMING.fade * 4;

  return (
    <AbsoluteFill style={{backgroundColor: COLORS.bg}}>
      <TransitionSeries>
        <TransitionSeries.Sequence
          name="Opening Hook"
          durationInFrames={TIMING.hook}
        >
          <OpeningHook />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={fadeTiming} />

        <TransitionSeries.Sequence
          name="Architecture"
          durationInFrames={TIMING.architecture}
        >
          <ArchitectureReveal />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={fadeTiming} />

        <TransitionSeries.Sequence
          name="Demo · Voice Intake"
          durationInFrames={TIMING.demo1}
        >
          <DemoSequence1 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={fadeTiming} />

        <TransitionSeries.Sequence
          name="Demo · Apotti + Dashboard"
          durationInFrames={TIMING.demo2}
        >
          <DemoSequence2 />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={fadeTiming} />

        <TransitionSeries.Sequence
          name="Evidence Outro"
          durationInFrames={TIMING.outro}
        >
          <EvidenceOutro />
        </TransitionSeries.Sequence>
      </TransitionSeries>

      {/* Full layer explanation plays once, unbroken, then stops cleanly */}
      <Sequence from={0} durationInFrames={VO_LAYERS_SECONDS * FPS} layout="none">
        <Audio src={staticFile("audio/vo_part_a.mp3")} volume={0.9} />
      </Sequence>

      {/* Evidence / lockup VO only on the outro — no mid-layer resume */}
      <Sequence from={outroFrom} layout="none">
        <Audio src={staticFile("audio/vo_part_b.mp3")} volume={0.88} />
      </Sequence>
    </AbsoluteFill>
  );
};
