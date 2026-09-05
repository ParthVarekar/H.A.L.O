# BAS-HAR Progress Log

## Continuation checkpoint

**Date:** 2026-09-05
**Repository:** `C:\Users\Parth\Desktop\HAR_for_BAS`
**Active UI:** React dashboard at `http://127.0.0.1:5767`
**Current branch information:** Handover identifies `main`; this working directory did not expose
  a Git repository root during the latest read-only status check.

## Verified before this continuation

- Existing project handover reports 81 pytest tests passing.
- Ruff lint and format checks were clean.
- React dashboard and web smoke test were passing.
- CUDA inference was previously verified as `cuda:0` on the RTX 5050.
- The supplied red/blue sorting MP4 was previously accepted by the demo sequence tracker.
- Existing training CLIs are present: `prepare-yolo-dataset`, `annotate-yolo`, `train-yolo`, and
  `export-onnx`.
- The old PySide6 UI is absent; React is the active UI.
- The current generic evidence evaluator still reports `object_state` as not implemented.
- The current color sequence tracker contains red/blue demo-specific logic and must not become the
  generic activity path.

## Decisions recorded from the user

- Training data and logs stay on the laptop.
- Training Studio is part of the existing React dashboard.
- New procedures are created through a guided builder that generates validated YAML.
- Initial model organization is one package per activity.
- Initial camera assumption is one fixed calibrated view per activity.
- Annotation uses AI-assisted proposals with user review.
- Deliberate error examples should be included when available.
- Evaluation uses automatic session-level 70/20/10 splits.
- Live guidance is advisory only.
- Every trained package requires manual approval before Operations use.

## This checkpoint change

- Saved the complete approved plan in `docs/training_studio_plan.md`.
- Saved this continuation log so another agent can resume from the same decisions and boundaries.
- Next implementation work begins with schema/package contracts and registry plumbing.

## Checkpoint 1: package contracts and registry

**Status:** complete

- Added `bas_har/schema/activity_schema.py` with typed activity, take, timeline, bounding-box,
  visual annotation, dataset, job, evaluation, and model-release contracts.
- Added `bas_har/studio/registry.py` for local filesystem-backed activity packages.
- Added `activities_dir()` to the central path configuration.
- Added schema and registry tests.
- Verification: 11 targeted tests passed; full suite passed; Ruff lint and format checks passed.
- Next exact action: expose the registry through the existing web service and add the React Training
  Studio shell.

## Next exact checkpoint

1. Inspect and extend `bas_har/schema/` with activity, take, timeline, annotation, job, report,
   and release models.
2. Add tests for valid/invalid contracts before adding service logic.
3. Add local activity package storage and registry APIs to the existing web service.
4. Add the Training Studio React shell and activity creation/import workflow.
5. Run pytest, Ruff, React build, plan validation, and web smoke; append results here.

## Rules for future entries

Each implementation entry must record:

- date and checkpoint;
- files or subsystem changed;
- behavior completed;
- tests and commands run;
- known limitation or next exact action.

Do not mark a phase complete without the corresponding tests and smoke checks. Do not touch parked
3D HMR, Jetson, or learned temporal-head work without a new user decision.
