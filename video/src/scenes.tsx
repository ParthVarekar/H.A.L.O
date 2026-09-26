import { AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

import detections from "../public/detections.json";
import { Burst, Card, Check, Counter, Logo, Note, Push, Sheen, Split, Words, clamp, forwardFrame, useFlyIn, useRealTime, useRise, useSpring } from "./components";
import { STEPS, color, font } from "./theme";

type StepState = "pending" | "done" | "next" | "skipped" | "late";

const ROW = 64;

function Badge({ children, tone, bg, at }: { children: string; tone: string; bg: string; at: number }) {
  const pop = useSpring(at, 12, 0.6);
  return (
    <span
      style={{
        padding: "5px 12px",
        borderRadius: 8,
        background: bg,
        color: tone,
        fontFamily: font.mono,
        fontSize: 15,
        fontWeight: 700,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        transform: `scale(${pop})`,
        display: "inline-block",
      }}
    >
      {children}
    </span>
  );
}

type StepRowProps = { index: number; title: string; time?: string; state: StepState; since?: number; delay?: number; gone?: number };

function StepRow({ index, title, time, state, since = 0, delay = 0, gone = 0 }: StepRowProps) {
  const frame = useCurrentFrame();
  const enter = useSpring(delay, 18);
  const amber = state === "skipped" || state === "late";
  const checked = state === "done" || state === "late";
  const check = checked ? interpolate(frame - since, [0, 9], [0, 1], clamp) : 0;
  const tint = interpolate(frame - since, [0, 8], [0, 1], clamp);
  const tone = amber ? color.warn : color.ok;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        height: ROW * (1 - gone),
        padding: "0 28px",
        overflow: "hidden",
        borderTop: index === 0 ? "none" : `1px solid ${color.line}`,
        background: amber ? `rgba(196,122,6,${0.1 * tint})` : "transparent",
        opacity: Math.min(1, enter * 1.5) * (1 - gone),
        transform: `translateX(${(1 - enter) * 60 + gone * 180}px)`,
        filter: gone ? `blur(${gone * 6}px)` : undefined,
      }}
    >
      <div style={{ position: "relative", width: 30, height: 30, display: "grid", placeItems: "center" }}>
        {checked ? (
          <>
            <Check size={30} progress={check} tone={tone} />
            <Burst at={since} tone={tone} />
          </>
        ) : (
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: "50%",
              border: `1.5px solid ${state === "next" ? color.accent : amber ? color.warn : color.lineStrong}`,
              display: "grid",
              placeItems: "center",
              fontFamily: font.mono,
              fontSize: 13,
              fontWeight: 600,
              color: state === "next" ? color.accent : amber ? color.warn : color.text3,
            }}
          >
            {index + 1}
          </div>
        )}
      </div>
      <div style={{ flex: 1, fontSize: 24, fontWeight: 500, whiteSpace: "nowrap", color: state === "pending" ? color.text2 : color.text }}>{title}</div>
      {state === "next" && <Badge tone={color.accent} bg="rgba(47,123,255,0.14)" at={since}>Next</Badge>}
      {state === "skipped" && <Badge tone={color.warn} bg="rgba(196,122,6,0.14)" at={since}>Skipped</Badge>}
      {state === "late" && <Badge tone={color.warn} bg="rgba(196,122,6,0.14)" at={since}>Late</Badge>}
      {time && state === "done" && <span style={{ fontFamily: font.mono, fontSize: 18, color: color.text3, opacity: tint }}>{time}</span>}
    </div>
  );
}

