import { Composition } from "remotion";

import { INTRO_FRAMES, Intro } from "./Intro";
import { PITCH_FRAMES, Pitch } from "./pitch/Pitch";
import { LAUNCH_FRAMES, Launch } from "./launch/Launch";
import { FPS, HEIGHT, WIDTH } from "./theme";

export function RemotionRoot() {
  return (
    <>
      <Composition id="Launch" component={Launch} durationInFrames={LAUNCH_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
      <Composition id="Pitch" component={Pitch} durationInFrames={PITCH_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
      <Composition id="Intro" component={Intro} durationInFrames={INTRO_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
    </>
  );
}
