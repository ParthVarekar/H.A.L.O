import type { CSSProperties, ReactNode } from "react";
import { interpolate, random, useCurrentFrame } from "remotion";

import { launchColor as c } from "./palette";
import { Glow, Shadow, clamp, depthBlur, place, useSpring } from "./fx";

function metal(stops: string[]) {
  return `linear-gradient(100deg, ${stops.join(",")})`;
}

export function Slab({
  w,
  h,
  d,
  x,
  y,
  z,
  spin = 0,
  children,
  face,
  opacity = 1,
  strength,
}: {
  w: number;
  h: number;
  d: number;
  x: number;
  y: number;
  z: number;
  spin?: number;
  children?: ReactNode;
  face?: string;
  opacity?: number;
  strength?: number;
}) {
  const blur = strength ?? depthBlur(z, 0.013, 18);
  const filter = blur > 0.15 ? `blur(${blur}px)` : undefined;
  const edge = metal([c.steelDark, "#dde4ee", "#f2f5f9", c.steel]);
  const plate = (
    key_: string,
    px: number,
    py: number,
    pw: number,
    ph: number,
    extra: string,
    bg: string,
  ) => (
    <div
      key={key_}
      style={{
        ...place(px, py, z, extra),
        width: pw,
        height: ph,
        marginLeft: -pw / 2,
        marginTop: -ph / 2,
        borderRadius: 8,
        opacity,
        filter,
        background: bg,
      }}
    />
  );
  return (
    <>
      {plate("top", x, y - h / 2, w, d, " rotateX(90deg)", metal(["#f6f8fb", "#e2e8f0", "#ccd5e1"]))}
      {plate("right", x + w / 2, y, d, h, " rotateY(90deg)", edge)}
      {plate("left", x - w / 2, y, d, h, " rotateY(-90deg)", edge)}
      <div
        style={{
          ...place(x, y, z + d / 2, ` rotateY(${spin}deg)`),
          width: w,
          height: h,
          marginLeft: -w / 2,
          marginTop: -h / 2,
          borderRadius: 18,
          opacity,
          filter,
          background:
            face ??
            metal([
              "rgba(255,255,255,0.96)",
              "rgba(238,242,248,0.98)",
              "rgba(206,215,227,0.99)",
              "rgba(232,237,244,1)",
            ]),
          boxShadow:
            "inset 0 2px 0 rgba(255,255,255,0.95), inset 0 -22px 46px rgba(20,32,54,0.20), 0 40px 70px -34px rgba(20,40,80,0.42)",
          overflow: "hidden",
        }}
      >
        {children}
      </div>
    </>
  );
}

