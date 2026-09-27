import type { ReactNode } from "react";
import { AbsoluteFill, Audio, Easing, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

import { Backdrop, Logo, clamp, useRise } from "../components";
import { color, font } from "../theme";

const FPS = 30;
const FADE = 8;

type Part = { clip: string; from: number; to: number; rate?: number; label?: string; focus?: [number, number, number]; mute?: boolean };
type Card = { kind: "title" | "problem" | "section" | "close"; seconds: number; heading?: string; sub?: string };
type Beat = {
  kind: "clip";
  tag: string;
  title: string;
  sub: string;
  parts: Part[];
  pip?: { clip: string; from: number; after: number; label: string };
  caption?: "bottom-left" | "top-right";
};
type Segment = Card | Beat;

export const SEGMENTS: Segment[] = [
  { kind: "title", seconds: 4 },
  { kind: "problem", seconds: 8 },
  { kind: "section", seconds: 3, heading: "What you asked for", sub: "Seven requirements, shown working on real space-station footage" },
  { kind: "clip", tag: "Requirement 01 / 07", title: "Continuous local video processing", sub: "Real ISS footage · experiment recognised automatically · 1.00× real time", parts: [{ clip: "01_iss_recognise_and_run", from: 3.24, to: 17.64 }] },
  { kind: "clip", tag: "Requirement 02 / 07", title: "Suggests the next step", sub: "Spoken and shown on screen after every step", parts: [{ clip: "01_iss_recognise_and_run", from: 20.67, to: 25.7 }, { clip: "01_iss_recognise_and_run", from: 74.68, to: 79.68, label: "End of the run · 8 of 8 steps, in order" }] },
  { kind: "clip", tag: "Requirement 03 / 07", title: "Voice alert on a skipped step", sub: "The same footage with step 1 removed · caught in 1.5 seconds", parts: [{ clip: "03_skip_caught", from: 3.1, to: 6.6 }, { clip: "03_skip_caught", from: 8.1, to: 17.6 }] },
  { kind: "clip", tag: "Requirement 04 / 07", title: "Timestamped, structured record", sub: "Every event written with its exact time and outcome", parts: [{ clip: "04_session_log", from: 2.2, to: 7.4, focus: [0.4, 0.56, 1.7] }, { clip: "05_log_file", from: 2.4, to: 7.2 }] },
  { kind: "clip", tag: "Requirement 05 / 07", title: "Streams to a specific IP address", sub: "H.264 over UDP to 192.168.1.13 · the local recording continues", parts: [{ clip: "06a_stream_start", from: 6.2, to: 15.2, focus: [0.86, 0.8, 1.8], mute: true }], pip: { clip: "06b_stream_received", from: 4, after: 5.2, label: "Received at 192.168.1.13:5000" } },
  { kind: "clip", tag: "Requirement 06 / 07", title: "Graphical monitoring interface", sub: "Live video, step timeline, alerts and metrics", parts: [{ clip: "02_dashboard_tour", from: 2.0, to: 9.0, mute: true }] },
  { kind: "clip", tag: "Requirement 07 / 07", title: "A trained model, fully offline", sub: "YOLO11 trained on labelled ISS frames · held-out mAP50 0.79 · no internet needed", parts: [{ clip: "07_training_studio", from: 1.6, to: 9.6 }] },
  { kind: "section", seconds: 3, heading: "Beyond the brief", sub: "Where we went further" },
  { kind: "clip", tag: "Beyond the brief · 01", title: "Equipment states, not just objects", sub: "Hatch open · tray out · sample inside the compartment", parts: [{ clip: "08_states_closeup", from: 3.0, to: 10.0, mute: true }] },
  { kind: "clip", tag: "Beyond the brief · 02", title: "New experiments in plain English", sub: "A local vision-language model answers each step's question", parts: [{ clip: "09a_plain_english_yaml", from: 3.0, to: 9.0 }, { clip: "09b_model_answers", from: 15.7, to: 25.4 }] },
  { kind: "clip", tag: "Beyond the brief · 03", caption: "top-right", title: "A tamper-proof record", sub: "SHA-256 chained and Ed25519-signed · one changed digit is caught", parts: [{ clip: "10_tamper_proof", from: 7.9, to: 13.9 }, { clip: "10_tamper_proof", from: 14.7, to: 20.1 }, { clip: "10_tamper_proof", from: 27.6, to: 33.4 }] },
  { kind: "clip", tag: "Beyond the brief · 04", title: "The whole session in one kilobyte", sub: "A signed 999-byte report, 9,730× smaller than the video", parts: [{ clip: "11_signed_report", from: 3.0, to: 10.5, focus: [0.755, 0.55, 1.9] }] },
  { kind: "clip", tag: "Beyond the brief · 05", title: "English or Hindi", sub: "Announcements use the computer's own offline voices", parts: [{ clip: "12_language_switch", from: 2.6, to: 6.4, focus: [0.915, 0.155, 2.2] }, { clip: "12_language_switch", from: 15.35, to: 23.35 }] },
  { kind: "clip", tag: "Beyond the brief · 06", caption: "top-right", title: "Proven with one command", sub: "python -m halo verify · 8 of 8 checks · 276 automated tests", parts: [{ clip: "13_verify_all", from: 6.6, to: 10.6 }, { clip: "13_verify_all", from: 10.6, to: 62.6, rate: 13, label: "Sped up 13×" }, { clip: "13_verify_all", from: 62.6, to: 67.6 }] },
  { kind: "clip", tag: "Beyond the brief · 07", title: "No code per experiment", sub: "Every procedure is one validated file", parts: [{ clip: "14_one_file_per_experiment", from: 1.8, to: 9.3 }] },
  { kind: "close", seconds: 8 },
];

const partFrames = (part: Part) => Math.round(((part.to - part.from) / (part.rate ?? 1)) * FPS);
export const segmentFrames = (segment: Segment) =>
  segment.kind === "clip" ? segment.parts.reduce((total, part) => total + partFrames(part), 0) : Math.round(segment.seconds * FPS);
export const PITCH_FRAMES = SEGMENTS.reduce((total, segment) => total + segmentFrames(segment), 0);

function Fade({ children }: { children: ReactNode }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, FADE, durationInFrames - FADE, durationInFrames], [0, 1, 1, 0], clamp);
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
}

