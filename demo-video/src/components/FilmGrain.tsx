import React from "react";
import {AbsoluteFill, useCurrentFrame} from "remotion";

export const FilmGrain: React.FC<{opacity?: number}> = ({opacity = 0.08}) => {
  const frame = useCurrentFrame();
  const seed = (frame * 17) % 1000;
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        opacity,
        mixBlendMode: "overlay",
        backgroundImage: `url("data:image/svg+xml,${encodeURIComponent(
          `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>
            <filter id='n'>
              <feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='${seed}' stitchTiles='stitch'/>
            </filter>
            <rect width='100%' height='100%' filter='url(#n)' opacity='0.55'/>
          </svg>`,
        )}")`,
        backgroundSize: "180px 180px",
      }}
    />
  );
};
