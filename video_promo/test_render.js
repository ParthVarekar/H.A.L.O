const path = require("path");
const { bundle } = require("@remotion/bundler");
const { renderMedia, selectComposition } = require("@remotion/renderer");

async function main() {
  console.log("Testing Remotion pipeline...");
  const entryPoint = path.resolve(__dirname, "src/index.js");
  const bundleLocation = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });
  console.log("Bundled at:", bundleLocation);

  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "TestComp",
    browserExecutable: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  });
  console.log("Selected composition:", composition.id);

  const outputLocation = path.resolve(__dirname, "out_test.mp4");
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation,
    browserExecutable: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    onProgress: ({ progress }) => {
      console.log(`Render progress: ${(progress * 100).toFixed(0)}%`);
    },
  });

  console.log("Test render successful! File created:", outputLocation);
}

main().catch((err) => {
  console.error("Test render failed:", err);
  process.exit(1);
});
