import React from "react";

export const KnitSphere = ({
  size = 200,
  variant = "blue",
  x = 0,
  y = 0,
  z = 0,
  counterRotX = 0,
  counterRotY = 0,
  spin = 0,
  scale = 1,
  opacity = 1,
}) => {
  const configs = {
    blue: {
      base: "#2868CE",
      shadow: "#0F2856",
      highlight: "#68A5FF",
      rim: "rgba(104, 165, 255, 0.55)",
      patternId: "knit-pattern-blue",
      stitchStroke: "rgba(190, 225, 255, 0.6)",
      stitchShadow: "rgba(5, 20, 50, 0.7)",
    },
    green: {
      base: "#249852",
      shadow: "#0D4020",
      highlight: "#5FE28E",
      rim: "rgba(95, 226, 142, 0.5)",
      patternId: "knit-pattern-green",
      stitchStroke: "rgba(205, 255, 225, 0.6)",
      stitchShadow: "rgba(5, 40, 15, 0.7)",
    },
    grey: {
      base: "#7C8594",
      shadow: "#363C47",
      highlight: "#B0B9C6",
      rim: "rgba(215, 225, 240, 0.5)",
      patternId: "knit-pattern-grey",
      stitchStroke: "rgba(255, 255, 255, 0.65)",
      stitchShadow: "rgba(20, 25, 35, 0.75)",
    },
  };

  const cfg = configs[variant] || configs.blue;

  return (
    <div
      style={{
        position: "absolute",
        left: `calc(50% + ${x}px)`,
        top: `calc(50% + ${y}px)`,
        width: size,
        height: size,
        marginLeft: -size / 2,
        marginTop: -size / 2,
        transform: `translateZ(${z}px) rotateY(${-counterRotY}deg) rotateX(${-counterRotX}deg) scale(${scale})`,
        opacity,
        pointerEvents: "none",
      }}
    >
      {/* Perfect Circular 3D Spherical Geometry */}
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          position: "relative",
          overflow: "hidden",
          backgroundColor: cfg.base,
          boxShadow: `0 35px 70px -10px rgba(10, 20, 45, 0.4), inset 0 -16px 36px ${cfg.shadow}`,
          transform: `rotate(${spin}deg)`,
        }}
      >
        {/* Procedural Knitted Wool Stitch SVG Texture */}
        <svg
          width={size}
          height={size}
          style={{ position: "absolute", inset: 0, opacity: 0.88 }}
        >
          <defs>
            <pattern
              id={cfg.patternId}
              width="14"
              height="18"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 2,3 Q 7,10 12,3"
                fill="none"
                stroke={cfg.stitchShadow}
                strokeWidth="3.2"
                strokeLinecap="round"
              />
              <path
                d="M 2,2 Q 7,9 12,2"
                fill="none"
                stroke={cfg.stitchStroke}
                strokeWidth="2.2"
                strokeLinecap="round"
              />
              <path
                d="M 2,12 Q 7,19 12,12"
                fill="none"
                stroke={cfg.stitchShadow}
                strokeWidth="3.2"
                strokeLinecap="round"
              />
              <path
                d="M 2,11 Q 7,18 12,11"
                fill="none"
                stroke={cfg.stitchStroke}
                strokeWidth="2.2"
                strokeLinecap="round"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill={`url(#${cfg.patternId})`} />
        </svg>

        {/* Micro-fiber vertical ribbing texture */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "repeating-linear-gradient(90deg, rgba(0,0,0,0.16) 0px, transparent 3px, rgba(255,255,255,0.16) 6px, transparent 9px)",
            mixBlendMode: "overlay",
          }}
        />

        {/* Realistic Apple Studio 3D Spherical Lighting Shader */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(circle at 30% 25%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0.2) 28%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.65) 85%, rgba(0,0,0,0.92) 100%)",
            borderRadius: "50%",
          }}
        />

        {/* Studio Fresnel Edge Rim Highlight */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            boxShadow: `inset 0 0 26px ${cfg.rim}, inset 4px 6px 14px rgba(255,255,255,0.65)`,
          }}
        />
      </div>

      {/* Floor Contact Shadow */}
      <div
        style={{
          position: "absolute",
          top: size * 0.9,
          left: size * 0.1,
          width: size * 0.8,
          height: size * 0.32,
          borderRadius: "50%",
          background:
            "radial-gradient(ellipse at center, rgba(16, 28, 54, 0.32) 0%, rgba(16, 28, 54, 0.08) 45%, rgba(0,0,0,0) 70%)",
          filter: "blur(8px)",
          transform: "rotateX(75deg)",
          zIndex: -1,
        }}
      />
    </div>
  );
};

