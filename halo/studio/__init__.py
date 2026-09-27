"""Local activity package storage and Training Studio services."""

from bas_har.studio.annotations import (
    annotation_path,
    list_annotations,
    list_keyframes,
    read_take_frame,
    save_annotation,
)
from bas_har.studio.datasets import (
    activity_dataset_dir,
    ensure_dataset_config,
    load_dataset_version,
    prepare_activity_dataset,
)
from bas_har.studio.evaluation import (
    EvaluationJobManager,
    evaluate_boxes,
    evaluate_model,
    evaluation_csv,
)
from bas_har.studio.hardware import hardware_snapshot
from bas_har.studio.jobs import DatasetJobManager, TrainingJobManager
from bas_har.studio.plans import load_activity_plan, save_activity_plan
from bas_har.studio.quality import inspect_dataset, load_quality_report
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.releases import (
    activate_release,
    approve_release,
    create_candidate,
    list_releases,
    load_release,
)
from bas_har.studio.takes import list_takes, register_take
from bas_har.studio.timeline import import_timeline, list_timeline, parse_time, read_timeline
from bas_har.studio.verification import (
    load_verification,
    release_audit_csv,
    verify_activity_package,
)

__all__ = [
    "ActivityRegistry",
    "DatasetJobManager",
    "EvaluationJobManager",
    "TrainingJobManager",
    "activate_release",
    "activity_dataset_dir",
    "annotation_path",
    "approve_release",
    "create_candidate",
    "ensure_dataset_config",
    "evaluate_boxes",
    "evaluate_model",
    "evaluation_csv",
    "hardware_snapshot",
    "import_timeline",
    "inspect_dataset",
    "list_annotations",
    "list_keyframes",
    "list_releases",
    "list_takes",
    "list_timeline",
    "load_activity_plan",
    "load_dataset_version",
    "load_quality_report",
    "load_release",
    "load_verification",
    "parse_time",
    "prepare_activity_dataset",
    "read_take_frame",
    "read_timeline",
    "register_take",
    "release_audit_csv",
    "save_activity_plan",
    "save_annotation",
    "verify_activity_package",
]
