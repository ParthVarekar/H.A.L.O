import React from "react";
import { interpolate, Easing } from "remotion";

const TUNNEL_CARDS = [
  // Left Wall Cards (Enclosing left flank, staggered along Z)
  {
    wall: "left",
    z: 350,
    color: "#007AFF",
    icon: "👁️",
    title: "Pose Estimation",
    sub: "25 FPS On-Board Jetson",
  },
  {
    wall: "left",
    z: -150,
    color: "#34C759",
    icon: "📦",
    title: "Dewar Hatch",
    sub: "Detected in 0.4s",
  },
  {
    wall: "left",
    z: -650,
    color: "#AF52DE",
    icon: "⚡",
    title: "Single-Pass VLM",
    sub: "Zero Payload Retraining",
  },
  {
    wall: "left",
    z: -1150,
    color: "#FF9500",
    icon: "🛡️",
    title: "Deterministic FSM",
    sub: "Zero Hallucination",
  },
  {
    wall: "left",
    z: -1650,
    color: "#00E5FF",
    icon: "📐",
    title: "3D Joint Spatial Math",
    sub: "Containment Geometry",
  },
  {
    wall: "left",
    z: -2150,
    color: "#FF2D55",
    icon: "⚠️",
    title: "Real-Time Catch",
    sub: "Sub-400ms Detection",
  },

  // Right Wall Cards (Enclosing right flank, staggered along Z)
  {
    wall: "right",
    z: 250,
    color: "#FF2D55",
    icon: "❄️",
    title: "Cryo Storage",
    sub: "MELFI -80°C Monitored",
  },
  {
    wall: "right",
    z: -250,
    color: "#00E5FF",
    icon: "🛰️",
    title: "100% Offline Edge",
    sub: "Zero Ground Dependency",
  },
  {
    wall: "right",
    z: -750,
    color: "#FFD60A",
    icon: "🔑",
    title: "Ed25519 Signed",
    sub: "Cryptographic Audit Log",
  },
  {
    wall: "right",
    z: -1250,
    color: "#30B0C7",
    icon: "🔊",
    title: "Voice Audio Alert",
    sub: "120ms Instant Interrupt",
  },
  {
    wall: "right",
    z: -1750,
    color: "#34C759",
    icon: "🌐",
    title: "YAML Procedure Plan",
    sub: "Experiment Agnostic",
  },
  {
    wall: "right",
    z: -2250,
    color: "#FF9500",
    icon: "🚀",
    title: "Bharatiya Antariksh",
    sub: "Designed for BAS 2028",
  },

  // Ceiling Cards (Enclosing top, staggered along Z)
  {
    wall: "top",
    z: 400,
    color: "#5856D6",
    icon: "📐",
    title: "Spatial Containment",
    sub: "3D Bounding Envelope",
  },
  {
    wall: "top",
    z: -100,
    color: "#FF375F",
    icon: "🧪",
    title: "Sample Reagent",
    sub: "Step 03 Verified",
  },
  {
    wall: "top",
    z: -600,
    color: "#34C759",
    icon: "✓",
    title: "8 / 8 Steps Verified",
    sub: "Real ISS Video Tested",
  },
  {
    wall: "top",
    z: -1100,
    color: "#007AFF",
    icon: "🚀",
    title: "Flight Qualified",
    sub: "Radiation Tolerant Ready",
  },
  {
    wall: "top",
    z: -1600,
    color: "#FF9500",
    icon: "⏱️",
    title: "Sub-400ms Loop",
    sub: "Immediate Feedback",
  },
  {
    wall: "top",
    z: -2100,
    color: "#00E5FF",
    icon: "📡",
    title: "Tamper-Proof Downlink",
    sub: "Signed JSONL Telemetry",
  },

  // Floor Cards (Enclosing bottom, staggered along Z)
  {
    wall: "bottom",
    z: 300,
    color: "#FF9500",
    icon: "⏳",
    title: "Zero Latency",
    sub: "No Ground Relays",
  },
  {
    wall: "bottom",
    z: -200,
    color: "#AF52DE",
    icon: "🔬",
    title: "Microgravity HAR",
    sub: "Orientation Invariant",
  },
  {
    wall: "bottom",
    z: -700,
    color: "#00E5FF",
    icon: "📡",
    title: "Downlink Protocol",
    sub: "Direct Telemetry Stream",
  },
  {
    wall: "bottom",
    z: -1200,
    color: "#34C759",
    icon: "🎯",
    title: "Precision Tracker",
    sub: "Zero False Alarms",
  },
  {
    wall: "bottom",
    z: -1700,
    color: "#FF2D55",
    icon: "🛑",
    title: "Mistake Prevention",
    sub: "Speaks Before Breach",
  },
  {
    wall: "bottom",
    z: -2200,
    color: "#5856D6",
    icon: "✨",
    title: "Edge Neural Model",
    sub: "Optimized TensorRT",
  },
];