function Caption({ eyebrow, title, sub, place }: { eyebrow: string; title: string; sub: string; place: "bottom-left" | "top-right" }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const enter = interpolate(frame, [8, 26], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const exit = interpolate(frame, [durationInFrames - 14, durationInFrames - 4], [0, 1], { ...clamp, easing: Easing.in(Easing.quad) });
  const anchor = place === "top-right" ? { right: 44, top: 40 } : { left: 44, bottom: 40 };
  return (
    <div
      style={{
        position: "absolute",
        ...anchor,
        minWidth: 560,
        maxWidth: 900,
        padding: "20px 26px 22px",
        borderRadius: 14,
        background: "#ffffff",
        border: "1px solid rgba(15,23,42,0.08)",
        boxShadow: "0 1px 2px rgba(15,23,42,0.06), 0 18px 40px -24px rgba(15,23,42,0.35)",
        opacity: enter * (1 - exit),
        transform: `translateY(${(1 - enter) * (place === "top-right" ? -10 : 10)}px)`,
      }}
    >
      <div style={{ fontFamily: font.mono, fontSize: 15, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: color.accent }}>{eyebrow}</div>
      <div style={{ marginTop: 8, fontFamily: font.display, fontSize: 36, fontWeight: 600, letterSpacing: "-0.015em", lineHeight: 1.15, color: color.text }}>{title}</div>
      <div style={{ marginTop: 8, height: 1, background: "rgba(15,23,42,0.08)" }} />
      <div style={{ marginTop: 10, fontFamily: font.text, fontSize: 21, lineHeight: 1.4, color: color.text2 }}>{sub}</div>
    </div>
  );
}

function Label({ text, side }: { text: string; side: "left" | "right" }) {
  return (
    <div
      style={{
        position: "absolute",
        ...(side === "left" ? { left: 44 } : { right: 44 }),
        top: 40,
        padding: "9px 16px",
        borderRadius: 10,
        background: color.accent,
        color: "#fff",
        fontFamily: font.mono,
        fontSize: 18,
        fontWeight: 600,
      }}
    >
      {text}
    </div>
  );
}

function ClipBeat({ beat }: { beat: Beat }) {
  let offset = 0;
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {beat.parts.map((part, index) => {
        const duration = partFrames(part);
        const start = offset;
        offset += duration;
        return (
          <Sequence key={index} from={start} durationInFrames={duration}>
            <Focus focus={part.focus}>
            <OffthreadVideo
              src={staticFile(`pitch/${part.clip}.mp4`)}
              startFrom={Math.round(part.from * FPS)}
              endAt={Math.round(part.to * FPS)}
              playbackRate={part.rate ?? 1}
              volume={part.mute || (part.rate && part.rate > 1) ? 0 : 1}
              style={{ width: "100%", height: "100%" }}
            />
            </Focus>
            {part.label && <Label text={part.label} side={beat.caption === "top-right" ? "left" : "right"} />}
          </Sequence>
        );
      })}
      {beat.pip && (
        <Sequence from={Math.round(beat.pip.after * FPS)}>
          <Pip clip={beat.pip.clip} from={beat.pip.from} label={beat.pip.label} />
        </Sequence>
      )}
      <Caption eyebrow={beat.tag} title={beat.title} sub={beat.sub} place={beat.caption ?? "bottom-left"} />
    </AbsoluteFill>
  );
}

