import React from "react";
import { interpolate, spring } from "remotion";
import { KnitSphere, IridescentBubble, SoftSiliconeCube } from "../tactile/Spheres";
import { HardwareModule } from "../tactile/HardwareModule";

export const SolutionScene = ({ frame, fps }) => {
  const localFrame = frame - 133;

  const enterSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 14, stiffness: 120, mass: 0.95 },
  });

  const opacity = interpolate(
    localFrame,
    [0, 56, 59],
    [1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Cinematic 3D camera orbital swoop
  const camZ = interpolate(enterSpring, [0, 1], [-180, 0]);
  const rotY = interpolate(localFrame, [0, 60], [14, -8], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rotX = interpolate(localFrame, [0, 60], [-3, 3], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Zero-g floating drift
  const drift1 = Math.sin(frame * 0.07) * 10;
  const drift2 = Math.cos(frame * 0.08) * 8;

  // Bottom cards spring slide-up
  const cardsSpring = spring({
    frame: localFrame - 2,
    fps,
    config: { damping: 14, stiffness: 130 },
  });
  const cardsY = interpolate(cardsSpring, [0, 1], [60, 0]);

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
      {/* ========================================================= */}
      {/* 3D TACTILE SPHERES & OBJECTS (Kram.Visuals Aesthetics)     */}
      {/* ========================================================= */}
      {/* Blue Knitted Fabric Sphere (Left) */}
      <KnitSphere
        size={210}
        variant="blue"
        x={-520}
        y={-20 + drift1}
        z={100}
        counterRotX={rotX}
        counterRotY={rotY}
        spin={frame * 0.4}
      />

      {/* Heather Grey Tweed Wool Sphere (Bottom Right) */}
      <KnitSphere
        size={190}
        variant="grey"
        x={500}
        y={120 + drift2}
        z={-20}
        counterRotX={rotX}
        counterRotY={rotY}
        spin={-frame * 0.3}
      />

      {/* Green Knitted Fabric Sphere (Top Right) */}
      <KnitSphere
        size={160}
        variant="green"
        x={460}
        y={-150 - drift1}
        z={150}
        counterRotX={rotX}
        counterRotY={rotY}
        spin={frame * 0.5}
      />

      {/* Soft Chamfered Pink Silicone Cube */}
      <SoftSiliconeCube
        size={110}
        x={-420}
        y={180 - drift2}
        z={60}
        rotateX={24 + frame * 0.3}
        rotateY={-30 + frame * 0.4}
        rotateZ={14}
      />

      {/* Floating Microgravity Iridescent Bubbles */}
      <IridescentBubble
        size={110}
        x={-280}
        y={-200 + drift2}
        z={200}
        counterRotX={rotX}
        counterRotY={rotY}
        wobblePhase={frame}
      />
      <IridescentBubble
        size={85}
        x={290}
        y={210 - drift1}
        z={240}
        counterRotX={rotX}
        counterRotY={rotY}
        wobblePhase={frame + 45}
      />
      <IridescentBubble
        size={65}
        x={-240}
        y={180 + drift1}
        z={120}
        counterRotX={rotX}
        counterRotY={rotY}
        wobblePhase={frame + 90}
      />
      <IridescentBubble
        size={95}
        x={360}
        y={-70 + drift2}
        z={260}
        counterRotX={rotX}
        counterRotY={rotY}
        wobblePhase={frame + 120}
      />

      {/* ========================================================= */}
      {/* CENTRAL 3D HARDWARE MODULE (BAS-HAR Edge Station)         */}
      {/* ========================================================= */}
      <HardwareModule
        x={0}
        y={15}
        z={30}
        rotateX={interpolate(localFrame, [0, 60], [5, -3])}
        rotateY={interpolate(localFrame, [0, 60], [-12, 8])}
        rotateZ={interpolate(localFrame, [0, 60], [1.5, -1.5])}
        scale={interpolate(enterSpring, [0, 1], [0.92, 1])}
        frame={frame}
      />

      {/* ========================================================= */}
      {/* APPLE-STYLE SOLUTION HEADLINE & PILL BAR                  */}
      {/* ========================================================= */}
      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          textAlign: "center",
          transform: `translateZ(20px)`,
          zIndex: 40,
        }}
      >
        {/* Sleek Expanding Apple Search Pill */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "8px 22px",
            borderRadius: 999,
            backgroundColor: "rgba(255, 255, 255, 0.94)",
            backdropFilter: "blur(24px)",
            border: "1.5px solid rgba(255, 255, 255, 0.98)",
            boxShadow:
              "0 18px 45px rgba(47, 123, 255, 0.16), 0 4px 12px rgba(0,0,0,0.04)",
            marginBottom: 10,
          }}
        >
          <div
            style={{
              width: 11,
              height: 11,
              borderRadius: "50%",
              backgroundColor: "#2F7BFF",
              boxShadow: "0 0 12px #2F7BFF",
            }}
          />
          <span
            style={{
              fontSize: 18,
              fontWeight: 800,
              color: "#0E131F",
              letterSpacing: "-0.02em",
            }}
          >
            Autonomous Procedure Recognition
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              color: "#2F7BFF",
              padding: "3px 9px",
              borderRadius: 999,
              backgroundColor: "rgba(47, 123, 255, 0.12)",
              textTransform: "uppercase",
              letterSpacing: 1.4,
            }}
          >
            100% Offline Edge
          </span>
        </div>

        <h2
          style={{
            fontSize: 44,
            fontWeight: 900,
            letterSpacing: "-0.04em",
            color: "#0E131F",
            margin: "0 0 4px 0",
            textShadow: "0 2px 14px rgba(0,0,0,0.05)",
          }}
        >
          An on-board second pair of eyes.
        </h2>
        <p
          style={{
            fontSize: 19,
            fontWeight: 600,
            color: "#6E7787",
            letterSpacing: "-0.01em",
            margin: 0,
          }}
        >
          Watches every step. Speaks up the moment one is missed.
        </p>
      </div>

      {/* ========================================================= */}
      {/* 3D FAN OF TELEMETRY FEATURE CARDS (Bottom Display)        */}
      {/* ========================================================= */}
      <div
        style={{
          position: "absolute",
          bottom: 38,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 24,
          transformStyle: "preserve-3d",
          transform: `translateY(${cardsY}px) translateZ(25px)`,
          zIndex: 40,
        }}
      >
        {/* Card 1: ISS Proven */}
        <div
          style={{
            ...featureCardStyle,
            transform: "rotateY(5deg)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <span
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                backgroundColor: "#34C759",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 12,
              }}
            >
              ✓
            </span>
            <span style={{ fontSize: 11, fontWeight: 800, color: "#34C759", letterSpacing: 1.2 }}>
              PROVEN IN ORBIT
            </span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: "#0E131F", marginBottom: 2 }}>
            8 / 8 Steps Verified
          </div>
          <div style={{ fontSize: 12, color: "#6E7787", fontWeight: 600, lineHeight: 1.3 }}>
            Real ISS Ignis mission video. Zero false alerts at 25 fps.
          </div>
        </div>

        {/* Card 2: 0.4s Single-Pass VLM */}
        <div
          style={{
            ...featureCardStyle,
            transform: "scale(1.02)",
            borderColor: "rgba(47, 123, 255, 0.45)",
            boxShadow:
              "0 22px 55px rgba(47, 123, 255, 0.18), 0 4px 12px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <span
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                backgroundColor: "#2F7BFF",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 12,
              }}
            >
              ⚡
            </span>
            <span style={{ fontSize: 11, fontWeight: 800, color: "#2F7BFF", letterSpacing: 1.2 }}>
              DESCRIBED MODE
            </span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: "#0E131F", marginBottom: 2 }}>
            0.4s Single-Pass VLM
          </div>
          <div style={{ fontSize: 12, color: "#6E7787", fontWeight: 600, lineHeight: 1.3 }}>
            Plain-English questions. Zero retraining for new payloads.
          </div>
        </div>

        {/* Card 3: Zero Hallucination FSM */}
        <div
          style={{
            ...featureCardStyle,
            transform: "rotateY(-5deg)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <span
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                backgroundColor: "#FF9500",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: 12,
              }}
            >
              🛡️
            </span>
            <span style={{ fontSize: 11, fontWeight: 800, color: "#FF9500", letterSpacing: 1.2 }}>
              ZERO HALLUCINATION
            </span>
          </div>
          <div style={{ fontSize: 20, fontWeight: 900, color: "#0E131F", marginBottom: 2 }}>
            Deterministic FSM
          </div>
          <div style={{ fontSize: 12, color: "#6E7787", fontWeight: 600, lineHeight: 1.3 }}>
            State deltas, containment math & instant priority audio.
          </div>
        </div>
      </div>
    </div>
  );
};

const featureCardStyle = {
  width: 310,
  padding: "18px 20px",
  borderRadius: 22,
  backgroundColor: "rgba(255, 255, 255, 0.94)",
  backdropFilter: "blur(24px)",
  border: "1.5px solid rgba(255, 255, 255, 0.98)",
  boxShadow:
    "0 18px 40px rgba(0, 0, 0, 0.07), 0 4px 12px rgba(0, 0, 0, 0.02)",
  textAlign: "left",
};