export function ProcedureScene() {
  const frame = useCurrentFrame();
  const swap = 70;
  const outgoing = interpolate(frame, [swap - 12, swap], [0, 1], clamp);
  const card = useFlyIn(4);
  const gone = interpolate(frame, [swap + 10, swap + 34], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return (
    <Push>
      <Split
        text={
          <div style={{ position: "relative", height: 240 }}>
            <div style={{ position: "absolute", inset: 0, opacity: 1 - outgoing, transform: `translateY(${-outgoing * 30}px)`, filter: `blur(${outgoing * 8}px)` }}>
              <Words text="Every experiment in orbit follows a procedure." />
            </div>
            {frame >= swap - 2 && (
              <div style={{ position: "absolute", inset: 0 }}>
                <Words text="A missed step can cost the science." delay={swap} />
              </div>
            )}
          </div>
        }
        visual={
          <div style={card}>
            <Card width={680}>
              {STEPS.slice(0, 5).map((step, index) => (
                <StepRow key={step.title} index={index} title={step.title} state="pending" delay={10 + index * 4} gone={index === 2 ? gone : 0} />
              ))}
              <Sheen at={36} />
            </Card>
          </div>
        }
      />
    </Push>
  );
}

export function LogoScene() {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [0, 26], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const pop = useSpring(0, 11, 0.7);
  const ring = interpolate(frame, [18, 52], [0, 1], clamp);
  return (
    <Push amount={0.05}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 34 }}>
        <div style={{ position: "relative", transform: `scale(${pop}) rotate(${(1 - pop) * -20}deg)` }}>
          {[0, 0.35].map((offset) => {
            const t = Math.max(0, ring - offset);
            return (
              <div
                key={offset}
                style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: 40,
                  border: "2px solid rgba(47,123,255,0.5)",
                  transform: `scale(${1 + t * 1.2})`,
                  opacity: t > 0 && t < 1 ? 1 - t : 0,
                }}
              />
            );
          })}
          <Logo size={150} draw={draw} />
        </div>
        <Words text="BAS-HAR" delay={16} size={110} style={{ letterSpacing: "-0.04em" }} />
        <Words text="Watches each step of an experiment as it happens." delay={26} size={40} stagger={2} style={{ fontFamily: font.text, fontWeight: 400, color: color.text2, letterSpacing: "-0.01em" }} />
      </AbsoluteFill>
    </Push>
  );
}

type Box = { label: string; p: number; b: number[] };
const VIDEO_W = 1120;
const VIDEO_H = 630;
const CLIP_START_S = 0.5;
export const CLIP_RATE = 1.2;
const STORY = [
  { from: 0, to: 3.1, labels: ["Hatch · open"] },
  { from: 3.1, to: 9.6, labels: ["Tray 2 · out"] },
  { from: 9.6, to: 99, labels: ["Compartment 1 · open", "Sample"] },
];
const HOLD_FRAMES = 20;

function Boxes() {
  const frame = useCurrentFrame();
  const data = detections as { fps: number; frames: Box[][] };
  const clipTime = CLIP_START_S + (frame / 30) * CLIP_RATE;
  const index = Math.min(data.frames.length - 1, Math.floor(clipTime * data.fps));
  const part = STORY.find((entry) => clipTime >= entry.from && clipTime < entry.to);
  const partStart = part ? Math.round(((part.from - CLIP_START_S) / CLIP_RATE) * 30) : 0;
  const shown: Box[] = [];
  for (const label of part?.labels ?? []) {
    for (let back = 0; back <= HOLD_FRAMES && index - back >= 0; back += 1) {
      const match = data.frames[index - back].filter((box) => box.label === label && box.p >= 0.6).sort((a, b) => b.p - a.p)[0];
      if (match) {
        shown.push(match);
        break;
      }
    }
  }
  const draw = interpolate(frame - Math.max(partStart, 14), [0, 12], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <svg width={VIDEO_W} height={VIDEO_H} style={{ position: "absolute", inset: 0 }}>
      {shown.map((box) => {
        const [x1, y1, x2, y2] = box.b;
        const x = x1 * VIDEO_W;
        const y = y1 * VIDEO_H;
        const w = (x2 - x1) * VIDEO_W;
        const h = (y2 - y1) * VIDEO_H;
        const perimeter = 2 * (w + h);
        const label = `${box.label}  ${Math.round(box.p * 100)}%`;
        const tagWidth = label.length * 9.4 + 22;
        const tagY = y > 34 ? y - 32 : y + 4;
        return (
          <g key={box.label}>
            <rect x={x} y={y} width={w} height={h} rx={5} fill={`rgba(91,157,255,${0.08 * draw})`} stroke="#5b9dff" strokeWidth={2.4} strokeDasharray={perimeter} strokeDashoffset={perimeter * (1 - draw)} />
            <g style={{ transform: `translateY(${(1 - draw) * 8}px)`, opacity: draw }}>
              <rect x={x} y={tagY} width={tagWidth} height={27} rx={6} fill={color.accent} />
              <text x={x + 11} y={tagY + 18.5} fill="#fff" fontFamily={font.mono} fontSize={15} fontWeight={600}>
                {label}
              </text>
            </g>
          </g>
        );
      })}
    </svg>
  );
}