function Focus({ focus, children }: { focus?: [number, number, number]; children: ReactNode }) {
  const frame = useCurrentFrame();
  if (!focus) return <AbsoluteFill>{children}</AbsoluteFill>;
  const [x, y, zoom] = focus;
  const scale = interpolate(frame, [4, 34], [1, zoom], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: `${x * 100}% ${y * 100}%` }}>{children}</AbsoluteFill>;
}

function Pip({ clip, from, label }: { clip: string; from: number; label: string }) {
  const rise = useRise(0, 30);
  return (
    <div style={{ position: "absolute", left: 48, top: 110, width: 640, ...rise }}>
      <div style={{ borderRadius: 14, overflow: "hidden", boxShadow: "0 30px 60px -20px rgba(15,23,42,0.55), 0 0 0 1px rgba(15,23,42,0.1)", background: "#000" }}>
        <OffthreadVideo src={staticFile(`pitch/${clip}.mp4`)} startFrom={Math.round(from * FPS)} muted style={{ width: 640, height: 360, display: "block" }} />
      </div>
      <div style={{ marginTop: 10, textAlign: "left", fontFamily: font.mono, fontSize: 18, fontWeight: 600, color: color.text }}>
        <span style={{ display: "inline-block", width: 9, height: 9, borderRadius: "50%", background: color.ok, marginRight: 8 }} />
        {label}
      </div>
    </div>
  );
}

function Center({ children }: { children: ReactNode }) {
  return <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", textAlign: "center", fontFamily: font.text, color: color.text }}>{children}</AbsoluteFill>;
}

function TitleCard() {
  const logo = useRise(0, 16);
  const name = useRise(8, 18);
  const full = useRise(16, 14);
  const ps = useRise(28, 12);
  return (
    <>
      <Backdrop />
      <Center>
        <div style={logo}><Logo size={120} /></div>
        <div style={{ marginTop: 26, fontFamily: font.display, fontSize: 112, fontWeight: 600, letterSpacing: "-0.02em", ...name }}>H.A.L.O.</div>
        <div style={{ marginTop: 6, fontFamily: font.mono, fontSize: 28, fontWeight: 500, letterSpacing: "0.06em", color: color.accent, ...full }}>Human Activity Logging in Orbit</div>
        <div style={{ marginTop: 44, fontSize: 24, color: color.text2, ...ps }}>SIH26174 · AI Human Activity Recognition for on-board BAS experiments · ISRO</div>
      </Center>
    </>
  );
}

