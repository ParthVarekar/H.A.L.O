import type { CSSProperties, ReactNode } from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  random,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { ease, launchColor as c } from "./palette";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const PERSPECTIVE = 1500;

export function ramp(frame: number, from: number, to: number, a = 0, b = 1) {
  return interpolate(frame, [from, to], [a, b], { ...clamp, easing: Easing.bezier(...ease.out) });
}

export function smooth(frame: number, from: number, to: number, a = 0, b = 1) {
  return interpolate(frame, [from, to], [a, b], {
    ...clamp,
    easing: Easing.bezier(...ease.inOut),
  });
}

export function useSpring(delay = 0, damping = 14, mass = 0.7, stiffness = 130) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping, mass, stiffness } });
}

type Cam = { x: number; y: number; z: number; rx: number; ry: number; focus: number };

let activeFocus = 0;

export function setFocus(value: number) {
  activeFocus = value;
}

export function getFocus() {
  return activeFocus;
}

export function depthBlur(z: number, strength = 0.016, max = 16) {
  return Math.min(max, Math.abs(z - activeFocus) * strength);
}

export function Stage({
  cam,
  children,
  style,
}: {
  cam: Cam;
  children: ReactNode;
  style?: CSSProperties;
}) {
  setFocus(cam.focus);
  return (
    <AbsoluteFill style={{ perspective: PERSPECTIVE, perspectiveOrigin: "50% 50%", ...style }}>
      <AbsoluteFill
        style={{
          transformStyle: "preserve-3d",
          transform: `translate3d(${-cam.x}px, ${-cam.y}px, ${-cam.z}px) rotateX(${cam.rx}deg) rotateY(${cam.ry}deg)`,
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function place(x: number, y: number, z: number, extra = ""): CSSProperties {
  return {
    position: "absolute",
    left: "50%",
    top: "50%",
    transform: `translate3d(${x}px, ${y}px, ${z}px)${extra}`,
    transformStyle: "preserve-3d",
  };
}

export function Orb({
  size,
  x,
  y,
  z,
  core,
  rim,
  glow = 0.5,
  spin = 0,
  squash = 1,
  opacity = 1,
  strength,
}: {
  size: number;
  x: number;
  y: number;
  z: number;
  core: [string, string];
  rim: string;
  glow?: number;
  spin?: number;
  squash?: number;
  opacity?: number;
  strength?: number;
}) {
  const frame = useCurrentFrame();
  const blur = strength ?? depthBlur(z);
  const drift = Math.sin(frame / 46 + x * 0.01) * 9;
  const rise = Math.cos(frame / 61 + y * 0.013) * 7;
  const r = size / 2;
  return (
    <div
      style={{
        ...place(x, y + rise, z + drift),
        width: size,
        height: size * squash,
        marginLeft: -r,
        marginTop: (-size * squash) / 2,
        borderRadius: "50%",
        opacity,
        filter: blur > 0.15 ? `blur(${blur}px)` : undefined,
        background: [
          `radial-gradient(circle at 34% 26%, rgba(255,255,255,0.98), rgba(255,255,255,0) 46%)`,
          `radial-gradient(circle at 72% 80%, ${rim}, rgba(255,255,255,0) 58%)`,
          `radial-gradient(circle at 40% 34%, ${core[0]}, ${core[1]} 74%)`,
        ].join(","),
        boxShadow: `inset -${size * 0.06}px -${size * 0.05}px ${size * 0.16}px rgba(20,32,54,0.20), 0 ${size * 0.1}px ${size * 0.4}px rgba(20,32,54,0.10), 0 0 ${size * glow}px ${rim}`,
        transform: `translate3d(${x}px, ${y + rise}px, ${z + drift}px) rotate(${spin + frame * 0.12}deg)`,
      }}
    />
  );
}

function Sparkle({ size, tone }: { size: number; tone: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: "block" }}>
      <path
        d="M12 0C12 7.2 7.2 12 0 12c7.2 0 12 4.8 12 12 0-7.2 4.8-12 12-12-7.2 0-12-4.8-12-12Z"
        fill={tone}
      />
    </svg>
  );
}

export function Sparkles({
  count = 46,
  seed = "dust",
  z = -260,
  spreadX = 1500,
  spreadY = 900,
  size = 16,
  tone = "rgba(255,255,255,0.95)",
  opacity = 1,
  drift = 1,
}: {
  count?: number;
  seed?: string;
  z?: number;
  spreadX?: number;
  spreadY?: number;
  size?: number;
  tone?: string;
  opacity?: number;
  drift?: number;
}) {
  const frame = useCurrentFrame();
  const items: ReactNode[] = [];
  for (let i = 0; i < count; i += 1) {
    const rx = random(`${seed}-x-${i}`) - 0.5;
    const ry = random(`${seed}-y-${i}`) - 0.5;
    const rz = random(`${seed}-z-${i}`);
    const rs = random(`${seed}-s-${i}`);
    const rp = random(`${seed}-p-${i}`);
    const twinkle = 0.35 + 0.65 * Math.abs(Math.sin(frame / (7 + rp * 16) + rp * 9));
    const px = rx * spreadX + Math.sin(frame / 120 + rp * 12) * 26 * drift;
    const py = ry * spreadY - ((frame * (0.12 + rz * 0.4)) % (spreadY * 1.4)) * drift;
    const pz = z - rz * 900;
    const s = size * (0.35 + rs * 1.1);
    items.push(
      <div
        key={`${seed}-${i}`}
        style={{
          ...place(px, py + spreadY * 0.7, pz),
          opacity: opacity * twinkle,
          filter: depthBlur(pz, 0.01, 7) > 0.2 ? `blur(${depthBlur(pz, 0.01, 7)}px)` : undefined,
        }}
      >
        <Sparkle size={s} tone={tone} />
      </div>,
    );
  }
  return <>{items}</>;
}

export function Beam({
  x,
  y,
  z,
  width,
  height,
  rotate,
  tone = "rgba(47,123,255,0.30)",
  opacity = 1,
  strength,
}: {
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
  rotate: number;
  tone?: string;
  opacity?: number;
  strength?: number;
}) {
  const frame = useCurrentFrame();
  const blur = strength ?? depthBlur(z, 0.012, 22);
  const breathe = 0.72 + 0.28 * Math.sin(frame / 38);
  return (
    <div
      style={{
        ...place(x, y, z, ` rotate(${rotate}deg)`),
        width,
        height,
        marginLeft: -width / 2,
        marginTop: -height / 2,
        opacity: opacity * breathe,
        filter: `blur(${blur + 26}px)`,
        background: `linear-gradient(180deg, ${tone}, rgba(255,255,255,0) 78%)`,
        mixBlendMode: "screen",
      }}
    />
  );
}

export function Glow({
  size,
  x,
  y,
  z = 0,
  tone,
  opacity = 1,
  strength,
}: {
  size: number;
  x: number;
  y: number;
  z?: number;
  tone: string;
  opacity?: number;
  strength?: number;
}) {
  const blur = strength ?? depthBlur(z, 0.01, 18);
  return (
    <div
      style={{
        ...place(x, y, z),
        width: size,
        height: size,
        marginLeft: -size / 2,
        marginTop: -size / 2,
        borderRadius: "50%",
        opacity,
        filter: `blur(${blur + 30}px)`,
        background: `radial-gradient(circle, ${tone}, rgba(255,255,255,0) 68%)`,
        mixBlendMode: "screen",
      }}
    />
  );
}

export function Shadow({ w, x, y, z, opacity = 0.2 }: { w: number; x: number; y: number; z: number; opacity?: number }) {
  const blur = depthBlur(z, 0.014, 18);
  return (
    <div
      style={{
        ...place(x, y, z),
        width: w,
        height: w * 0.2,
        marginLeft: -w / 2,
        borderRadius: "50%",
        opacity: opacity * (1 - blur / 40),
        filter: `blur(${blur + 12}px)`,
        background: "radial-gradient(ellipse, rgba(18,28,46,0.55), rgba(18,28,46,0) 70%)",
      }}
    />
  );
}

export function Grain({ opacity = 0.05 }: { opacity?: number }) {
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        opacity,
        mixBlendMode: "overlay",
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E\")",
      }}
    />
  );
}

