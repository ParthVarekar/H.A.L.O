"""Tiny dataset recorder.

Sources:
  - Webcam (default `--source 0`).
  - MP4 file (`--source path\\to\\file.mp4`) for replay / testing without
    a camera. Press R to rewind, Q to quit. Useful for sanity-checking
    downstream tools without re-recording.

Output:
  - MP4 chunks under `datasets/<demo>/raw/take_<NNNN>/chunk_<HH>.mp4`.
  - A sidecar `meta.jsonl` per take with one row per chunk:
      {take_id, chunk_id, start_frame, end_frame, fps, source}
  - A session-level `session.json` with session_id, demo name, started_at,
    total_chunks, source kind.

Controls:
  SPACE  start a new chunk
  R      rewind source file (file mode only)
  Q      quit
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

from bas_har import config
from bas_har.config import default_camera_source


@dataclass(slots=True)
class ChunkMeta:
    take_id: int
    chunk_id: int
    start_frame: int
    end_frame: int
    fps: float
    source: str
    started_at: str
    ended_at: str


def _next_take_dir(raw_dir: Path) -> Path:
    existing = [p for p in raw_dir.iterdir() if p.is_dir() and p.name.startswith("take_")]
    nums = [int(p.name.split("_", 1)[1]) for p in existing if p.name.split("_", 1)[1].isdigit()]
    next_num = (max(nums) + 1) if nums else 1
    return raw_dir / f"take_{next_num:04d}"


def _resolve_source(source: str | int) -> tuple[cv2.VideoCapture, str]:
    if isinstance(source, str) and source.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        cap = cv2.VideoCapture(source)
        kind = f"file:{source}"
    else:
        idx = int(source) if isinstance(source, str) else source
        cap = cv2.VideoCapture(idx)
        kind = f"webcam:{idx}"
    if not cap.isOpened():
        raise RuntimeError(f"could not open source: {source}")
    return cap, kind


def _open_writer(path: Path, fps: float, width: int, height: int) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(str(path), fourcc, fps, (width, height))


def record(
    source: str | int,
    demo: str,
    max_chunks: int | None,
    out_root: Path,
) -> int:
    raw_dir = out_root / demo / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    take_dir = _next_take_dir(raw_dir)
    take_dir.mkdir(parents=True, exist_ok=True)

    cap, kind = _resolve_source(source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)

    print(f"[record] take_dir={take_dir}")
    print(f"[record] source={kind} fps={fps:.2f} {width}x{height}")
    print("[record] SPACE=new chunk  R=rewind(file)  Q=quit")

    session = {
        "demo": demo,
        "take_id": int(take_dir.name.split("_")[1]),
        "started_at": datetime.now(UTC).isoformat(),
        "source": kind,
        "fps": fps,
        "resolution": [width, height],
    }

    chunk_id = 0
    recording = False
    writer: cv2.VideoWriter | None = None
    chunk_meta: list[ChunkMeta] = []
    global_frame = 0
    chunk_start_frame = 0
    chunk_started_at: str | None = None

    def close_chunk(end_frame: int) -> None:
        nonlocal writer, chunk_id, chunk_start_frame, chunk_started_at
        if writer is None:
            return
        writer.release()
        writer = None
        chunk_meta.append(
            ChunkMeta(
                take_id=int(take_dir.name.split("_")[1]),
                chunk_id=chunk_id,
                start_frame=chunk_start_frame,
                end_frame=end_frame,
                fps=fps,
                source=kind,
                started_at=chunk_started_at or "",
                ended_at=datetime.now(UTC).isoformat(),
            )
        )
        print(f"[record] closed chunk {chunk_id:02d} frames={end_frame - chunk_start_frame}")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[record] source exhausted")
                break
            global_frame += 1

            preview = frame.copy()
            cv2.putText(
                preview,
                f"REC {'ON' if recording else 'OFF'}  frame={global_frame}  chunk={chunk_id:02d}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0) if recording else (0, 0, 255),
                2,
            )
            cv2.imshow("bas_har recorder", preview)

            if recording and writer is not None:
                writer.write(frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r") and kind.startswith("file:"):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                global_frame = 0
                print("[record] rewound source")
            if key == 32:
                if not recording:
                    chunk_id += 1
                    chunk_path = take_dir / f"chunk_{chunk_id:02d}.mp4"
                    writer = _open_writer(chunk_path, fps, width, height)
                    chunk_start_frame = global_frame
                    chunk_started_at = datetime.now(UTC).isoformat()
                    recording = True
                    print(f"[record] start chunk {chunk_id:02d} -> {chunk_path.name}")
                else:
                    close_chunk(global_frame)
                    recording = False
                    if max_chunks and chunk_id >= max_chunks:
                        print(f"[record] hit max_chunks={max_chunks}")
                        break
    finally:
        if writer is not None:
            close_chunk(global_frame)
        cap.release()
        cv2.destroyAllWindows()

    session_meta_path = take_dir / "session.json"
    session["ended_at"] = datetime.now(UTC).isoformat()
    session["chunks"] = [asdict(m) for m in chunk_meta]
    session_meta_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    print(f"[record] wrote {session_meta_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="record-dataset", description=__doc__)
    parser.add_argument(
        "--source",
        default=default_camera_source(),
        help="Webcam index (0, 1, ...) or path to MP4 file.",
    )
    parser.add_argument(
        "--demo",
        default="red_blue_box",
        help="Demo folder name under datasets/.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=config.datasets_dir(),
        help="Output root (default: datasets/).",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Stop after N chunks per take.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return record(args.source, args.demo, args.max_chunks, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