function ProblemCard() {
  const a = useRise(4, 16);
  const b = useRise(60, 16);
  const clip = useRise(10, 24);
  return (
    <>
      <Backdrop />
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", padding: "0 130px", gap: 90, fontFamily: font.text, color: color.text }}>
        <div style={{ width: 720 }}>
          <div style={{ fontFamily: font.display, fontSize: 58, fontWeight: 600, lineHeight: 1.12, letterSpacing: "-0.02em", ...a }}>Every experiment on the station follows a written procedure.</div>
          <div style={{ marginTop: 34, fontFamily: font.display, fontSize: 58, fontWeight: 600, lineHeight: 1.12, letterSpacing: "-0.02em", color: color.warn, ...b }}>One missed step can cost months of science.</div>
        </div>
        <div style={{ flex: 1, ...clip }}>
          <div style={{ borderRadius: 18, overflow: "hidden", boxShadow: "0 30px 70px -30px rgba(15,23,42,0.5)" }}>
            <OffthreadVideo src={staticFile("pitch/08_states_closeup.mp4")} startFrom={0} muted style={{ width: "100%", display: "block" }} />
          </div>
          <div style={{ marginTop: 12, fontFamily: font.mono, fontSize: 17, color: color.text3 }}>ESA Ignis mission · MELFI −80 °C freezer, International Space Station</div>
        </div>
      </AbsoluteFill>
    </>
  );
}

function SectionCard({ heading, sub }: { heading: string; sub: string }) {
  const h = useRise(0, 18);
  const s = useRise(10, 14);
  return (
    <>
      <Backdrop />
      <Center>
        <div style={{ fontFamily: font.display, fontSize: 84, fontWeight: 600, letterSpacing: "-0.025em", ...h }}>{heading}</div>
        <div style={{ marginTop: 18, fontSize: 30, color: color.text2, ...s }}>{sub}</div>
      </Center>
    </>
  );
}

function CloseCard() {
  const lines = ["Every requirement met, on real space-station footage", "A tamper-proof record and a one-kilobyte report for the ground", "Experiments described in plain English, all running offline"];
  const logo = useRise(0, 14);
  const end = useRise(100, 12);
  return (
    <>
      <Backdrop />
      <Center>
        <div style={{ display: "flex", alignItems: "center", gap: 26, ...logo }}>
          <Logo size={92} />
          <div style={{ textAlign: "left" }}>
            <div style={{ fontFamily: font.display, fontSize: 80, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1 }}>H.A.L.O.</div>
            <div style={{ marginTop: 8, fontFamily: font.mono, fontSize: 22, color: color.accent, letterSpacing: "0.05em" }}>Human Activity Logging in Orbit</div>
          </div>
        </div>
        <div style={{ marginTop: 56, display: "flex", flexDirection: "column", gap: 16 }}>
          {lines.map((line, index) => (
            <CloseLine key={line} text={line} delay={30 + index * 22} />
          ))}
        </div>
        <div style={{ marginTop: 60, fontSize: 26, color: color.text2, ...end }}>Built for Bharatiya Antariksh Station · Thank you</div>
      </Center>
    </>
  );
}

function CloseLine({ text, delay }: { text: string; delay: number }) {
  const rise = useRise(delay, 12);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 32, color: color.text, ...rise }}>
      <span style={{ width: 12, height: 12, borderRadius: "50%", background: color.ok }} />
      {text}
    </div>
  );
}

function renderSegment(segment: Segment) {
  if (segment.kind === "clip") return <ClipBeat beat={segment} />;
  if (segment.kind === "title") return <TitleCard />;
  if (segment.kind === "problem") return <ProblemCard />;
  if (segment.kind === "section") return <SectionCard heading={segment.heading ?? ""} sub={segment.sub ?? ""} />;
  return <CloseCard />;
}

export function Pitch() {
  let offset = 0;
  return (
    <AbsoluteFill style={{ background: color.bg }}>
      <Audio src={staticFile("audio/pad.m4a")} loop volume={(frame) => interpolate(frame, [0, 45, PITCH_FRAMES - 60, PITCH_FRAMES], [0, 0.07, 0.07, 0], clamp)} />
      {SEGMENTS.map((segment, index) => {
        const duration = segmentFrames(segment);
        const start = offset;
        offset += duration;
        return (
          <Sequence key={index} from={start} durationInFrames={duration}>
            <Fade>{renderSegment(segment)}</Fade>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}
