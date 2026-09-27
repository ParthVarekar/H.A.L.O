import React from "react";
import { Composition, registerRoot } from "remotion";
import { IntroVideo } from "./IntroVideo.jsx";

const RemotionRoot = () => {
  return (
    <Composition
      id="IntroVideo"
      component={IntroVideo}
      durationInFrames={270}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};

registerRoot(RemotionRoot);
