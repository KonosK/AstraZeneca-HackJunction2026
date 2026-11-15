import React from "react";
import {Composition} from "remotion";
import {SiltaCinema} from "./SiltaCinema";
import {DURATION_FRAMES, FPS} from "./theme";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SiltaCinema"
        component={SiltaCinema}
        durationInFrames={DURATION_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
