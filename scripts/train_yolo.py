"""Fine-tune an Ultralytics YOLO detector on a dataset YAML file."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _train(args: argparse.Namespace) -> int:
    if not args.data.is_file():
        raise FileNotFoundError(f"dataset YAML not found: {args.data}")

    _validate_dataset(args.data, allow_missing_classes=args.allow_missing_classes)

    from ultralytics import YOLO

    model = YOLO(args.model)
    options = {
        "data": str(args.data),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "project": str(args.project),
        "name": args.name,
        "workers": args.workers,
        "patience": args.patience,
    }
    options["device"] = _resolve_device(args.device)
    model.train(**options)
    return 0


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
    except ImportError:
        return "cpu"
    return "0" if torch.cuda.is_available() else "cpu"


def _resolve_dataset_path(value: str | Path, dataset_root: Path) -> Path:
    value_path = Path(value)
    if value_path.is_absolute():
        return value_path
    return dataset_root / value_path


def _validate_dataset(data_path: Path, allow_missing_classes: bool) -> None:
    config = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    names = config.get("names")
    if isinstance(names, list):
        class_ids = set(range(len(names)))
    elif isinstance(names, dict):
        class_ids = {int(index) for index in names}
    else:
        raise ValueError("dataset YAML must contain names as a list or mapping")
    train_value = config.get("train")
    val_value = config.get("val")
    if not isinstance(train_value, (str, Path)) or not isinstance(val_value, (str, Path)):
        raise ValueError("dataset YAML must contain train and val image paths")
    raw_root = Path(config.get("path", "."))
    dataset_root = raw_root if raw_root.is_absolute() else data_path.parent / raw_root
    train_dir = _resolve_dataset_path(train_value, dataset_root)
    val_dir = _resolve_dataset_path(val_value, dataset_root)
    train_images = [
        path for path in train_dir.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    val_images = [
        path for path in val_dir.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    if not train_images:
        raise ValueError(
            f"no training images found under {train_dir}; run prepare-yolo-dataset first"
        )
    if not val_images:
        raise ValueError(
            f"no validation images found under {val_dir}; provide at least 3 videos for video-level splits"
        )
    labels_root = train_dir.parent.parent / "labels"
    found_classes: set[int] = set()
    for label_path in labels_root.rglob("*.txt"):
        for line in label_path.read_text(encoding="utf-8").splitlines():
            values = line.split()
            if values:
                found_classes.add(int(values[0]))
    missing = sorted(class_ids - found_classes)
    if missing and not allow_missing_classes:
        raise ValueError(
            f"missing labels for class ids {missing}; run annotate-yolo or pass --allow-missing-classes"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="train-yolo", description=__doc__)
    parser.add_argument("data", type=Path, help="Ultralytics dataset YAML file.")
    parser.add_argument("--model", default="yolo11n.pt", help="Base .pt or .yaml model.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--device", default="auto", help="Ultralytics device: auto, 0, or cpu.")
    parser.add_argument("--allow-missing-classes", action="store_true")
    parser.add_argument("--project", type=Path, default=Path("runs/train"))
    parser.add_argument("--name", default="red_blue_box")
    return parser


def main(argv: list[str] | None = None) -> int:
    return _train(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
