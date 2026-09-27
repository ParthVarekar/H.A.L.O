"""Live perception preview.

Source: webcam index or MP4 file. Runs the full perception pipeline
(detector + pose + hands + HOI heuristic) and shows an annotated preview
window. Optional `--dump <path>.jsonl` writes one PerceptionResult per frame
to a JSONL file for offline analysis.

Controls:
  Q  quit
  P  toggle pose overlay
  H  toggle hand overlay
  D  toggle detection overlay
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from halo.config import default_camera_source
from halo.perception.pipeline import PerceptionPipeline
from halo.perception.types import PerceptionResult


def _draw_detections(frame, result: PerceptionResult) -> None:
    for det in result.detections:
        x1, y1 = int(det.bbox.x1), int(det.bbox.y1)
        x2, y2 = int(det.bbox.x2), int(det.bbox.y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"{det.cls} {det.conf:.2f}",
            (x1, max(0, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )


def _draw_pose(frame, result: PerceptionResult) -> None:
    if result.pose is None:
        return
    for x, y, _ in result.pose.keypoints:
        cv2.circle(frame, (int(x), int(y)), 3, (255, 128, 0), -1)


def _draw_hands(frame, result: PerceptionResult) -> None:
    for hand in result.hands:
        for x, y, _ in hand.keypoints:
            cv2.circle(frame, (int(x), int(y)), 4, (255, 0, 255), -1)
    for hoi in result.hoi:
        cv2.putText(
            frame,
            f"HOI {hoi.hand}:{hoi.object_cls}:{hoi.label} ({hoi.score:.2f})",
            (20, 80 + 20 * result.hoi.index(hoi)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 200, 255),
            2,
        )


def _open(source: str | int) -> tuple[cv2.VideoCapture, str]:
    if isinstance(source, str) and any(
        source.lower().endswith(ext) for ext in (".mp4", ".avi", ".mov", ".mkv")
    ):
        cap = cv2.VideoCapture(source)
        kind = f"file:{source}"
    else:
        idx = int(source) if isinstance(source, str) else source
        cap = cv2.VideoCapture(idx)
        kind = f"webcam:{idx}"
    if not cap.isOpened():
        raise RuntimeError(f"could not open source: {source}")
    return cap, kind


def preview(
    source: str | int,
    yolo_model: str | Path | None,
    target_classes: list[str] | None,
    dump: Path | None,
    show_pose: bool = True,
    show_hands: bool = True,
    show_det: bool = True,
) -> int:
    pipeline = PerceptionPipeline(
        yolo_model=yolo_model,
        target_classes=target_classes,
        run_pose=show_pose,
        run_hands=show_hands,
    )
    cap, kind = _open(source)
    print(f"[preview] source={kind}")

    dump_handle = None
    if dump is not None:
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump_handle = dump.open("w", encoding="utf-8")
        print(f"[preview] dumping frames to {dump}")

    show_pose = True
    show_hands = True
    show_det = True
    frame_id = 0
    start = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[preview] source exhausted")
                break
            ts_ms = int((time.perf_counter() - start) * 1000)
            result = pipeline.process(frame, frame_id=frame_id, ts_ms=ts_ms)
            if show_det:
                _draw_detections(frame, result)
            if show_pose:
                _draw_pose(frame, result)
            if show_hands:
                _draw_hands(frame, result)
            cv2.putText(
                frame,
                f"frame={frame_id} det={len(result.detections)} hands={len(result.hands)}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            cv2.imshow("halo perception preview", frame)
            if dump_handle is not None:
                dump_handle.write(result.to_json() + "\n")
            frame_id += 1
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("p"):
                show_pose = not show_pose
            if key == ord("h"):
                show_hands = not show_hands
            if key == ord("d"):
                show_det = not show_det
    finally:
        cap.release()
        if dump_handle is not None:
            dump_handle.close()
        cv2.destroyAllWindows()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="preview-perception", description=__doc__)
    parser.add_argument("--source", default=default_camera_source())
    parser.add_argument("--yolo-model", default=None, help="Path to custom YOLO .pt or .onnx.")
    parser.add_argument(
        "--target-classes",
        nargs="*",
        default=None,
        help="Optional whitelist of class names to keep (lowercased).",
    )
    parser.add_argument(
        "--dump",
        type=Path,
        default=None,
        help="Optional path to a JSONL file to dump per-frame PerceptionResult.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = [c.lower() for c in args.target_classes] if args.target_classes else None
    return preview(args.source, args.yolo_model, target, args.dump)


if __name__ == "__main__":
    raise SystemExit(main())
