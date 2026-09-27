"""Mocked replay harness for the procedure engine.

Use a tiny DSL script to drive the engine without any real perception models.
Each line is one of:

  silence           enable the silence window (audit logged)
  step:ID evidence  hand-object-interaction evidence for `ID` for `evidence` frames
  wait:N            wait N frames with no evidence
  grasp:ID          short for `step:ID grasping` for the persistence window
  place:ID          short for `step:ID placing` for the persistence window
  open:ID           short for `step:ID opening` for the persistence window
  close:ID          short for `step:ID closing` for the persistence window

Example script (red/blue box golden path):

  grasp:big_box
  grasp:small_red_box
  place:small_red_box
  grasp:small_blue_box
  place:small_blue_box
  close:big_box
  wait:5

The CLI prints the engine output per frame and writes a JSONL event log.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from halo.config import logs_dir
from halo.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    HandObjectInteraction,
    PerceptionResult,
    PoseKeypoints,
)
from halo.procedure import build_engine
from halo.schema.cli import load_plan


def _plan_object_classes(plan) -> dict[str, list[str]]:
    return {obj.id: obj.classes for obj in plan.objects}


def _result(
    target: tuple[str, str] | None,
    frame_id: int,
    plan_objects: dict[str, list[str]] | None = None,
) -> PerceptionResult:
    if target is None:
        return PerceptionResult(frame_id=frame_id, ts_ms=0, width=100, height=100)
    obj_id, label = target
    if plan_objects and obj_id in plan_objects and plan_objects[obj_id]:
        cls = plan_objects[obj_id][0]
    else:
        cls = obj_id
    det = Detection(cls=cls, conf=0.9, bbox=BBox(0, 0, 100, 100))
    hand = HandKeypoints(handedness="right", score=0.9, keypoints=[(0, 0, 0)] * 21)
    hand.keypoints[8] = (50.0, 50.0, 0.9)
    hoi = HandObjectInteraction(hand="right", object_cls=cls, label=label, score=0.9)
    return PerceptionResult(
        frame_id=frame_id,
        ts_ms=0,
        width=100,
        height=100,
        detections=[det],
        pose=PoseKeypoints(keypoints=[(50, 50, 0.9)] * 33, score=0.9),
        hands=[hand],
        hoi=[hoi],
    )


_LINE_RE = re.compile(r"^\s*(?P<cmd>[a-z_]+)(?::(?P<arg>\S+))?(?:\s*x\s*(?P<count>\d+))?\s*$")


def parse_script(text: str) -> list[tuple[str, str | int | None]]:
    out: list[tuple[str, str | int | None]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _LINE_RE.match(line)
        if not m:
            raise ValueError(f"bad script line: {raw!r}")
        cmd = m.group("cmd")
        arg = m.group("arg")
        count = int(m.group("count") or "1")
        if cmd in {"grasp", "place", "open", "close", "step"}:
            if arg is None:
                raise ValueError(f"{cmd} requires an argument")
            if ":" in arg:
                obj_id, label = arg.split(":", 1)
            else:
                label = {
                    "grasp": "grasping",
                    "place": "placing",
                    "open": "opening",
                    "close": "closing",
                }.get(cmd, "grasping")
                obj_id = arg
            for _ in range(count):
                out.append(("evidence", (obj_id, label)))
        elif cmd == "wait":
            out.append(("wait", int(arg or "1") * count))
        elif cmd == "silence":
            for _ in range(count):
                out.append(("silence", None))
        else:
            raise ValueError(f"unknown command: {cmd}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="replay-motor", description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("script", type=Path, help="DSL file (see module docstring).")
    parser.add_argument("--log", type=Path, default=None, help="Output JSONL path.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    plan = load_plan(args.plan)
    log_path = args.log or (logs_dir() / f"replay_{plan.experiment_id}_{int(time.time())}.jsonl")
    engine = build_engine(plan, sink_path=log_path)
    plan_objects = _plan_object_classes(plan)

    script = parse_script(args.script.read_text(encoding="utf-8"))
    frame_id = 0
    for cmd, arg in script:
        if cmd == "silence":
            engine.silence()
            continue
        if cmd == "wait":
            for _ in range(int(arg)):
                out = engine.step(_result(None, frame_id, plan_objects))
                if not args.quiet:
                    print(
                        f"frame {frame_id:4d}  state={out.state:11s}  "
                        f"cur={out.current_step_id:18s}  cof={out.current_step_confidence:.2f}"
                    )
                frame_id += 1
            continue
        if cmd == "evidence":
            out = engine.step(_result(arg, frame_id, plan_objects))
            if not args.quiet:
                obj_id, label = arg  # type: ignore[misc]
                print(
                    f"frame {frame_id:4d}  state={out.state:11s}  "
                    f"cur={out.current_step_id:18s}  cof={out.current_step_confidence:.2f}  "
                    f"feed={obj_id}:{label}  fired={out.fired_alerts}"
                )
            frame_id += 1
    engine.close()
    print(f"event log -> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
