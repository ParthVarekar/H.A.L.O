"""Dataset integrity checks for local activity packages."""

from __future__ import annotations

from pathlib import Path

import yaml

from halo.schema.activity_schema import (
    ActivityId,
    DatasetQualityReport,
)
from halo.studio.datasets import activity_dataset_dir, load_dataset_version
from halo.studio.registry import ActivityRegistry

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SPLITS = ("train", "val", "test")


def inspect_dataset(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> DatasetQualityReport:
    manifest = registry.load(activity_id)
    dataset = load_dataset_version(registry, manifest.activity_id)
    dataset_dir = activity_dataset_dir(registry, manifest.activity_id)
    data_path = dataset_dir / "data.yaml"
    class_names = _class_names(data_path)
    images_by_split: dict[str, int] = {}
    label_files_by_split: dict[str, int] = {}
    empty_label_images: list[str] = []
    missing_label_files: list[str] = []
    invalid_label_files: list[str] = []
    class_counts = {name: 0 for name in class_names.values()}
    for split in SPLITS:
        image_dir = _split_path(data_path, split, "images")
        label_dir = _split_path(data_path, split, "labels")
        images = (
            sorted(
                path
                for path in image_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            )
            if image_dir.is_dir()
            else []
        )
        images_by_split[split] = len(images)
        label_files_by_split[split] = 0
        for image_path in images:
            label_path = label_dir / f"{image_path.stem}.txt"
            relative = str(image_path.relative_to(dataset_dir))
            if not label_path.is_file():
                missing_label_files.append(relative)
                continue
            label_files_by_split[split] += 1
            rows = label_path.read_text(encoding="utf-8").splitlines()
            if not any(row.strip() for row in rows):
                empty_label_images.append(relative)
                continue
            valid = True
            for row in rows:
                values = row.split()
                if len(values) != 5:
                    valid = False
                    continue
                try:
                    class_id = int(values[0])
                    coordinates = [float(value) for value in values[1:]]
                except ValueError:
                    valid = False
                    continue
                if (
                    class_id not in class_names
                    or any(value < 0 or value > 1 for value in coordinates)
                    or coordinates[2] <= 0
                    or coordinates[3] <= 0
                ):
                    valid = False
                    continue
                class_counts[class_names[class_id]] += 1
            if not valid:
                invalid_label_files.append(relative)
    warnings: list[str] = []
    sessions_by_split = dataset.split_sessions
    session_ids = {session_id for values in sessions_by_split.values() for session_id in values}
    if len(session_ids) < 3:
        warnings.append("fewer than 3 independent recording sessions; validation is prototype-only")
    elif len(session_ids) < 10:
        warnings.append(
            "fewer than 10 independent recording sessions; release robustness is limited"
        )
    if not sessions_by_split.get("val"):
        warnings.append("validation has no independent recording session")
    if not sessions_by_split.get("test"):
        warnings.append("test has no independent recording session")
    if images_by_split["val"] == 0:
        warnings.append("validation split is empty; training and evaluation are not reliable")
    if images_by_split["test"] == 0:
        warnings.append("test split is empty; held-out evaluation is unavailable")
    missing_classes = [name for name, count in class_counts.items() if count == 0]
    if missing_classes:
        warnings.append(f"classes have no labels: {', '.join(missing_classes)}")
    passed = bool(images_by_split["train"]) and not missing_label_files and not invalid_label_files
    passed = passed and not missing_classes and images_by_split["val"] > 0
    report = DatasetQualityReport(
        id=f"quality-{dataset.dataset_id}",
        activity_id=manifest.activity_id,
        dataset_id=dataset.dataset_id,
        passed=passed,
        images_by_split=images_by_split,
        label_files_by_split=label_files_by_split,
        empty_label_images=empty_label_images,
        missing_label_files=missing_label_files,
        invalid_label_files=invalid_label_files,
        class_counts=class_counts,
        sessions_by_split=sessions_by_split,
        warnings=warnings,
    )
    report_path = registry.package_dir(manifest.activity_id) / "reports" / "dataset_quality.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    return report


def load_quality_report(
    registry: ActivityRegistry,
    activity_id: ActivityId | str,
) -> DatasetQualityReport:
    manifest = registry.load(activity_id)
    path = registry.package_dir(manifest.activity_id) / "reports" / "dataset_quality.json"
    if not path.is_file():
        raise FileNotFoundError(f"dataset quality report not found: {path}")
    return DatasetQualityReport.model_validate_json(path.read_text(encoding="utf-8"))


def _class_names(data_path: Path) -> dict[int, str]:
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset YAML not found: {data_path}")
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    names = data.get("names")
    if isinstance(names, list):
        return {index: str(name) for index, name in enumerate(names)}
    if isinstance(names, dict):
        return {int(index): str(name) for index, name in names.items()}
    raise ValueError("dataset YAML must contain names as a list or mapping")


def _split_path(data_path: Path, split: str, kind: str) -> Path:
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    if kind == "labels":
        return data_path.parent / "labels" / split
    raw_root = Path(data.get("path", "."))
    root = raw_root if raw_root.is_absolute() else data_path.parent / raw_root
    value = data.get(split, f"{kind}/{split}")
    path = Path(value)
    return path if path.is_absolute() else root / path


__all__ = ["inspect_dataset", "load_quality_report"]
