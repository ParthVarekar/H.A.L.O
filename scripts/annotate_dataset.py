"""Label YOLO images with a small local drag-box annotation window."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import yaml

from bas_har.config import datasets_dir

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
CLASS_COLORS = [(50, 190, 255), (70, 70, 255), (255, 150, 50), (180, 80, 220)]


def _load_class_names(data_path: Path) -> dict[int, str]:
    data = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    names = data.get("names")
    if isinstance(names, list):
        return {index: str(name) for index, name in enumerate(names)}
    if isinstance(names, dict):
        return {int(index): str(name) for index, name in names.items()}
    raise ValueError("dataset YAML must contain names as a list or mapping")


def _read_labels(path: Path) -> list[list[float]]:
    if not path.is_file():
        return []
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) != 5:
            continue
        rows.append([float(value) for value in values])
    return rows


def _write_labels(path: Path, labels: list[list[float]]) -> None:
    path.write_text(
        "".join(
            f"{int(row[0])} {row[1]:.6f} {row[2]:.6f} {row[3]:.6f} {row[4]:.6f}\n" for row in labels
        ),
        encoding="utf-8",
    )


def _draw_labels(
    image: cv2.typing.MatLike,
    labels: list[list[float]],
    class_names: dict[int, str],
    scale: float,
    current_class: int,
    drag_start: tuple[int, int] | None,
    drag_end: tuple[int, int] | None,
) -> cv2.typing.MatLike:
    preview = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    height, width = image.shape[:2]
    for row in labels:
        class_id, center_x, center_y, box_width, box_height = row
        x1 = int((center_x - box_width / 2) * width * scale)
        y1 = int((center_y - box_height / 2) * height * scale)
        x2 = int((center_x + box_width / 2) * width * scale)
        y2 = int((center_y + box_height / 2) * height * scale)
        color = CLASS_COLORS[int(class_id) % len(CLASS_COLORS)]
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            preview,
            class_names.get(int(class_id), str(int(class_id))),
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    if drag_start is not None and drag_end is not None:
        color = CLASS_COLORS[current_class % len(CLASS_COLORS)]
        cv2.rectangle(preview, drag_start, drag_end, color, 2)
    return preview


def annotate(dataset: Path, split: str, start: int, limit: int | None) -> int:
    data_path = dataset / "data.yaml"
    class_names = _load_class_names(data_path)
    image_dir = dataset / "images" / split
    label_dir = dataset / "labels" / split
    images = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise FileNotFoundError(f"no images found under: {image_dir}")
    if start < 0 or start >= len(images):
        raise ValueError(f"start must be between 0 and {len(images) - 1}")
    end = min(len(images), start + limit) if limit is not None else len(images)
    window = "bas-har YOLO annotator"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    image_index = start
    try:
        while image_index < end:
            image_path = images[image_index]
            label_path = label_dir / f"{image_path.stem}.txt"
            image = cv2.imread(str(image_path))
            if image is None:
                raise RuntimeError(f"could not read image: {image_path}")
            labels = _read_labels(label_path)
            current_class = 0
            drag_start: tuple[int, int] | None = None
            drag_end: tuple[int, int] | None = None
            scale = min(1.0, 1200 / image.shape[1], 800 / image.shape[0])
            state = {"start": None, "end": None}

            def mouse_callback(
                event: int,
                x: int,
                y: int,
                _flags: int,
                _param: object,
                draw_state: dict[str, tuple[int, int] | None] = state,
            ) -> None:
                if event == cv2.EVENT_LBUTTONDOWN:
                    draw_state["start"] = (x, y)
                    draw_state["end"] = (x, y)
                elif (
                    event in {cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONUP}
                    and draw_state["start"] is not None
                ):
                    draw_state["end"] = (x, y)

            cv2.setMouseCallback(window, mouse_callback)
            while True:
                drag_start = state["start"]
                drag_end = state["end"]
                preview = _draw_labels(
                    image,
                    labels,
                    class_names,
                    scale,
                    current_class,
                    drag_start,
                    drag_end,
                )
                help_text = (
                    f"{image_index + 1}/{len(images)}  class={current_class}: "
                    f"{class_names.get(current_class, '?')}  "
                    "1-3 class | drag add | u undo | s save | n next | q quit"
                )
                cv2.putText(
                    preview,
                    help_text,
                    (12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.52,
                    (240, 240, 240),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window, preview)
                key = cv2.waitKey(20) & 0xFF
                if key in {ord("1"), ord("2"), ord("3"), ord("4"), ord("5")}:
                    current_class = key - ord("1")
                elif key == ord("u"):
                    if labels:
                        labels.pop()
                elif key in {ord("s"), ord("n"), ord("q")}:
                    if drag_start is not None and drag_end is not None:
                        x1, y1 = drag_start
                        x2, y2 = drag_end
                        left, right = sorted((x1, x2))
                        top, bottom = sorted((y1, y2))
                        if right - left >= 4 and bottom - top >= 4:
                            image_width = image.shape[1] * scale
                            image_height = image.shape[0] * scale
                            labels.append(
                                [
                                    float(current_class),
                                    (left + right) / 2 / image_width,
                                    (top + bottom) / 2 / image_height,
                                    (right - left) / image_width,
                                    (bottom - top) / image_height,
                                ]
                            )
                    _write_labels(label_path, labels)
                    state["start"] = None
                    state["end"] = None
                    if key == ord("n"):
                        image_index += 1
                    elif key == ord("q"):
                        return 0
                    else:
                        break
                elif key == ord("r"):
                    labels = _read_labels(label_path)
                    state["start"] = None
                    state["end"] = None
    finally:
        cv2.destroyAllWindows()
    print(f"annotated={end - start} split={split} dataset={dataset}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="annotate-yolo", description=__doc__)
    parser.add_argument("dataset", type=Path, nargs="?", default=datasets_dir() / "red_blue_box")
    parser.add_argument("--split", choices=("train", "val", "test"), default="train")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return annotate(args.dataset, args.split, args.start, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
