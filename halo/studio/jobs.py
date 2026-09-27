"""Background dataset-preparation and model-training jobs."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import ClassVar
from uuid import uuid4

from halo.config import project_root
from halo.schema.activity_schema import (
    DatasetPreparationJob,
    JobStatus,
    TrainingJob,
    TrainingPreset,
)
from halo.studio.datasets import activity_dataset_dir, prepare_activity_dataset
from halo.studio.hardware import hardware_snapshot
from halo.studio.registry import ActivityRegistry


class DatasetJobManager:
    def __init__(self, registry: ActivityRegistry) -> None:
        self.registry = registry
        self.lock = threading.RLock()
        self.jobs: dict[str, DatasetPreparationJob] = {}
        self._load_jobs()

    def start(
        self,
        activity_id: str,
        sample_every: int = 5,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
    ) -> DatasetPreparationJob:
        self.registry.load(activity_id)
        job = DatasetPreparationJob(
            id=f"dataset-{uuid4().hex[:12]}",
            activity_id=activity_id,
        )
        self._store(job)
        thread = threading.Thread(
            target=self._run,
            args=(job, sample_every, val_ratio, test_ratio),
            name=f"halo-dataset-{job.job_id}",
            daemon=True,
        )
        thread.start()
        return job

    def list(self, activity_id: str) -> list[DatasetPreparationJob]:
        self._load_jobs()
        with self.lock:
            return [job for job in self.jobs.values() if job.activity_id == activity_id]

    def _load_jobs(self) -> None:
        for activity_dir in self.registry.root.glob("*/jobs"):
            for path in activity_dir.glob("dataset-*.json"):
                try:
                    job = DatasetPreparationJob.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                except (OSError, ValueError):
                    continue
                with self.lock:
                    current = self.jobs.get(job.job_id)
                    if current is None or _job_state_rank(job.status) > _job_state_rank(
                        current.status
                    ):
                        self.jobs[job.job_id] = job

    def _run(
        self, job: DatasetPreparationJob, sample_every: int, val_ratio: float, test_ratio: float
    ) -> None:
        self._store(job.model_copy(update={"status": JobStatus.RUNNING, "progress": 0.1}))
        try:
            dataset = prepare_activity_dataset(
                self.registry,
                job.activity_id,
                sample_every,
                val_ratio,
                test_ratio,
            )
        except Exception as exc:
            self._store(job.model_copy(update={"status": JobStatus.FAILED, "error": str(exc)}))
            return
        self._store(
            job.model_copy(
                update={
                    "status": JobStatus.COMPLETED,
                    "progress": 1.0,
                    "dataset_id": dataset.dataset_id,
                }
            )
        )

    def _store(self, job: DatasetPreparationJob) -> None:
        with self.lock:
            self.jobs[job.job_id] = job
        path = self.registry.package_dir(job.activity_id) / "jobs" / f"{job.job_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(job.model_dump_json(by_alias=True, indent=2), encoding="utf-8")


class TrainingJobManager:
    PRESETS: ClassVar[dict[TrainingPreset, dict[str, int]]] = {
        TrainingPreset.LAPTOP_SAFE: {
            "epochs": 50,
            "imgsz": 512,
            "batch": 4,
            "workers": 0,
            "patience": 15,
        },
        TrainingPreset.BALANCED: {
            "epochs": 100,
            "imgsz": 640,
            "batch": 8,
            "workers": 2,
            "patience": 30,
        },
        TrainingPreset.QUALITY: {
            "epochs": 150,
            "imgsz": 640,
            "batch": 8,
            "workers": 2,
            "patience": 40,
        },
    }

    def __init__(self, registry: ActivityRegistry) -> None:
        self.registry = registry
        self.lock = threading.RLock()
        self.jobs: dict[str, TrainingJob] = {}
        self._load_jobs()

    def start(
        self,
        activity_id: str,
        dataset_id: str,
        preset: TrainingPreset = TrainingPreset.LAPTOP_SAFE,
        requested_device: str = "auto",
        model_path: str = "models/yolo11n.pt",
    ) -> TrainingJob:
        self.registry.load(activity_id)
        job = TrainingJob(
            id=f"train-{uuid4().hex[:12]}",
            activity_id=activity_id,
            dataset_id=dataset_id,
            preset=preset,
            requested_device=requested_device,
        )
        self._store(job)
        dataset_path = activity_dataset_dir(self.registry, activity_id) / "dataset.json"
        if not dataset_path.is_file():
            return self._fail_missing_dataset(job, dataset_path)
        thread = threading.Thread(
            target=self._run,
            args=(job, model_path),
            name=f"halo-train-{job.job_id}",
            daemon=True,
        )
        thread.start()
        return job

    def _fail_missing_dataset(self, job: TrainingJob, dataset_path: Path) -> TrainingJob:
        failed = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "error": f"dataset metadata not found: {dataset_path}",
            }
        )
        self._store(failed)
        return failed

    def list(self, activity_id: str) -> list[TrainingJob]:
        self._load_jobs()
        with self.lock:
            return [job for job in self.jobs.values() if job.activity_id == activity_id]

    def _load_jobs(self) -> None:
        for activity_dir in self.registry.root.glob("*/jobs"):
            for path in activity_dir.glob("train-*.json"):
                try:
                    job = TrainingJob.model_validate_json(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                with self.lock:
                    current = self.jobs.get(job.job_id)
                    if current is None or _job_state_rank(job.status) > _job_state_rank(
                        current.status
                    ):
                        self.jobs[job.job_id] = job

    def _run(self, job: TrainingJob, model_path: str) -> None:
        device = self._resolve_device(job.requested_device)
        running = job.model_copy(
            update={"status": JobStatus.RUNNING, "progress": 0.05, "resolved_device": device}
        )
        self._store(running)
        try:
            from halo.studio.datasets import activity_dataset_dir, load_dataset_version
            from scripts.train_yolo import _validate_dataset

            dataset_dir = activity_dataset_dir(self.registry, job.activity_id)
            data_path = dataset_dir / "data.yaml"
            _validate_dataset(data_path, allow_missing_classes=False)
            dataset = load_dataset_version(self.registry, job.activity_id)
            if dataset.dataset_id != job.dataset_id:
                raise ValueError("requested dataset is not the current activity dataset")
            from ultralytics import YOLO

            model = YOLO(str(self._resolve_model_path(model_path)))
            options = self.PRESETS[job.preset].copy()
            options.update(
                {
                    "data": str(data_path),
                    "project": str(dataset_dir / "runs"),
                    "name": job.job_id,
                    "device": device,
                }
            )
            model.train(**options)
            output_path = dataset_dir / "runs" / job.job_id / "weights" / "best.pt"
        except Exception as exc:
            self._store(running.model_copy(update={"status": JobStatus.FAILED, "error": str(exc)}))
            return
        self._store(
            running.model_copy(
                update={
                    "status": JobStatus.COMPLETED,
                    "progress": 1.0,
                    "output_path": str(output_path),
                }
            )
        )

    def _resolve_device(self, requested: str) -> str:
        if requested != "auto":
            return requested
        snapshot = hardware_snapshot()
        return str(snapshot["device"])

    def _resolve_model_path(self, model_path: str) -> Path:
        path = Path(model_path)
        return path if path.is_absolute() else project_root() / path

    def _store(self, job: TrainingJob) -> None:
        with self.lock:
            self.jobs[job.job_id] = job
        path = self.registry.package_dir(job.activity_id) / "jobs" / f"{job.job_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(job.model_dump_json(by_alias=True, indent=2), encoding="utf-8")


def _job_state_rank(status: JobStatus) -> int:
    return {
        JobStatus.QUEUED: 0,
        JobStatus.RUNNING: 1,
        JobStatus.COMPLETED: 2,
        JobStatus.FAILED: 2,
        JobStatus.CANCELLED: 2,
    }[status]


__all__ = ["DatasetJobManager", "TrainingJobManager"]
