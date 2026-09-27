"""Held-out detector evaluation and durable evaluation jobs."""

from __future__ import annotations

import csv
import io
import threading
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter

from halo.config import project_root
from halo.schema.activity_schema import (
    ActivityId,
    EvaluationJob,
    EvaluationReport,
    JobStatus,
    RecordId,
)
from halo.studio.datasets import activity_dataset_dir, load_dataset_version
from halo.studio.hardware import hardware_snapshot
from halo.studio.quality import inspect_dataset
from halo.studio.registry import ActivityRegistry

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
Box = tuple[int, float, float, float, float]


def evaluate_boxes(
    ground_truths: Iterable[Box],
    predictions: Iterable[Box],
    iou_threshold: float = 0.5,
) -> dict[str, float]:
    if not 0 < iou_threshold < 1:
        raise ValueError("iou_threshold must be between 0 and 1")
    truths = list(ground_truths)
    candidates = list(predictions)
    matched: set[int] = set()
    true_positive = 0
    false_positive = 0
    for prediction in candidates:
        best_index = -1
        best_iou = 0.0
        for index, truth in enumerate(truths):
            if index in matched or truth[0] != prediction[0]:
                continue
            overlap = _iou(truth, prediction)
            if overlap > best_iou:
                best_index = index
                best_iou = overlap
        if best_index >= 0 and best_iou >= iou_threshold:
            matched.add(best_index)
            true_positive += 1
        else:
            false_positive += 1
    false_negative = len(truths) - len(matched)
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "true_positive": float(true_positive),
        "false_positive": float(false_positive),
        "false_negative": float(false_negative),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_model(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    training_job_id: str,
    model_path: str | Path,
    requested_device: str = "auto",
    iou_threshold: float = 0.5,
) -> EvaluationReport:
    manifest = registry.load(activity_id)
    dataset = load_dataset_version(registry, manifest.activity_id)
    quality = inspect_dataset(registry, manifest.activity_id)
    if not quality.passed:
        raise ValueError("dataset quality gate failed; fix labels before held-out evaluation")
    dataset_dir = activity_dataset_dir(registry, manifest.activity_id)
    test_dir = dataset_dir / "images" / "test"
    test_images = sorted(
        path
        for path in test_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not test_images:
        raise ValueError("test split is empty; provide held-out takes before evaluation")
    model_file = _model_path(model_path)
    if not model_file.is_file():
        raise FileNotFoundError(f"trained model not found: {model_file}")
    device = _resolve_device(requested_device)
    from ultralytics import YOLO

    model = YOLO(str(model_file))
    ground_truths: list[Box] = []
    predictions: list[Box] = []
    failure_gallery: list[dict[str, str | float]] = []
    for image_path in test_images:
        image_truths = _read_labels(dataset_dir / "labels" / "test" / f"{image_path.stem}.txt")
        results = model.predict(source=str(image_path), device=device, verbose=False)
        image_predictions: list[Box] = []
        if results:
            image_predictions = _result_boxes(results[0])
        image_metrics = evaluate_boxes(image_truths, image_predictions, iou_threshold)
        if image_metrics["false_positive"] or image_metrics["false_negative"]:
            failure_gallery.append(
                {
                    "image": str(image_path.relative_to(dataset_dir)),
                    "false_positive": image_metrics["false_positive"],
                    "false_negative": image_metrics["false_negative"],
                }
            )
        ground_truths.extend(image_truths)
        predictions.extend(image_predictions)
    metrics = evaluate_boxes(ground_truths, predictions, iou_threshold)
    passed = metrics["precision"] >= 0.5 and metrics["recall"] >= 0.5 and metrics["f1"] >= 0.5
    warnings = (
        [] if passed else ["detector did not meet the minimum precision, recall, and F1 gate"]
    )
    report = EvaluationReport(
        id=f"evaluation-{uuid4().hex[:12]}",
        activity_id=manifest.activity_id,
        dataset_id=dataset.dataset_id,
        training_job_id=training_job_id,
        passed=passed,
        metrics=metrics,
        warnings=warnings,
        device=device,
        failure_gallery=failure_gallery,
    )
    report_path = (
        registry.package_dir(manifest.activity_id) / "reports" / f"{report.report_id}.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    return report


def evaluation_csv(report: EvaluationReport) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["field", "value"])
    writer.writerow(["report_id", report.report_id])
    writer.writerow(["activity_id", report.activity_id])
    writer.writerow(["dataset_id", report.dataset_id])
    writer.writerow(["passed", report.passed])
    writer.writerow(["device", report.device])
    for name, value in report.metrics.items():
        writer.writerow([name, value])
    writer.writerow([])
    writer.writerow(["failure_image", "false_positive", "false_negative"])
    for failure in report.failure_gallery:
        writer.writerow([failure["image"], failure["false_positive"], failure["false_negative"]])
    return output.getvalue().encode("utf-8")


def load_evaluation_report(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
    report_id: str,
) -> EvaluationReport:
    manifest = registry.load(activity_id)
    safe_id = TypeAdapter(RecordId).validate_python(report_id)
    path = registry.package_dir(manifest.activity_id) / "reports" / f"{safe_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"evaluation report not found: {path}")
    return EvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))