function ScanLine({ at }: { at: number }) {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [at, at + 30], [-10, 110], { ...clamp, easing: Easing.inOut(Easing.quad) });
  if (frame < at || frame > at + 30) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: `${y}%`,
        height: 120,
        marginTop: -60,
        background: "linear-gradient(180deg, transparent, rgba(91,157,255,0.28) 48%, rgba(170,205,255,0.9) 50%, rgba(91,157,255,0.28) 52%, transparent)",
        mixBlendMode: "screen",
      }}
    />
  );
}

export function SeesScene() {
  const card = useFlyIn(0);
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 180], [1.0, 1.08], { easing: Easing.inOut(Easing.sin) });
  return (
    <Push amount={0.02}>
      <Split
        textWidth={480}
        text={
          <>
            <Words text="Recognises equipment and its state." delay={4} size={66} />
            <Note delay={20}>Real ISS footage · ESA Ignis mission</Note>
          </>
        }
        visual={
          <div style={card}>
            <Card width={VIDEO_W} style={{ height: VIDEO_H, borderRadius: 20 }}>
              <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})`, transformOrigin: "55% 50%" }}>
                <OffthreadVideo src={staticFile("footage/melfi.mp4")} startFrom={CLIP_START_S * 30} playbackRate={CLIP_RATE} muted style={{ width: VIDEO_W, height: VIDEO_H, display: "block" }} />
                <Boxes />
              </div>
              <ScanLine at={8} />
            </Card>
          </div>
        }
      />
    </Push>
  );
}

export const VOICE_AT = 16;
export const VOICE_FRAMES = 145;

function Waveform({ active }: { active: boolean }) {
  const frame = useRealTime().frame;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, height: 34 }}>
      {Array.from({ length: 14 }, (_, index) => {
        const h = active ? 8 + Math.abs(Math.sin(frame / 3.2 + index * 0.9) * Math.cos(frame / 7 + index)) * 26 : 4;
        return <div key={index} style={{ width: 4, height: h, borderRadius: 2, background: color.accent, opacity: 0.85 }} />;
      })}
    </div>
  );
}

export function GuideScene() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const doneAt = [8, VOICE_AT + 2, 120, 132, 144];
  const rows = STEPS.map((_, index) => {
    const finished = doneAt[index];
    if (finished !== undefined && frame >= finished) return { state: "done" as StepState, since: finished };
    const start = index === 0 ? 0 : doneAt[index - 1];
    if (start !== undefined && frame >= start) return { state: "next" as StepState, since: start };
    return { state: "pending" as StepState, since: 0 };
  });
  const nextIndex = Math.max(0, rows.findIndex((row) => row.state === "next"));
  const lastMove = rows[nextIndex]?.since ?? 0;
  const previousIndex = Math.max(0, nextIndex - 1);
  const glide = spring({ frame: frame - lastMove, fps, config: { damping: 18, stiffness: 170 } });
  const highlightTop = (previousIndex + (nextIndex - previousIndex) * glide) * ROW;
  const card = useFlyIn(0);
  const quote = useRise(VOICE_AT, 16);
  const real = useRealTime();
  const voiceStart = forwardFrame(VOICE_AT, real.holds);
  const speaking = real.frame >= voiceStart && real.frame < voiceStart + VOICE_FRAMES - 5;
  return (
    <Push>
      <Split
        text={
          <>
            <Words text="Tells the crew what comes next." delay={2} />
            <div style={{ display: "flex", flexDirection: "column", gap: 14, ...quote }}>
              <Waveform active={speaking} />
              <p style={{ margin: 0, fontSize: 28, lineHeight: 1.4, color: color.text2, fontStyle: "italic" }}>“Step 2 done. Next: pull tray 2 out of dewar 1.”</p>
            </div>
          </>
        }
        visual={
          <div style={card}>
            <Card width={680}>
              <div style={{ position: "absolute", left: 0, right: 0, top: highlightTop, height: ROW, background: color.accentSoft, borderLeft: `3px solid ${color.accent}` }} />
              {STEPS.map((step, index) => (
                <StepRow key={step.title} index={index} title={step.title} time={step.time} state={rows[index].state} since={rows[index].since} delay={4 + index * 3} />
              ))}
            </Card>
          </div>
        }
      />
    </Push>
  );
}

function AlertStrip({ late }: { late: boolean }) {
  const frame = useCurrentFrame();
  const enter = useSpring(0, 13, 0.6);
  const shake = frame < 14 ? Math.sin(frame * 2.2) * (14 - frame) * 0.6 : 0;
  const pulse = (frame % 30) / 30;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        height: 72,
        padding: "0 28px",
        borderTop: `1px solid ${color.line}`,
        background: "rgba(196,122,6,0.09)",
        opacity: enter,
        transform: `translateY(${(1 - enter) * 40}px) translateX(${shake}px)`,
      }}
    >
      <div style={{ position: "relative", width: 26, height: 26 }}>
        <div style={{ position: "absolute", inset: -6, borderRadius: "50%", border: `2px solid ${color.warn}`, transform: `scale(${0.8 + pulse * 0.9})`, opacity: 1 - pulse }} />
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={color.warn} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>
      <span style={{ flex: 1, fontSize: 24, fontWeight: 600, color: color.text }}>{late ? "Step 1 done out of order" : "Alert · Step 1 skipped"}</span>
      <span style={{ fontFamily: font.mono, fontSize: 18, color: color.text3 }}>{late ? "0:03.0" : "0:01.5"}</span>
    </div>
  );
}

export const SKIP_AT = 32;
export const LATE_AT = 82;

export function SkipScene() {
  const frame = useCurrentFrame();
  const card = useFlyIn(0);
  const rows: { state: StepState; since: number }[] = [
    frame >= LATE_AT ? { state: "late", since: LATE_AT } : frame >= SKIP_AT ? { state: "skipped", since: SKIP_AT } : { state: "pending", since: 0 },
    frame >= 24 ? { state: "done", since: 24 } : { state: "pending", since: 0 },
    frame >= 24 ? { state: "next", since: 24 } : { state: "pending", since: 0 },
    { state: "pending", since: 0 },
  ];
  const flash = interpolate(frame, [SKIP_AT, SKIP_AT + 4, SKIP_AT + 18], [0, 0.35, 0], clamp);
  return (
    <Push>
      <AbsoluteFill style={{ background: `radial-gradient(900px 600px at 70% 50%, rgba(196,122,6,${flash}), transparent 70%)` }} />
      <Split
        text={<Words text="Notices when a step is skipped or out of order." delay={2} />}
        visual={
          <div style={card}>
            <Card width={680}>
              {STEPS.slice(0, 4).map((step, index) => (
                <StepRow key={step.title} index={index} title={step.title} time={index === 1 ? "0:01.5" : step.time} state={rows[index].state} since={rows[index].since} delay={4 + index * 3} />
              ))}
              {frame >= SKIP_AT && (
                <Sequence from={SKIP_AT} layout="none">
                  <AlertStrip late={frame >= LATE_AT} />
                </Sequence>
              )}
            </Card>
          </div>
        }
      />
    </Push>
  );
}

const QUESTION = "Is a long cylindrical tray pulled out of the freezer?";

export function DescribeScene() {
  const frame = useCurrentFrame();
  const card = useFlyIn(0);
  const typed = Math.floor(interpolate(frame, [12, 52], [0, QUESTION.length], clamp));
  const fill = interpolate(frame, [58, 80], [0, 0.8], { ...clamp, easing: Easing.out(Easing.cubic) });
  const yes = useSpring(82, 10, 0.6);
  const cursor = frame < 56 && Math.floor(frame / 8) % 2 === 0;
  return (
    <Push>
      <Split
        text={<Words text="New procedures can be described in plain language." delay={2} />}
        visual={
          <div style={card}>
            <Card width={720} style={{ padding: "34px 38px" }}>
              <div style={{ fontFamily: font.mono, fontSize: 16, fontWeight: 600, letterSpacing: "0.08em", color: color.accent, textTransform: "uppercase" }}>Step 3 · plain English</div>
              <div style={{ marginTop: 18, minHeight: 88, fontSize: 32, fontWeight: 500, lineHeight: 1.35, color: color.text }}>
                {QUESTION.slice(0, typed)}
                <span style={{ opacity: cursor ? 1 : 0, color: color.accent }}>|</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 30 }}>
                <div style={{ position: "relative", flex: 1, height: 12, borderRadius: 6, background: "#e6eaf0", overflow: "hidden" }}>
                  <div style={{ width: `${fill * 100}%`, height: "100%", borderRadius: 6, background: `linear-gradient(90deg, #0f8f5c, ${color.ok})`, boxShadow: `0 0 18px rgba(18,162,106,${fill})` }} />
                </div>
                <span style={{ width: 64, fontFamily: font.mono, fontSize: 21, color: color.text2, textAlign: "right" }}>{Math.round(fill * 100)}%</span>
                <span style={{ display: "inline-block", padding: "6px 16px", borderRadius: 9, background: color.okSoft, color: color.ok, fontSize: 21, fontWeight: 700, transform: `scale(${yes})` }}>Yes</span>
              </div>
              <Sheen at={84} />
            </Card>
          </div>
        }
      />
    </Push>
  );
}