export function Hatch({
  size,
  open,
  glowTone,
}: {
  size: number;
  open: number;
  glowTone?: string;
}) {
  const frame = useCurrentFrame();
  const r = size / 2;
  const lid = interpolate(open, [0, 1], [0, 150], clamp);
  const spin = interpolate(open, [0, 1], [0, 108], clamp);
  const interior = interpolate(open, [0, 1], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", left: "50%", top: "46%", width: size, height: size, marginLeft: -r, marginTop: -r }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: [
            "radial-gradient(circle at 40% 32%, rgba(190,214,240,0.5), rgba(255,255,255,0) 42%)",
            "radial-gradient(circle at 38% 30%, #16233a, #05080e 74%)",
          ].join(","),
          boxShadow: `inset 0 ${size * 0.06}px ${size * 0.16}px rgba(0,0,0,0.9), 0 0 0 ${size * 0.045}px rgba(150,163,180,0.9), 0 0 0 ${size * 0.07}px rgba(255,255,255,0.6)`,
          opacity: 0.25 + interior * 0.75,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: size * 0.1,
            borderRadius: "50%",
            background: "radial-gradient(circle at 46% 62%, rgba(120,150,190,0.30), rgba(0,0,0,0) 66%)",
          }}
        />
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${18 + i * 24}%`,
              top: `${34 + (i % 2) * 22}%`,
              width: size * 0.1,
              height: size * 0.26,
              borderRadius: size * 0.05,
              background: "linear-gradient(180deg, rgba(226,236,248,0.75), rgba(150,170,196,0.5))",
              opacity: interior * 0.8,
              transform: `rotate(${-8 + i * 7}deg)`,
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          inset: -size * 0.02,
          borderRadius: "50%",
          background: metal([
            "rgba(255,255,255,0.98)",
            "rgba(214,222,233,0.99)",
            "rgba(168,179,194,1)",
            "rgba(238,243,249,1)",
          ]),
          boxShadow: "inset 0 -6px 14px rgba(20,32,54,0.28), 0 18px 34px -18px rgba(20,40,80,0.5)",
          transform: `translate(${lid * 0.62}px, ${-lid * 0.30}px) rotate(${spin * 0.26}deg)`,
          transformOrigin: "2% 50%",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: size * 0.1,
            borderRadius: "50%",
            border: `${size * 0.012}px solid rgba(120,132,150,0.55)`,
            background: "radial-gradient(circle at 34% 28%, rgba(255,255,255,0.9), rgba(255,255,255,0) 60%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: size * 0.3,
            height: size * 0.07,
            marginLeft: -size * 0.15,
            marginTop: -size * 0.035,
            borderRadius: size * 0.04,
            background: metal(["#eef2f7", "#9aa5b5", "#e8edf4"]),
            boxShadow: "0 2px 6px rgba(20,32,54,0.4)",
            transform: `rotate(${-spin * 0.5}deg)`,
          }}
        />
      </div>
      {glowTone ? (
        <div
          style={{
            position: "absolute",
            inset: -size * 0.3,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${glowTone}, rgba(255,255,255,0) 62%)`,
            opacity: 0.35 + 0.25 * Math.sin(frame / 12),
            mixBlendMode: "screen",
            filter: "blur(14px)",
          }}
        />
      ) : null}
    </div>
  );
}

export function Tray({
  w,
  h,
  x,
  y,
  z,
  pull,
  spin = 0,
  opacity = 1,
  strength,
}: {
  w: number;
  h: number;
  x: number;
  y: number;
  z: number;
  pull: number;
  spin?: number;
  opacity?: number;
  strength?: number;
}) {
  const blur = strength ?? depthBlur(z, 0.013, 18);
  const d = h * 0.92;
  return (
    <div style={{ ...place(x, y, z, ` rotateY(${spin}deg)`), opacity, filter: blur > 0.15 ? `blur(${blur}px)` : undefined }}>
      <div
        style={{
          position: "absolute",
          left: -d / 2,
          top: -h / 2,
          width: d,
          height: h,
          borderRadius: "50%",
          background: "radial-gradient(circle at 40% 34%, #f4f7fb, #aab4c4 74%)",
          boxShadow: "inset -3px -4px 10px rgba(20,32,54,0.35)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: -d / 2 + 2,
          top: -h / 2,
          width: d,
          height: h,
          borderRadius: "50%",
          background: "radial-gradient(circle at 40% 34%, rgba(255,255,255,0.9), rgba(255,255,255,0) 70%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          top: -h / 2,
          width: w,
          height: h,
          borderRadius: h / 2,
          background: metal([
            "rgba(150,161,177,1)",
            "rgba(240,244,249,1)",
            "rgba(255,255,255,1)",
            "rgba(226,232,240,1)",
            "rgba(140,151,167,1)",
          ]),
          boxShadow: "0 26px 44px -26px rgba(20,40,80,0.55)",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "10%",
            right: "10%",
            top: "26%",
            height: "16%",
            borderRadius: 6,
            background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.95), rgba(255,255,255,0))",
          }}
        />
        {[0.3, 0.62].map((at) => (
          <div
            key={at}
            style={{
              position: "absolute",
              left: `${at * 100}%`,
              top: "18%",
              width: 3,
              height: "64%",
              borderRadius: 2,
              background: "rgba(120,132,150,0.5)",
            }}
          />
        ))}
      </div>
      <div style={{ position: "absolute", left: w - 3, top: -h / 2, width: 6, height: h, borderRadius: 3, background: "linear-gradient(#e6ebf2,#aab4c4)" }} />
    </div>
  );
}

