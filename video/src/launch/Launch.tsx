import {
  AbsoluteFill,
  Audio,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { launchColor as c } from "./palette";
import { BackdropWash, Grain, Stage, Vignette, clamp, smooth, useSpring } from "./fx";
import { Bubbles, Chip, Hatch, Halo, Slab, Tray } from "./world";
import { Beam3D, DetectBox, Line3D, Mark, ScanSweep, detectIcon } from "./ui";
import { HEIGHT, WIDTH, loadFonts } from "../theme";

const ready = delayRender("Loading launch fonts");
loadFonts().then(() => continueRender(ready));

const FRAMES = 288;

type Key = { f: number; x: number; y: number; z: number; rx: number; ry: number; focus: number };

const KEYS: Key[] = [
  { f: 0, x: 0, y: 0, z: 780, rx: 0, ry: 0, focus: 0 },
  { f: 40, x: -110, y: 40, z: 520, rx: 5, ry: -24, focus: 0 },
  { f: 78, x: 150, y: -30, z: 350, rx: -4, ry: 30, focus: -260 },
  { f: 94, x: -60, y: 16, z: -170, rx: 3, ry: -26, focus: 0 },
  { f: 140, x: -170, y: -40, z: -30, rx: -3, ry: 22, focus: 0 },
  { f: 186, x: 60, y: -84, z: 190, rx: 4, ry: -14, focus: -170 },
  { f: 214, x: 0, y: 0, z: 660, rx: 0, ry: 0, focus: 0 },
  { f: 288, x: 0, y: 0, z: 720, rx: 0, ry: 0, focus: 0 },
];

function cameraAt(frame: number) {
  let a = KEYS[0];
  let b = KEYS[1];
  for (let i = 0; i < KEYS.length - 1; i += 1) {
    if (frame >= KEYS[i].f && frame <= KEYS[i + 1].f) {
      a = KEYS[i];
      b = KEYS[i + 1];
      break;
    }
    if (frame > KEYS[KEYS.length - 1].f) {
      a = KEYS[KEYS.length - 1];
      b = a;
    }
  }
  const span = b.f - a.f;
  const t = span <= 0 ? 0 : smooth(frame, a.f, b.f);
  const lerp = (p: "x" | "y" | "z" | "rx" | "ry" | "focus") => a[p] + (b[p] - a[p]) * t;
  return { x: lerp("x"), y: lerp("y"), z: lerp("z"), rx: lerp("rx"), ry: lerp("ry"), focus: lerp("focus") };
}

const CHIPS = [
  { label: "dewar_hatch", sub: "OPEN", tone: c.accent, icon: detectIcon("hatch"), angle: -2.62, at: 92 },
  { label: "tray_2", sub: "OUT", tone: c.accent, icon: detectIcon("tray"), angle: -1.92, at: 97 },
  { label: "compartment_1", sub: "OPEN", tone: c.ok, icon: detectIcon("box"), angle: -1.22, at: 107 },
  { label: "sample", sub: "PLACED", tone: c.ok, icon: detectIcon("pouch"), angle: -0.52, at: 102 },
  { label: "dewar_latch", sub: "LEFT", tone: c.accent, icon: detectIcon("latch"), angle: 0.18, at: 112 },
  { label: "astronaut", sub: "VISIBLE", tone: c.accent, icon: detectIcon("person"), angle: 0.88, at: 122 },
  { label: "ice_vapor", sub: "TRACKED", tone: c.warn, icon: detectIcon("vapour"), angle: 1.58, at: 117 },
  { label: "8 / 8", sub: "STEPS", tone: c.ok, icon: detectIcon("check"), angle: 2.28, at: 127 },
  { label: "1.00×", sub: "REAL TIME", tone: c.accent, icon: detectIcon("gauge"), angle: 2.98, at: 132 },
];

const RING_X = 520;
const RING_Y = 312;
const RING_Z = 230;

const BOXES = [
  { label: "dewar_hatch", conf: 0.94, w: 312, h: 312, x: -70, y: -87, z: 44, at: 98, tone: c.accent },
  { label: "compartment_1", conf: 0.88, w: 238, h: 238, x: -34, y: -60, z: 80, at: 114, tone: c.ok },
  { label: "tray_2", conf: 0.92, w: 452, h: 122, x: 150, y: -87, z: 64, at: 106, tone: c.accent },
  { label: "sample", conf: 0.81, w: 110, h: 130, x: 128, y: -212, z: 98, at: 122, tone: c.ok },
];

export function Launch() {
  const frame = useCurrentFrame();
  const cam = cameraAt(frame);

  const cold = interpolate(frame, [0, 74, 92, 200], [1, 1, 0, 0], clamp);
  const flash = interpolate(frame, [78, 84, 96], [0, 0.92, 0], clamp);
  const fadeIn = interpolate(frame, [0, 12], [0, 1], clamp);
  const fadeOut = interpolate(frame, [280, 288], [1, 0], clamp);
  const worldFade = interpolate(frame, [196, 222], [1, 0], clamp);
  const rush = smooth(frame, 196, 224);
  const warm = interpolate(frame, [86, 116], [0, 1], clamp);

  const hatchOpen = interpolate(frame, [16, 44], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 2 });
  const trayPull = interpolate(frame, [32, 60], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 2 });
  const trayReturn = interpolate(frame, [88, 116], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 2 });
  const trayOut = trayPull - trayReturn;
  const alertAt = 48;
  const alertPulse = frame > alertAt ? 0.5 + 0.5 * Math.sin(frame / 6) : 0;
  const caughtAt = 150;
  const shake = frame > alertAt && frame < 14 + caughtAt ? Math.sin(frame * 2.4) * Math.max(0, 1 - (frame - alertAt) / 40) * 7 : 0;

  const heroSpin = interpolate(frame, [0, 288], [-9, 15], clamp);
  const heroY = -70;
  const hatchY = heroY - 17;
  const trayX = -170 + trayOut * 420;
  const trayZ = -95 + trayOut * 150;
  const rushZ = rush * 1500;

  return (
    <AbsoluteFill style={{ background: c.voidWarm, overflow: "hidden" }}>
      <Audio
        src={staticFile("audio/pad.m4a")}
        volume={(f) => interpolate(f, [0, 24, 262, 288], [0, 0.17, 0.17, 0], clamp)}
      />
      {[
        { at: 0, sound: "impact", volume: 0.5 },
        { at: 30, sound: "whoosh", volume: 0.22 },
        { at: 78, sound: "impact", volume: 0.62 },
        { at: 84, sound: "scan", volume: 0.4 },
        { at: 92, sound: "whoosh", volume: 0.18 },
        { at: 97, sound: "tick", volume: 0.5 },
        { at: 102, sound: "tick", volume: 0.5 },
        { at: 107, sound: "tick", volume: 0.5 },
        { at: 112, sound: "tick", volume: 0.5 },
        { at: 117, sound: "tick", volume: 0.45 },
        { at: 122, sound: "tick", volume: 0.45 },
        { at: 127, sound: "tick", volume: 0.45 },
        { at: 132, sound: "tick", volume: 0.45 },
        { at: 48, sound: "alert", volume: 0.34 },
        { at: 150, sound: "alert", volume: 0.26 },
        { at: 150, sound: "chime", volume: 0.3 },
        { at: 200, sound: "whoosh", volume: 0.5 },
        { at: 212, sound: "impact", volume: 0.5 },
        { at: 220, sound: "chime", volume: 0.42 },
      ].map((cue) => (
        <Sequence key={`${cue.sound}-${cue.at}`} from={cue.at} layout="none">
          <Audio src={staticFile(`audio/sfx/${cue.sound}.wav`)} volume={cue.volume} />
        </Sequence>
      ))}
      <div style={{ position: "absolute", inset: 0, isolation: "isolate" }}>
        <BackdropWash from={warm > 0.4 ? "rgba(226,238,255,0.95)" : "rgba(206,214,226,0.95)"} to={warm > 0.4 ? "#eef4ff" : c.voidCold} />
        <AbsoluteFill style={{ opacity: fadeIn * worldFade, transform: `translateZ(${rushZ}px) scale(${1 + rush * 0.4})`, transformStyle: "preserve-3d" }}>
          <Stage cam={cam}>
            <Bubbles count={26} seed="far" warm={warm} />
            <Halo size={1700} x={-120} y={-40} z={-700} tone={warm > 0.4 ? "rgba(120,180,255,0.5)" : "rgba(150,168,196,0.4)"} opacity={0.45 + warm * 0.4} />

            <div style={{ position: "absolute", inset: 0, transformStyle: "preserve-3d", transform: `translate3d(${shake}px, 0, 0)` }}>
              <Slab w={520} h={430} d={300} x={-70} y={heroY} z={0} spin={heroSpin}>
                <div style={{ position: "absolute", inset: 0, background: "radial-gradient(120% 90% at 30% 12%, rgba(255,255,255,0.85), rgba(255,255,255,0) 58%)" }} />
                <Hatch size={286} open={hatchOpen} glowTone={frame > alertAt && frame < caughtAt ? c.warnLight : warm > 0.4 ? c.accentLight : "rgba(160,176,200,0.6)"} />
                <div style={{ position: "absolute", left: 34, bottom: 30, display: "flex", gap: 8 }}>
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} style={{ width: 26, height: 6, borderRadius: 3, background: "rgba(120,134,155,0.45)" }} />
                  ))}
                </div>
                <div style={{ position: "absolute", right: 30, top: 26, fontFamily: "JetBrains Mono", fontSize: 17, fontWeight: 700, letterSpacing: "0.16em", color: "rgba(90,104,126,0.75)" }}>
                  MELFI
                </div>
              </Slab>

              <Tray w={430} h={108} x={trayX} y={hatchY} z={trayZ} pull={trayOut} spin={heroSpin} />

              <ScanSweep at={86} tone={c.accent} size={2200} />

              {CHIPS.map((chip) => (
                <Chip
                  key={chip.label}
                  at={chip.at}
                  angle={chip.angle}
                  orbitX={RING_X}
                  orbitY={RING_Y}
                  orbitZ={RING_Z}
                  label={chip.label}
                  sub={chip.sub}
                  tone={chip.tone}
                  icon={chip.icon}
                  seed={chip.label}
                  emphasis={frame > caughtAt ? 1 : 0}
                />
              ))}

              {BOXES.map((box) => (
                <DetectBox key={box.label} {...box} />
              ))}
            </div>
          </Stage>
        </AbsoluteFill>

        <AbsoluteFill style={{ perspective: 1700 }}>
          <AlertCard at={alertAt} caughtAt={caughtAt} pulse={alertPulse} />
        </AbsoluteFill>

        <AbsoluteFill style={{ mixBlendMode: "saturation", opacity: cold * 0.7, background: "hsl(212,12%,46%)" }} />
        <AbsoluteFill style={{ mixBlendMode: "multiply", opacity: cold * 0.16, background: "linear-gradient(180deg,#c3cede,#94a5bd)" }} />

        <AbsoluteFill style={{ perspective: 1700, opacity: fadeIn * fadeOut }}>
          <Line3D
            text="In orbit, a missed step is gone forever."
            x={0}
            y={330}
            z={0}
            at={8}
            until={94}
            size={78}
            stagger={2.4}
            width={1720}
          />
          <Line3D
            text="BAS-HAR follows every step."
            x={0}
            y={330}
            z={0}
            at={108}
            until={146}
            size={78}
            stagger={2.4}
            width={1720}
            color={c.ink}
          />
          <Line3D
            text="And speaks the moment one is missed."
            x={0}
            y={330}
            z={0}
            at={152}
            until={206}
            size={78}
            stagger={2.4}
            width={1780}
            color={c.ink}
          />
        </AbsoluteFill>

        <AbsoluteFill style={{ opacity: fadeIn * fadeOut * (1 - worldFade) }}>
          <LogoAct frame={frame} />
        </AbsoluteFill>

        <AbsoluteFill style={{ opacity: flash, mixBlendMode: "screen", background: `radial-gradient(70% 60% at 50% 48%, rgba(255,255,255,0.98), rgba(214,230,255,0.5) 60%, transparent 78%)` }} />
        <Grain opacity={0.045} />
        <Vignette strength={0.16 + cold * 0.14} />
        <AbsoluteFill style={{ opacity: (1 - fadeIn) + (1 - fadeOut), background: c.white }} />
      </div>
    </AbsoluteFill>
  );
}