export function OfflineScene() {
  const frame = useCurrentFrame();
  const laptop = useFlyIn(0);
  const badge = useSpring(28, 10, 0.6);
  const strike = interpolate(frame, [38, 50], [0, 1], clamp);
  return (
    <Push amount={0.05}>
      <Split
        textWidth={600}
        text={
          <>
            <Words text="Runs on board, in real time, without internet." delay={2} />
            <div style={{ display: "flex", gap: 40, fontFamily: font.display }}>
              {[
                [<Counter key="rt" from={0} to={1} start={20} end={56} format={(value) => `${value.toFixed(2)}×`} />, "real time"],
                [<Counter key="fps" from={0} to={25} start={24} end={60} format={(value) => `${Math.round(value)}`} />, "frames / s"],
                ["0", "network calls"],
              ].map(([value, label], index) => (
                <Stat key={index} value={value} label={label as string} delay={18 + index * 5} />
              ))}
            </div>
          </>
        }
        visual={
          <div style={{ position: "relative", ...laptop }}>
            <div style={{ width: 840, padding: 16, borderRadius: "22px 22px 6px 6px", background: "#1b2029", boxShadow: "0 50px 90px -40px rgba(20,40,80,0.5)" }}>
              <div style={{ position: "relative", overflow: "hidden", borderRadius: 8 }}>
                <Img src={staticFile("dashboard.jpg")} style={{ width: "100%", display: "block" }} />
                <Sheen at={18} duration={30} />
              </div>
            </div>
            <div style={{ width: 980, height: 22, marginLeft: -70, borderRadius: "4px 4px 18px 18px", background: "linear-gradient(#d9dde3, #b9bfc8)" }} />
            <div
              style={{
                position: "absolute",
                right: -40,
                top: -40,
                width: 100,
                height: 100,
                borderRadius: "50%",
                background: color.surface,
                border: `1px solid ${color.line}`,
                boxShadow: "0 18px 40px -18px rgba(20,40,80,0.35)",
                display: "grid",
                placeItems: "center",
                transform: `scale(${badge})`,
              }}
            >
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={color.text2} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12.55a11 11 0 0 1 14.08 0" />
                <path d="M1.42 9a16 16 0 0 1 21.16 0" />
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                <line x1="12" y1="20" x2="12.01" y2="20" />
                <line x1="3" y1="3" x2="21" y2="21" stroke={color.warn} strokeDasharray="26" strokeDashoffset={26 * (1 - strike)} />
              </svg>
            </div>
          </div>
        }
      />
    </Push>
  );
}

