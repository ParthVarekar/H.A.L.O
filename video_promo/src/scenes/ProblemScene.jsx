import React from "react";
import { interpolate, spring } from "remotion";
import { IridescentBubble } from "../tactile/Spheres";

export const ProblemScene = ({ frame, fps }) => {
  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 120 },
  });

  const opacity = interpolate(frame, [0, 8, 63, 69], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fast camera pull-in trajectory
  const camZ = interpolate(frame, [0, 48, 70], [0, 240, 950], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rotY = interpolate(frame, [0, 70], [-10, 14], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rotX = interpolate(frame, [0, 70], [6, -4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 3D Warning Cards flight paths (flying out towards the camera)
  const card1Z = interpolate(frame, [8, 72], [-100, 750]);
  const card2Z = interpolate(frame, [12, 72], [-160, 800]);
  const card3Z = interpolate(frame, [16, 72], [-80, 700]);
  const card4Z = interpolate(frame, [20, 72], [-140, 760]);

  // Microgravity floating cryo canister in background (offset to the right)
  const canisterFloatY = Math.sin(frame * 0.08) * 12;
  const canisterRotY = 24 + frame * 0.5;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transformStyle: "preserve-3d",
        transform: `translateZ(${camZ}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`,
        opacity,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Floating Microgravity Bubbles */}
      <IridescentBubble size={150} x={-520} y={-180 + canisterFloatY} z={160} wobblePhase={frame} />
      <IridescentBubble size={95} x={-360} y={220 - canisterFloatY} z={240} wobblePhase={frame + 30} />
      <IridescentBubble size={75} x={420} y={240} z={90} wobblePhase={frame + 60} />
      <IridescentBubble size={120} x={580} y={-240} z={310} wobblePhase={frame + 90} />

      {/* 3D Floating Cryogenic Sample Module (Floating on Right Side) */}
      <div
        style={{
          position: "absolute",
          left: "calc(50% + 460px)",
          top: `calc(50% + ${-40 + canisterFloatY}px)`,
          transform: `translateZ(60px) rotateY(${canisterRotY}deg) rotateX(16deg) rotateZ(-6deg)`,
          width: 250,
          height: 250,
          borderRadius: 48,
          background:
            "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(220,230,245,0.85) 50%, rgba(180,200,225,0.9) 100%)",
          border: "2px solid rgba(255,255,255,0.9)",
          boxShadow:
            "0 40px 80px -15px rgba(20, 35, 60, 0.35), inset 0 2px 4px rgba(255,255,255,0.95)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transformStyle: "preserve-3d",
        }}
      >
        {/* Core Cryo Dewar Circular Port */}
        <div
          style={{
            width: 130,
            height: 130,
            borderRadius: "50%",
            background:
              "radial-gradient(circle at 35% 35%, #182A45 0%, #08101E 70%)",
            border: "5px solid #D2DCE8",
            boxShadow:
              "inset 0 10px 25px rgba(0,0,0,0.85), 0 0 24px rgba(47, 123, 255, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
        >
          {/* Glowing Liquid Nitrogen Vapor Glow */}
          <div
            style={{
              width: 75,
              height: 75,
              borderRadius: "50%",
              background:
                "radial-gradient(circle, rgba(91,157,255,0.85) 0%, rgba(91,157,255,0) 70%)",
              filter: "blur(8px)",
              opacity: 0.7 + 0.3 * Math.sin(frame * 0.2),
            }}
          />
          <span style={{ fontSize: 32, zIndex: 2 }}>❄️</span>
        </div>
        <div
          style={{
            marginTop: 12,
            fontSize: 11,
            fontFamily: "monospace",
            fontWeight: 800,
            letterSpacing: 2,
            color: "#475569",
          }}
        >
          MELFI CORE -80°C
        </div>
      </div>

      {/* Center Cinematic Problem Headline */}
      <div
        style={{
          textAlign: "center",
          transform: `translateZ(80px) scale(${interpolate(
            enterSpring,
            [0, 1],
            [0.85, 1]
          )})`,
          maxWidth: 1060,
          zIndex: 20,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            padding: "9px 24px",
            borderRadius: 999,
            backgroundColor: "rgba(255, 59, 48, 0.12)",
            border: "1.5px solid rgba(255, 59, 48, 0.35)",
            color: "#D70015",
            fontSize: 16,
            fontWeight: 800,
            letterSpacing: 1.8,
            textTransform: "uppercase",
            marginBottom: 24,
            boxShadow: "0 10px 30px rgba(255,59,48,0.16)",
          }}
        >
          <span
            style={{
              width: 9,
              height: 9,
              borderRadius: "50%",
              backgroundColor: "#FF3B30",
              boxShadow: "0 0 12px #FF3B30",
            }}
          />
          The Zero-G Reality
        </div>

        <h1
          style={{
            fontSize: 78,
            fontWeight: 900,
            letterSpacing: "-0.04em",
            lineHeight: 1.05,
            color: "#0B0E14",
            margin: "0 0 16px 0",
            textShadow: "0 2px 20px rgba(0,0,0,0.06)",
          }}
        >
          In microgravity, one missed step...
        </h1>

        <p
          style={{
            fontSize: 34,
            fontWeight: 600,
            color: "#5B6475",
            letterSpacing: "-0.02em",
            margin: 0,
          }}
        >
          destroys months of irreplaceable science.
        </p>
      </div>

      {/* Floating 3D Warning Badges Erupting Past Camera */}
      {/* Badge 1: Top-Left */}
      <div
        style={{
          position: "absolute",
          top: "14%",
          left: "8%",
          transform: `translate3d(0, 0, ${card1Z}px) rotateY(24deg) rotateX(-12deg) rotateZ(-5deg)`,
          ...glassWarningCardStyle,
          borderColor: "rgba(255, 59, 48, 0.4)",
          boxShadow:
            "0 24px 60px rgba(255,59,48,0.18), 0 4px 16px rgba(0,0,0,0.04)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: "rgba(255, 59, 48, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
            }}
          >
            ⚠️
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#8E8E93", fontWeight: 700, letterSpacing: 1.2 }}>
              PROCEDURE ANOMALY
            </div>
            <div style={{ fontSize: 22, color: "#D70015", fontWeight: 800 }}>
              Step 04 Skipped Ahead
            </div>
          </div>
        </div>
      </div>

      {/* Badge 2: Bottom-Right */}
      <div
        style={{
          position: "absolute",
          bottom: "16%",
          right: "7%",
          transform: `translate3d(0, 0, ${card2Z}px) rotateY(-26deg) rotateX(14deg) rotateZ(4deg)`,
          ...glassWarningCardStyle,
          borderColor: "rgba(255, 149, 0, 0.45)",
          boxShadow:
            "0 24px 60px rgba(255,149,0,0.18), 0 4px 16px rgba(0,0,0,0.04)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: "rgba(255, 149, 0, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
            }}
          >
            ❄️
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#8E8E93", fontWeight: 700, letterSpacing: 1.2 }}>
              MELFI FREEZER
            </div>
            <div style={{ fontSize: 22, color: "#FF9500", fontWeight: 800 }}>
              −80°C Sample Compromised
            </div>
          </div>
        </div>
      </div>

      {/* Badge 3: Bottom-Left */}
      <div
        style={{
          position: "absolute",
          bottom: "12%",
          left: "10%",
          transform: `translate3d(0, 0, ${card3Z}px) rotateY(16deg) rotateX(8deg)`,
          ...glassWarningCardStyle,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              backgroundColor: "rgba(47, 123, 255, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
            }}
          >
            📡
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#8E8E93", fontWeight: 700, letterSpacing: 1 }}>
              MISSION CONTROL
            </div>
            <div style={{ fontSize: 19, color: "#1C1C1E", fontWeight: 700 }}>
              42-Min Ground Latency
            </div>
          </div>
        </div>
      </div>

      {/* Badge 4: Top-Right */}
      <div
        style={{
          position: "absolute",
          top: "16%",
          right: "9%",
          transform: `translate3d(0, 0, ${card4Z}px) rotateY(-18deg) rotateX(-8deg)`,
          ...glassWarningCardStyle,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              backgroundColor: "rgba(175, 82, 222, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
            }}
          >
            ⏳
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#8E8E93", fontWeight: 700, letterSpacing: 1 }}>
              CREW WORKLOAD
            </div>
            <div style={{ fontSize: 19, color: "#1C1C1E", fontWeight: 700 }}>
              High Task Saturation
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const glassWarningCardStyle = {
  padding: "20px 30px",
  borderRadius: 26,
  backgroundColor: "rgba(255, 255, 255, 0.9)",
  backdropFilter: "blur(24px)",
  border: "1.5px solid rgba(255, 255, 255, 0.95)",
  boxShadow: "0 24px 50px rgba(0, 0, 0, 0.08), 0 4px 16px rgba(0,0,0,0.03)",
};