function AlertCard({ at, caughtAt, pulse }: { at: number; caughtAt: number; pulse: number }) {
  const frame = useCurrentFrame();
  const caught = frame >= caughtAt;
  const tone = caught ? c.ok : c.warn;
  const enter = useSpring(at, 13, 0.75, 120);
  const flip = interpolate(frame, [caughtAt, caughtAt + 12], [0, 1], clamp);
  const out = interpolate(frame, [180, 194], [1, 0], clamp);
  const pop = interpolate(enter, [0, 1], [0.86, 1], clamp);
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: 128,
        marginLeft: -290,
        opacity: enter * out,
        transform: `translateY(${(1 - enter) * -34}px) scale(${pop}) rotateY(${(1 - enter) * -18}deg)`,
        transformOrigin: "50% 50%",
      }}
    >
      <div
        style={{
          position: "relative",
          width: 580,
          height: 116,
          borderRadius: 24,
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "0 28px",
          boxSizing: "border-box",
          background: caught ? "rgba(238,253,246,0.96)" : "rgba(255,248,238,0.96)",
          border: `1.5px solid ${tone}59`,
          boxShadow: `0 40px 74px -34px rgba(20,40,80,0.5), 0 0 40px ${tone}26, inset 0 2px 0 rgba(255,255,255,0.95)`,
          backdropFilter: "blur(10px)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 5,
            background: `linear-gradient(180deg, ${tone}, ${tone}55)`,
          }}
        />
        <div
          style={{
            width: 50,
            height: 50,
            borderRadius: 14,
            background: `${tone}1f`,
            display: "grid",
            placeItems: "center",
            color: tone,
            flexShrink: 0,
          }}
        >
          {caught ? (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={tone} strokeWidth="2.7" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="4.5 12.5 9.5 17.5 19.5 6.5" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={tone} strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          )}
        </div>
        <div style={{ flex: 1, position: "relative", height: "100%" }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              opacity: 1 - flip,
              transform: `translateY(${(1 - flip) * -22}px)`,
            }}
          >
            <div style={{ fontFamily: "JetBrains Mono", fontSize: 13, fontWeight: 700, letterSpacing: "0.17em", color: tone }}>
              STEP 3 · TRAY 2 OUT
            </div>
            <div style={{ marginTop: 7, fontFamily: "Space Grotesk", fontSize: 28, fontWeight: 650, color: c.ink, whiteSpace: "nowrap" }}>
              Missed. Sample at risk.
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              opacity: flip,
              transform: `translateY(${(1 - flip) * 22}px)`,
            }}
          >
            <div style={{ fontFamily: "JetBrains Mono", fontSize: 13, fontWeight: 700, letterSpacing: "0.17em", color: tone }}>
              CAUGHT INSTANTLY
            </div>
            <div style={{ marginTop: 7, fontFamily: "Space Grotesk", fontSize: 28, fontWeight: 650, color: c.ink, whiteSpace: "nowrap" }}>
              Spoken to the crew.
            </div>
          </div>
        </div>
        {!caught ? (
          <div
            style={{
              position: "absolute",
              inset: -2,
              borderRadius: 26,
              border: `2px solid ${c.warn}`,
              opacity: pulse * 0.85,
              transform: `scale(${1 + pulse * 0.04})`,
              pointerEvents: "none",
            }}
          />
        ) : null}
      </div>
    </div>
  );
}

