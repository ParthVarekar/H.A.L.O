import { Composition } from "remotion";

import { INTRO_FRAMES, Intro } from "./Intro";
import { FPS, HEIGHT, WIDTH } from "./theme";

export function RemotionRoot() {
  return (
    <>
      <Composition id="Intro" component={Intro} durationInFrames={INTRO_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
    </>
  );
}
