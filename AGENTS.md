# AGENTS.md — AI assistant conventions for this repo

This file is for any AI coding assistant (Claude Code, opencode, Cursor, etc.) that touches this repo.
Read it first. Keep it short. Update it when conventions actually change.

## Project one-liner

A **general-purpose procedure-recognition framework** that watches a fixed camera, validates an
experiment step-graph encoded in YAML, fires voice alerts on skip / out-of-sequence, writes a
timestamped JSONL log, and serves a React dashboard. The framework is experiment-agnostic — the red/blue box
demo is a config, not code.

## Hard rules

1. **No comments unless asked.** Code should read like prose.
2. **Schema-first.** Every feature starts with a Pydantic model in `bas_har/schema/` before any
   logic in `bas_har/procedure/`, `bas_har/io/`, etc. The procedure engine in
   `bas_har/procedure/` is generic over the schema; experiment-specific knowledge
   lives only in YAML.
3. **YAML is the only place experiment-specific knowledge lives.** No hard-coded step lists in
   Python. No hard-coded class names. If you find yourself writing `if step == "open box"`,
   stop and add an evidence rule to the YAML schema.
4. **No ML dependencies in core.** `pyproject.toml` `dependencies` stays lean (pydantic,
   pyyaml, loguru, cryptography). `cryptography` is core because every event log is Ed25519-signed.
   ML deps live in the `perception` extra.
5. **Tests are mandatory for every public function in `bas_har/`.** No `_` prefixes unless the
   function is a true private helper used in one place.
6. **Python version pin is `<3.14`** in `pyproject.toml` because MediaPipe / PyTorch wheels
   lag. If you bump it, update `requires-python` and add a note here.
7. **Single source of truth for paths.** Use `pathlib.Path`; never `os.path.join`.
8. **One command per CLI.** `python -m bas_har` (subcommands `verify`, `verify-log`,
   `verify-downlink`) and `validate-plan` are the only entry points for now. No
   `python scripts/foo.py`.

## Layout

```
bas_har/
  __main__.py        # python -m bas_har
  config.py          # runtime config (paths, env)
  schema/            # Pydantic models: plan_schema.py, event_schema.py, cli.py
  procedure/         # FSM engine, evidence, alerts (Phase 3)
  perception/        # YOLO, pose, hands, HOI (Phase 2)
  io/                # capture, RTSP, MP4, JSONL (Phase 5)
  voice/             # TTS, silence (Phase 4)
  web/               # React dashboard and Python capture service (Phase 6)
experiments/         # one folder per demo, each with experiment_plan.yaml
datasets/            # recorded takes (gitignored)
models/              # exported weights (gitignored)
docs/                # architecture, SIH submission
scripts/             # CLI utilities
tests/               # pytest, mirrors bas_har/ structure
```

## Style

- Ruff, line length 100, target py311. Run `ruff check .` and `ruff format .` before committing.
- Type hints on every public function. `from __future__ import annotations` not needed (py311+).
- Use `loguru.logger` not `logging.getLogger`.
- Errors: raise specific exceptions (`FileNotFoundError`, `ValueError`, `pydantic.ValidationError`).
  Never bare `raise Exception`.
- Strings: double quotes. f-strings for interpolation. No `.format()`.
- Imports: stdlib first, third-party second, local third. One blank line between groups.

## Testing

- `pytest` with `tmp_path` for filesystem tests.
- One test file per source file, named `tests/test_<module>.py`.
- Fixtures in `tests/conftest.py`.
- Every Pydantic model gets a `tests/test_<model>.py` with at least: valid minimal, valid
  full, invalid (each required field missing), invalid (bad enum).

## Git

- Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- Branch names: `phase-N-short-name` (e.g. `phase-3-procedure-engine`).
- Don't commit datasets, models, `.venv`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`.

## When in doubt

- Re-read `docs/architecture.md` and `docs/validation_matrix.md`.
- Re-read the authoritative spec: `docs/SIH26174_AI_HAR_BAS_TechnicalDoc_v1.0_2026-08-27.docx`.
- The Strategic Research doc has better terminology ("orientation-diverse augmentation" not
  "microgravity simulation") — prefer it for phrasing.
- When a decision is irreversible and affects schema, ask the user. Otherwise, decide and
  document.

## Known risks (re-read before major changes)

1. Dataset will be small (~20 takes) — overfitting risk; session-level splits mandatory.
2. 3D HMR is parked — do not import HMR 2.0 / SMPLer-X / smplfitter yet.
3. Jetson bring-up is parked — ONNX export is required at the end of Phase 2 / 3 but actual
   TensorRT / INT8 quantisation is Phase 9.
4. Demo hardware (webcam) may fail on stage — keep a pre-recorded MP4 + replay harness as a
   fallback (Phase 6 deliverable).