class EvaluationJobManager:
    def __init__(self, registry: ActivityRegistry) -> None:
        self.registry = registry
        self.lock = threading.RLock()
        self.jobs: dict[str, EvaluationJob] = {}
        self._load_jobs()

    def start(
        self,
        activity_id: str,
        training_job_id: str,
        model_path: str,
        requested_device: str = "auto",
        iou_threshold: float = 0.5,
    ) -> EvaluationJob:
        self.registry.load(activity_id)
        job = EvaluationJob(
            id=f"evaluation-{uuid4().hex[:12]}",
            activity_id=activity_id,
            training_job_id=training_job_id,
            model_path=model_path,
            requested_device=requested_device,
            iou_threshold=iou_threshold,
        )
        self._store(job)
        dataset_path = activity_dataset_dir(self.registry, activity_id) / "dataset.json"
        if not dataset_path.is_file():
            return self._fail_missing_dataset(job, dataset_path)
        thread = threading.Thread(
            target=self._run,
            args=(job,),
            name=f"halo-evaluate-{job.job_id}",
            daemon=True,
        )
        thread.start()
        return job

    def _fail_missing_dataset(self, job: EvaluationJob, dataset_path: Path) -> EvaluationJob:
        failed = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "error": f"dataset metadata not found: {dataset_path}",
            }
        )
        self._store(failed)
        return failed

    def list(self, activity_id: str) -> list[EvaluationJob]:
        self._load_jobs()
        with self.lock:
            return [job for job in self.jobs.values() if job.activity_id == activity_id]

    def _load_jobs(self) -> None:
        for activity_dir in self.registry.root.glob("*/jobs"):
            for path in activity_dir.glob("evaluation-*.json"):
                try:
                    job = EvaluationJob.model_validate_json(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                with self.lock:
                    current = self.jobs.get(job.job_id)
                    if current is None or _job_state_rank(job.status) > _job_state_rank(
                        current.status
                    ):
                        self.jobs[job.job_id] = job

    def _run(self, job: EvaluationJob) -> None:
        device = _resolve_device(job.requested_device)
        running = job.model_copy(
            update={"status": JobStatus.RUNNING, "progress": 0.05, "resolved_device": device}
        )
        self._store(running)
        try:
            report = evaluate_model(
                self.registry,
                job.activity_id,
                job.training_job_id,
                job.model_path,
                job.requested_device,
                job.iou_threshold,
            )
        except Exception as exc:
            self._store(running.model_copy(update={"status": JobStatus.FAILED, "error": str(exc)}))
            return
        self._store(
            running.model_copy(
                update={
                    "status": JobStatus.COMPLETED,
                    "progress": 1.0,
                    "report_id": report.report_id,
                }
            )
        )

    def _store(self, job: EvaluationJob) -> None:
        with self.lock:
            self.jobs[job.job_id] = job
        path = self.registry.package_dir(job.activity_id) / "jobs" / f"{job.job_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(job.model_dump_json(by_alias=True, indent=2), encoding="utf-8")


def _read_labels(path: Path) -> list[Box]:
    if not path.is_file():
        return []
    boxes: list[Box] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) == 5:
            boxes.append((int(values[0]), *(float(value) for value in values[1:])))
    return boxes


def _result_boxes(result: object) -> list[Box]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    classes = boxes.cls.cpu().tolist()
    coordinates = boxes.xywhn.cpu().tolist()
    return [
        (int(class_id), float(center_x), float(center_y), float(width), float(height))
        for class_id, (center_x, center_y, width, height) in zip(classes, coordinates, strict=True)
    ]


def _iou(first: Box, second: Box) -> float:
    first_left = first[1] - first[3] / 2
    first_top = first[2] - first[4] / 2
    first_right = first[1] + first[3] / 2
    first_bottom = first[2] + first[4] / 2
    second_left = second[1] - second[3] / 2
    second_top = second[2] - second[4] / 2
    second_right = second[1] + second[3] / 2
    second_bottom = second[2] + second[4] / 2
    intersection = max(0.0, min(first_right, second_right) - max(first_left, second_left)) * max(
        0.0, min(first_bottom, second_bottom) - max(first_top, second_top)
    )
    union = first[3] * first[4] + second[3] * second[4] - intersection
    return intersection / union if union else 0.0


def _model_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root() / path


def _resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    return str(hardware_snapshot()["device"])


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _job_state_rank(status: JobStatus) -> int:
    return {
        JobStatus.QUEUED: 0,
        JobStatus.RUNNING: 1,
        JobStatus.COMPLETED: 2,
        JobStatus.FAILED: 2,
        JobStatus.CANCELLED: 2,
    }[status]


__all__ = [
    "EvaluationJobManager",
    "evaluate_boxes",
    "evaluate_model",
    "evaluation_csv",
    "load_evaluation_report",
]
