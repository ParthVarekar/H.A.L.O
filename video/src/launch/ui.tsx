import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { spring } from "remotion";

import { launchColor as c } from "./palette";
import { clamp, depthBlur, place, useSpring } from "./fx";

export function DetectBox({
  w,
  h,
  x,
  y,
  z,
  label,
  conf,
  at,
  tone = c.accent,
  rotation = 0,
  strength,
}: {
  w: number;
  h: number;
  x: number;
  y: number;
  z: number;
  label: string;
  conf: number;
  at: number;
  tone?: string;
  rotation?: number;
  strength?: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - at;
  if (local < -2) return null;
  const draw = interpolate(local, [0, 13], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 3 });
  const tagPop = spring({ frame: local - 5, fps, config: { damping: 13, mass: 0.6, stiffness: 150 } });
  const hold = interpolate(local, [30, 40], [1, 0], clamp);
  const opacity = hold * (1 - local / 90 > 0 ? 1 : 0);
  const blur = (strength ?? depthBlur(z, 0.012, 12)) + (1 - hold) * 3;
  const perimeter = 2 * (w + h);
  const text = `${label} · ${Math.round(conf * 100)}%`;
  const tagW = text.length * 8.6 + 20;
  const tagH = 26;

  return (
    <div
      style={{
        ...place(x, y, z, ` rotateY(${rotation}deg)`),
        width: w,
        height: h,
        marginLeft: -w / 2,
        marginTop: -h / 2,
        opacity,
        filter: blur > 0.15 ? `blur(${blur}px)` : undefined,
      }}
    >
      <svg width={w} height={h} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <rect
          x={1}
          y={1}
          width={w - 2}
          height={h - 2}
          rx={6}
          fill={`${tone}12`}
          stroke={tone}
          strokeWidth={2.4}
          strokeDasharray={perimeter}
          strokeDashoffset={perimeter * (1 - draw)}
        />
        <g style={{ opacity: draw, transform: `translateY(${(1 - tagPop) * -10}px)`, transformOrigin: `0 ${-h / 2 + 2}px` }}>
          <rect x={1} y={-h / 2 - tagH + 3} width={tagW} height={tagH} rx={6} fill={tone} />
          <text x={11} y={-h / 2 - tagH / 2 + 5.5} fill="#fff" fontFamily="JetBrains Mono" fontSize={14} fontWeight={600}>
            {text}
          </text>
        </g>
      </svg>
    </div>
  );
}

export function CornerTicks({ size, tone, at }: { size: number; tone: string; at: number }) {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [at, at + 16], [0, 1], clamp);
  const arm = size * 0.22 * t;
  const o = size / 2;
  const corner = (sx: number, sy: number, dx: number, dy: number, key: string) => (
    <path key={key} d={`M ${o + sx * o} ${o + sy * o} L ${o + sx * (o - arm)} ${o + sy * o} M ${o + sx * o} ${o + sy * o} L ${o + sx * o} ${o + sy * (o - arm)}`} stroke={tone} strokeWidth={2} fill="none" strokeLinecap="round" />
  );
  return (
    <svg width={size} height={size} style={{ position: "absolute", left: -size / 2, top: -size / 2, opacity: t }}>
      {corner(-1, -1, -1, -1, "tl")}
      {corner(1, -1, 1, -1, "tr")}
      {corner(-1, 1, -1, 1, "bl")}
      {corner(1, 1, 1, 1, "br")}
    </svg>
  );
}

