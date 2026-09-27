import React from "react";

export const HardwareModule = ({
  x = 0,
  y = 0,
  z = 0,
  rotateX = 8,
  rotateY = -18,
  rotateZ = 3,
  scale = 1,
  opacity = 1,
  frame = 0,
}) => {
  // Skeleton pulse and inference sweep
  const scanY = (frame * 3.5) % 320;
  const pulse = 0.8 + 0.2 * Math.sin(frame * 0.15);

  return (
    <div
      style={{
        position: "absolute",
        left: `calc(50% + ${x}px)`,
        top: `calc(50% + ${y}px)`,
        width: 580,
        height: 380,
        marginLeft: -290,
        marginTop: -190,
        transform: `translateZ(${z}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) rotateZ(${rotateZ}deg) scale(${scale})`,
        transformStyle: "preserve-3d",
        opacity,
        pointerEvents: "none",
      }}
    >
      {/* 3D Chassis Base (Space Gray & Machined Titanium) */}
      <div
        style={{
          width: 580,
          height: 380,
          borderRadius: 36,
          background:
            "linear-gradient(135deg, #2A313E 0%, #171C25 50%, #0D1117 100%)",
          border: "2px solid rgba(255, 255, 255, 0.25)",
          boxShadow:
            "0 45px 90px -20px rgba(8, 15, 30, 0.55), inset 0 2px 4px rgba(255,255,255,0.7), inset 0 -4px 8px rgba(0,0,0,0.8)",
          position: "relative",
          overflow: "hidden",
          padding: 16,
          boxSizing: "border-box",
        }}
      >
        {/* Diamond-cut Chamfer Edge Highlight */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: 34,
            boxShadow:
              "inset 1px 1px 1px rgba(255, 255, 255, 0.4), inset -1px -1px 2px rgba(0, 0, 0, 0.6)",
            pointerEvents: "none",
          }}
        />

        {/* Top Dual Optical Camera Lenses (Aerospace Stereoscopic Sensors) */}
        <div
          style={{
            position: "absolute",
            top: 22,
            right: 28,
            display: "flex",
            gap: 14,
            alignItems: "center",
            zIndex: 10,
          }}
        >
          {[0, 1].map((idx) => (
            <div
              key={idx}
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background:
                  "radial-gradient(circle at 35% 35%, #1A385C 0%, #081220 70%)",
                border: "2px solid #5A6980",
                boxShadow:
                  "0 2px 6px rgba(0,0,0,0.5), inset 0 0 8px rgba(47, 123, 255, 0.6)",
                position: "relative",
              }}
            >
              {/* Anti-reflective sapphire coating specular gleam */}
              <div
                style={{
                  position: "absolute",
                  top: 4,
                  left: 6,
                  width: 7,
                  height: 4,
                  borderRadius: "50%",
                  background: "rgba(255, 255, 255, 0.8)",
                  transform: "rotate(-30deg)",
                }}
              />
            </div>
          ))}
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#34C759",
              boxShadow: "0 0 8px #34C759",
              marginLeft: 4,
            }}
          />
        </div>

        {/* OLED Glass Screen Face */}
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 24,
            background:
              "linear-gradient(170deg, #090D14 0%, #06090E 100%)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow: "inset 0 0 30px rgba(0, 0, 0, 0.95)",
            position: "relative",
            overflow: "hidden",
            padding: "24px 28px",
            boxSizing: "border-box",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          {/* Subtle live radar grid lines */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundSize: "28px 28px",
              backgroundImage:
                "linear-gradient(to right, rgba(47, 123, 255, 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(47, 123, 255, 0.04) 1px, transparent 1px)",
              pointerEvents: "none",
            }}
          />

          {/* Laser Scan Sweep Line */}
          <div
            style={{
              position: "absolute",
              top: scanY,
              left: 0,
              right: 0,
              height: 2,
              background:
                "linear-gradient(90deg, transparent 0%, rgba(47, 123, 255, 0.8) 50%, transparent 100%)",
              boxShadow: "0 0 14px rgba(47, 123, 255, 0.9)",
              pointerEvents: "none",
            }}
          />

          {/* Screen Top Status Bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              zIndex: 2,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  backgroundColor: "#2F7BFF",
                  boxShadow: "0 0 8px #2F7BFF",
                }}
              />
              <span
                style={{
                  fontSize: 12,
                  fontFamily: "monospace",
                  fontWeight: 700,
                  letterSpacing: 1.5,
                  color: "#99BBE8",
                  textTransform: "uppercase",
                }}
              >
                BAS-HAR // ORBITAL VISION ENGINE
              </span>
            </div>
            <div
              style={{
                fontSize: 11,
                fontFamily: "monospace",
                color: "#34C759",
                backgroundColor: "rgba(52, 199, 89, 0.12)",
                padding: "3px 8px",
                borderRadius: 4,
                border: "1px solid rgba(52, 199, 89, 0.3)",
              }}
            >
              25 FPS · OFFLINE EDGE
            </div>
          </div>

          {/* Center AI Detection Viewport & Skeletal Pose Overlay */}
          <div
            style={{
              position: "relative",
              flex: 1,
              margin: "12px 0",
              borderRadius: 14,
              border: "1px dashed rgba(47, 123, 255, 0.25)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
              zIndex: 2,
            }}
          >
            {/* Live 3D AI Skeleton Wireframe */}
            <svg
              width="360"
              height="180"
              viewBox="0 0 360 180"
              style={{ opacity: 0.9 }}
            >
              {/* Arm / Hand Joints */}
              <line
                x1="80"
                y1="130"
                x2="150"
                y2="75"
                stroke="#2F7BFF"
                strokeWidth="2.5"
                strokeDasharray="4 2"
              />
              <line
                x1="150"
                y1="75"
                x2="220"
                y2="95"
                stroke="#2F7BFF"
                strokeWidth="2.5"
              />
              <line
                x1="220"
                y1="95"
                x2="270"
                y2="60"
                stroke="#34C759"
                strokeWidth="3"
              />

              {/* Joint Dots */}
              <circle cx="80" cy="130" r="5" fill="#2F7BFF" />
              <circle cx="150" cy="75" r="5" fill="#2F7BFF" />
              <circle cx="220" cy="95" r="6" fill="#34C759" />
              <circle
                cx="270"
                cy="60"
                r="7"
                fill="#34C759"
                style={{ filter: "drop-shadow(0 0 6px #34C759)" }}
              />

              {/* Bounding Box 1: Cryo Dewar Hatch */}
              <rect
                x="200"
                y="35"
                width="135"
                height="100"
                fill="none"
                stroke="#34C759"
                strokeWidth="1.8"
                rx="6"
              />
              <text
                x="205"
                y="30"
                fill="#34C759"
                fontSize="11"
                fontFamily="monospace"
                fontWeight="700"
              >
                dewar_hatch: 99.4%
              </text>

              {/* Bounding Box 2: Cryo Sample Pouch */}
              <rect
                x="65"
                y="45"
                width="100"
                height="80"
                fill="none"
                stroke="#2F7BFF"
                strokeWidth="1.5"
                strokeDasharray="3 3"
                rx="4"
              />
              <text
                x="70"
                y="40"
                fill="#2F7BFF"
                fontSize="10"
                fontFamily="monospace"
              >
                sample_vial: 98.1%
              </text>
            </svg>
          </div>

          {/* Bottom Telemetry Card Bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 14px",
              borderRadius: 12,
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              zIndex: 2,
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "#8E99A8",
                  letterSpacing: 1,
                  textTransform: "uppercase",
                }}
              >
                ACTIVE EXPERIMENT STEP 04 / 08
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: "#FFFFFF",
                  letterSpacing: "-0.01em",
                }}
              >
                Dewar Hatch Opened · Cryo Pouch Transferred
              </div>
            </div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                backgroundColor: "rgba(52, 199, 89, 0.18)",
                padding: "6px 12px",
                borderRadius: 999,
                border: "1px solid rgba(52, 199, 89, 0.4)",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: "#34C759",
                  boxShadow: "0 0 8px #34C759",
                }}
              />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#34C759",
                  fontFamily: "monospace",
                }}
              >
                VERIFIED (0.4s)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Deep Contact Shadow underneath the 3D unit */}
      <div
        style={{
          position: "absolute",
          top: 340,
          left: 40,
          width: 500,
          height: 90,
          borderRadius: "50%",
          background:
            "radial-gradient(ellipse at center, rgba(10, 20, 40, 0.42) 0%, rgba(10, 20, 40, 0.1) 50%, rgba(0,0,0,0) 75%)",
          filter: "blur(14px)",
          transform: "rotateX(70deg)",
          zIndex: -1,
        }}
      />
    </div>
  );
};
