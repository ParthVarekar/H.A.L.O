"""Pydantic contracts for local activity packages and training data."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from bas_har.schema.plan_schema import StrictModel

ActivityId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"),
]
RecordId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"),
]


class ActivityKind(StrEnum):
    EXPERIMENT = "experiment"
    MAINTENANCE = "maintenance"
    TRAINING = "training"
    EXERCISE = "exercise"
    INSPECTION = "inspection"
    OTHER = "other"


class ActivityLifecycle(StrEnum):
    DRAFT = "draft"
    IMPORTED = "imported"
    ANNOTATED = "annotated"
    TRAINED = "trained"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"


class GroundTruthStatus(StrEnum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"
    OUT_OF_ORDER = "out_of_order"
    UNCERTAIN = "uncertain"


class AnnotationKind(StrEnum):
    OBJECT_BOX = "object_box"
    REGION = "region"
    OBJECT_STATE = "object_state"
    POSE = "pose"


class TrainingPreset(StrEnum):
    LAPTOP_SAFE = "laptop_safe"
    BALANCED = "balanced"
    QUALITY = "quality"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReleaseStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"


class ActivityManifest(StrictModel):
    activity_id: ActivityId = Field(alias="id")
    name: str = Field(min_length=1, max_length=160)
    kind: ActivityKind
    version: str = Field(default="0.1.0", min_length=1, max_length=32)
    author: str = Field(default="unknown", min_length=1, max_length=120)
    reviewer: str | None = Field(default=None, max_length=120)
    description: str = Field(default="", max_length=1000)
    plan_path: str = "plan.yaml"
    camera_profile: str = Field(default="default", min_length=1, max_length=64)
    lifecycle: ActivityLifecycle = ActivityLifecycle.DRAFT
    active_release_id: RecordId | None = None


class TakeRecord(StrictModel):
    take_id: RecordId = Field(alias="id")
    filename: str = Field(min_length=1, max_length=500)
    recording_session_id: RecordId
    actor_id: str | None = Field(default=None, max_length=120)
    camera_profile: str = Field(default="default", min_length=1, max_length=64)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    duration_s: float | None = Field(default=None, ge=0)
    fps: float | None = Field(default=None, gt=0, le=240)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class TimelineRecord(StrictModel):
    record_id: RecordId = Field(alias="id")
    take_id: RecordId
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    expected_step_id: str = Field(min_length=1, max_length=64)
    observed_action: str = Field(min_length=1, max_length=300)
    result: GroundTruthStatus
    object_ids: list[str] = Field(default_factory=list)
    region_ids: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check_interval(self) -> TimelineRecord:
        if self.end_s < self.start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        return self


class BoundingBox(StrictModel):
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    @model_validator(mode="after")
    def check_dimensions(self) -> BoundingBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bounding box must have positive width and height")
        return self


class VisualAnnotation(StrictModel):
    annotation_id: RecordId = Field(alias="id")
    take_id: RecordId
    frame_id: int = Field(ge=0)
    time_s: float = Field(ge=0)
    kind: AnnotationKind
    label: str = Field(min_length=1, max_length=120)
    bbox: BoundingBox | None = None
    region_id: str | None = None
    state: str | None = Field(default=None, max_length=120)
    source: str = Field(default="human", min_length=1, max_length=32)

    @model_validator(mode="after")
    def check_geometry(self) -> VisualAnnotation:
        if self.kind == AnnotationKind.OBJECT_BOX and self.bbox is None:
            raise ValueError("object_box annotations require bbox")
        if self.kind == AnnotationKind.REGION and self.region_id is None:
            raise ValueError("region annotations require region_id")
        if self.kind == AnnotationKind.OBJECT_STATE and self.state is None:
            raise ValueError("object_state annotations require state")
        return self


class DatasetVersion(StrictModel):
    dataset_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    take_ids: list[RecordId] = Field(min_length=1)
    session_ids: list[RecordId] = Field(min_length=1)
    train_ratio: float = Field(default=0.7, gt=0, lt=1)
    validation_ratio: float = Field(default=0.2, gt=0, lt=1)
    test_ratio: float = Field(default=0.1, gt=0, lt=1)
    split_locked: bool = True
    split_sessions: dict[str, list[RecordId]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_ratios(self) -> DatasetVersion:
        total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError("dataset split ratios must sum to 1")
        return self


class TrainingJob(StrictModel):
    job_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    dataset_id: RecordId
    preset: TrainingPreset = TrainingPreset.LAPTOP_SAFE
    requested_device: str = Field(default="auto", min_length=1, max_length=32)
    resolved_device: str | None = Field(default=None, max_length=32)
    status: JobStatus = JobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0, le=1)
    output_path: str | None = None
    error: str | None = None


class DatasetPreparationJob(StrictModel):
    job_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    status: JobStatus = JobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0, le=1)
    dataset_id: RecordId | None = None
    error: str | None = None


class EvaluationJob(StrictModel):
    job_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    training_job_id: RecordId
    model_path: str = Field(min_length=1, max_length=500)
    requested_device: str = Field(default="auto", min_length=1, max_length=32)
    resolved_device: str | None = Field(default=None, max_length=32)
    iou_threshold: float = Field(default=0.5, gt=0, lt=1)
    status: JobStatus = JobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0, le=1)
    report_id: RecordId | None = None
    error: str | None = None


class DatasetQualityReport(StrictModel):
    report_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    dataset_id: RecordId
    passed: bool
    images_by_split: dict[str, int] = Field(default_factory=dict)
    label_files_by_split: dict[str, int] = Field(default_factory=dict)
    empty_label_images: list[str] = Field(default_factory=list)
    missing_label_files: list[str] = Field(default_factory=list)
    invalid_label_files: list[str] = Field(default_factory=list)
    class_counts: dict[str, int] = Field(default_factory=dict)
    sessions_by_split: dict[str, list[RecordId]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class EvaluationReport(StrictModel):
    report_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    dataset_id: RecordId
    training_job_id: RecordId
    passed: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    device: str = Field(default="unknown", min_length=1, max_length=32)
    inference_fps: float | None = Field(default=None, ge=0)
    timestamp_tolerance_s: float = Field(default=2.0, gt=0)
    failure_gallery: list[dict[str, str | float]] = Field(default_factory=list)


class ModelRelease(StrictModel):
    release_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    version: str = Field(min_length=1, max_length=32)
    model_path: str = Field(min_length=1, max_length=500)
    plan_path: str = Field(default="plan.yaml", min_length=1, max_length=500)
    dataset_id: RecordId
    evaluation_report_id: RecordId
    status: ReleaseStatus = ReleaseStatus.CANDIDATE
    model_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    approved_by: str | None = Field(default=None, max_length=120)


class PackageVerification(StrictModel):
    verification_id: RecordId = Field(alias="id")
    activity_id: ActivityId
    release_id: RecordId | None = None
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


__all__ = [
    "ActivityId",
    "ActivityKind",
    "ActivityLifecycle",
    "ActivityManifest",
    "AnnotationKind",
    "BoundingBox",
    "DatasetPreparationJob",
    "DatasetQualityReport",
    "DatasetVersion",
    "EvaluationJob",
    "EvaluationReport",
    "GroundTruthStatus",
    "JobStatus",
    "ModelRelease",
    "PackageVerification",
    "RecordId",
    "ReleaseStatus",
    "TakeRecord",
    "TimelineRecord",
    "TrainingJob",
    "TrainingPreset",
    "VisualAnnotation",
]
