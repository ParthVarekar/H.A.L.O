import path from "path";
import { fileURLToPath } from "url";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("=== BAS-HAR Apple 3D Motion Intro Render ===");
  const entryPoint = path.resolve(__dirname, "src/index.jsx");

  console.log("Bundling Remotion React composition...");
  const bundleLocation = await bundle({
    entryPoint,
    publicDir: path.resolve(__dirname, "public"),
    webpackOverride: (config) => config,
  });
  console.log("Bundled successfully!");

  console.log("Selecting composition IntroVideo...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "IntroVideo",
    browserExecutable: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  });
  console.log(`Composition: ${composition.id} (${composition.durationInFrames} frames @ ${composition.fps}fps)`);

  const outputLocation = path.resolve(__dirname, "../output/BAS_HAR_Intro_Apple_Style.mp4");
  console.log("Rendering to:", outputLocation);

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation,
    browserExecutable: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    onProgress: ({ progress, renderedFrames }) => {
      if (renderedFrames % 30 === 0 || progress === 1) {
        console.log(`Progress: ${(progress * 100).toFixed(1)}% (${renderedFrames}/${composition.durationInFrames} frames)`);
      }
    },
  });

  console.log("=== Render Complete! File created at: ===");
  console.log(outputLocation);
}

main().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});
