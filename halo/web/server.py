"""Serve the React dashboard and run capture, perception, and procedure state."""

from __future__ import annotations

import argparse
import contextlib
import json
import mimetypes
import queue
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from bas_har.config import keys_dir, logs_dir, project_root
from bas_har.procedure import (
    ColorSequenceTracker,
    ProcedureEngine,
    build_engine,
    detections_needed,
    perception_needs,
    question_verdict,
)
from bas_har.schema.activity_schema import (
    ActivityId,
    ActivityLifecycle,
    ActivityManifest,
    JobStatus,
    RecordId,
    ReleaseStatus,
    TrainingPreset,
)
from bas_har.schema.cli import load_plan
from bas_har.schema.display_schema import DisplaySettings
from bas_har.schema.event_schema import EventRecord
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.schema.recognition_schema import ActivityRecognition
from bas_har.schema.stream_schema import StreamOutputSettings
from bas_har.studio.annotations import (
    delete_annotation,
    list_annotations,
    list_keyframes,
    read_take_frame,
    save_annotation,
)
from bas_har.studio.datasets import activity_dataset_dir, load_dataset_version
from bas_har.studio.evaluation import EvaluationJobManager, evaluation_csv, load_evaluation_report
from bas_har.studio.hardware import hardware_snapshot
from bas_har.studio.jobs import DatasetJobManager, TrainingJobManager
from bas_har.studio.plans import load_activity_plan, save_activity_plan
from bas_har.studio.quality import inspect_dataset, load_quality_report
from bas_har.studio.recognition import activity_detector_path, recognize_activity
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.releases import (
    activate_release,
    approve_release,
    create_candidate,
    list_releases,
)
from bas_har.studio.takes import list_takes, register_take
from bas_har.studio.timeline import import_timeline, list_timeline
from bas_har.studio.verification import release_audit_csv, verify_activity_package
from bas_har.voice import ConfirmationSound
from bas_har.web.frame_encoder import FrameEncoder

STATIC_DIR = project_root() / "web" / "dist"
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/svg+xml", ".svg")
DEFAULT_TARGET_CLASSES = ["box", "cup", "bottle", "bowl", "book", "orange", "banana", "apple"]
VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_VIDEO_BYTES = 4_000_000_000
DISCARD_BODY_LIMIT = 64_000_000
MAX_PLAYBACK_LAG_S = 0.5
RECORDER_QUEUE_FRAMES = 50
PERF_LOG_INTERVAL_S = 5.0
STATUS_TIMING_INTERVAL_S = 0.5
BOX_COLOR_BGR = (255, 157, 91)
BOX_LABEL_BGR = (255, 214, 176)
BOX_TAG_BGR = (16, 11, 8)
BOX_LABEL_SCALE = 0.36


def _is_file_source(source: int | str) -> bool:
    if isinstance(source, int):
        return False
    text = str(source)
    if text.isdigit() or "://" in text:
        return False
    return Path(text).suffix.lower() in VIDEO_SUFFIXES


def _nvidia_gpu_present() -> bool:
    try:
        import pynvml
    except ImportError:
        return False
    try:
        pynvml.nvmlInit()
        try:
            return pynvml.nvmlDeviceGetCount() > 0
        finally:
            pynvml.nvmlShutdown()
    except pynvml.NVMLError:
        return False


def _activity_run_mode(registry: ActivityRegistry, activity_id: str) -> str:
    """How an activity would be monitored: trained detector, described objects, or not at all."""
    if activity_detector_path(registry, activity_id).is_file():
        return "trained"
    try:
        plan = load_activity_plan(registry, activity_id)
    except (FileNotFoundError, ValueError, ValidationError):
        return "unavailable"
    return "described" if any(obj.prompts for obj in plan.objects) else "unavailable"


def _recognition_mode(zero_shot: bool, has_questions: bool) -> str:
    if zero_shot:
        return "zero_shot"
    return "hybrid" if has_questions else "trained"


def _cpu_fallback(device: str, gpu_present: bool) -> bool:
    return device == "cpu" and gpu_present


class PlaybackClock:
    """Releases file frames at the video's own frame rate against a wall clock."""

    def __init__(
        self,
        fps: float,
        stop_event: threading.Event,
        now: Callable[[], float] = time.perf_counter,
        max_lag_s: float = MAX_PLAYBACK_LAG_S,
    ) -> None:
        self.fps = max(fps, 1.0)
        self.stop_event = stop_event
        self.now = now
        self.max_lag_s = max_lag_s
        self.started: float | None = None

    def start(self) -> None:
        self.started = self.now()

    def lag_s(self, frame_id: int) -> float:
        if self.started is None:
            return 0.0
        return self.now() - (self.started + frame_id / self.fps)

    def wait_for(self, frame_id: int) -> bool:
        if self.started is None:
            self.start()
        lag = self.lag_s(frame_id)
        if lag < 0:
            self.stop_event.wait(-lag)
            return True
        return lag <= self.max_lag_s


