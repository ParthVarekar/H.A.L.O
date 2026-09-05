"""Analyze a color-coded experiment video and write timestamped step events."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from bas_har.config import logs_dir
from bas_har.io import CrcJsonlEventSink, VideoCaptureSource
from bas_har.perception.pipeline import PerceptionPipeline
from bas_har.procedure.sequence import ColorSequenceTracker, SequenceObservation
from bas_har.schema.cli import load_plan
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.voice import ConfirmationSound


def _source_value(source: str) -> int | str:
    return int(source) if source.isdigit() else source


def _plan_color_names(plan: ExperimentPlan) -> list[str]:
    return sorted(
        {
            color.lower()
            for obj in plan.objects
            for color in obj.colors_any
            if color.lower() in {"red", "blue"}
        }
    )


def analyze(
    plan_path: Path,
    source: str,
    log_path: Path | None,
    device: str,
    yolo_model: str,
    max_frames: int | None,
    require_complete: bool,
) -> int:
    plan = load_plan(plan_path)
    output_path = log_path or (
        logs_dir() / f"sequence_{plan.experiment_id}_{int(time.time())}.jsonl"
    )
    capture = VideoCaptureSource(
        _source_value(source),
        resolution=tuple(plan.camera.resolution),
        fps=plan.camera.fps,
    )
    sink = CrcJsonlEventSink(output_path)
    confirmation = ConfirmationSound()
    tracker = ColorSequenceTracker(plan)
    pipeline = PerceptionPipeline(
        yolo_model=yolo_model,
        target_classes=["box", "cup", "bottle", "bowl", "book", "orange", "banana", "apple"],
        run_pose=False,
        run_hands=False,
        device=device,
        color_names=_plan_color_names(plan),
    )
    frame_id = 0
    observation: SequenceObservation | None = None
    started = time.perf_counter()
    try:
        capture.open()
        fps = capture.fps or plan.camera.fps
        while max_frames is None or frame_id < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            result = pipeline.process(frame, frame_id, int(frame_id * 1000 / fps))
            observation = tracker.update(result)
            for event in observation.events:
                sink.write(event)
                if event.step_status.value == "completed":
                    confirmation.ping()
                print(
                    f"{event.extra['video_time_s']:7.3f}s  {event.step_id:18s}  "
                    f"{event.confidence:.0%}  {event.evidence_summary}"
                )
            frame_id += 1
    finally:
        capture.close()
        sink.close()
        confirmation.shutdown()
    elapsed = time.perf_counter() - started
    final_state = observation.state if observation is not None else "no_frames"
    print(f"state={final_state} frames={frame_id} fps={frame_id / max(elapsed, 0.001):.1f}")
    print(f"device={pipeline.device}")
    print(f"event_log={output_path}")
    if require_complete and final_state != "completed":
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analyze-sequence", description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("source", help="Webcam index or MP4 file path.")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--yolo-model", default="models/yolo11n.pt")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return analyze(
        args.plan,
        args.source,
        args.log,
        args.device,
        args.yolo_model,
        args.max_frames,
        args.require_complete,
    )


if __name__ == "__main__":
    raise SystemExit(main())
