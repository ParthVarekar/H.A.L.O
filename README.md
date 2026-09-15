# HAR_for_BAS

Human activity recognition for Bharatiya Antariksh Station experiments and operations.

The repository contains the React Training Studio, the schema-first procedure engine, activity
packages, annotation data, and the reproducible training/evaluation pipeline.

## Quick start

    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -e ".[perception,streaming,voice,studio,dev]"
    startup_training_studio.bat

Open http://127.0.0.1:5767/?workspace=studio.

To run the complete local check:

    cmd /c startup.bat test

To stop everything a launcher started:

    close_startup.bat              # closes what startup.bat started
    close_training_studio.bat      # closes what startup_training_studio.bat started

## Current state (2026-09-15)

`cold_stowage_melfi` now holds the real MELFI video (`slawosz_using_melfi.mp4`, ESA astronaut
Slawosz stowing a sample during the Ignis mission), replacing the earlier take, which was moved
intact to its own activity, `studying_cells_lsg`. The owner boxed 55 frames (775 boxes) across 20
objects — including per-object states (hatch/compartment open-closed, tray in-out, latch
left-right) and boxes nested inside other boxes — and a detector has been trained and installed.
Running the video through the dashboard completes all 8 steps in order with no false alerts.

- Claude Code handover: CLAUDE_CODE_HANDOVER.md
- Dataset progress: dataset_progress.md
- Training Studio guide: training_guide.md
- Engineering handover: HANDOVER.md
- Architecture: docs/architecture.md
- Validation matrix: docs/validation_matrix.md
- Risk register: docs/risk_register.md
- Progress log: docs/progress_log.md (see Checkpoints 27-32 for the most recent work)

## Scope notes

The React Studio on port 5767 is authoritative for annotation. The procedure FSM is the primary
sequence engine, now with per-object state (`object_state`) and `inside_of` containment evidence.
The laptop RTX 5050 target is active; the dashboard runs uploaded video at its own real-time frame
rate with GPU-accelerated JPEG encoding. Jetson deployment, 3D HMR, and a learned temporal head
remain parked.
