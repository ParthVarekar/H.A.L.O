# Dataset Progress

Last updated: 2026-09-08

This file is the collaborator handoff for the current datasets.

## Current project state

- Repository: `HAR_for_BAS`
- Intended interface: React Training Studio at `http://127.0.0.1:5767/?workspace=studio`
- Current branch: `main`
- Current edge target: laptop with RTX 5050 8 GB VRAM and 24 GB RAM
- Active next task: annotate the MELFI video in the Training Studio
- Current MELFI annotation count: `0`
- MELFI model training: not started
- Concrete Hardening training: not a reliable trained model; the one-session quality gate is not usable for evaluation

## Activities stored in the repository

| Activity | Take | State | What exists |
|---|---|---|---|
| `cold_stowage_melfi` | `studying_cells_in_space-c2dce8af89` | Imported, ready for annotation | Video, plan, 8-step timeline, 0 annotations |
| `concrete_hardening_msl` | `Material_Sciences_test_1-17b6df0d55` | Annotated, not evaluation-ready | Video, plan, timeline, 87 annotation rows, 517 training images |

## MELFI video to annotate

The video is already copied into the repository, so a collaborator does not need the original Downloads path.

- Activity: `cold_stowage_melfi`
- Take: `studying_cells_in_space-c2dce8af89`
- Original filename: `studying cells in space.mp4`
- Recording session: `cold_stowage_melfi_session_001`
- Duration: `153.04` seconds
- Frame rate: approximately `25.0065` FPS
- Resolution: `768 x 432`
- Timeline coverage: `0.00–153.04` seconds with 8 contiguous records
- Annotation status: no bounding boxes yet

### MELFI procedure and timeline

| Step | Time range | Expected content |
|---|---:|---|
| `step_001` | 0–5 s | Title card and opening logos |
| `step_002` | 5–65 s | Interviewee explains Cold Stowage and MELFI |
| `step_003` | 65–75 s | MELFI freezer is shown |
| `step_004` | 75–85 s | Freezer/dewar compartments are shown |
| `step_005` | 85–95 s | Sample containers are shown |
| `step_006` | 95–105 s | MELFI control panel or display is shown |
| `step_007` | 105–143.04 s | Astronaut works with visible ISS equipment and a mounted computer |
| `step_008` | 143.04–153.04 s | ESA logo animation/end card |

### MELFI object classes

Use these exact class names in the Studio:

- `interviewee`
- `melfi_freezer`
- `dewar_compartment`
- `sample_container`
- `control_panel`
- `astronaut`
- `computer`
- `nasa_logo`
- `esa_logo`
- `title_card`

The plan also contains stable internal object IDs such as `interviewee_1` and `astronaut_1`; the visible class names above are what the annotation UI uses.

### What to box

Box only objects that are visibly present and identifiable in the selected frame. It is acceptable for a class to be absent from a frame. Do not guess hidden objects or identify generic ISS hardware as `melfi_freezer`. The astronaut and the mounted computer in the final live-action section are intentionally separate classes; surrounding hardware is not a class unless it is clearly the MELFI equipment.

For title/logo frames, box the visible title or logo only when it is large enough to identify consistently. Because the current quality gate counts every plan class, the collaborator should annotate the contextual classes consistently or flag them for a later plan revision before training.

## Next actions for the collaborator

1. Clone the repository and install the project using `training_guide.md`.
2. Start the Training Studio and open the existing `cold_stowage_melfi` activity.
3. In STEP 05, select take `studying_cells_in_space-c2dce8af89`.
4. Generate keyframes with sampling interval `40` frames. The MELFI video is about 3,826 frames; `40` gives roughly 1.6-second spacing and fits within the Studio's 120-keyframe limit.
5. For each frame, choose the correct class, drag its box, and press `Enter` or use `Save & next frame`.
6. Review the saved count and use STEP 06 to run the quality gate.
7. Do not train until the quality gate says that train, validation, and test data are non-empty and every required class has coverage.
8. When the MELFI dataset passes, use the `laptop_safe` preset first and evaluate before considering a larger run.

## Dataset rules

- A single video is useful for testing the pipeline but is not enough to measure generalization.
- Keep recording-session IDs unique for independent videos.
- Split by session, never by neighboring frames from the same video.
- For a meaningful MELFI baseline, add at least two more independent sessions after this one; ten or more varied sessions is a better robustness target.
- Keep train, validation, and test sessions separate.
- Do not call a failed quality gate a trained result.

## Concrete Hardening reference state

The first activity is retained as a schema and workflow reference:

- Activity: `concrete_hardening_msl`
- Take: `Material_Sciences_test_1-17b6df0d55`
- 87 annotation JSONL rows across `glovebag`, `container`, `mixing_tool`, `syringe`, `laptop`, and `esa_logo`
- 517 generated training images
- Validation and test splits were empty because there was only one session
- Two CUDA-resolved training attempts stopped before a valid evaluation result

This means the current repository demonstrates the full annotation pipeline, but it does not contain a trustworthy production detector yet.

## Important files

- `activities/cold_stowage_melfi/activity.yaml`: activity metadata
- `activities/cold_stowage_melfi/plan.yaml`: procedure and object contract
- `activities/cold_stowage_melfi/timeline.jsonl`: expected time ranges
- `activities/cold_stowage_melfi/takes.jsonl`: imported take metadata
- `activities/cold_stowage_melfi/takes/`: source video files
- `activities/<activity>/annotations.jsonl`: saved frame boxes
- `activities/<activity>/datasets/`: generated detector datasets
- `training_guide.md`: complete collaborator operating guide
- `HANDOVER.md`: engineering handoff and current implementation status
- `docs/architecture.md`: phase plan and locked architecture decisions
- `docs/progress_log.md`: chronological project checkpoints

## Definition of done for this dataset pass

- All intended MELFI keyframes are reviewed.
- Boxes use only the exact plan classes.
- Quality gate passes with non-empty train, validation, and test splits.
- A `laptop_safe` training run completes on CUDA or clearly reports why it fell back.
- Evaluation metrics and error cases are saved before any release decision.