export const IridescentBubble = ({
  size = 110,
  x = 0,
  y = 0,
  z = 0,
  counterRotX = 0,
  counterRotY = 0,
  wobblePhase = 0,
  opacity = 1,
  scale = 1,
}) => {
  // Microgravity liquid wobble
  const wobbleX = 1 + 0.05 * Math.sin(wobblePhase * 0.09);
  const wobbleY = 1 - 0.05 * Math.sin(wobblePhase * 0.09);

  return (
    <div
      style={{
        position: "absolute",
        left: `calc(50% + ${x}px)`,
        top: `calc(50% + ${y}px)`,
        width: size,
        height: size,
        marginLeft: -size / 2,
        marginTop: -size / 2,
        transform: `translateZ(${z}px) rotateY(${-counterRotY}deg) rotateX(${-counterRotX}deg) scale(${scale * wobbleX}, ${scale * wobbleY})`,
        opacity,
        pointerEvents: "none",
      }}
    >
      {/* Outer Rainbow Thin-Film Interference Rim */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background:
            "conic-gradient(from 120deg, #FF6EA7, #A765FF, #45B8FE, #3EECAC, #FFE600, #FF7B54, #FF6EA7)",
          filter: "blur(3px)",
          opacity: 0.85,
        }}
      />

      {/* Translucent Glass Bubble Body */}
      <div
        style={{
          position: "absolute",
          inset: 2,
          borderRadius: "50%",
          background:
            "radial-gradient(circle at 35% 28%, rgba(255,255,255,0.75) 0%, rgba(255,255,255,0.06) 46%, rgba(180,220,255,0.18) 78%, rgba(255,255,255,0.38) 98%)",
          backdropFilter: "blur(6px)",
          boxShadow:
            "inset 0 0 18px rgba(255,255,255,0.8), inset -4px -6px 16px rgba(69, 184, 254, 0.45), 0 16px 36px rgba(45, 90, 160, 0.18)",
          border: "1px solid rgba(255,255,255,0.75)",
        }}
      >
        {/* Primary Specular Key Light Glint (Crescent at 10 o'clock) */}
        <div
          style={{
            position: "absolute",
            top: "14%",
            left: "22%",
            width: size * 0.28,
            height: size * 0.18,
            borderRadius: "50%",
            background:
              "radial-gradient(ellipse at center, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.4) 60%, rgba(255,255,255,0) 100%)",
            transform: "rotate(-32deg)",
            filter: "blur(0.8px)",
          }}
        />

        {/* Secondary Glint Dot */}
        <div
          style={{
            position: "absolute",
            top: "28%",
            left: "17%",
            width: size * 0.08,
            height: size * 0.08,
            borderRadius: "50%",
            backgroundColor: "#FFFFFF",
            boxShadow: "0 0 6px rgba(255,255,255,0.95)",
          }}
        />

        {/* Secondary Bounce Highlight (Bottom-right at 4 o'clock) */}
        <div
          style={{
            position: "absolute",
            bottom: "16%",
            right: "22%",
            width: size * 0.22,
            height: size * 0.12,
            borderRadius: "50%",
            background:
              "radial-gradient(ellipse at center, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0) 100%)",
            transform: "rotate(-25deg)",
            filter: "blur(1.5px)",
          }}
        />
      </div>
    </div>
  );
};

export const SoftSiliconeCube = ({
  size = 130,
  x = 0,
  y = 0,
  z = 0,
  rotateX = 24,
  rotateY = -32,
  rotateZ = 12,
  scale = 1,
  opacity = 1,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        left: `calc(50% + ${x}px)`,
        top: `calc(50% + ${y}px)`,
        width: size,
        height: size,
        marginLeft: -size / 2,
        marginTop: -size / 2,
        transform: `translateZ(${z}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) rotateZ(${rotateZ}deg) scale(${scale})`,
        transformStyle: "preserve-3d",
        opacity,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: size,
          height: size,
          borderRadius: size * 0.28,
          background:
            "linear-gradient(135deg, #FF8EA8 0%, #E85B82 50%, #B82E56 100%)",
          boxShadow:
            "0 30px 60px -10px rgba(180, 40, 80, 0.4), inset 0 3px 6px rgba(255,255,255,0.6), inset -6px -8px 18px rgba(90, 10, 35, 0.6)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(circle at 25% 25%, rgba(255,255,255,0.55) 0%, transparent 60%)",
          }}
        />
      </div>
    </div>
  );
};