function Stat({ value, label, delay }: { value: React.ReactNode; label: string; delay: number }) {
  const rise = useRise(delay, 18);
  return (
    <div style={rise}>
      <div style={{ fontSize: 48, fontWeight: 600, letterSpacing: "-0.03em", color: color.accent, fontVariantNumeric: "tabular-nums" }}>{value}</div>
      <div style={{ marginTop: 4, fontFamily: font.mono, fontSize: 17, color: color.text3 }}>{label}</div>
    </div>
  );
}

const RECORD_LINES = [
  ["0", "header · plan 3223…4dc"],
  ["1", "step 1 completed · 0:00.2"],
  ["2", "step 2 completed · 0:12.9"],
  ["3", "step 3 completed · 0:15.4"],
  ["4", "step 4 completed · 0:21.1"],
];
const IMPLODE_AT = 64;

export function RecordScene() {
  const frame = useCurrentFrame();
  const implode = interpolate(frame, [IMPLODE_AT, IMPLODE_AT + 18], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  const file = useSpring(IMPLODE_AT + 14, 12, 0.7);
  return (
    <Push>
      <Split
        textWidth={620}
        text={
          <>
            <Words text="Every session becomes a signed record of about a kilobyte." delay={2} size={66} />
            <Note delay={18}>SHA-256 chained · Ed25519 signed</Note>
          </>
        }
        visual={
          <div style={{ position: "relative", width: 640, height: 520 }}>
            {RECORD_LINES.map(([seq, text], index) => (
              <RecordLine key={seq} seq={seq} text={text} index={index} implode={implode} />
            ))}
            {frame >= IMPLODE_AT + 10 && (
              <div style={{ position: "absolute", left: 30, right: 30, top: 150, transform: `scale(${file})`, opacity: Math.min(1, file * 1.5) }}>
                <Card style={{ padding: "34px 38px", display: "flex", alignItems: "center", gap: 26 }}>
                  <div style={{ position: "relative" }}>
                    <svg width="68" height="68" viewBox="0 0 24 24" fill="none" stroke={color.ok} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" fill={color.okSoft} />
                      <polyline points="8.5 12 11 14.5 15.5 10" />
                    </svg>
                    <Burst at={IMPLODE_AT + 24} size={60} />
                  </div>
                  <div>
                    <div style={{ fontFamily: font.mono, fontSize: 23, fontWeight: 600, color: color.text }}>session.downlink.json</div>
                    <div style={{ marginTop: 8, fontFamily: font.display, fontSize: 40, fontWeight: 600, letterSpacing: "-0.02em", color: color.ok, fontVariantNumeric: "tabular-nums" }}>
                      <Counter from={9720664} to={1002} start={IMPLODE_AT + 18} end={IMPLODE_AT + 58} format={(value) => `${Math.round(value).toLocaleString("en-US")} bytes`} />
                    </div>
                    <div style={{ marginTop: 4, fontSize: 19, color: color.text3 }}>9.7 MB of video, sealed and signed</div>
                  </div>
                  <Sheen at={IMPLODE_AT + 56} />
                </Card>
              </div>
            )}
          </div>
        }
      />
    </Push>
  );
}

function RecordLine({ seq, text, index, implode }: { seq: string; text: string; index: number; implode: number }) {
  const enter = useSpring(4 + index * 7, 16);
  const link = interpolate(useCurrentFrame(), [10 + index * 7, 18 + index * 7], [0, 1], clamp);
  const top = index * 90;
  const toward = 190 - top;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top,
        opacity: Math.min(1, enter * 1.5) * (1 - implode),
        transform: `translateX(${(1 - enter) * -80}px) translateY(${toward * implode}px) scale(${1 - implode * 0.5})`,
        filter: implode ? `blur(${implode * 8}px)` : undefined,
      }}
    >
      {index > 0 && <div style={{ position: "absolute", left: 44, top: -26, width: 2, height: 26 * link, background: color.accent, opacity: 0.5 }} />}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          height: 64,
          padding: "0 24px",
          borderRadius: 14,
          background: color.surface,
          border: `1px solid ${color.line}`,
          boxShadow: "0 12px 30px -22px rgba(20,40,80,0.3)",
          fontFamily: font.mono,
          fontSize: 19,
        }}
      >
        <span style={{ width: 42, height: 30, borderRadius: 7, display: "grid", placeItems: "center", background: color.accentSoft, color: color.accent, fontWeight: 700 }}>{seq}</span>
        <span style={{ flex: 1, color: color.text }}>{text}</span>
        <span style={{ color: color.ok, opacity: link }}>✓ signed</span>
      </div>
    </div>
  );
}

export function CloseScene() {
  const frame = useCurrentFrame();
  const pop = useSpring(0, 11, 0.7);
  const glow = interpolate(frame, [0, 40], [0, 1], clamp);
  return (
    <Push amount={0.04}>
      <AbsoluteFill style={{ background: `radial-gradient(700px 420px at 50% 46%, rgba(47,123,255,${0.1 * glow}), transparent 70%)` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 28 }}>
        <div style={{ transform: `scale(${pop})` }}>
          <Logo size={112} draw={interpolate(frame, [0, 22], [0, 1], clamp)} />
        </div>
        <Words text="BAS-HAR" delay={8} size={92} style={{ letterSpacing: "-0.04em" }} />
        <Words text="Built for Bharatiya Antariksh Station." delay={18} size={36} stagger={2} style={{ fontFamily: font.text, fontWeight: 400, color: color.text2, letterSpacing: "-0.005em" }} />
      </AbsoluteFill>
    </Push>
  );
}
