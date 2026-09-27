"""Runtime configuration: paths, env, defaults.

Single source of truth for where things live on disk. Phase 0 keeps this tiny.
"""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).absolute().parent.parent


def experiments_dir() -> Path:
    return project_root() / "experiments"


def activities_dir() -> Path:
    return project_root() / "activities"


def datasets_dir() -> Path:
    return project_root() / "datasets"


def models_dir() -> Path:
    return project_root() / "models"


def logs_dir() -> Path:
    path = project_root() / "logs"
    path.mkdir(exist_ok=True)
    return path


def keys_dir() -> Path:
    path = project_root() / "keys"
    path.mkdir(exist_ok=True)
    return path


def default_camera_source() -> int:
    env = os.environ.get("HALO_CAMERA")
    if env and env.isdigit():
        return int(env)
    return 0