export function Sample({
  size,
  x,
  y,
  z,
  spin = 0,
  opacity = 1,
  tone = c.accent,
  strength,
}: {
  size: number;
  x: number;
  y: number;
  z: number;
  spin?: number;
  opacity?: number;
  tone?: string;
  strength?: number;
}) {
  const frame = useCurrentFrame();
  const blur = strength ?? depthBlur(z, 0.013, 16);
  const float = Math.sin(frame / 28) * 7;
  const tilt = Math.sin(frame / 34) * 7;
  return (
    <div
      style={{
        ...place(x, y + float, z, ` rotate(${spin + tilt}deg)`),
        width: size,
        height: size * 1.24,
        marginLeft: -size / 2,
        marginTop: (-size * 1.24) / 2,
        borderRadius: `${size * 0.22}px ${size * 0.22}px ${size * 0.34}px ${size * 0.34}px`,
        opacity,
        filter: blur > 0.15 ? `blur(${blur}px)` : undefined,
        background: [
          "radial-gradient(ellipse at 32% 22%, rgba(255,255,255,0.99), rgba(255,255,255,0) 52%)",
          `linear-gradient(158deg, rgba(255,255,255,0.98) 34%, ${tone}38 78%, ${tone}1c)`,
        ].join(","),
        border: `2px solid ${tone}99`,
        boxShadow: `0 26px 46px -24px ${tone}66, inset 0 -16px 28px ${tone}26, inset 0 2px 0 rgba(255,255,255,0.9)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: size * 0.12,
          right: size * 0.12,
          top: -size * 0.06,
          height: size * 0.14,
          borderRadius: 3,
          background: `repeating-linear-gradient(90deg, ${tone}55 0 3px, transparent 3px 7px)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "22%",
          top: "34%",
          width: "56%",
          height: size * 0.4,
          borderRadius: size * 0.06,
          background: "rgba(255,255,255,0.55)",
        }}
      />
    </div>
  );
}

export function Bubbles({ count = 22, seed = "bub", warm = 0 }: { count?: number; seed?: string; warm?: number }) {
  const frame = useCurrentFrame();
  const items: ReactNode[] = [];
  for (let i = 0; i < count; i += 1) {
    const rx = random(`${seed}-x-${i}`);
    const ry = random(`${seed}-y-${i}`);
    const rz = random(`${seed}-z-${i}`);
    const rs = random(`${seed}-s-${i}`);
    const drift = random(`${seed}-d-${i}`);
    const px = (rx - 0.5) * 2100;
    const py = (ry - 0.5) * 1250 + Math.sin(frame / (110 + drift * 90) + drift * 10) * 30;
    const pz = -220 - rz * 1500;
    const size = 26 + rs * 108;
    const glassy = rz > 0.62;
    items.push(
      <div
        key={`${seed}-${i}`}
        style={{
          ...place(px, py, pz),
          width: size,
          height: size,
          marginLeft: -size / 2,
          marginTop: -size / 2,
          borderRadius: "50%",
          filter: `blur(${depthBlur(pz, 0.009, 15)}px)`,
          background: glassy
            ? `radial-gradient(circle at 34% 28%, rgba(255,255,255,0.95), rgba(255,255,255,0.1) 48%, rgba(255,255,255,0.42) 78%, rgba(255,255,255,0.08))`
            : `radial-gradient(circle at 36% 30%, ${warm > 0.5 ? "#ffffff" : "#eef2f8"}, ${warm > 0.5 ? "#dfe9fb" : "#cdd6e4"} 76%)`,
          boxShadow: glassy
            ? `inset -${size * 0.08}px -${size * 0.06}px ${size * 0.2}px rgba(47,123,255,0.30), inset ${size * 0.06}px ${size * 0.05}px ${size * 0.14}px rgba(255,255,255,0.95)`
            : `inset -${size * 0.07}px -${size * 0.05}px ${size * 0.18}px rgba(20,32,54,0.20), 0 ${size * 0.1}px ${size * 0.36}px rgba(20,32,54,0.10)`,
          opacity: 0.9,
        }}
      />,
    );
  }
  return <>{items}</>;
}

