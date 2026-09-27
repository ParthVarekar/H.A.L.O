import React from "react";
import { interpolate, spring } from "remotion";
import { IridescentBubble, KnitSphere } from "../tactile/Spheres";

export const LogoScene = ({ frame, fps }) => {
  const localFrame = frame - 222;

  const logoSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 13, stiffness: 140, mass: 0.9 },
  });

  const textSpring = spring({
    frame: localFrame - 2,
    fps,
    config: { damping: 13, stiffness: 130 },
  });

  const pillSpring = spring({
    frame: localFrame - 5,
    fps,
    config: { damping: 13, stiffness: 130 },
  });

  const logoY = interpolate(logoSpring, [0, 1], [-90, 0]);
  const logoScale = interpolate(logoSpring, [0, 1], [0.8, 1]);
  const opacity = 1;

  // Gleam light sweep diagonally across the squircle tile
  const gleamX = interpolate(localFrame, [4, 26], [-220, 260], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const bubbleDrift = Math.sin(frame * 0.08) * 8;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        zIndex: 50,
      }}
    >
      {/* Floating Tactile Elements Flanking the Logo */}
      <KnitSphere
        size={160}
        variant="blue"
        x={500}
        y={-120 + bubbleDrift}
        z={-40}
        spin={frame * 0.4}
      />
      <KnitSphere
        size={140}
        variant="grey"
        x={-520}
        y={120 - bubbleDrift}
        z={-60}
        spin={-frame * 0.3}
      />
      <IridescentBubble
        size={100}
        x={-400}
        y={-50 + bubbleDrift}
        z={80}
        wobblePhase={frame}
      />
      <IridescentBubble
        size={80}
        x={410}
        y={40 - bubbleDrift}
        z={120}
        wobblePhase={frame + 45}
      />

      {/* ========================================================= */}
      {/* 3D LOGO HERO TILE (Official BAS-HAR Insignia)             */}
      {/* ========================================================= */}
      <div
        style={{
          transform: `translateY(${logoY}px) scale(${logoScale})`,
          position: "relative",
          marginBottom: 30,
        }}
      >
        {/* Soft Colored Ambient Floor Glow */}
        <div
          style={{
            position: "absolute",
            top: 40,
            left: -60,
            right: -60,
            bottom: -60,
            background:
              "radial-gradient(circle, rgba(47, 123, 255, 0.45) 0%, rgba(47, 123, 255, 0) 70%)",
            filter: "blur(36px)",
            zIndex: 0,
          }}
        />

        {/* The 3D Squircle Tile */}
        <div
          style={{
            width: 156,
            height: 156,
            borderRadius: 42,
            background: "linear-gradient(145deg, #1C2B48 0%, #0A0F1D 100%)",
            border: "2px solid rgba(91, 157, 255, 0.55)",
            boxShadow:
              "0 35px 80px rgba(10, 15, 30, 0.45), 0 12px 30px rgba(47, 123, 255, 0.28), inset 0 2px 3px rgba(255,255,255,0.45)",
            position: "relative",
            overflow: "hidden",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1,
          }}
        >
          {/* Anamorphic Gleam Light Sweep */}
          <div
            style={{
              position: "absolute",
              top: -20,
              bottom: -20,
              width: 80,
              background:
                "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.45) 50%, rgba(255,255,255,0) 100%)",
              transform: `translateX(${gleamX}px) skewX(-25deg)`,
              pointerEvents: "none",
            }}
          />

          {/* Official BAS-HAR Vector Insignia */}
          <svg
            width="100"
            height="100"
            viewBox="0 0 32 32"
            style={{ position: "relative", zIndex: 2 }}
          >
            {/* Orbit Arc */}
            <path
              d="M25.29 14.03A9.5 9.5 0 1 1 17.98 6.71"
              fill="none"
              stroke="#5B9DFF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            {/* Satellite Dot */}
            <circle cx="22.72" cy="9.28" r="2.4" fill="#FFFFFF" />
            {/* Verified Procedure Checkmark */}
            <polyline
              points="11.4 16.4 14.4 19.3 19.5 13.9"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {/* Main Title & Tagline */}
      <div
        style={{
          textAlign: "center",
          transform: `scale(${interpolate(
            textSpring,
            [0, 1],
            [0.85, 1]
          )})`,
        }}
      >
        <h1
          style={{
            fontSize: 84,
            fontWeight: 900,
            letterSpacing: "-0.04em",
            color: "#0E131F",
            margin: "0 0 10px 0",
            textShadow: "0 2px 24px rgba(0,0,0,0.06)",
          }}
        >
          BAS-HAR
        </h1>
        <p
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: "#6E7787",
            letterSpacing: "-0.02em",
            margin: "0 0 28px 0",
          }}
        >
          Autonomous Procedure Intelligence
        </p>
      </div>

      {/* Bharatiya Antariksh Station Pill Badge */}
      <div
        style={{
          transform: `scale(${interpolate(
            pillSpring,
            [0, 1],
            [0.75, 1]
          )})`,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "14px 34px",
            borderRadius: 999,
            backgroundColor: "#FFFFFF",
            boxShadow:
              "0 20px 50px rgba(0, 0, 0, 0.09), 0 4px 14px rgba(0,0,0,0.03)",
            border: "1.5px dashed #FF9500",
            position: "relative",
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: "#FF9500",
              boxShadow: "0 0 12px #FF9500",
            }}
          />
          <span
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#0E131F",
              letterSpacing: "-0.01em",
            }}
          >
            Bharatiya Antariksh Station · 2028
          </span>
        </div>
      </div>

      {/* Slogan & Verification Footer */}
      <div
        style={{
          position: "absolute",
          bottom: 44,
          textAlign: "center",
          color: "#8E8E93",
          fontSize: 15,
          fontWeight: 700,
          letterSpacing: 2.2,
          textTransform: "uppercase",
        }}
      >
        Describe it. Watch it. Trust it. · ISRO SIH26174
      </div>

      {/* Studio Floor Perspective Mirror Reflection */}
      <div
        style={{
          position: "absolute",
          bottom: -190,
          left: 0,
          right: 0,
          height: 240,
          transform: "scaleY(-1)",
          opacity: 0.16,
          filter: "blur(4px)",
          maskImage:
            "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 80%)",
          WebkitMaskImage:
            "linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0) 80%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            width: 156,
            height: 156,
            borderRadius: 42,
            background: "linear-gradient(145deg, #1C2B48 0%, #0A0F1D 100%)",
            marginBottom: 30,
          }}
        />
        <h1
          style={{
            fontSize: 84,
            fontWeight: 900,
            letterSpacing: "-0.04em",
            color: "#0E131F",
            margin: "0 0 10px 0",
          }}
        >
          BAS-HAR
        </h1>
      </div>
    </div>
  );
};
