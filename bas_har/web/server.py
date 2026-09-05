"""Serve the React dashboard and run capture, perception, and procedure state."""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from bas_har.config import logs_dir, project_root
from bas_har.procedure import ColorSequenceTracker, ProcedureEngine, build_engine
from bas_har.schema.activity_schema import ActivityId, ActivityManifest
from bas_har.schema.cli import load_plan
from bas_har.schema.event_schema import EventRecord
from bas_har.schema.plan_schema import ExperimentPlan
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.plans import load_activity_plan, save_activity_plan
from bas_har.studio.takes import list_takes, register_take
from bas_har.studio.timeline import import_timeline, list_timeline
from bas_har.voice import ConfirmationSound

STATIC_DIR = project_root() / "web" / "dist"
DEFAULT_TARGET_CLASSES = ["box", "cup", "bottle", "bowl", "book", "orange", "banana", "apple"]


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
                "evidence": [rule.kind for rule in step.evidence],
            }
            for step in plan.steps
        ],
    }


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


def _annotate_frame(
    frame: Any, result: Any, state: str, confidence: float, description: str
) -> Any:
    import cv2

    for detection in result.detections:
        bbox = detection.bbox
        top_left = (int(bbox.x1), int(bbox.y1))
        bottom_right = (int(bbox.x2), int(bbox.y2))
        cv2.rectangle(frame, top_left, bottom_right, (68, 216, 163), 2)
        label = f"{detection.color + ' ' if detection.color else ''}{detection.cls} {detection.conf:.2f}"
        cv2.putText(
            frame,
            label,
            (top_left[0], max(22, top_left[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (68, 216, 163),
            2,
            cv2.LINE_AA,
        )
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 76), (8, 16, 30), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    current = description or "Procedure complete"
    cv2.putText(
        frame,
        f"{state.upper()}  |  {current}",
        (18, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (240, 244, 250),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"Confidence {confidence:.0%}  |  Detections {len(result.detections)}",
        (18, 59),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (173, 187, 209),
        1,
        cv2.LINE_AA,
    )
    return frame


class WebState:
    def __init__(self, plan: ExperimentPlan) -> None:
        self.plan = plan
        self.plan_data = _plan_summary(plan)
        first = plan.steps[0]
        self.lock = threading.RLock()
        self.runner: SessionRunner | None = None
        self.frame_jpeg: bytes | None = None
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
        }

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {**self.status, "events": list(self.events)}

    def update(self, **values: Any) -> None:
        with self.lock:
            self.status.update(values)

    def prepare_for_capture(self, source: int | str) -> None:
        first = self.plan.steps[0]
        with self.lock:
            self.frame_jpeg = None
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

    def set_frame(self, frame_jpeg: bytes, frame_id: int) -> None:
        with self.lock:
            self.frame_jpeg = frame_jpeg
            self.status["frame_id"] = frame_id

    def frame_snapshot(self) -> tuple[bytes | None, int]:
        with self.lock:
            return self.frame_jpeg, int(self.status["frame_id"])


class SessionRunner:
    def __init__(
        self,
        state: WebState,
        source: int | str,
        yolo_model: str,
        max_frames: int | None = None,
        device: str = "auto",
    ) -> None:
        self.state = state
        self.source = source
        self.yolo_model = yolo_model
        self.max_frames = max_frames
        self.device = device
        self.stop_event = threading.Event()
        self.engine: ProcedureEngine | None = None
        self.engine_lock = threading.Lock()
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

    def _run(self) -> None:
        import cv2

        from bas_har.io import CrcJsonlEventSink, VideoCaptureSource
        from bas_har.perception import PerceptionPipeline

        capture: Any | None = None
        buffer: Any | None = None
        sink: Any | None = None
        confirmation: ConfirmationSound | None = None
        try:
            width, height = self.state.plan.camera.resolution
            capture = VideoCaptureSource(
                _source_value(self.source),
                resolution=(width, height),
                fps=self.state.plan.camera.fps,
            )
            capture.open()
            fps = capture.fps or self.state.plan.camera.fps
            log_path = logs_dir() / f"web_{self.state.plan.experiment_id}_{int(time.time())}.jsonl"
            sink = CrcJsonlEventSink(log_path)
            confirmation = ConfirmationSound()
            buffer_dir = logs_dir() / "buffer" / self.state.plan.experiment_id
            try:
                sequence: ColorSequenceTracker | None = ColorSequenceTracker(self.state.plan)
            except ValueError:
                sequence = None
            self.engine = build_engine(self.state.plan, sink=None if sequence is not None else sink)
            pipeline = PerceptionPipeline(
                yolo_model=self.yolo_model,
                target_classes=DEFAULT_TARGET_CLASSES,
                run_pose=sequence is None,
                run_hands=sequence is None,
                device=self.device,
                color_names=_plan_color_names(self.state.plan),
            )
            self.state.update(
                running=True,
                source=str(self.source),
                frame_id=-1,
                fps=0.0,
                state=self.engine.state.value,
                message="Capturing and analyzing",
                error=None,
                log_path=str(log_path),
                buffer_dir=str(buffer_dir),
                buffer_segment_count=0,
                device=pipeline.device,
                recognizer="color_sequence" if sequence is not None else "procedure_engine",
                has_frame=False,
                started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
            started = time.perf_counter()
            frame_id = 0
            last_engine_event: EventRecord | None = None
            while not self.stop_event.is_set():
                if self.max_frames is not None and frame_id >= self.max_frames:
                    break
                ok, frame = capture.read()
                if not ok:
                    break
                if buffer is None:
                    from bas_har.io import Mp4CircularBuffer
                    from bas_har.schema.io_schema import CircularBufferConfig

                    frame_height, frame_width = frame.shape[:2]
                    buffer = Mp4CircularBuffer(
                        CircularBufferConfig(
                            directory=buffer_dir,
                            fps=fps,
                            resolution=(frame_width, frame_height),
                        )
                    )
                buffer.write(frame)
                ts_ms = int(frame_id * 1000 / max(fps, 1.0))
                result = pipeline.process(frame, frame_id=frame_id, ts_ms=ts_ms)
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
                    if output.last_event is not None and output.last_event is not last_engine_event:
                        last_engine_event = output.last_event
                        self.state.append_event(output.last_event)
                        if (
                            output.last_event.step_status.value == "completed"
                            and confirmation is not None
                        ):
                            confirmation.ping()
                    display_state = output.state.value
                    display_step_id = output.current_step_id
                    display_confidence = output.current_step_confidence
                    display_pause = output.pause_active
                    display_cooldown = output.in_cooldown
                    display_message = "Capturing and analyzing"
                current = self.state.plan.steps_dict.get(display_step_id)
                description = current.description if current is not None else "Procedure complete"
                encoded_frame = _annotate_frame(
                    frame, result, display_state, display_confidence, description
                )
                encoded_ok, encoded = cv2.imencode(
                    ".jpg", encoded_frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
                )
                if encoded_ok:
                    self.state.set_frame(encoded.tobytes(), frame_id)
                elapsed = time.perf_counter() - started
                self.state.update(
                    running=True,
                    frame_id=frame_id,
                    fps=round((frame_id + 1) / max(elapsed, 0.001), 1),
                    state=display_state,
                    current_step_id=display_step_id,
                    current_step_description=description,
                    next_step_id=(
                        current.next[0] if current is not None and current.next else None
                    ),
                    confidence=round(display_confidence, 3),
                    pause_active=display_pause,
                    in_cooldown=display_cooldown,
                    detections=_detection_dict(result),
                    buffer_segment_count=len(buffer.paths()),
                    has_frame=encoded_ok,
                    message=display_message,
                )
                frame_id += 1
        except Exception as exc:
            self.state.update(running=False, message="Capture error", error=str(exc))
        finally:
            if buffer is not None:
                buffer.close()
                self.state.update(buffer_segment_count=len(buffer.paths()))
            if capture is not None:
                capture.close()
            if self.engine is not None:
                with self.engine_lock:
                    self.engine.close()
            if sink is not None:
                sink.close()
            if confirmation is not None:
                confirmation.shutdown()
            with self.state.lock:
                was_error = self.state.status["error"] is not None
                message = "Capture stopped" if self.stop_event.is_set() else "Source complete"
                if was_error:
                    message = "Capture error"
                self.state.status.update(running=False, message=message)
            if self.state.get_runner() is self:
                self.state.set_runner(None)


class DashboardHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "service": "bas-har-web"})
            return
        if parsed.path == "/api/status":
            self._send_json(self.server.state.snapshot())
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
        if parsed.path.count("/") == 4 and parsed.path.endswith("/takes"):
            self._upload_take(parsed.path.removesuffix("/takes"))
            return
        if parsed.path.count("/") == 4 and parsed.path.endswith("/timeline"):
            self._upload_timeline(parsed.path.removesuffix("/timeline"))
            return
        if parsed.path not in {"/api/activities", "/api/start", "/api/stop", "/api/silence"}:
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            if parsed.path == "/api/activities":
                self._create_activity(payload)
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
        )
        self.server.state.set_runner(runner)
        runner.start()
        self._send_json({"ok": True, "source": str(source)}, HTTPStatus.ACCEPTED)

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

    def _send_frame(self) -> None:
        frame, _frame_id = self.server.state.frame_snapshot()
        if frame is None:
            self._send_json({"error": "no frame available"}, HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(frame)))
        self.end_headers()
        self.wfile.write(frame)

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
                frame, frame_id = self.server.state.frame_snapshot()
                if frame is not None and frame_id != last_frame_id:
                    header = (
                        f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame)}\r\n"
                        f"X-Frame-ID: {frame_id}\r\n\r\n"
                    ).encode("ascii")
                    self.wfile.write(header + frame + b"\r\n")
                    self.wfile.flush()
                    last_frame_id = frame_id
                time.sleep(1 / 30)
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
    ) -> None:
        super().__init__(address, DashboardHandler)
        self.state = state
        self.yolo_model = yolo_model
        self.device = device
        self.registry = registry or ActivityRegistry()


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
    server = DashboardServer((args.host, args.port), state, args.yolo_model, args.device)
    if not args.no_start:
        state.prepare_for_capture(source)
        runner = SessionRunner(
            state,
            source=source,
            yolo_model=args.yolo_model,
            max_frames=args.max_frames,
            device=args.device,
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
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
