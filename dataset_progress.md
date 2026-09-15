# Dataset Progress

Last updated: 2026-09-15

This file tracks the current state of every activity package's data: takes, boxes, dataset, and
training/evaluation status.

## Current project state

- Repository: `HAR_for_BAS`
- Interface: React Training Studio at `http://127.0.0.1:5767/?workspace=studio`
- Current branch: `main`
- Edge target: laptop with RTX 5050 8 GB VRAM and 24 GB RAM
- The project owner boxes MELFI themselves; there is no separate collaborator/friend workflow

## Activities stored in the repository

| Activity | Take | State | What exists |
|---|---|---|---|
| `cold_stowage_melfi` | `slawosz_using_melfi-8821822197` | Boxed, trained, tested | Video, plan v1.1.0, 8-step timeline, 775 boxes on 55 frames, `models/detector.pt` installed |
| `studying_cells_lsg` | `studying_cells_in_space-c2dce8af89` | Archived reference | The take, 70 boxes, timeline, dataset and detector this activity had before it was found not to be MELFI footage; kept for a later broad video showcase, not being extended |
| `concrete_hardening_msl` | `Material_Sciences_test_1-17b6df0d55` | Annotated, not evaluation-ready | Video, plan, timeline, 87 annotation rows, 517 training images; boxes found unreliable (container boxes drawn on subtitles) — do not train on this without re-annotating |
| `foaming_fluid_science` | `stuying_fluid_sciences_in_space-4fe26c68f3` | Annotated | 46 boxes, all classes covered; a detector exists but recognition/monitoring for it has not been re-verified since the MELFI-only push |

## MELFI activity (`cold_stowage_melfi`)

The video is stored in the repository, so no Downloads path is required.

- Activity: `cold_stowage_melfi`, name "MELFI Sample Stowage (Ignis)"
- Take: `slawosz_using_melfi-8821822197`
- Original filename: `slawosz_using_melfi.mp4`
- Recording session: `melfi_ignis_session_001`
- Duration: `67.16` seconds, `~25.01` FPS, `768 x 432`
- Plan version: `1.1.0`
- Timeline: 8 records, one per step, derived from where the owner's boxes show each state changing
- Annotation status: 775 boxes on 55 frames (every 30th frame plus denser passes)
- Detector: `activities/cold_stowage_melfi/models/detector.pt` (yolo11n, image size 768, no
  horizontal flip — flipping would swap dewar/tray quadrant numbers and latch left/right)

### What the video shows

ESA astronaut Slawosz (Ignis mission) stores a sample pouch in MELFI, the ISS's -80°C lab freezer.
MELFI has 4 dewars, each with 4 trays, each tray with 2 compartments. Numbering follows quadrants
as seen facing the open MELFI door: **1 top-right, 2 top-left, 3 bottom-left, 4 bottom-right**
(confirmed against the video — Slawosz opens the top-right door, "dewar 1"). Compartment 1 is the
one nearest the hatch.

### MELFI object classes

Use these exact class names in the Studio. Classes marked with states get a state dropdown when
boxing; the detector treats each class+state pair (e.g. `dewar_hatch__open`) as its own YOLO class.

| Object | Classes | States |
|---|---|---|
| Sample pouch | `sample` | — |
| MELFI unit | `melfi_freezer` | — |
| Dewars | `dewar_1`, `dewar_2`, `dewar_3`, `dewar_4` | — |
| Dewar latch | `dewar_latch` | `left` (closed), `right` (open) |
| Dewar hatch | `dewar_hatch` | `open`, `closed` |
| Trays | `tray_1`, `tray_2`, `tray_3`, `tray_4` | `in`, `out` |
| Compartments | `compartment_1`, `compartment_2` | `open`, `closed` |
| Compartment knob | `compartment_knob` | — |
| Astronauts | `astronaut_slawosz`, `astronaut_other` | — |
| Issue markers | `ice_vapor`, `fabric` | — |
| End card | `logo` | — |

