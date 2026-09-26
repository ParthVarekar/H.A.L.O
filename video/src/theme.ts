import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const color = {
  bg: "#f6f7f9",
  surface: "#ffffff",
  surface2: "#f1f3f6",
  line: "rgba(12, 20, 36, 0.08)",
  lineStrong: "rgba(12, 20, 36, 0.14)",
  text: "#0b0e13",
  text2: "#4b5563",
  text3: "#8a93a0",
  accent: "#2f7bff",
  accentSoft: "rgba(47, 123, 255, 0.10)",
  ok: "#12a26a",
  okSoft: "rgba(18, 162, 106, 0.12)",
  warn: "#c47a06",
  warnSoft: "rgba(196, 122, 6, 0.10)",
};

export const font = {
  display: "Space Grotesk",
  text: "Inter",
  mono: "JetBrains Mono",
};

export const shadow = "0 30px 70px -34px rgba(20, 40, 80, 0.28), 0 2px 6px rgba(20, 40, 80, 0.05)";

export function loadFonts(): Promise<unknown> {
  return Promise.all([
    loadFont({ family: font.display, url: staticFile("fonts/space-grotesk-latin-wght-normal.woff2"), weight: "300 700" }),
    loadFont({ family: font.text, url: staticFile("fonts/inter-latin-wght-normal.woff2"), weight: "100 900" }),
    loadFont({ family: font.mono, url: staticFile("fonts/jetbrains-mono-latin-wght-normal.woff2"), weight: "100 800" }),
  ]);
}

export const STEPS = [
  { title: "Hold up the sample pouch", time: "0:00.2" },
  { title: "Open the dewar 1 hatch", time: "0:12.9" },
  { title: "Pull tray 2 out of dewar 1", time: "0:15.4" },
  { title: "Open compartment 1", time: "0:21.1" },
  { title: "Place the sample inside", time: "0:22.4" },
  { title: "Close compartment 1", time: "0:27.3" },
  { title: "Slide tray 2 back in", time: "0:35.1" },
  { title: "Close the hatch and latch it", time: "0:42.8" },
];