function LogoAct({ frame }: { frame: number }) {
  const inT = interpolate(frame, [204, 220], [0, 1], clamp);
  const markAt = 212;
  const wordAt = 234;
  const tagAt = 258;
  const breathe = 0.5 + 0.5 * Math.sin(frame / 26);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: inT }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 1500,
          height: 1500,
          marginLeft: -750,
          marginTop: -750,
          background: `radial-gradient(circle, rgba(91,157,255,${0.10 + breathe * 0.05}), rgba(255,255,255,0) 62%)`,
          mixBlendMode: "screen",
        }}
      />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 128, height: 340, background: "radial-gradient(60% 100% at 50% 100%, rgba(20,40,80,0.10), rgba(20,40,80,0) 70%)" }} />
      <div style={{ transform: `translateY(${-96}px)`, position: "relative" }}>
        <Mark size={212} at={markAt} glow={1} />
      </div>
      <div
        style={{
          position: "relative",
          marginTop: 46,
          fontFamily: "Space Grotesk",
          fontSize: 126,
          fontWeight: 700,
          letterSpacing: "-0.045em",
          color: c.ink,
        }}
      >
        <Wordmark text="BAS-HAR" at={wordAt} />
      </div>
      <div style={{ position: "relative", marginTop: 26, opacity: interpolate(frame, [tagAt, tagAt + 14], [0, 1], clamp) }}>
        <div style={{ fontFamily: "JetBrains Mono", fontSize: 30, fontWeight: 500, letterSpacing: "0.22em", color: c.ink3 }}>
          DESCRIBE IT. WATCH IT. TRUST IT.
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Wordmark({ text, at }: { text: string; at: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <span style={{ display: "inline-flex" }}>
      {text.split("").map((ch, i) => {
        const p = interpolate(frame, [at + i * 1.8, at + i * 1.8 + 16], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 3 });
        return (
          <span
            key={`${ch}-${i}`}
            style={{
              display: "inline-block",
              opacity: p,
              transform: `translateY(${(1 - p) * 46}px) scale(${0.86 + p * 0.14})`,
              filter: p > 0.98 ? undefined : `blur(${(1 - p) * 4}px)`,
            }}
          >
            {ch}
          </span>
        );
      })}
    </span>
  );
}

export const LAUNCH_FRAMES = FRAMES;