export const TunnelScene = ({ frame, fps }) => {
  const localFrame = frame - 68;

  const opacity = interpolate(
    localFrame,
    [0, 4, 62, 64],
    [0, 1, 1, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // High-speed plunge through 3D corridor smoothly through frame 132
  const camZ = interpolate(localFrame, [0, 64], [-1400, 600], {
    easing: Easing.bezier(0.2, 0.05, 0.35, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Dynamic camera banking and roll
  const rotZ = interpolate(localFrame, [0, 22, 44, 64], [-6, 8, -5, 2]);
  const rotX = interpolate(localFrame, [0, 32, 64], [4, -3, 2]);
  const rotY = interpolate(localFrame, [0, 32, 64], [-5, 6, -2]);

  // Center Apple Intelligence pill flight
  const pillZ = interpolate(localFrame, [0, 34, 64], [600, 520, 450]);
  const pillScale = interpolate(localFrame, [0, 34, 64], [0.75, 1.15, 1.55]);

  // Rainbow Siri aura rotation
  const siriAngle = (localFrame * 9) % 360;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transformStyle: "preserve-3d",
        transform: `translateZ(${camZ}px) rotateZ(${rotZ}deg) rotateX(${rotX}deg) rotateY(${rotY}deg)`,
        opacity,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* 3D Fly-Through Tunnel Cards */}
      {TUNNEL_CARDS.map((card, idx) => {
        let wallTransform = "";
        if (card.wall === "left") {
          wallTransform = `translateX(-540px) translateY(${(idx % 2 === 0 ? -110 : 110)}px) translateZ(${card.z}px) rotateY(74deg)`;
        } else if (card.wall === "right") {
          wallTransform = `translateX(540px) translateY(${(idx % 2 === 0 ? 100 : -100)}px) translateZ(${card.z}px) rotateY(-74deg)`;
        } else if (card.wall === "top") {
          wallTransform = `translateY(-360px) translateX(${(idx % 2 === 0 ? -140 : 140)}px) translateZ(${card.z}px) rotateX(-72deg)`;
        } else {
          wallTransform = `translateY(360px) translateX(${(idx % 2 === 0 ? 130 : -130)}px) translateZ(${card.z}px) rotateX(72deg)`;
        }

        return (
          <div
            key={idx}
            style={{
              position: "absolute",
              transform: wallTransform,
              transformStyle: "preserve-3d",
              width: 440,
              height: 180,
              marginLeft: -220,
              marginTop: -90,
            }}
          >
            {/* Colorful Apple-Style Offset Backplate */}
            <div
              style={{
                position: "absolute",
                inset: -8,
                borderRadius: 32,
                backgroundColor: card.color,
                opacity: 0.92,
                transform: `translate3d(${idx % 2 === 0 ? 16 : -16}px, 14px, -18px) rotate(${idx % 2 === 0 ? 5 : -5}deg)`,
                boxShadow: `0 24px 50px ${card.color}66`,
              }}
            />

            {/* Front Frosted Glass Card */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: 28,
                backgroundColor: "rgba(255, 255, 255, 0.94)",
                backdropFilter: "blur(24px)",
                border: "2px solid rgba(255, 255, 255, 1)",
                boxShadow:
                  "0 35px 70px rgba(0, 0, 0, 0.14), 0 4px 16px rgba(0,0,0,0.05)",
                display: "flex",
                alignItems: "center",
                gap: 20,
                padding: "24px 28px",
                boxSizing: "border-box",
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 20,
                  backgroundColor: `${card.color}16`,
                  border: `2px solid ${card.color}44`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 32,
                  flexShrink: 0,
                }}
              >
                {card.icon}
              </div>
              <div>
                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 900,
                    color: "#0E131F",
                    letterSpacing: "-0.03em",
                    marginBottom: 6,
                  }}
                >
                  {card.title}
                </div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#6E7787",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {card.sub}
                </div>
              </div>
            </div>
          </div>
        );
      })}

      {/* Central Floating Apple Intelligence Pill in Corridor */}
      <div
        style={{
          position: "absolute",
          transform: `translateZ(${pillZ}px) scale(${pillScale})`,
          zIndex: 100,
          pointerEvents: "none",
        }}
      >
        {/* Pulsing Siri Rainbow Aura Ring */}
        <div
          style={{
            position: "absolute",
            inset: -12,
            borderRadius: 999,
            background: `conic-gradient(from ${siriAngle}deg, #FF6EA7, #A765FF, #45B8FE, #3EECAC, #FFE600, #FF7B54, #FF6EA7)`,
            filter: "blur(16px)",
            opacity: 0.9,
          }}
        />

        {/* Crisp Apple Intelligence Glass Pill */}
        <div
          style={{
            position: "relative",
            display: "inline-flex",
            alignItems: "center",
            gap: 22,
            padding: "22px 52px",
            borderRadius: 999,
            backgroundColor: "rgba(255, 255, 255, 0.96)",
            backdropFilter: "blur(36px)",
            border: "2.5px solid rgba(255, 255, 255, 1)",
            boxShadow:
              "0 35px 90px rgba(69, 184, 254, 0.4), 0 10px 30px rgba(0,0,0,0.1)",
          }}
        >
          {/* Animated Glowing AI Icon */}
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: "50%",
              background:
                "linear-gradient(135deg, #2F7BFF 0%, #AF52DE 50%, #FF2D55 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 20px rgba(47, 123, 255, 0.85)",
            }}
          >
            <span style={{ fontSize: 22 }}>✨</span>
          </div>

          <div style={{ textAlign: "left" }}>
            <div
              style={{
                fontSize: 32,
                fontWeight: 900,
                letterSpacing: "-0.04em",
                color: "#0E131F",
              }}
            >
              Autonomous Experiment Guardian
            </div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 800,
                color: "#2F7BFF",
                letterSpacing: 1.8,
                textTransform: "uppercase",
              }}
            >
              100% On-Board Edge Neural Vision
            </div>
          </div>
        </div>
      </div>

      {/* Kinetic Speed Particles & Bokeh Discs */}
      {Array.from({ length: 50 }).map((_, i) => {
        const xPos = ((i * 157) % 1800) - 900;
        const yPos = ((i * 241) % 1100) - 550;
        const zPos = ((i * 383) % 3600) - 1800;
        const colors = ["#45B8FE", "#FF6EA7", "#FFE600", "#3EECAC", "#FFFFFF", "#AF52DE"];
        const pColor = colors[i % colors.length];

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `calc(50% + ${xPos}px)`,
              top: `calc(50% + ${yPos}px)`,
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: pColor,
              transform: `translateZ(${zPos}px)`,
              boxShadow: `0 0 16px ${pColor}`,
              filter: `blur(${Math.abs(zPos) > 500 ? 3 : 0.5}px)`,
              opacity: 0.8,
              pointerEvents: "none",
            }}
          />
        );
      })}
    </div>
  );
};