class LatestSlot:
    """Single-item hand-off where a newer item replaces one not yet taken."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._item: Any = None
        self._closed = False
        self.dropped = 0

    def put(self, item: Any) -> None:
        with self._condition:
            if self._item is not None:
                self.dropped += 1
            self._item = item
            self._condition.notify()

    def take(self, timeout: float = 0.5) -> Any:
        with self._condition:
            if self._item is None and not self._closed:
                self._condition.wait(timeout)
            item, self._item = self._item, None
            return item

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed and self._item is None


class StageTimer:
    def __init__(self, alpha: float = 0.1) -> None:
        self.alpha = alpha
        self._values: dict[str, float] = {}
        self._lock = threading.Lock()

    def record(self, stage: str, seconds: float) -> None:
        value = seconds * 1000.0
        with self._lock:
            previous = self._values.get(stage)
            self._values[stage] = (
                value if previous is None else previous + self.alpha * (value - previous)
            )

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return {stage: round(value, 2) for stage, value in self._values.items()}


def _source_value(source: int | str) -> int | str:
    if isinstance(source, int):
        return source
    return int(source) if source.isdigit() else source


def _existing_dashboard_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("dashboard response must be a JSON object")
    return value


def _control_existing_dashboard(
    host: str,
    port: int,
    source: int | str,
    max_frames: int | None,
    device: str,
) -> bool:
    base_url = _existing_dashboard_url(host, port)
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as response:
            health = json.loads(response.read().decode("utf-8"))
        if not isinstance(health, dict) or health.get("service") != "bas-har-web":
            return False
        _post_json(f"{base_url}/api/stop", {})
        payload: dict[str, Any] = {"source": source}
        if max_frames is not None:
            payload["max_frames"] = max_frames
        payload["device"] = device
        _post_json(f"{base_url}/api/start", payload)
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _plan_summary(plan: ExperimentPlan) -> dict[str, Any]:
    return {
        "id": plan.experiment_id,
        "name": plan.name,
        "version": plan.version,
        "description": plan.description,
        "steps": [
            {
                "id": step.id,
                "description": step.description,
                "expected_duration_s": step.expected_duration_s,
                "timeout_s": step.timeout_s,
                "instruction": {str(lang): text for lang, text in step.instruction.items()},
                "evidence": [rule.kind for rule in step.evidence],
            }
            for step in plan.steps
        ],
        "spoken_name": {str(lang): text for lang, text in plan.spoken_name.items()},
    }


def uses_default_classes_only(plan: ExperimentPlan) -> bool:
    """Whether every class the plan relies on is a stock detector class, so the rest can be ignored."""
    return set(plan.detector_classes()) <= set(DEFAULT_TARGET_CLASSES)


def _plan_color_names(plan: ExperimentPlan) -> list[str]:
    return sorted(
        {
            color.lower()
            for obj in plan.objects
            for color in obj.colors_any
            if color.lower() in {"red", "blue"}
        }
    )


def _event_dict(event: EventRecord | None) -> dict[str, Any] | None:
    return event.model_dump(mode="json") if event is not None else None


def _detection_dict(result: Any) -> list[dict[str, Any]]:
    return [
        {
            "class": detection.cls,
            "color": detection.color,
            "confidence": round(detection.conf, 3),
            "bbox": {
                "x1": round(detection.bbox.x1, 1),
                "y1": round(detection.bbox.y1, 1),
                "x2": round(detection.bbox.x2, 1),
                "y2": round(detection.bbox.y2, 1),
            },
        }
        for detection in result.detections
    ]


def _annotate_frame(frame: Any, detections: list[Any]) -> Any:
    import cv2
    import numpy as np

    font = cv2.FONT_HERSHEY_SIMPLEX
    for detection in detections:
        bbox = detection.bbox
        x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR_BGR, 1, cv2.LINE_AA)
        name = detection.cls.replace("__", " ").replace("_", " ")
        label = f"{detection.color + ' ' if detection.color else ''}{name} {detection.conf:.0%}"
        (width, height), _ = cv2.getTextSize(label, font, BOX_LABEL_SCALE, 1)
        top = y1 - height - 5 if y1 - height - 5 >= 0 else y1 + 1
        tag = frame[max(0, top) : top + height + 5, max(0, x1) : x1 + width + 6]
        if tag.size:
            cv2.addWeighted(tag, 0.3, np.full_like(tag, BOX_TAG_BGR), 0.7, 0, dst=tag)
        cv2.putText(
            frame,
            label,
            (x1 + 3, top + height + 2),
            font,
            BOX_LABEL_SCALE,
            BOX_LABEL_BGR,
            1,
            cv2.LINE_AA,
        )
    return frame


def _render_frame(frame: Any, result: Any, display: DisplaySettings) -> Any:
    if not display.show_boxes:
        return frame
    shown = [det for det in result.detections if det.conf >= display.min_confidence]
    return _annotate_frame(frame.copy(), shown)


def _encode_still(frame: Any) -> bytes | None:
    import cv2

    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return encoded.tobytes() if ok else None


class WebState:
    def __init__(self, plan: ExperimentPlan) -> None:
        self.plan = plan
        self.plan_data = _plan_summary(plan)
        first = plan.steps[0]
        self.lock = threading.RLock()
        self.frame_ready = threading.Condition(self.lock)
        self.runner: SessionRunner | None = None
        self.frame_jpeg: bytes | None = None
        self.last_render: tuple[Any, Any, int] | None = None
        self.display = DisplaySettings()
        self.stream_out = StreamOutputSettings()
        self.publisher: Any | None = None
        self.events: list[dict[str, Any]] = []
        self.status: dict[str, Any] = {
            "running": False,
            "source": str(plan.camera.source),
            "frame_id": -1,
            "fps": 0.0,
            "state": "in_progress",
            "current_step_id": first.id,
            "current_step_description": first.description,
            "next_step_id": first.next[0] if first.next else None,
            "confidence": 0.0,
            "pause_active": False,
            "in_cooldown": False,
            "detections": [],
            "last_event": None,
            "message": "Ready to capture",
            "error": None,
            "log_path": None,
            "buffer_dir": None,
            "buffer_segment_count": 0,
            "device": None,
            "recognizer": None,
            "has_frame": False,
            "started_at": None,
            "summary": None,
            "analysis": None,
            "plan_revision": 0,
            "realtime": False,
            "realtime_factor": None,
            "lag_s": 0.0,
            "timings_ms": {},
            "display_fps": 0.0,
            "encoder": None,
            "cpu_fallback": False,
            "falling_behind": False,
            "mode": "trained",
            "questions": 0,
            "questions_answered": 0,
            "answers": {},
            "show_boxes": True,
            "min_box_confidence": 0.0,
            "video_time_s": 0.0,
            "downlink": None,
        }

    def snapshot(self) -> dict[str, Any]:
        stream_out = self.stream_out_status()
        with self.lock:
            return {**self.status, "events": list(self.events), "stream_out": stream_out}

    def stream_out_status(self) -> dict[str, Any]:
        with self.lock:
            settings = self.stream_out
            publisher = self.publisher
        if publisher is not None:
            return {**settings.model_dump(mode="json"), **publisher.status().model_dump()}
        return {
            **settings.model_dump(mode="json"),
            "target": settings.target,
            "player_url": settings.player_url,
            "frames_sent": 0,
            "codec": None,
            "error": None,
        }

    def set_stream_out(self, settings: StreamOutputSettings) -> None:
        """Stop any running stream and start a new one to the configured address when enabled."""
        from bas_har.io.stream_out import UdpStreamPublisher

        with self.lock:
            previous = self.publisher
            self.publisher = None
            self.stream_out = settings
        if previous is not None:
            previous.close()
        if settings.enabled:
            publisher = UdpStreamPublisher(settings)
            with self.lock:
                self.publisher = publisher

    def offer_stream(self, frame: Any) -> None:
        publisher = self.publisher
        if publisher is not None:
            publisher.offer(frame)

    def close_stream(self) -> None:
        with self.lock:
            publisher = self.publisher
            self.publisher = None
        if publisher is not None:
            publisher.close()

    def update(self, **values: Any) -> None:
        with self.lock:
            self.status.update(values)

    def prepare_for_capture(self, source: int | str) -> None:
        first = self.plan.steps[0]
        with self.lock:
            self.frame_jpeg = None
            self.last_render = None
            self.events.clear()
            self.status.update(
                running=True,
                source=str(source),
                frame_id=-1,
                fps=0.0,
                state="starting",
                current_step_id=first.id,
                current_step_description=first.description,
                next_step_id=first.next[0] if first.next else None,
                confidence=0.0,
                pause_active=False,
                in_cooldown=False,
                detections=[],
                last_event=None,
                message="Starting capture pipeline",
                error=None,
                log_path=None,
                buffer_dir=None,
                buffer_segment_count=0,
                device=None,
                recognizer=None,
                has_frame=False,
                started_at=None,
                summary=None,
                video_time_s=0.0,
                downlink=None,
            )

    def append_event(self, event: EventRecord) -> None:
        event_data = _event_dict(event)
        if event_data is None:
            return
        with self.lock:
            self.events.append(event_data)
            self.events = self.events[-40:]
            self.status["last_event"] = event_data

    def get_runner(self) -> SessionRunner | None:
        with self.lock:
            return self.runner

    def set_runner(self, runner: SessionRunner | None) -> None:
        with self.lock:
            self.runner = runner

    def replace_plan(self, plan: ExperimentPlan) -> None:
        first = plan.steps[0]
        with self.lock:
            self.plan = plan
            self.plan_data = _plan_summary(plan)
            self.frame_jpeg = None
            self.last_render = None
            self.events.clear()
            self.status.update(
                running=False,
                source=str(plan.camera.source),
                frame_id=-1,
                fps=0.0,
                state="in_progress",
                current_step_id=first.id,
                current_step_description=first.description,
                next_step_id=first.next[0] if first.next else None,
                confidence=0.0,
                pause_active=False,
                in_cooldown=False,
                detections=[],
                last_event=None,
                message="Activity package selected",
                error=None,
                log_path=None,
                buffer_dir=None,
                buffer_segment_count=0,
                device=None,
                recognizer=None,
                has_frame=False,
                started_at=None,
                summary=None,
                analysis=None,
                downlink=None,
                plan_revision=int(self.status.get("plan_revision", 0)) + 1,
            )

    def set_frame(self, frame_jpeg: bytes, frame_id: int) -> None:
        with self.frame_ready:
            self.frame_jpeg = frame_jpeg
            self.status["frame_id"] = frame_id
            self.status["has_frame"] = True
            self.frame_ready.notify_all()

    def frame_snapshot(self) -> tuple[bytes | None, int]:
        with self.lock:
            return self.frame_jpeg, int(self.status["frame_id"])

    def remember_render(self, frame: Any, result: Any, frame_id: int) -> None:
        with self.lock:
            self.last_render = (frame, result, frame_id)

    def set_display(self, display: DisplaySettings) -> None:
        """Apply display settings and redraw the still frame shown after a session ends."""
        with self.lock:
            self.display = display
            self.status["show_boxes"] = display.show_boxes
            self.status["min_box_confidence"] = display.min_confidence
            last = self.last_render
            running = bool(self.status["running"])
        if last is None or running:
            return
        frame, result, frame_id = last
        still = _encode_still(_render_frame(frame, result, display))
        if still is not None:
            self.set_frame(still, frame_id)

    def wait_for_frame(self, last_frame_id: int, timeout: float) -> tuple[bytes | None, int]:
        with self.frame_ready:
            self.frame_ready.wait_for(
                lambda: (
                    self.frame_jpeg is not None and int(self.status["frame_id"]) != last_frame_id
                ),
                timeout,
            )
            return self.frame_jpeg, int(self.status["frame_id"])


class SessionRunner:
    def __init__(
        self,
        state: WebState,
        source: int | str,
        yolo_model: str,
        max_frames: int | None = None,
        device: str = "auto",
        filter_default_classes: bool = True,
        use_media_time: bool = False,
        realtime: bool | None = None,
        record_buffer: bool | None = None,
        upload: bool = False,
        zero_shot: bool = False,
        answer_questions: bool = True,
    ) -> None:
        self.state = state
        self.source = source
        self.yolo_model = yolo_model
        self.zero_shot = zero_shot
        self.answer_questions = answer_questions
        self.max_frames = max_frames
        self.device = device
        self.filter_default_classes = filter_default_classes
        self.use_media_time = use_media_time
        is_file = _is_file_source(source)
        self.realtime = is_file if realtime is None else realtime
        self.record_buffer = (not upload) if record_buffer is None else record_buffer
        self.stop_event = threading.Event()
        self.engine: ProcedureEngine | None = None
        self.engine_lock = threading.Lock()
        self.timer = StageTimer()
        self.thread = threading.Thread(target=self._run, name="bas-har-capture", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def is_alive(self) -> bool:
        return self.thread.is_alive()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not threading.current_thread():
            self.thread.join(timeout=5)

    def silence(self) -> None:
        with self.engine_lock:
            if self.engine is not None:
                self.engine.silence()

    def _present(self, slot: LatestSlot, encoder: FrameEncoder) -> None:
        shown = 0
        started = time.perf_counter()
        while not slot.closed:
            item = slot.take(timeout=0.5)
            if item is None:
                continue
            frame_id, frame, result = item
            began = time.perf_counter()
            self.state.remember_render(frame, result, frame_id)
            annotated = _render_frame(frame, result, self.state.display)
            self.state.offer_stream(annotated)
            drawn = time.perf_counter()
            encoded = encoder.encode(annotated)
            encoded_at = time.perf_counter()
            self.timer.record("draw", drawn - began)
            self.timer.record("encode", encoded_at - drawn)
            if encoded is not None:
                self.state.set_frame(encoded, frame_id)
                shown += 1
                self.state.update(display_fps=round(shown / max(encoded_at - started, 0.001), 1))

    def _record(self, frames: queue.Queue[Any], buffer_dir: Path, fps: float) -> None:
        from bas_har.io import Mp4CircularBuffer
        from bas_har.schema.io_schema import CircularBufferConfig

        buffer: Any | None = None
        try:
            while True:
                frame = frames.get()
                if frame is None:
                    break
                if buffer is None:
                    frame_height, frame_width = frame.shape[:2]
                    buffer = Mp4CircularBuffer(
                        CircularBufferConfig(
                            directory=buffer_dir,
                            fps=fps,
                            resolution=(frame_width, frame_height),
                        )
                    )
                began = time.perf_counter()
                buffer.write(frame)
                self.timer.record("record", time.perf_counter() - began)
        finally:
            if buffer is not None:
                buffer.close()
                self.state.update(buffer_segment_count=len(buffer.paths()))

    @staticmethod
    def _offer_recording(frames: queue.Queue[Any], frame: Any) -> None:
        try:
            frames.put_nowait(frame)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                frames.get_nowait()
            with contextlib.suppress(queue.Full):
                frames.put_nowait(frame)

    def _source_bytes(self, buffer_dir: Path | None) -> int | None:
        if _is_file_source(self.source):
            with contextlib.suppress(OSError):
                return Path(str(self.source)).stat().st_size
        if self.record_buffer and buffer_dir is not None and buffer_dir.is_dir():
            return sum(path.stat().st_size for path in buffer_dir.glob("*.mp4")) or None
        return None

    def _write_downlink(self, sink: Any, buffer_dir: Path | None) -> None:
        """Seal the session in a signed, kilobyte-scale report and check it against the log."""
        from bas_har.io.signed_log import build_downlink, verify_downlink, write_downlink

        try:
            source_bytes = self._source_bytes(buffer_dir)
            report = build_downlink(sink, sink.key, source_bytes=source_bytes)
            path = sink.path.with_suffix(".downlink.json")
            size = write_downlink(report, path)
            check = verify_downlink(path, sink.key.public_bytes, sink.path)
        except (OSError, ValueError) as exc:
            self.state.update(downlink={"error": str(exc)})
            return
        self.state.update(
            downlink={
                "path": str(path),
                "log_path": str(sink.path),
                "bytes": size,
                "source_bytes": source_bytes,
                "ratio": round(source_bytes / size) if source_bytes else None,
                "events": report.event_count,
                "key_id": report.key_id,
                "final_hash": report.log_final_hash,
                "verified": check.ok,
            }
        )

    def _build_questioner(self, questions: list[str]) -> Any | None:
        if not questions:
            return None
        from bas_har.perception.vlm import AsyncVisualQuestioner, VisualQuestionAnswerer

        self.state.update(message="Loading the vision-language model")
        answerer = VisualQuestionAnswerer(
            device=self.device,
            context=f"You are watching {self.state.plan.name}.",
        )
        return AsyncVisualQuestioner(answerer, questions)

    def _run(self) -> None:
        from bas_har.io import VideoCaptureSource
        from bas_har.io.signed_log import SignedJsonlEventSink, load_or_create_station_key
        from bas_har.perception import PerceptionPipeline

        capture: Any | None = None
        sink: Any | None = None
        buffer_dir: Path | None = None
        confirmation: ConfirmationSound | None = None
        sequence: ColorSequenceTracker | None = None
        slot = LatestSlot()
        presenter: threading.Thread | None = None
        recorder: threading.Thread | None = None
        recording: queue.Queue[Any] | None = None
        perf_handle: Any | None = None
        completed_steps: list[str] = []
        late_steps: list[str] = []
        try:
            width, height = self.state.plan.camera.resolution
            capture = VideoCaptureSource(
                _source_value(self.source),
                resolution=(width, height),
                fps=self.state.plan.camera.fps,
            )
            capture.open()
            fps = capture.fps or self.state.plan.camera.fps
            stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime()) + f"_{uuid4().hex[:6]}"
            log_path = logs_dir() / f"web_{self.state.plan.experiment_id}_{stamp}.jsonl"
            station_key = load_or_create_station_key(keys_dir())
            sink = SignedJsonlEventSink(log_path, station_key, self.state.plan)
            perf_handle = log_path.with_suffix(".perf.jsonl").open("a", encoding="utf-8")
            confirmation = ConfirmationSound()
            buffer_dir = logs_dir() / "buffer" / self.state.plan.experiment_id / stamp
            try:
                sequence = ColorSequenceTracker(self.state.plan)
            except ValueError:
                sequence = None
            self.engine = build_engine(
                self.state.plan,
                sink=None if sequence is not None else sink,
                use_media_time=self.use_media_time,
            )
            needs_pose, needs_hands = perception_needs(self.state.plan)
            questions = self.state.plan.visual_questions() if self.answer_questions else []
            questioner = self._build_questioner(questions)
            pipeline = PerceptionPipeline(
                yolo_model=self.yolo_model,
                target_classes=DEFAULT_TARGET_CLASSES if self.filter_default_classes else None,
                run_pose=sequence is None and needs_pose,
                run_hands=sequence is None and needs_hands,
                device=self.device,
                color_names=_plan_color_names(self.state.plan),
                prompt_classes=self.state.plan.prompt_classes() if self.zero_shot else None,
                questioner=questioner,
                run_detector=not self.zero_shot or detections_needed(self.state.plan),
            )
            encoder = FrameEncoder(device=pipeline.device)
            self.state.update(message="Warming up the detector")
            pipeline.warmup(width, height)
            presenter = threading.Thread(
                target=self._present, args=(slot, encoder), name="bas-har-present", daemon=True
            )
            presenter.start()
            if self.record_buffer:
                recording = queue.Queue(maxsize=RECORDER_QUEUE_FRAMES)
                recorder = threading.Thread(
                    target=self._record,
                    args=(recording, buffer_dir, fps),
                    name="bas-har-record",
                    daemon=True,
                )
                recorder.start()
            self.state.update(
                running=True,
                source=str(self.source),
                frame_id=-1,
                fps=0.0,
                state=self.engine.state.value,
                message="Capturing and analyzing",
                error=None,
                log_path=str(log_path),
                buffer_dir=str(buffer_dir) if self.record_buffer else None,
                buffer_segment_count=0,
                device=pipeline.device,
                recognizer="color_sequence" if sequence is not None else "procedure_engine",
                has_frame=False,
                started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                realtime=self.realtime,
                realtime_factor=None,
                lag_s=0.0,
                timings_ms={},
                display_fps=0.0,
                encoder=encoder.backend,
                cpu_fallback=_cpu_fallback(pipeline.device, _nvidia_gpu_present()),
                falling_behind=False,
                mode=_recognition_mode(self.zero_shot, bool(questions)),
                questions=len(questions),
                questions_answered=0,
            )
            clock = PlaybackClock(fps, self.stop_event) if self.realtime else None
            started = time.perf_counter()
            if clock is not None:
                clock.start()
            frame_id = 0
            analysed = 0
            skipped = 0
            last_status = 0.0
            last_perf = started
            while not self.stop_event.is_set():
                if self.max_frames is not None and frame_id >= self.max_frames:
                    break
                began = time.perf_counter()
                ok, frame = capture.read()
                if not ok:
                    break
                decoded = time.perf_counter()
                self.timer.record("decode", decoded - began)
                if recording is not None:
                    self._offer_recording(recording, frame.copy())
                if clock is not None and not clock.wait_for(frame_id):
                    skipped += 1
                    frame_id += 1
                    continue
                ts_ms = int(frame_id * 1000 / max(fps, 1.0))
                detect_began = time.perf_counter()
                result = pipeline.process(frame, frame_id=frame_id, ts_ms=ts_ms)
                detected = time.perf_counter()
                self.timer.record("detect", detected - detect_began)
                if sequence is not None:
                    with self.engine_lock:
                        observation = sequence.update(result)
                    for event in observation.events:
                        sink.write(event)
                        self.state.append_event(event)
                        if event.step_status.value == "completed" and confirmation is not None:
                            confirmation.ping()
                    display_state = observation.state
                    display_step_id = observation.current_step_id
                    display_confidence = observation.confidence
                    display_pause = False
                    display_cooldown = False
                    display_message = (
                        "Sequence recognized"
                        if observation.state == "completed"
                        else "Capturing with color sequence tracker"
                    )
                else:
                    with self.engine_lock:
                        output = self.engine.step(result)
                    for event in output.events:
                        self.state.append_event(event)
                        if event.step_status.value == "completed":
                            if event.step_id not in completed_steps:
                                completed_steps.append(event.step_id)
                            if event.extra.get("out_of_order") and event.step_id not in late_steps:
                                late_steps.append(event.step_id)
                            if confirmation is not None:
                                confirmation.ping()
                    display_state = output.state.value
                    display_step_id = output.current_step_id
                    display_confidence = output.current_step_confidence
                    display_pause = output.pause_active
                    display_cooldown = output.in_cooldown
                    display_message = "Capturing and analyzing"
                engine_done = time.perf_counter()
                self.timer.record("engine", engine_done - detected)
                current = self.state.plan.steps_dict.get(display_step_id)
                description = current.description if current is not None else "Procedure complete"
                slot.put((frame_id, frame, result))
                analysed += 1
                now = time.perf_counter()
                elapsed = now - started
                lag = clock.lag_s(frame_id) if clock is not None else 0.0
                values: dict[str, Any] = {
                    "running": True,
                    "fps": round(analysed / max(elapsed, 0.001), 1),
                    "state": display_state,
                    "current_step_id": display_step_id,
                    "current_step_description": description,
                    "next_step_id": (
                        current.next[0] if current is not None and current.next else None
                    ),
                    "confidence": round(display_confidence, 3),
                    "pause_active": display_pause,
                    "in_cooldown": display_cooldown,
                    "detections": _detection_dict(result),
                    "message": display_message,
                }
                if now - last_status >= STATUS_TIMING_INTERVAL_S:
                    last_status = now
                    video_s = (frame_id + 1) / max(fps, 1.0)
                    values.update(
                        video_time_s=round(video_s, 1),
                        realtime_factor=round(video_s / max(elapsed, 0.001), 2),
                        lag_s=round(max(0.0, lag), 3),
                        timings_ms=self.timer.snapshot(),
                        falling_behind=lag > MAX_PLAYBACK_LAG_S / 2,
                    )
                    if questioner is not None:
                        values.update(
                            questions_answered=questioner.answered,
                            answers={
                                question: {
                                    "p": round(probability, 2),
                                    "verdict": question_verdict(probability),
                                }
                                for question, probability in result.questions.items()
                            },
                        )
                self.state.update(**values)
                if now - last_perf >= PERF_LOG_INTERVAL_S and perf_handle is not None:
                    last_perf = now
                    perf_handle.write(
                        json.dumps(
                            {
                                "wall_s": round(elapsed, 2),
                                "video_s": round((frame_id + 1) / max(fps, 1.0), 2),
                                "analysed": analysed,
                                "skipped": skipped,
                                "display_dropped": slot.dropped,
                                "lag_s": round(lag, 3),
                                "timings_ms": self.timer.snapshot(),
                            }
                        )
                        + "\n"
                    )
                    perf_handle.flush()
                frame_id += 1
        except Exception as exc:
            self.state.update(running=False, message="Capture error", error=str(exc))
        finally:
            slot.close()
            if questioner is not None:
                questioner.close()
            if presenter is not None:
                presenter.join(timeout=5)
            if recording is not None:
                recording.put(None)
            if recorder is not None:
                recorder.join(timeout=10)
            if capture is not None:
                capture.close()
            if self.engine is not None:
                with self.engine_lock:
                    self.engine.close()
            if sink is not None:
                sink.close()
                self._write_downlink(sink, buffer_dir)
            if perf_handle is not None:
                perf_handle.close()
            if confirmation is not None:
                confirmation.shutdown()
            with self.state.lock:
                was_error = self.state.status["error"] is not None
                message = "Capture stopped" if self.stop_event.is_set() else "Source complete"
                if was_error:
                    message = "Capture error"
                summary: dict[str, Any] | None = None
                if self.engine is not None and sequence is None:
                    plan_steps = [step.id for step in self.state.plan.steps]
                    skipped_steps = set(self.engine.skipped_step_ids)
                    summary = {
                        "experiment_id": self.state.plan.experiment_id,
                        "total_steps": len(plan_steps),
                        "completed_steps": [s for s in plan_steps if s in completed_steps],
                        "out_of_order_steps": [s for s in plan_steps if s in late_steps],
                        "skipped_steps": [s for s in plan_steps if s in skipped_steps],
                        "missed_steps": [
                            s
                            for s in plan_steps
                            if s not in completed_steps and s not in skipped_steps
                        ],
                        "source_finished": not self.stop_event.is_set() and not was_error,
                    }
                self.state.status.update(
                    running=False,
                    message=message,
                    summary=summary,
                    timings_ms=self.timer.snapshot(),
                    falling_behind=False,
                )
            if self.state.get_runner() is self:
                self.state.set_runner(None)


class DashboardHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "service": "bas-har-web"})
            return
        if parsed.path == "/api/hardware":
            self._send_json(hardware_snapshot())
            return
        if parsed.path == "/api/status":
            self._send_json(self.server.state.snapshot())
            return
        if parsed.path == "/api/stream-out":
            self._send_json(self.server.state.stream_out_status())
            return
        if parsed.path in {"/api/downlink", "/api/session-log"}:
            self._send_session_file("path" if parsed.path == "/api/downlink" else "log_path")
            return
        if parsed.path == "/api/plan":
            self._send_json(self.server.state.plan_data)
            return
        if parsed.path == "/api/events":
            self._send_json(self.server.state.snapshot()["events"])
            return
        if parsed.path == "/api/activities":
            self._send_json(
                [
                    manifest.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for manifest in self.server.registry.list_activities()
                ]
            )
            return
        if parsed.path == "/api/analyze/activities":
            self._send_json(
                [
                    {
                        "id": manifest.activity_id,
                        "name": manifest.name,
                        "has_detector": activity_detector_path(
                            self.server.registry, manifest.activity_id
                        ).is_file(),
                        "mode": _activity_run_mode(self.server.registry, manifest.activity_id),
                    }
                    for manifest in self.server.registry.list_activities()
                ]
            )
            return
        if parsed.path == "/api/operations/activities":
            approved = [
                manifest
                for manifest in self.server.registry.list_activities()
                if manifest.lifecycle in {ActivityLifecycle.APPROVED, ActivityLifecycle.ACTIVE}
            ]
            self._send_json(
                [
                    manifest.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for manifest in approved
                ]
            )
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/keyframes"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/keyframes"))
                query = urllib.parse.parse_qs(parsed.query)
                take_id = self._record_id(query.get("take_id", [""])[0])
                every_frames = int(query.get("every_frames", [30])[0])
                limit = int(query.get("limit", [120])[0])
                frames = list_keyframes(
                    self.server.registry, activity_id, take_id, every_frames, limit
                )
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            for frame in frames:
                frame["image_url"] = (
                    f"/api/activities/{urllib.parse.quote(str(activity_id))}/takes/"
                    f"{urllib.parse.quote(str(take_id))}/frames/{frame['frame_id']}.jpg"
                )
            self._send_json(frames)
            return
        frame_parts = parsed.path.strip("/").split("/")
        if (
            len(frame_parts) == 7
            and frame_parts[0] == "api"
            and frame_parts[1] == "activities"
            and frame_parts[3] == "takes"
            and frame_parts[5] == "frames"
            and frame_parts[6].lower().endswith(".jpg")
        ):
            try:
                activity_id = self._activity_id(f"/api/activities/{frame_parts[2]}")
                take_id = self._record_id(frame_parts[4])
                frame_id = int(Path(frame_parts[6]).stem)
                frame = read_take_frame(self.server.registry, activity_id, take_id, frame_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_bytes(frame, "image/jpeg")
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/annotations"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/annotations"))
                query = urllib.parse.parse_qs(parsed.query)
                raw_take_id = query.get("take_id", [None])[0]
                take_id = self._record_id(raw_take_id) if raw_take_id else None
                annotations = list_annotations(self.server.registry, activity_id, take_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(
                [annotation.model_dump(mode="json", by_alias=True) for annotation in annotations]
            )
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/takes"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/takes"))
                takes = list_takes(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json([take.model_dump(mode="json", by_alias=True) for take in takes])
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/timeline"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/timeline"))
                records = list_timeline(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json([record.model_dump(mode="json", by_alias=True) for record in records])
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/timeline-template"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/timeline-template"))
                self.server.registry.load(activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            template = (
                b"id,take_id,start_s,end_s,expected_step_id,observed_action,result,"
                b"object_ids,region_ids,notes\n"
                b"event-1,take-id,00:00:01.000,00:00:03.000,step_id,describe action,"
                b"completed,,,\n"
            )
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="timeline_template.csv"')
            self.send_header("Content-Length", str(len(template)))
            self.end_headers()
            self.wfile.write(template)
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/plan"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/plan"))
                plan = load_activity_plan(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(plan.model_dump(mode="json", by_alias=True))
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/dataset/jobs"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/dataset/jobs"))
                jobs = self.server.dataset_jobs.list(activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json([job.model_dump(mode="json", by_alias=True) for job in jobs])
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/training/jobs"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/training/jobs"))
                jobs = self.server.training_jobs.list(activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json([job.model_dump(mode="json", by_alias=True) for job in jobs])
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/evaluation/jobs"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/evaluation/jobs"))
                jobs = self.server.evaluation_jobs.list(activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json([job.model_dump(mode="json", by_alias=True) for job in jobs])
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/releases"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/releases"))
                releases = list_releases(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(
                [release.model_dump(mode="json", by_alias=True) for release in releases]
            )
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/releases/audit.csv"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/releases/audit.csv"))
                audit = release_audit_csv(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_bytes(audit, "text/csv; charset=utf-8", "release-audit.csv")
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/verification"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/verification"))
                verification = verify_activity_package(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(verification.model_dump(mode="json", by_alias=True))
            return
        if parsed.path == "/api/operations/select":
            try:
                payload = self._read_json()
                self._select_activity(payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/dataset/quality"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/dataset/quality"))
                report = load_quality_report(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(report.model_dump(mode="json", by_alias=True))
            return
        report_parts = parsed.path.strip("/").split("/")
        if (
            len(report_parts) == 6
            and report_parts[:4] == ["api", "activities", report_parts[2], "evaluation"]
            and report_parts[4] == "reports"
        ):
            try:
                activity_id = self._activity_id(f"/api/activities/{report_parts[2]}")
                report_id = (
                    Path(report_parts[5]).stem
                    if report_parts[5].lower().endswith(".csv")
                    else report_parts[5]
                )
                report = load_evaluation_report(self.server.registry, activity_id, report_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            if report_parts[5].lower().endswith(".csv"):
                self._send_bytes(
                    evaluation_csv(report), "text/csv; charset=utf-8", "evaluation.csv"
                )
                return
            self._send_json(report.model_dump(mode="json", by_alias=True))
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/dataset"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/dataset"))
                dataset = load_dataset_version(self.server.registry, activity_id)
                data_path = activity_dataset_dir(self.server.registry, activity_id) / "data.yaml"
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(
                {
                    "dataset": dataset.model_dump(mode="json", by_alias=True),
                    "data_path": str(data_path),
                }
            )
            return
        if parsed.path.startswith("/api/activities/"):
            try:
                activity_id = self._activity_id(parsed.path)
                manifest = self.server.registry.load(activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(manifest.model_dump(mode="json", by_alias=True, exclude_none=True))
            return
        if parsed.path == "/api/frame.jpg":
            self._send_frame()
            return
        if parsed.path == "/api/stream.mjpg":
            self._send_stream()
            return
        self._send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/analyze":
            self._analyze_video()
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/takes"):
            self._upload_take(parsed.path.removesuffix("/takes"))
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/timeline"):
            self._upload_timeline(parsed.path.removesuffix("/timeline"))
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/annotations"):
            try:
                payload = self._read_json()
                self._save_annotation(parsed.path.removesuffix("/annotations"), payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/releases"):
            try:
                payload = self._read_json()
                self._create_release(parsed.path.removesuffix("/releases"), payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        release_parts = parsed.path.strip("/").split("/")
        if (
            len(release_parts) == 6
            and release_parts[0] == "api"
            and release_parts[1] == "activities"
            and release_parts[3] == "releases"
            and release_parts[5] in {"approve", "activate"}
        ):
            try:
                payload = self._read_json()
                self._update_release(release_parts, payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.count("/") == 5 and parsed.path.endswith("/dataset/prepare"):
            try:
                payload = self._read_json()
                self._start_dataset(parsed.path.removesuffix("/dataset/prepare"), payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.count("/") == 6 and parsed.path.endswith("/dataset/quality/check"):
            try:
                activity_id = self._activity_id(parsed.path.removesuffix("/dataset/quality/check"))
                report = inspect_dataset(self.server.registry, activity_id)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(report.model_dump(mode="json", by_alias=True), HTTPStatus.OK)
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/evaluation"):
            try:
                payload = self._read_json()
                self._start_evaluation(parsed.path.removesuffix("/evaluation"), payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/training"):
            try:
                payload = self._read_json()
                self._start_training(parsed.path.removesuffix("/training"), payload)
            except (FileNotFoundError, ValueError, ValidationError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path not in {
            "/api/activities",
            "/api/start",
            "/api/stop",
            "/api/silence",
            "/api/display",
            "/api/stream-out",
        }:
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            if parsed.path == "/api/activities":
                self._create_activity(payload)
            elif parsed.path == "/api/display":
                display = DisplaySettings.model_validate(
                    {**self.server.state.display.model_dump(), **payload}
                )
                self.server.state.set_display(display)
                self._send_json(display.model_dump())
            elif parsed.path == "/api/stream-out":
                settings = StreamOutputSettings.model_validate(
                    {**self.server.state.stream_out.model_dump(mode="json"), **payload}
                )
                self.server.state.set_stream_out(settings)
                self._send_json(self.server.state.stream_out_status())
            elif parsed.path == "/api/start":
                self._start(payload)
            elif parsed.path == "/api/stop":
                self._stop()
            else:
                self._silence()
        except FileExistsError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.CONFLICT)
        except (ValueError, ValidationError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 5 or parts[:2] != ["api", "activities"] or parts[3] != "annotations":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            activity_id = self._activity_id(f"/api/activities/{parts[2]}")
            annotation_id = self._record_id(urllib.parse.unquote(parts[4]))
            delete_annotation(self.server.registry, activity_id, annotation_id)
        except FileNotFoundError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except (ValueError, ValidationError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"ok": True, "id": annotation_id})

    def do_PUT(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.count("/") != 4 or not parsed.path.endswith("/plan"):
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            self._save_plan(parsed.path.removesuffix("/plan"))
        except FileNotFoundError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except (ValueError, ValidationError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _save_plan(self, activity_path: str) -> None:
        activity_id = self._activity_id(activity_path)
        payload = self._read_json()
        plan = ExperimentPlan.model_validate(payload)
        saved = save_activity_plan(self.server.registry, activity_id, plan)
        self._send_json(saved.model_dump(mode="json", by_alias=True), HTTPStatus.OK)

    def _save_annotation(self, activity_path: str, payload: dict[str, Any]) -> None:
        activity_id = self._activity_id(activity_path)
        annotation = save_annotation(self.server.registry, activity_id, payload)
        self._send_json(annotation.model_dump(mode="json", by_alias=True), HTTPStatus.CREATED)

    def _create_release(self, activity_path: str, payload: dict[str, Any]) -> None:
        activity_id = self._activity_id(activity_path)
        report_id = str(payload.get("evaluation_report_id", "")).strip()
        model_path = str(payload.get("model_path", "")).strip()
        version = str(payload.get("version", "")).strip()
        if not report_id or not model_path or not version:
            raise ValueError("evaluation_report_id, model_path, and version are required")
        release = create_candidate(
            self.server.registry, activity_id, report_id, model_path, version
        )
        self._send_json(release.model_dump(mode="json", by_alias=True), HTTPStatus.CREATED)

    def _select_activity(self, payload: dict[str, Any]) -> None:
        activity_id = TypeAdapter(ActivityId).validate_python(str(payload.get("activity_id", "")))
        runner = self.server.state.get_runner()
        if runner is not None and runner.is_alive():
            raise ValueError("stop capture before selecting another activity")
        manifest = self.server.registry.load(activity_id)
        if manifest.lifecycle not in {ActivityLifecycle.APPROVED, ActivityLifecycle.ACTIVE}:
            raise ValueError("only an approved or active activity can be selected")
        releases = [
            release
            for release in list_releases(self.server.registry, activity_id)
            if release.status in {ReleaseStatus.APPROVED, ReleaseStatus.ACTIVE}
        ]
        if not releases:
            raise ValueError("activity has no approved release")
        release = next(
            (
                candidate
                for candidate in releases
                if candidate.release_id == manifest.active_release_id
            ),
            releases[-1],
        )
        plan = load_activity_plan(self.server.registry, activity_id)
        model_path = self.server.registry.package_dir(activity_id) / release.model_path
        if not model_path.is_file():
            raise FileNotFoundError(f"release model not found: {model_path}")
        verification = verify_activity_package(
            self.server.registry, activity_id, release.release_id
        )
        if not verification.passed:
            raise ValueError("activity package verification failed")
        self.server.yolo_model = str(model_path)
        self.server.filter_default_classes = False
        self.server.state.replace_plan(plan)
        self._send_json(
            {
                "activity": manifest.model_dump(mode="json", by_alias=True),
                "release": release.model_dump(mode="json", by_alias=True),
                "plan": _plan_summary(plan),
            },
            HTTPStatus.OK,
        )

    def _update_release(self, parts: list[str], payload: dict[str, Any]) -> None:
        activity_path = f"/api/activities/{parts[2]}"
        activity_id = self._activity_id(activity_path)
        release_id = self._record_id(parts[4])
        if parts[5] == "approve":
            release = approve_release(
                self.server.registry, activity_id, release_id, str(payload.get("reviewer", ""))
            )
        else:
            release = activate_release(self.server.registry, activity_id, release_id)
        self._send_json(release.model_dump(mode="json", by_alias=True), HTTPStatus.OK)

    def _start_dataset(self, activity_path: str, payload: dict[str, Any]) -> None:
        activity_id = self._activity_id(activity_path)
        job = self.server.dataset_jobs.start(
            activity_id,
            sample_every=int(payload.get("sample_every", 5)),
            val_ratio=float(payload.get("val_ratio", 0.2)),
            test_ratio=float(payload.get("test_ratio", 0.1)),
        )
        self._send_json(job.model_dump(mode="json", by_alias=True), HTTPStatus.ACCEPTED)

    def _start_training(self, activity_path: str, payload: dict[str, Any]) -> None:
        activity_id = self._activity_id(activity_path)
        dataset = load_dataset_version(self.server.registry, activity_id)
        preset = TrainingPreset(payload.get("preset", TrainingPreset.LAPTOP_SAFE.value))
        job = self.server.training_jobs.start(
            activity_id,
            dataset.dataset_id,
            preset=preset,
            requested_device=str(payload.get("device", "auto")),
            model_path=str(payload.get("model", self.server.yolo_model)),
        )
        self._send_json(job.model_dump(mode="json", by_alias=True), HTTPStatus.ACCEPTED)

    def _start_evaluation(self, activity_path: str, payload: dict[str, Any]) -> None:
        activity_id = self._activity_id(activity_path)
        training_job_id = str(payload.get("training_job_id", "")).strip()
        model_path = str(payload.get("model", "")).strip()
        if not training_job_id or not model_path:
            completed = [
                job
                for job in self.server.training_jobs.list(activity_id)
                if job.status is JobStatus.COMPLETED and job.output_path
            ]
            if not completed:
                raise ValueError("select a completed training job before evaluation")
            selected = completed[-1]
            training_job_id = selected.job_id
            model_path = selected.output_path or ""
        job = self.server.evaluation_jobs.start(
            activity_id,
            training_job_id,
            model_path,
            requested_device=str(payload.get("device", "auto")),
            iou_threshold=float(payload.get("iou_threshold", 0.5)),
        )
        self._send_json(job.model_dump(mode="json", by_alias=True), HTTPStatus.ACCEPTED)

    def _upload_take(self, activity_path: str) -> None:
        try:
            activity_id = self._activity_id(activity_path)
            manifest = self.server.registry.load(activity_id)
            filename = self.headers.get("X-Filename", "")
            session_id = self.headers.get("X-Recording-Session-ID", "").strip()
            if not filename:
                raise ValueError("X-Filename header is required")
            if not session_id:
                raise ValueError("X-Recording-Session-ID header is required")
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("uploaded video body is empty")
            if content_length > 4_000_000_000:
                raise ValueError("uploaded video exceeds the 4 GB local limit")
            suffix = Path(filename).suffix.lower()
            if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
                raise ValueError(f"unsupported video type: {suffix or 'none'}")
            temp_path = (
                self.server.registry.package_dir(manifest.activity_id)
                / "takes"
                / f".upload-{uuid4().hex}{suffix}"
            )
            remaining = content_length
            try:
                with temp_path.open("wb") as handle:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("uploaded video ended before Content-Length")
                        handle.write(chunk)
                        remaining -= len(chunk)
                record = register_take(
                    self.server.registry,
                    activity_id,
                    temp_path,
                    filename,
                    session_id,
                    self.headers.get("X-Actor-ID") or None,
                )
            finally:
                temp_path.unlink(missing_ok=True)
        except FileExistsError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.CONFLICT)
            return
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(record.model_dump(mode="json", by_alias=True), HTTPStatus.CREATED)

    def _upload_timeline(self, activity_path: str) -> None:
        temp_path: Path | None = None
        try:
            activity_id = self._activity_id(activity_path)
            manifest = self.server.registry.load(activity_id)
            filename = self.headers.get("X-Filename", "timeline.csv")
            suffix = Path(filename).suffix.lower()
            if suffix not in {".csv", ".xlsx", ".xlsm"}:
                raise ValueError("timeline must be a CSV or Excel workbook")
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("uploaded timeline body is empty")
            if content_length > 100_000_000:
                raise ValueError("uploaded timeline exceeds the 100 MB local limit")
            temp_path = (
                self.server.registry.package_dir(manifest.activity_id)
                / f".timeline-{uuid4().hex}{suffix}"
            )
            remaining = content_length
            with temp_path.open("wb") as handle:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("uploaded timeline ended before Content-Length")
                    handle.write(chunk)
                    remaining -= len(chunk)
            records = import_timeline(self.server.registry, activity_id, temp_path)
        except (FileNotFoundError, ValueError, ValidationError, ImportError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        self._send_json(
            {"records": [record.model_dump(mode="json", by_alias=True) for record in records]},
            HTTPStatus.CREATED,
        )

    def _create_activity(self, payload: dict[str, Any]) -> None:
        manifest = ActivityManifest.model_validate(payload)
        created = self.server.registry.create(manifest)
        self._send_json(
            created.model_dump(mode="json", by_alias=True, exclude_none=True),
            HTTPStatus.CREATED,
        )

    @staticmethod
    def _activity_id(path: str) -> ActivityId:
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "activities"] or not parts[2]:
            raise ValueError("activity path must be /api/activities/<id>")
        value = urllib.parse.unquote(parts[2])
        return TypeAdapter(ActivityId).validate_python(value)

    @staticmethod
    def _record_id(value: str) -> RecordId:
        if not value:
            raise ValueError("record id is required")
        return TypeAdapter(RecordId).validate_python(urllib.parse.unquote(value))

    def _start(self, payload: dict[str, Any]) -> None:
        existing = self.server.state.get_runner()
        if existing is not None and existing.is_alive():
            self._send_json({"error": "capture is already running"}, HTTPStatus.CONFLICT)
            return
        requested = payload.get("source")
        if requested is None or requested == "":
            requested = self.server.state.plan.camera.source
        source: int | str = requested if isinstance(requested, int) else str(requested)
        self.server.state.prepare_for_capture(source)
        requested_device = payload.get("device")
        if isinstance(requested_device, str) and requested_device:
            self.server.device = requested_device
        runner = SessionRunner(
            self.server.state,
            source=source,
            yolo_model=self.server.yolo_model,
            max_frames=payload.get("max_frames"),
            device=self.server.device,
            filter_default_classes=self.server.filter_default_classes,
        )
        self.server.state.set_runner(runner)
        runner.start()
        self._send_json({"ok": True, "source": str(source)}, HTTPStatus.ACCEPTED)

    def _analyze_video(self) -> None:
        existing = self.server.state.get_runner()
        if existing is not None and existing.is_alive():
            self._send_json(
                {"error": "stop the running capture before analysing a video"},
                HTTPStatus.CONFLICT,
            )
            return
        selected_id = self.headers.get("X-Activity-Id", "").strip()
        try:
            video = self._receive_video_upload()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        try:
            if selected_id:
                recognition = self._manual_recognition(video, selected_id)
            else:
                recognition = self.server.recognizer(self.server.registry, video)
        except (FileNotFoundError, ValueError, ValidationError, RuntimeError, OSError) as exc:
            video.unlink(missing_ok=True)
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        analysis = recognition.model_dump(mode="json", by_alias=True)
        if not recognition.recognized or recognition.activity_id is None:
            video.unlink(missing_ok=True)
            self.server.state.update(analysis=analysis, message="Experiment not recognised")
            self._send_json(analysis)
            return
        try:
            plan = load_activity_plan(self.server.registry, recognition.activity_id)
            detector = activity_detector_path(self.server.registry, recognition.activity_id)
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            video.unlink(missing_ok=True)
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        zero_shot = not detector.is_file()
        if zero_shot and not any(obj.prompts for obj in plan.objects):
            video.unlink(missing_ok=True)
            self.server.state.update(
                analysis=analysis,
                message="Experiment recognised, but it has no trained detector and no object descriptions",
            )
            self._send_json(analysis)
            return
        self.server.state.replace_plan(plan)
        self.server.yolo_model = str(detector)
        self.server.filter_default_classes = False
        self.server.state.prepare_for_capture(str(video))
        self.server.state.update(analysis=analysis)
        runner = SessionRunner(
            self.server.state,
            source=str(video),
            yolo_model=str(detector),
            device=self.server.device,
            filter_default_classes=False,
            use_media_time=True,
            realtime=True,
            upload=True,
            zero_shot=zero_shot,
        )
        self.server.state.set_runner(runner)
        runner.start()
        self._send_json(analysis, HTTPStatus.ACCEPTED)

    def _receive_video_upload(self) -> Path:
        filename = urllib.parse.unquote(self.headers.get("X-Filename", ""))
        suffix = Path(filename).suffix.lower()
        content_length = int(self.headers.get("Content-Length", "0"))
        if suffix not in VIDEO_SUFFIXES:
            self._discard_body(content_length)
            raise ValueError(f"unsupported video type: {suffix or 'none'}")
        if content_length <= 0:
            raise ValueError("uploaded video body is empty")
        if content_length > MAX_VIDEO_BYTES:
            self.close_connection = True
            raise ValueError("uploaded video exceeds the 4 GB local limit")
        self.server.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = self.server.upload_dir / f"{uuid4().hex}{suffix}"
        remaining = content_length
        try:
            with destination.open("wb") as handle:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("uploaded video ended before Content-Length")
                    handle.write(chunk)
                    remaining -= len(chunk)
        except ValueError:
            destination.unlink(missing_ok=True)
            raise
        return destination

    def _manual_recognition(self, video: Path, activity_id: str) -> ActivityRecognition:
        manifest = next(
            (m for m in self.server.registry.list_activities() if m.activity_id == activity_id),
            None,
        )
        if manifest is None:
            raise ValueError(f"unknown activity: {activity_id}")
        return ActivityRecognition(
            video=str(video),
            sampled_frames=0,
            min_score=0.0,
            min_margin=0.0,
            min_similarity=-1.0,
            recognized=True,
            activity_id=manifest.activity_id,
            reason=f"{manifest.name} was selected manually; scene recognition was skipped",
        )

    def _discard_body(self, length: int) -> None:
        if length > DISCARD_BODY_LIMIT:
            self.close_connection = True
            return
        remaining = max(0, length)
        while remaining:
            chunk = self.rfile.read(min(1024 * 1024, remaining))
            if not chunk:
                return
            remaining -= len(chunk)

    def _stop(self) -> None:
        runner = self.server.state.get_runner()
        if runner is not None:
            runner.stop()
        self._send_json({"ok": True})

    def _silence(self) -> None:
        runner = self.server.state.get_runner()
        if runner is not None:
            runner.silence()
        self._send_json({"ok": True})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        if length > 1_000_000:
            raise ValueError("request body too large")
        data = self.rfile.read(length)
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _send_session_file(self, key: str) -> None:
        downlink = self.server.state.snapshot().get("downlink") or {}
        location = downlink.get(key)
        if not location or not Path(location).is_file():
            self._send_json({"error": "no finished session"}, HTTPStatus.NOT_FOUND)
            return
        path = Path(location)
        self._send_bytes(path.read_bytes(), "application/json", download_name=path.name)

    def _send_frame(self) -> None:
        frame, _frame_id = self.server.state.frame_snapshot()
        if frame is None:
            self._send_json({"error": "no frame available"}, HTTPStatus.NOT_FOUND)
            return
        self._send_bytes(frame, "image/jpeg")

    def _send_bytes(self, data: bytes, content_type: str, download_name: str | None = None) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        if download_name is not None:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        last_frame_id = -1
        try:
            while True:
                frame, frame_id = self.server.state.wait_for_frame(last_frame_id, timeout=1.0)
                if frame is not None and frame_id != last_frame_id:
                    header = (
                        f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n"
                        f"X-Frame-ID: {frame_id}\r\n\r\n"
                    ).encode("ascii")
                    self.wfile.write(header + frame + b"\r\n")
                    self.wfile.flush()
                    last_frame_id = frame_id
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            self.close_connection = True

    def _send_static(self, request_path: str) -> None:
        relative = urllib.parse.unquote(request_path.lstrip("/")) or "index.html"
        root = STATIC_DIR.resolve()
        candidate = (root / relative).resolve()
        if root not in candidate.parents and candidate != root:
            self._send_json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
            return
        if not candidate.is_file():
            candidate = root / "index.html"
        if not candidate.is_file():
            self._send_json({"error": "React build not found"}, HTTPStatus.NOT_FOUND)
            return
        data = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Cache-Control",
            "no-cache" if candidate.name == "index.html" else "public, max-age=3600",
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        state: WebState,
        yolo_model: str,
        device: str,
        registry: ActivityRegistry | None = None,
        recognizer: Callable[[ActivityRegistry, Path], ActivityRecognition] = recognize_activity,
        upload_dir: Path | None = None,
    ) -> None:
        super().__init__(address, DashboardHandler)
        self.state = state
        self.yolo_model = yolo_model
        self.device = device
        self.filter_default_classes = True
        self.registry = registry or ActivityRegistry()
        self.recognizer = recognizer
        self.upload_dir = upload_dir or logs_dir() / "uploads"
        self.dataset_jobs = DatasetJobManager(self.registry)
        self.training_jobs = TrainingJobManager(self.registry)
        self.evaluation_jobs = EvaluationJobManager(self.registry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run-web", description=__doc__)
    parser.add_argument(
        "--plan",
        type=Path,
        default=project_root() / "experiments" / "red_blue_box" / "experiment_plan.yaml",
    )
    parser.add_argument("--source", default=None, help="Webcam index, MP4 path, or RTSP URL.")
    parser.add_argument("--yolo-model", default="models/yolo11n.pt")
    parser.add_argument(
        "--device",
        default="auto",
        help="Inference device: auto, cpu, cuda, or cuda:0.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5767)
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--no-start", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument(
        "--stream-to",
        default=None,
        help="Also stream the monitored video to udp://<ip>:<port> (open it in VLC).",
    )
    args = parser.parse_args(argv)

    if not STATIC_DIR.joinpath("index.html").is_file():
        raise RuntimeError(
            f"React build not found at {STATIC_DIR}. Run npm install and npm run build in web."
        )
    plan = load_plan(args.plan)
    source: int | str = args.source if args.source is not None else plan.camera.source
    if not args.no_start and _control_existing_dashboard(
        args.host, args.port, _source_value(source), args.max_frames, args.device
    ):
        if args.open_browser:
            threading.Timer(0.2, webbrowser.open, args=(f"http://{args.host}:{args.port}",)).start()
        return 0
    state = WebState(plan)
    if args.stream_to:
        state.set_stream_out(StreamOutputSettings.from_url(args.stream_to))
    server = DashboardServer((args.host, args.port), state, args.yolo_model, args.device)
    server.filter_default_classes = uses_default_classes_only(plan)
    if not args.no_start:
        state.prepare_for_capture(source)
        runner = SessionRunner(
            state,
            source=source,
            yolo_model=args.yolo_model,
            max_frames=args.max_frames,
            device=args.device,
            filter_default_classes=server.filter_default_classes,
        )
        state.set_runner(runner)
        runner.start()
    url = f"http://{args.host}:{args.port}"
    if args.open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runner = state.get_runner()
        if runner is not None:
            runner.stop()
        state.close_stream()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