export function Vignette({ strength = 0.3, tone = "10,18,32" }: { strength?: number; tone?: string }) {
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        background: `radial-gradient(120% 100% at 50% 46%, rgba(${tone},0) 42%, rgba(${tone},${strength}) 100%)`,
      }}
    />
  );
}

export function BackdropWash({
  from,
  to,
  cx = 50,
  cy = 42,
}: {
  from: string;
  to: string;
  cx?: number;
  cy?: number;
}) {
  const frame = useCurrentFrame();
  const driftX = cx + Math.sin(frame / 150) * 7;
  const driftY = cy + Math.cos(frame / 190) * 5;
  return (
    <AbsoluteFill
      style={{
        background: `
          radial-gradient(1500px 1000px at ${driftX}% ${driftY}%, ${from}, rgba(255,255,255,0) 72%),
          linear-gradient(168deg, ${to} 0%, ${c.white} 58%, ${to} 100%)`,
      }}
    />
  );
}

export function RefractedEdge({ thickness = 2, opacity = 0.5 }: { thickness?: number; opacity?: number }) {
  return (
    <AbsoluteFill
      style={{
        borderRadius: "inherit",
        padding: thickness,
        background: `conic-gradient(from 210deg, rgba(47,123,255,0.0), rgba(47,123,255,${opacity}), rgba(18,162,106,${opacity * 0.8}), rgba(255,196,107,${opacity * 0.7}), rgba(47,123,255,0.0))`,
        WebkitMask:
          "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
        WebkitMaskComposite: "xor",
        maskComposite: "exclude",
        pointerEvents: "none",
      }}
    />
  );
}