export function GlassCard({
  w,
  h,
  x,
  y,
  z,
  at,
  children,
  tone = "rgba(255,255,255,0.9)",
  border = "rgba(255,255,255,0.95)",
  rotateY = 0,
  rotateX = 0,
  pad = 26,
  radius = 26,
  strength,
}: {
  w: number;
  h: number;
  x: number;
  y: number;
  z: number;
  at: number;
  children: ReactNode;
  tone?: string;
  border?: string;
  rotateY?: number;
  rotateX?: number;
  pad?: number;
  radius?: number;
  strength?: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: frame - at, fps, config: { damping: 15, mass: 0.85, stiffness: 110 } });
  const bob = Math.sin(frame / 46) * 5;
  const blur = strength ?? depthBlur(z, 0.011, 12);
  const ry = interpolate(enter, [0, 1], [-24, rotateY], clamp);
  return (
    <div
      style={{
        ...place(x, y + bob, z, ` rotateX(${interpolate(enter, [0, 1], [rotateX + 16, rotateX], clamp)}deg) rotateY(${ry}deg)`),
        width: w,
        height: h,
        marginLeft: -w / 2,
        marginTop: -h / 2,
        padding: pad,
        boxSizing: "border-box",
        borderRadius: radius,
        opacity: enter,
        filter: blur > 0.15 ? `blur(${blur}px)` : undefined,
        background: tone,
        border: `1.5px solid ${border}`,
        boxShadow: "0 46px 80px -40px rgba(20,40,80,0.55), inset 0 2px 0 rgba(255,255,255,0.9)",
        backdropFilter: "blur(14px)",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

const ICON_PATHS: Record<string, ReactNode> = {
  hatch: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  tray: (
    <>
      <rect x="2.5" y="8.5" width="19" height="7" rx="3.5" />
      <line x1="7" y1="8.5" x2="7" y2="15.5" />
      <line x1="14" y1="8.5" x2="14" y2="15.5" />
    </>
  ),
  box: (
    <>
      <path d="M12 2.6 20.5 7v10L12 21.4 3.5 17V7z" />
      <path d="M3.5 7 12 11.4 20.5 7" />
    </>
  ),
  pouch: (
    <>
      <path d="M6 8.5h12l-1 11.5H7z" />
      <path d="M9 8.5V6.2a3 3 0 0 1 6 0v2.3" />
    </>
  ),
  latch: (
    <>
      <path d="M4 12h11" />
      <path d="M15 8.5 18.5 12 15 15.5" />
      <circle cx="5" cy="12" r="2" />
    </>
  ),
  person: (
    <>
      <circle cx="12" cy="6.2" r="3.2" />
      <path d="M5.5 20.5c1.4-4 3.7-6 6.5-6s5.1 2 6.5 6" />
    </>
  ),
  vapour: (
    <>
      <path d="M7 20c-1.7-2.6-1-5 .6-6.6C6 11 5.6 8.4 7.4 6.4c1.7-1.9 4.4-1.8 5.8.2 1.2 1.7.8 3.8-.6 5.2 1.9 1.2 2.8 3.3 1.9 5.3" />
      <path d="M13.6 20c1.6-1.4 2-3.4 1.2-5" />
    </>
  ),
  check: <polyline points="4.5 12.5 9.5 17.5 19.5 6.5" />,
  gauge: (
    <>
      <path d="M4 17a8.5 8.5 0 1 1 16 0" />
      <line x1="12" y1="17" x2="16" y2="11" />
      <circle cx="12" cy="17" r="1.4" />
    </>
  ),
};

export function detectIcon(name: string) {
  return (
    <svg
      width={30}
      height={30}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICON_PATHS[name] ?? ICON_PATHS.check}
    </svg>
  );
}

export function ScanSweep({ at, tone = c.accent, size = 2600, opacity = 1 }: { at: number; tone?: string; size?: number; opacity?: number }) {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [at, at + 34], [0, 1], clamp);
  if (frame < at) return null;
  const radius = t * size;
  const fade = interpolate(t, [0, 0.1, 0.85, 1], [0, 1, 1, 0], clamp) * opacity;
  return (
    <div style={{ ...place(0, 0, -40), pointerEvents: "none" }}>
      <svg width={size * 2} height={size * 2} style={{ position: "absolute", left: -size, top: -size, opacity: fade, filter: "blur(2px)" }}>
        <defs>
          <linearGradient id={`sweep-${at}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor={tone} stopOpacity={0} />
            <stop offset="0.5" stopColor={tone} stopOpacity={0.75} />
            <stop offset="1" stopColor={tone} stopOpacity={0} />
          </linearGradient>
        </defs>
        <circle cx={size} cy={size} r={Math.max(1, radius)} fill="none" stroke={`url(#sweep-${at})`} strokeWidth={9} />
      </svg>
      <div
        style={{
          position: "absolute",
          left: -size,
          top: -size,
          width: size * 2,
          height: size * 2,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${tone}00 58%, ${tone}1f 76%, transparent 84%)`,
          mixBlendMode: "screen",
        }}
      />
    </div>
  );
}

export function Beam3D({ w, h, x, y, z, at, tone, rotate = 0 }: { w: number; h: number; x: number; y: number; z: number; at: number; tone: string; rotate?: number }) {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [at, at + 18], [0, 1], clamp);
  if (frame < at) return null;
  return (
    <div
      style={{
        ...place(x, y, z, ` rotate(${rotate}deg)`),
        width: w * t,
        height: h,
        marginLeft: (-w * t) / 2,
        marginTop: -h / 2,
        background: `linear-gradient(90deg, transparent, ${tone}, transparent)`,
        filter: "blur(9px)",
        mixBlendMode: "screen",
      }}
    />
  );
}

export function Line3D({
  text,
  x,
  y,
  z,
  at,
  until,
  size = 92,
  stagger = 2.6,
  color = c.ink,
  weight = 600,
  align = "center",
  width = 1500,
  family = "Space Grotesk",
  tracking = "-0.035em",
}: {
  text: string;
  x: number;
  y: number;
  z: number;
  at: number;
  until?: number;
  size?: number;
  stagger?: number;
  color?: string;
  weight?: number;
  align?: CSSProperties["textAlign"];
  width?: number;
  family?: string;
  tracking?: string;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");
  const fadeIn = interpolate(frame, [at - 6, at + 4], [0, 1], clamp);
  const fadeOut = until === undefined ? 1 : interpolate(frame, [until, until + 12], [1, 0], clamp);
  const opacity = Math.min(fadeIn, fadeOut);
  return (
    <div
      style={{
        ...place(x, y + (1 - fadeOut) * -78, z),
        width,
        marginLeft: -width / 2,
        textAlign: align,
        opacity,
        filter: fadeOut < 1 ? `blur(${(1 - fadeOut) * 6}px)` : undefined,
      }}
    >
      <div style={{ display: "inline-block", transformStyle: "preserve-3d" }}>
        {words.map((word, index) => {
          const p = spring({ frame: frame - at - index * stagger, fps, config: { damping: 20, mass: 0.75, stiffness: 150 } });
          return (
            <span
              key={`${word}-${index}`}
              style={{
                display: "inline-block",
                overflow: "hidden",
                verticalAlign: "bottom",
                paddingBottom: "0.14em",
                marginBottom: "-0.14em",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  fontFamily: family,
                  fontSize: size,
                  fontWeight: weight,
                  letterSpacing: tracking,
                  color,
                  whiteSpace: "pre",
                  transform: `translate3d(0, ${(1 - p) * 108}%, ${(1 - p) * -260}px) rotateX(${(1 - p) * -22}deg)`,
                  transformOrigin: "50% 100%",
                  filter: p > 0.98 ? undefined : `blur(${(1 - p) * 5}px)`,
                  opacity: Math.min(1, p * 1.5),
                }}
              >
                {word}
                {" "}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export function Mark({
  size,
  at,
  spin = 0,
  glow = 1,
}: {
  size: number;
  at: number;
  spin?: number;
  glow?: number;
}) {
  const frame = useCurrentFrame();
  const pop = useSpring(at, 11, 0.62, 120);
  const ring = interpolate(frame, [at + 2, at + 34], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 3 });
  const dot = interpolate(frame, [at + 14, at + 30], [0, 1], clamp);
  const check = interpolate(frame, [at + 20, at + 40], [0, 1], clamp);
  const arc = 46;
  const breathe = 0.5 + 0.5 * Math.sin(frame / 26);
  return (
    <div style={{ position: "relative", transform: `scale(${0.6 + pop * 0.4}) rotate(${(1 - pop) * -18}deg)`, transformOrigin: "50% 50%" }}>
      <svg
        width={size * 1.9}
        height={size * 1.9}
        viewBox="0 0 100 100"
        style={{ position: "absolute", left: -size * 0.45, top: -size * 0.45 }}
      >
        <defs>
          <linearGradient id="orbit-a" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#5b9dff" stopOpacity="0" />
            <stop offset="0.5" stopColor="#5b9dff" stopOpacity="0.85" />
            <stop offset="1" stopColor="#5b9dff" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="orbit-b" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#12a26a" stopOpacity="0" />
            <stop offset="0.5" stopColor="#12a26a" stopOpacity="0.7" />
            <stop offset="1" stopColor="#12a26a" stopOpacity="0" />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="url(#orbit-a)"
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeDasharray="52 230"
          transform={`rotate(${-90 + frame * 1.5} 50 50)`}
          opacity={ring}
        />
        <circle
          cx="50"
          cy="50"
          r="37"
          fill="none"
          stroke="url(#orbit-b)"
          strokeWidth="0.8"
          strokeLinecap="round"
          strokeDasharray="40 200"
          transform={`rotate(${120 - frame * 1.1} 50 50)`}
          opacity={ring * 0.9}
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="rgba(91,157,255,0.20)"
          strokeWidth="0.5"
          opacity={ring * 0.7}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: -size * 0.34,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(91,157,255,${0.30 * glow * (0.75 + breathe * 0.25)}), rgba(255,255,255,0) 66%)`,
          mixBlendMode: "screen",
          filter: "blur(12px)",
        }}
      />
      <svg width={size} height={size} viewBox="0 0 32 32" style={{ display: "block", transform: `rotate(${spin}deg)` }}>
        <defs>
          <linearGradient id="mark-tile" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={c.navyMid} />
            <stop offset="1" stopColor={c.navy} />
          </linearGradient>
        </defs>
        <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="url(#mark-tile)" stroke="#2c3a52" />
        <path
          d="M25.29 14.03A9.5 9.5 0 1 1 17.98 6.71"
          fill="none"
          stroke="#5b9dff"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeDasharray={arc}
          strokeDashoffset={arc * (1 - ring)}
        />
        <circle cx="22.72" cy="9.28" r={2.1 * dot} fill="#eef2f7" />
        <polyline
          points="11.4 16.4 14.4 19.3 19.5 13.9"
          fill="none"
          stroke="#eef2f7"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={12}
          strokeDashoffset={12 * (1 - check)}
        />
      </svg>
    </div>
  );
}

export function Counter({
  from,
  to,
  at,
  format,
  size = 96,
  color = c.accent,
}: {
  from: number;
  to: number;
  at: number;
  format: (v: number) => string;
  size?: number;
  color?: string;
}) {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [at, at + 38], [from, to], { ...clamp, easing: (t) => 1 - (1 - t) ** 4 });
  return (
    <span style={{ fontFamily: "Space Grotesk", fontSize: size, fontWeight: 600, letterSpacing: "-0.04em", color, fontVariantNumeric: "tabular-nums" }}>
      {format(v)}
    </span>
  );
}

export function RingGauge({ size, at, tone, label }: { size: number; at: number; tone: string; label: string }) {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [at, at + 26], [0, 1], clamp);
  const r = size / 2 - 8;
  const cLen = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} style={{ display: "block" }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`${tone}33`} strokeWidth={7} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={tone}
        strokeWidth={7}
        strokeLinecap="round"
        strokeDasharray={cLen}
        strokeDashoffset={cLen * (1 - t)}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" fill={c.ink} fontFamily="JetBrains Mono" fontSize={size * 0.17} fontWeight={700}>
        {label}
      </text>
    </svg>
  );
}

export function ScanLine({ at, tone = "rgba(91,157,255,0.9)", height = 140 }: { at: number; tone?: string; height?: number }) {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [at, at + 40], [-14, 114], { ...clamp, easing: (t) => t * t * (3 - 2 * t) });
  if (frame < at || frame > at + 40) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: `${y}%`,
          height,
          marginTop: -height / 2,
          background: `linear-gradient(180deg, transparent, ${tone.replace("0.9", "0.22)")} 46%, ${tone} 50%, ${tone.replace("0.9", "0.22)")} 54%, transparent)`,
          mixBlendMode: "screen",
        }}
      />
    </AbsoluteFill>
  );
}
