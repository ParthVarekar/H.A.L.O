import React from "react";
import { interpolate, spring } from "remotion";
import { KnitSphere, IridescentBubble } from "../tactile/Spheres";

export const KineticPunchScene = ({ frame, fps }) => {
  const localFrame = frame - 192;

  const textSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 13, stiffness: 140, mass: 0.9 },
  });

  const pillSpring = spring({
    frame: localFrame - 3,
    fps,
    config: { damping: 12, stiffness: 150, mass: 0.8 },
  });

  const opacity = interpolate(
    localFrame,
    [0, 2, 28, 31],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const scale = interpolate(textSpring, [0, 1], [0.8, 1]);
  const pillScale = interpolate(pillSpring, [0, 1], [0.65, 1]);

  // Dash animation offset
  const dashOffset = (localFrame * 4) % 100;
  const drift = Math.sin(frame * 0.1) * 8;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        transform: `scale(${scale})`,
        zIndex: 60,
      }}
    >
      {/* Peripheral Tactile Spheres & Bubbles */}
      <KnitSphere
        size={140}
        variant="blue"
        x={-560}
        y={-120 + drift}
        z={-60}
        spin={frame * 0.5}
      />
      <KnitSphere
        size={130}
        variant="green"
        x={540}
        y={140 - drift}
        z={-40}
        spin={-frame * 0.4}
      />
      <IridescentBubble
        size={90}
        x={-380}
        y={160 + drift}
        z={120}
        wobblePhase={frame}
      />
      <IridescentBubble
        size={105}
        x={440}
        y={-140 - drift}
        z={140}
        wobblePhase={frame + 50}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* Massive Bold Headline: "We watch." */}
        <span
          style={{
            fontSize: 104,
            fontWeight: 900,
            letterSpacing: "-0.05em",
            color: "#0A0D14",
            lineHeight: 1,
            textShadow: "0 4px 30px rgba(0,0,0,0.06)",
          }}
        >
          We watch,
        </span>

        {/* The Animated Kram "+ gotchu" Style Pill */}
        <div
          style={{
            transform: `scale(${pillScale})`,
            display: "inline-flex",
            alignItems: "center",
            gap: 14,
            padding: "16px 36px 16px 20px",
            borderRadius: 999,
            backgroundColor: "#FFFFFF",
            boxShadow:
              "0 24px 60px rgba(0, 0, 0, 0.12), 0 6px 16px rgba(0,0,0,0.04)",
            position: "relative",
          }}
        >
          {/* Animated Multi-Color Dashed Gradient Border SVG */}
          <svg
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              overflow: "visible",
              pointerEvents: "none",
            }}
          >
            <defs>
              <linearGradient id="rainbow-dash" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF5E3A" />
                <stop offset="25%" stopColor="#FF9500" />
                <stop offset="50%" stopColor="#4CD964" />
                <stop offset="75%" stopColor="#5AC8FA" />
                <stop offset="100%" stopColor="#5856D6" />
              </linearGradient>
            </defs>
            <rect
              x="1.5"
              y="1.5"
              width="calc(100% - 3px)"
              height="calc(100% - 3px)"
              rx="40"
              ry="40"
              fill="none"
              stroke="url(#rainbow-dash)"
              strokeWidth="2.5"
              strokeDasharray="8 6"
              strokeDashoffset={-dashOffset}
            />
          </svg>

          {/* Plus / Eye Action Button */}
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background:
                "linear-gradient(135deg, #F0F3F7 0%, #DCE2EB 100%)",
              boxShadow:
                "0 2px 8px rgba(0,0,0,0.1), inset 0 1px 1px #FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              fontWeight: 900,
              color: "#0E131F",
            }}
          >
            +
          </div>

          {/* Pill text */}
          <span
            style={{
              fontSize: 38,
              fontWeight: 800,
              color: "#0E131F",
              letterSpacing: "-0.03em",
            }}
          >
            so crew discovers.
          </span>
        </div>
      </div>
    </div>
  );
};
