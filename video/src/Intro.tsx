import type { ComponentType, ReactNode } from "react";
import { AbsoluteFill, Audio, Easing, Freeze, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

import { Backdrop, type Hold, RealTime, clamp, forwardFrame, remapFrame } from "./components";
import {
  CloseScene,
  DescribeScene,
  GuideScene,
  LATE_AT,
  LogoScene,
  VOICE_AT,
  VOICE_FRAMES,
  OfflineScene,
  ProcedureScene,
  RecordScene,
  SKIP_AT,
  SeesScene,
  SkipScene,
} from "./scenes";
import { color, font, loadFonts } from "./theme";

const fontsReady = delayRender("Loading fonts");
loadFonts().then(() => continueRender(fontsReady));

const OVERLAP = 12;

type Cue = { at: number; sound: string; volume?: number };
type SceneSpec = { name: string; frames: number; Scene: ComponentType; cues: Cue[]; holds?: Hold[] };

const SCENES: SceneSpec[] = [
  { name: "procedure", frames: 135, Scene: ProcedureScene, cues: [{ at: 80, sound: "whoosh", volume: 0.35 }], holds: [{ at: 56, frames: 30 }, { at: 108, frames: 30 }] },
  { name: "logo", frames: 85, Scene: LogoScene, cues: [{ at: 0, sound: "impact", volume: 0.8 }, { at: 22, sound: "chime", volume: 0.35 }], holds: [{ at: 50, frames: 30 }] },
  { name: "sees", frames: 264, Scene: SeesScene, cues: [{ at: 8, sound: "scan", volume: 0.4 }] },
  {
    name: "guide",
    frames: 175,
    Scene: GuideScene,
    cues: [...[8, 18, 120, 132, 144].map((at) => ({ at, sound: "tick", volume: 0.5 })), { at: VOICE_AT, sound: "voice", volume: 1 }],
    holds: [{ at: 34, frames: 24 }, { at: 156, frames: 26 }],
  },
  {
    name: "skip",
    frames: 125,
    Scene: SkipScene,
    cues: [
      { at: 24, sound: "tick", volume: 0.5 },
      { at: SKIP_AT, sound: "alert", volume: 0.55 },
      { at: LATE_AT, sound: "alert", volume: 0.4 },
    ],
    holds: [{ at: 52, frames: 30 }, { at: 100, frames: 30 }],
  },
  { name: "describe", frames: 120, Scene: DescribeScene, cues: [{ at: 82, sound: "tick", volume: 0.6 }], holds: [{ at: 55, frames: 18 }, { at: 100, frames: 28 }] },
  { name: "offline", frames: 110, Scene: OfflineScene, cues: [{ at: 28, sound: "tick", volume: 0.4 }], holds: [{ at: 64, frames: 30 }] },
  {
    name: "record",
    frames: 150,
    Scene: RecordScene,
    cues: [
      { at: 60, sound: "whoosh", volume: 0.4 },
      { at: 88, sound: "chime", volume: 0.45 },
    ],
    holds: [{ at: 52, frames: 24 }, { at: 128, frames: 30 }],
  },
  { name: "close", frames: 105, Scene: CloseScene, cues: [{ at: 0, sound: "impact", volume: 0.6 }], holds: [{ at: 50, frames: 20 }] },
];

const held = (scene: SceneSpec) => scene.frames + (scene.holds ?? []).reduce((total, hold) => total + hold.frames, 0);
const STARTS = SCENES.map((_, index) => SCENES.slice(0, index).reduce((total, scene) => total + held(scene) - OVERLAP, 0));
export const INTRO_FRAMES = STARTS[STARTS.length - 1] + held(SCENES[SCENES.length - 1]);
const GUIDE = SCENES.findIndex((scene) => scene.name === "guide");
const VOICE_START = STARTS[GUIDE] + forwardFrame(VOICE_AT, SCENES[GUIDE].holds ?? []);

function Remap({ holds, children }: { holds: Hold[]; children: ReactNode }) {
  const frame = useCurrentFrame();
  return (
    <RealTime.Provider value={{ frame, holds }}>
      <Freeze frame={remapFrame(frame, holds)}>{children}</Freeze>
    </RealTime.Provider>
  );
}

function Dolly({ children, first, last }: { children: ReactNode; first: boolean; last: boolean }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const enter = first ? 1 : interpolate(frame, [5, OVERLAP + 8], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const exitLength = last ? 24 : OVERLAP;
  const exit = interpolate(frame, [durationInFrames - exitLength, durationInFrames - (last ? 0 : 4)], [0, 1], { ...clamp, easing: Easing.in(Easing.quad) });
  const scale = (0.9 + enter * 0.1) * (1 + exit * (last ? 0 : 0.14));
  const blur = (1 - enter) * 18 + exit * (last ? 0 : 18);
  return (
    <AbsoluteFill style={{ opacity: enter * (1 - exit), transform: `scale(${scale})`, filter: blur > 0.1 ? `blur(${blur}px)` : undefined }}>
      {children}
    </AbsoluteFill>
  );
}

export function Intro() {
  return (
    <AbsoluteFill style={{ fontFamily: font.text, color: color.text }}>
      <Backdrop />
      <Audio
        src={staticFile("audio/pad.m4a")}
        volume={(frame) => {
          const level = interpolate(frame, [0, 30, INTRO_FRAMES - 45, INTRO_FRAMES], [0, 0.2, 0.2, 0], clamp);
          const duck = interpolate(frame, [VOICE_START - 8, VOICE_START, VOICE_START + VOICE_FRAMES - 5, VOICE_START + VOICE_FRAMES + 7], [1, 0.4, 0.4, 1], clamp);
          return level * duck;
        }}
      />
      {SCENES.map((spec, index) => {
        const { name, Scene, cues } = spec;
        const holds = spec.holds ?? [];
        return (
        <Sequence key={name} from={STARTS[index]} durationInFrames={held(spec)} name={name}>
          <Dolly first={index === 0} last={index === SCENES.length - 1}>
            <Remap holds={holds}>
              <Scene />
            </Remap>
          </Dolly>
          {index > 0 && (
            <Sequence from={0} layout="none">
              <Audio src={staticFile("audio/sfx/whoosh.wav")} volume={0.45} />
            </Sequence>
          )}
          {cues.map((cue) => (
            <Sequence key={`${cue.sound}-${cue.at}`} from={forwardFrame(cue.at, holds)} layout="none">
              <Audio src={staticFile(cue.sound === "voice" ? "audio/voice.m4a" : `audio/sfx/${cue.sound}.wav`)} volume={cue.volume ?? 0.5} />
            </Sequence>
          ))}
        </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}
