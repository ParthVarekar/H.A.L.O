import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { ProblemScene } from "./scenes/ProblemScene";
import { TunnelScene } from "./scenes/TunnelScene";
import { SolutionScene } from "./scenes/SolutionScene";
import { KineticPunchScene } from "./scenes/KineticPunchScene";
import { LogoScene } from "./scenes/LogoScene";

export const IntroVideo = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Snappy 2-frame optical gleam hits for punchy cuts (matching Kram.Visuals)
  const flash1 = interpolate(frame, [68, 69, 70], [0, 0.55, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flash2 = interpolate(frame, [133, 134, 135], [0, 0.55, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flash3 = interpolate(frame, [191, 192, 193], [0, 0.5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flash4 = interpolate(frame, [221, 222, 223], [0, 0.55, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const activeFlash = Math.max(flash1, flash2, flash3, flash4);

  // Floating Ambient Zero-G Bokeh Particles
  const ambientParticles = [
    { x: -620, y: -280, z: 320, s: 24, c: "#45B8FE", o: 0.55 },
    { x: 580, y: -220, z: 220, s: 30, c: "#FF6EA7", o: 0.5 },
    { x: -440, y: 280, z: 420, s: 18, c: "#3EECAC", o: 0.6 },
    { x: 520, y: 260, z: 160, s: 36, c: "#FFE600", o: 0.55 },
    { x: 40, y: -420, z: 480, s: 22, c: "#FFFFFF", o: 0.7 },
    { x: -700, y: 60, z: 120, s: 32, c: "#2F7BFF", o: 0.5 },
    { x: 720, y: -90, z: 360, s: 20, c: "#FF9500", o: 0.6 },
    { x: -280, y: -340, z: 200, s: 26, c: "#AF52DE", o: 0.5 },
    { x: 300, y: 340, z: 280, s: 22, c: "#45B8FE", o: 0.55 },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#F4F6FA",
        overflow: "hidden",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* Background Audio Track */}
      <Audio src={staticFile("audio_9s.mp3")} volume={1} />

      {/* Pristine Apple Studio Infinity Cove Radial Gradient */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 135% 115% at 50% 16%, #FFFFFF 0%, #F5F7FC 42%, #DEE4F0 100%)",
        }}
      />

      {/* Studio Floor Reflection & Shadow Plane */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "40%",
          background:
            "linear-gradient(to top, rgba(205,214,230,0.5) 0%, rgba(244,246,250,0) 100%)",
          borderTop: "1px solid rgba(255, 255, 255, 0.4)",
          pointerEvents: "none",
        }}
      />

      {/* Main 3D World Stage */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          perspective: 1200,
          perspectiveOrigin: "50% 50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 1920,
            height: 1080,
            transformStyle: "preserve-3d",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
        >
          {/* Floating Zero-G Ambient Bokeh */}
          {ambientParticles.map((p, idx) => {
            const floatY = Math.sin((frame + idx * 30) * 0.07) * 16;
            const floatX = Math.cos((frame + idx * 35) * 0.05) * 12;
            return (
              <div
                key={idx}
                style={{
                  position: "absolute",
                  left: `calc(50% + ${p.x + floatX}px)`,
                  top: `calc(50% + ${p.y + floatY}px)`,
                  width: p.s,
                  height: p.s,
                  borderRadius: "50%",
                  background: `radial-gradient(circle, ${p.c} 0%, ${p.c}00 70%)`,
                  transform: `translateZ(${p.z}px)`,
                  opacity: p.o,
                  filter: `blur(${p.z > 250 ? 4 : 1.5}px)`,
                  pointerEvents: "none",
                }}
              />
            );
          })}

          {/* ==================================================== */}
          {/* SCENE 1: THE ZERO-G PROBLEM (Frames 0 - 70)          */}
          {/* ==================================================== */}
          {frame < 70 && <ProblemScene frame={frame} fps={fps} />}

          {/* ==================================================== */}
          {/* SCENE 2: 3D KINETIC TUNNEL FLY-THROUGH (68 - 132)    */}
          {/* ==================================================== */}
          {frame >= 68 && frame < 133 && (
            <TunnelScene frame={frame} fps={fps} />
          )}

          {/* ==================================================== */}
          {/* SCENE 3: THE 3D SOLUTION SHOWCASE (133 - 193)        */}
          {/* ==================================================== */}
          {frame >= 133 && frame < 194 && (
            <SolutionScene frame={frame} fps={fps} />
          )}

          {/* ==================================================== */}
          {/* SCENE 4: KINETIC TYPOGRAPHY PUNCH (192 - 224)        */}
          {/* ==================================================== */}
          {frame >= 192 && frame < 224 && (
            <KineticPunchScene frame={frame} fps={fps} />
          )}

          {/* ==================================================== */}
          {/* SCENE 5: THE GRAND FINALE LOGO REVEAL (222 - 270)    */}
          {/* ==================================================== */}
          {frame >= 222 && <LogoScene frame={frame} fps={fps} />}
        </div>
      </div>

      {/* Screen Flash Transition Overlays */}
      {activeFlash > 0 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "#FFFFFF",
            opacity: activeFlash,
            pointerEvents: "none",
            zIndex: 999,
          }}
        />
      )}
    </AbsoluteFill>
  );
};