`tray_3` in the `out` state and `compartment_2` in the `open` state never occur in this take, so
they have zero training boxes; that is expected, not a labelling gap.

### What to box

Box every visibly identifiable object, including one box nested inside another (for example the
sample inside the open compartment, inside tray 2, inside dewar 1). Do not guess a hidden object's
state — leave a box's state unset only if the Studio genuinely doesn't require one for that class.

### MELFI procedure (8 steps, plan v1.1.0)

Each step checks exactly one observable state change (earlier drafts bundled several actions into
one step; that was split apart after testing against the video):

1. Holds the sample pouch in front of MELFI — `sample` visible
2. Opens the dewar 1 hatch — `dewar_hatch` state `open`
3. Pulls tray 2 out of dewar 1 — `tray_2` state `out`
4. Opens compartment 1 with its knob — `compartment_1` state `open`
5. Places the sample inside the open compartment 1 — `sample` `inside_of` `compartment_1`, plus
   `compartment_1` still `open`
6. Closes compartment 1 — `compartment_1` state `closed`
7. Slides tray 2 back into dewar 1 — `tray_2` state `in`
8. Closes the dewar 1 hatch and turns the latch back to left — `dewar_hatch` state `closed` and
   `dewar_latch` state `left`, both `inside_of` `dewar_1`

Two issues were noted from the video for a future alert (not yet built — the owner said to add
this after training): ice vapour bursts near Slawosz's face around step 7, and fabric obstructs
the hatch closing around step 8. The `ice_vapor` and `fabric` classes are already boxed so no
re-annotation will be needed when that alert is built.

### Verified result

Running the take through the dashboard (either by choosing "MELFI Sample Stowage" in the
Experiment picker or via auto-detect scene recognition) completes all 8 steps in order with no
skip, out-of-order, or pause alerts, each within about a second of the state-change time visible
in the owner's own boxes. Playback runs at the video's real 25 fps with GPU-accelerated detection
and JPEG encoding.

## Dataset rules

- A single video is useful for testing the pipeline but is not enough to measure generalisation.
  All current MELFI results are internal consistency checks on the same video the model trained on.
- Keep recording-session IDs unique for independent videos.
- Split by session, never by neighbouring frames from the same video.
- Do not use the Studio's own "Start laptop-safe training" button on `cold_stowage_melfi` — it
  still mirrors images left-right by default, which is wrong for a plan with quadrant-numbered
  and left/right-stated classes. Train with `scripts/train_yolo.py` (or an equivalent call to
  `ultralytics.YOLO.train`) with `fliplr=0` instead.

## Important files

- `activities/cold_stowage_melfi/activity.yaml`: activity metadata
- `activities/cold_stowage_melfi/plan.yaml`: procedure, objects, and states
- `activities/cold_stowage_melfi/timeline.jsonl`: expected time ranges
- `activities/cold_stowage_melfi/takes.jsonl`: imported take metadata
- `activities/cold_stowage_melfi/takes/`: source video files
- `activities/cold_stowage_melfi/annotations.jsonl`: saved frame boxes (775 rows)
- `activities/cold_stowage_melfi/models/detector.pt`: the installed detector
- `activities/<activity>/datasets/`: generated detector datasets
- `training_guide.md`: Studio operating guide
- `HANDOVER.md` / `CLAUDE_CODE_HANDOVER.md`: engineering handoff and current implementation status
- `docs/architecture.md`: phase plan and locked architecture decisions
- `docs/progress_log.md`: chronological project checkpoints (see Checkpoints 27-32)

## Definition of done for the current MELFI milestone

- [x] Real MELFI video imported and boxed with owner-supplied context
- [x] States (open/closed, in/out, left/right) and nested boxes represented
- [x] Detector trained and installed
- [x] All 8 steps verified end to end on the source video with no false alerts
- [x] Dashboard plays uploaded video at real speed with GPU-accelerated detection
- [ ] A second, independent MELFI recording session (needed before any generalisation claim)
- [ ] Ice-vapour / fabric issue alerts (deferred, owner will say when to start)
