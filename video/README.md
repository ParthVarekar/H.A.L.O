# BAS-HAR videos

Two Remotion compositions live here. `Intro` is the long project intro; `Launch` is a
sub-10-second product launch cut.

## Commands

```bash
npm install
npm run dev            # Remotion Studio, scrub either composition
npm run render         # Intro   -> ../docs/assets/intro.mp4   (1089 frames, ~36 s)
npm run render:launch  # Launch  -> ../docs/assets/launch.mp4  (288 frames, 9.66 s)
```

- Single frame: `npx remotion still Launch out/frame.png --frame=200`.
- Both compositions are 1920×1080 at 30 fps.

## `Launch` — the 9.7-second launch cut

Three acts, one idea each.

| Frames | Act | What happens |
|---|---|---|
| 0–86 | The problem | A cold, desaturated zero-g void. The MELFI dewar's hatch swings open, tray 2 slides out, an amber alert fires. *"In orbit, a missed step is gone forever."* |
| 86–200 | The solution | A white flash, the world warms and saturates, a scan ring sweeps out, nine detection chips tumble in from off-screen and settle into an orbit, the alert flips green. *"BAS-HAR follows every step."* → *"And speaks the moment one is missed."* |
| 200–288 | The mark | The world rushes the camera and dissolves. The mark draws, the wordmark sets letter by letter, the tagline lands. |

Everything in the cut is real: the object names, states and step numbers are the plan's
(`activities/cold_stowage_melfi/plan.yaml`), and the alert wording is the app's own.

### How the motion works

- **A real 3D stage.** `src/launch/fx.tsx` `Stage` sets `perspective` on the viewport and
  `preserve-3d` on the world, then transforms the world by the inverse of the camera. Objects are
  placed with `translate3d(x, y, z)`, so the parallax between a chip at z=+230 and one at z=-230 is
  real, not faked.
- **A keyframed camera.** `KEYS` in `Launch.tsx` holds camera positions and rotations; `cameraAt()`
  eases between them. `ry` swings -26° → +30° across the first act, so the dewar's side and top
  plates rotate into view as it passes.
- **Depth of field.** `focus` is a camera key too, and racked to -260° during the flash for a focus
  pull. `depthBlur(z)` turns depth into a blur radius, so the background bokeh stays soft while the
  hero is sharp. UI text is pinned to `strength={0}` or capped so it never blurs.
- **Tumbling chips.** The Kram signature: each `Chip` starts at a random point far behind the
  camera, springs to its slot on a shared elliptical ring, and keeps a slow residual orbit. Entry
  is `useSpring`, so it lands without a bounce.
- **Everything is deterministic.** Particles and chip entry points come from Remotion's seeded
  `random()`, never `Math.random()`, so any frame re-renders identically.

### Where things live

| Path | What it is |
|---|---|
| `src/launch/Launch.tsx` | The whole timeline: camera keys, act boundaries, text beats, sound cues |
| `src/launch/fx.tsx` | 3D stage, camera, depth of field, sparkles, beams, grain, backdrop |
| `src/launch/world.tsx` | The dewar slab, hatch, tray, bubbles, tumbling chips |
| `src/launch/ui.tsx` | Detection boxes, glass cards, 3D word reveals, the mark |
| `src/launch/palette.ts` | Colours, fonts, easing curves |
| `public/audio/` | Shared SFX and music bed (the pad ducks under nothing here; the launch is cue-only) |

## `Intro` — the long cut

The project intro, 1920×1080, 30 fps, about 36 s, rendered to `docs/assets/intro.mp4`.

### Where things live

| Path | What it is |
|---|---|
| `src/Intro.tsx` | Scene order, durations and sound cues (the only place to retime the video), the dolly transition between scenes, and the music bed |
| `src/scenes.tsx` | One component per scene, one idea each |
| `src/components.tsx` | Motion toolkit: drifting backdrop, camera push, word-by-word headlines, 3D fly-in, sheen, burst, counters, animated logo |
| `src/theme.ts` | Colours, fonts, and the MELFI step list with their real completion times |
| `public/detections.json` | Real detector output (`activities/cold_stowage_melfi/models/detector.pt`) for the clip, frame by frame |
| `public/audio/voice.m4a` | The dashboard's own announcement, spoken by the Windows "Microsoft Heera" voice |
| `public/audio/pad.m4a` | Music bed: ambient chords over a soft 112 BPM pulse, synthesised for this video |
| `public/audio/sfx/` | Synthesised whoosh, tick, chime, impact and scan sounds, plus the dashboard's own 440 Hz alert tone |
| `public/footage/melfi.mp4` | Not committed; regenerate it with the command below |

## Regenerating the footage clip

The clip is 12 s of the committed ESA Ignis take, upscaled for the frame. Run from the repository
root:

```bash
ffmpeg -ss 12 -t 12 -i activities/cold_stowage_melfi/takes/slawosz_using_melfi-8821822197.mp4 -vf "scale=1536:864:flags=lanczos,unsharp=5:5:0.4" -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -an video/public/footage/melfi.mp4
```

Footage credit: ESA (European Space Agency), Ignis mission.
