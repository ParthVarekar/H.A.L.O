"""Run the procedure engine on a real MP4 using PerceptionPipeline.

Same wiring the dashboard uses: capture -> perception -> engine.step() -> JSONL log.
Real perception is dumb for the demo MP4 (no boxes detected) so no steps
complete, but it proves the hot path is hooked up end to end.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

from halo.config import logs_dir
from halo.io import CrcJsonlEventSink
from halo.perception import PerceptionPipeline
from halo.procedure import build_engine
from halo.schema.cli import load_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run-engine", description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("source", help="Webcam index or MP4 file path.")
    parser.add_argument("--yolo-model", default="models/yolo11n.pt")
    parser.add_argument(
        "--target-classes",
        nargs="*",
        default=["box", "cup", "bottle", "bowl", "book", "orange", "banana", "apple"],
    )
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument(
        "--crc-log",
        action="store_true",
        help="Write each event as a CRC32-enveloped JSONL record.",
    )
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args(argv)

    plan = load_plan(args.plan)
    log_path = args.log or (logs_dir() / f"engine_{plan.experiment_id}_{int(time.time())}.jsonl")
    sink = CrcJsonlEventSink(log_path) if args.crc_log else None
    engine = build_engine(plan, sink=sink, sink_path=None if sink is not None else log_path)

    if args.source.isdigit() or (isinstance(args.source, str) and args.source.isdigit()):
        cap = cv2.VideoCapture(int(args.source))
    else:
        cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise RuntimeError(f"could not open source: {args.source}")

    pipeline = PerceptionPipeline(
        yolo_model=args.yolo_model,
        target_classes=[c.lower() for c in args.target_classes],
        run_pose=True,
        run_hands=True,
    )

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or args.max_frames or 0
    if args.max_frames:
        n = min(n, args.max_frames)
    print(f"source fps={fps:.2f} max_frames={n}")

    start = time.perf_counter()
    last_print = 0
    for i in range(n) if n else iter(int, 1):
        ok, frame = cap.read()
        if not ok:
            break
        result = pipeline.process(frame, frame_id=i, ts_ms=int(i * 1000 / fps))
        out = engine.step(result)
        if i - last_print >= 30:
            print(
                f"frame {i:5d}  state={out.state:11s}  cur={out.current_step_id:18s}  "
                f"cof={out.current_step_confidence:.2f}  det={len(result.detections)}"
            )
            last_print = i

    cap.release()
    engine.close()
    elapsed = time.perf_counter() - start
    print(f"processed {n} frames in {elapsed:.2f}s = {n / max(elapsed, 0.01):.1f} fps")
    print(f"event log -> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
