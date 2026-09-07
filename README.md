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

## Current collaborator task

The cold_stowage_melfi activity is already imported with its video, eight-step procedure, and
ground-truth timeline. Its bounding boxes have not yet been annotated. The next collaborator can
clone this repository and use the Studio to label the MELFI video.

- Dataset progress: dataset_progress.md
- Training Studio guide: training_guide.md
- Engineering handover: HANDOVER.md
- Architecture: docs/architecture.md
- Validation matrix: docs/validation_matrix.md
- Risk register: docs/risk_register.md
- Progress log: docs/progress_log.md

## Scope notes

The React Studio on port 5767 is authoritative for annotation. The procedure FSM is the primary
sequence engine. The laptop RTX 5050 target is active; Jetson deployment, 3D HMR, and a learned
temporal head remain parked.