const CHIP_W = 166;
const CHIP_H = 150;

export function Chip({
  at,
  angle,
  orbitX,
  orbitY,
  orbitZ,
  label,
  sub,
  tone,
  icon,
  seed,
  scale = 1,
  dim = 0,
  emphasis = 0,
}: {
  at: number;
  angle: number;
  orbitX: number;
  orbitY: number;
  orbitZ: number;
  label: string;
  sub?: string;
  tone: string;
  icon: ReactNode;
  seed: string;
  scale?: number;
  dim?: number;
  emphasis?: number;
}) {
  const frame = useCurrentFrame();
  const enter = useSpring(at, 15, 0.8, 120);
  const a = angle + frame * 0.0042 + random(`${seed}-spin`) * 0.4;
  const breathe = Math.sin(frame / 42 + random(`${seed}-ph`) * 6) * 6;
  const tx = Math.cos(a) * orbitX;
  const ty = Math.sin(a) * orbitY + breathe;
  const tz = Math.sin(a) * orbitZ;

  const sx = (random(`${seed}-sx`) - 0.5) * 2400;
  const sy = (random(`${seed}-sy`) - 0.5) * 1500 - 300;
  const sz = -900 - random(`${seed}-sz`) * 700;
  const tumble = interpolate(enter, [0, 1], [1, 0], clamp);

  const px = sx + (tx - sx) * enter;
  const py = sy + (ty - sy) * enter;
  const pz = sz + (tz - sz) * enter;
  const rotY = interpolate(enter, [0, 1], [-150, 0], clamp);
  const rotX = interpolate(enter, [0, 1], [60, 0], clamp);
  const rotZ = interpolate(enter, [0, 1], [-40, 0], clamp);

  const blur = Math.min(depthBlur(pz, 0.011, 12), 2.4) + dim * 5;
  const pop = 1 + emphasis * 0.22;
  const s = scale * pop;

  return (
    <div
      style={{
        ...place(px, py, pz, ` rotateX(${rotX}deg) rotateY(${rotY}deg) rotateZ(${rotZ}deg) scale(${s})`),
        width: CHIP_W,
        height: CHIP_H,
        marginLeft: -CHIP_W / 2,
        marginTop: -CHIP_H / 2,
        borderRadius: 34,
        opacity: enter * (1 - dim * 0.55),
        filter: `blur(${blur}px)`,
        background: [
          "linear-gradient(150deg, rgba(255,255,255,0.98), rgba(255,255,255,0.86))",
          `radial-gradient(circle at 26% 18%, ${tone}2e, rgba(255,255,255,0) 58%)`,
        ].join(","),
        border: `1.5px solid ${tone}3d`,
        boxShadow: `0 30px 54px -30px rgba(20,40,80,0.5), inset 0 2px 0 rgba(255,255,255,0.95), 0 0 ${18 + emphasis * 30}px ${tone}44`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        transformStyle: "preserve-3d",
      }}
    >
      <div style={{ display: "grid", placeItems: "center", height: 46, color: tone }}>{icon}</div>
      <div style={{ fontFamily: "Inter", fontSize: 17, fontWeight: 650, color: c.ink, letterSpacing: "-0.012em", whiteSpace: "nowrap" }}>{label}</div>
      {sub ? (
        <div style={{ fontFamily: "JetBrains Mono", fontSize: 12, fontWeight: 600, color: tone, letterSpacing: "0.05em" }}>{sub}</div>
      ) : null}
      {tumble > 0.02 ? (
        <div style={{ position: "absolute", inset: 0, borderRadius: 34, background: `rgba(255,255,255,${tumble * 0.5})` }} />
      ) : null}
    </div>
  );
}

export function HeroShadow({ x, y, z, w, opacity = 0.26 }: { x: number; y: number; z: number; w: number; opacity?: number }) {
  return <Shadow w={w} x={x} y={y} z={z} opacity={opacity} />;
}

export function Halo({ size, x, y, z, tone, opacity = 1 }: { size: number; x: number; y: number; z: number; tone: string; opacity?: number }) {
  return <Glow size={size} x={x} y={y} z={z} tone={tone} opacity={opacity} />;
}
