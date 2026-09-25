import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import cv2
import numpy as np
import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.schema.cli import load_plan
from bas_har.schema.recognition_schema import ActivityRecognition
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take
from bas_har.web.server import DashboardServer, WebState, _plan_summary, _source_value


def test_source_value_converts_camera_indices_only() -> None:
    assert _source_value("0") == 0
    assert _source_value("17") == 17
    assert _source_value("C:/captures/demo.mp4") == "C:/captures/demo.mp4"


def test_plan_summary_is_derived_from_the_yaml_contract() -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    summary = _plan_summary(plan)

    assert summary["id"] == plan.experiment_id
    assert [step["id"] for step in summary["steps"]] == [step.id for step in plan.steps]
    assert summary["steps"][0]["evidence"] == [rule.kind for rule in plan.steps[0].evidence]


def test_mjpeg_stream_returns_new_frame_payload() -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    state.set_frame(b"\xff\xd8test-jpeg\xff\xd9", 7)
    server = DashboardServer(("127.0.0.1", 0), state, "models/yolo11n.pt", "cpu")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/stream.mjpg", timeout=2
        ) as response:
            assert response.headers["Content-Type"] == "multipart/x-mixed-replace; boundary=frame"
            assert response.readline() == b"--frame\r\n"
            content_length = 0
            while True:
                line = response.readline()
                if line == b"\r\n":
                    break
                if line.lower().startswith(b"content-length:"):
                    content_length = int(line.split(b":", 1)[1].strip())
            assert response.read(content_length) == b"\xff\xd8test-jpeg\xff\xd9"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_activity_registry_api_creates_and_lists_activity(tmp_path: Path) -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    server = DashboardServer(
        ("127.0.0.1", 0),
        state,
        "models/yolo11n.pt",
        "cpu",
        registry=ActivityRegistry(tmp_path),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.dumps(
            {"id": "sample_handling", "name": "Sample Handling", "kind": ActivityKind.EXPERIMENT}
        ).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/activities",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            assert response.status == 201
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/activities", timeout=2
        ) as response:
            activities = json.loads(response.read().decode("utf-8"))
        assert [activity["id"] for activity in activities] == ["sample_handling"]
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/operations/activities", timeout=2
        ) as response:
            assert json.loads(response.read().decode("utf-8")) == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_activity_timeline_template_is_downloadable(tmp_path: Path) -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    server = DashboardServer(("127.0.0.1", 0), state, "models/yolo11n.pt", "cpu", registry=registry)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/activities/sample_handling/timeline-template",
            timeout=2,
        ) as response:
            content = response.read().decode("utf-8")
            assert response.status == 200
            assert "expected_step_id" in content
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_activity_plan_api_saves_validated_plan(tmp_path: Path) -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    server = DashboardServer(("127.0.0.1", 0), state, "models/yolo11n.pt", "cpu", registry=registry)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = plan.model_dump(mode="json", by_alias=True)
        payload["id"] = "sample_handling"
        payload["name"] = "Sample Handling Procedure"
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/activities/sample_handling/plan",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urlopen(request, timeout=2) as response:
            assert response.status == 200
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/api/activities/sample_handling/plan",
            timeout=2,
        ) as response:
            saved = json.loads(response.read().decode("utf-8"))
        assert saved["id"] == "sample_handling"
        assert saved["name"] == "Sample Handling Procedure"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_keyframe_and_annotation_api_round_trip(tmp_path: Path) -> None:
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    registry = ActivityRegistry(tmp_path)
    registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    source = tmp_path / "take.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (80, 60))
    for index in range(5):
        writer.write(np.full((60, 80, 3), index * 25, dtype=np.uint8))
    writer.release()
    take = register_take(registry, "sample_handling", source, source.name, "session-a")
    server = DashboardServer(("127.0.0.1", 0), state, "models/yolo11n.pt", "cpu", registry=registry)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/api/activities/sample_handling"
        with urlopen(
            f"{base}/keyframes?take_id={take.take_id}&every_frames=2", timeout=2
        ) as response:
            frames = json.loads(response.read().decode("utf-8"))
        assert len(frames) == 3
        with urlopen(
            f"http://127.0.0.1:{server.server_port}{frames[1]['image_url']}", timeout=2
        ) as response:
            assert response.headers["Content-Type"] == "image/jpeg"
            assert len(response.read()) > 100
        payload = {
            "id": "box-frame-2",
            "take_id": take.take_id,
            "frame_id": 2,
            "time_s": 0.4,
            "kind": "object_box",
            "label": "red_block",
            "bbox": {"x1": 5, "y1": 5, "x2": 30, "y2": 30},
        }
        request = Request(
            f"{base}/annotations",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            assert response.status == 201
        with urlopen(f"{base}/annotations?take_id={take.take_id}", timeout=2) as response:
            annotations = json.loads(response.read().decode("utf-8"))
        assert annotations[0]["label"] == "red_block"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _unrecognized(registry: ActivityRegistry, video: Path) -> ActivityRecognition:
    return ActivityRecognition(
        video=str(video),
        sampled_frames=3,
        min_score=0.5,
        min_margin=0.25,
        min_similarity=0.9,
        recognized=False,
        reason="no match",
    )


def _analysis_server(tmp_path: Path, state: WebState) -> tuple[DashboardServer, Thread]:
    server = DashboardServer(
        ("127.0.0.1", 0),
        state,
        "models/yolo11n.pt",
        "cpu",
        registry=ActivityRegistry(tmp_path / "activities"),
        recognizer=_unrecognized,
        upload_dir=tmp_path / "uploads",
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_analyze_reports_unrecognized_video_without_starting_capture(tmp_path: Path) -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    server, thread = _analysis_server(tmp_path, state)
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/analyze",
            data=b"video-bytes",
            headers={"X-Filename": "take.mp4"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 200
            body = json.loads(response.read().decode("utf-8"))
        assert body["recognized"] is False
        assert state.get_runner() is None
        assert state.snapshot()["analysis"]["reason"] == "no match"
        assert list((tmp_path / "uploads").iterdir()) == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_analyze_with_selected_activity_skips_recognition(tmp_path: Path) -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    server, thread = _analysis_server(tmp_path, state)
    server.recognizer = _fail_if_called
    server.registry.create(
        ActivityManifest(id="sample_handling", name="Sample Handling", kind=ActivityKind.EXPERIMENT)
    )
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(f"{base}/api/analyze/activities", timeout=5) as response:
            listed = json.loads(response.read().decode("utf-8"))
        assert listed == [
            {
                "id": "sample_handling",
                "name": "Sample Handling",
                "has_detector": False,
                "mode": "unavailable",
            }
        ]
        request = Request(
            f"{base}/api/analyze",
            data=b"video-bytes",
            headers={"X-Filename": "take.mp4", "X-Activity-Id": "sample_handling"},
            method="POST",
        )
        with pytest.raises(HTTPError) as caught:
            urlopen(request, timeout=5)
        assert caught.value.code == 400
        assert list((tmp_path / "uploads").iterdir()) == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_analyze_rejects_unknown_selected_activity(tmp_path: Path) -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    server, thread = _analysis_server(tmp_path, state)
    server.recognizer = _fail_if_called
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/analyze",
            data=b"video-bytes",
            headers={"X-Filename": "take.mp4", "X-Activity-Id": "nope"},
            method="POST",
        )
        with pytest.raises(HTTPError) as caught:
            urlopen(request, timeout=5)
        assert caught.value.code == 400
        assert "unknown activity" in json.loads(caught.value.read().decode("utf-8"))["error"]
        assert list((tmp_path / "uploads").iterdir()) == []
        assert state.get_runner() is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _fail_if_called(registry: ActivityRegistry, video: Path) -> ActivityRecognition:
    raise AssertionError("recognizer must not run when an activity is selected")


def test_analyze_rejects_unsupported_file_type(tmp_path: Path) -> None:
    state = WebState(load_plan(Path("experiments/red_blue_box/experiment_plan.yaml")))
    server, thread = _analysis_server(tmp_path, state)
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/analyze",
            data=b"not-a-video",
            headers={"X-Filename": "notes.txt"},
            method="POST",
        )
        with pytest.raises(HTTPError) as caught:
            urlopen(request, timeout=5)
        assert caught.value.code == 400
        assert "unsupported video type" in json.loads(caught.value.read().decode("utf-8"))["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_activity_run_mode_reports_trained_described_or_unavailable(tmp_path: Path) -> None:
    from bas_har.schema.plan_schema import ExperimentPlan
    from bas_har.studio.plans import save_activity_plan
    from bas_har.studio.recognition import activity_detector_path
    from bas_har.web.server import _activity_run_mode

    registry = ActivityRegistry(tmp_path)
    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    for activity_id in ("boxed", "described", "empty"):
        registry.create(
            ActivityManifest(id=activity_id, name=activity_id, kind=ActivityKind.EXPERIMENT)
        )
    payload = plan.model_dump(mode="json", by_alias=True)
    payload["objects"][0]["prompts"] = ["a big cardboard box"]
    payload["id"] = "described"
    save_activity_plan(registry, "described", ExperimentPlan.model_validate(payload))
    detector = activity_detector_path(registry, "boxed")
    detector.parent.mkdir(parents=True, exist_ok=True)
    detector.write_bytes(b"weights")

    assert _activity_run_mode(registry, "boxed") == "trained"
    assert _activity_run_mode(registry, "described") == "described"
    assert _activity_run_mode(registry, "empty") == "unavailable"


def test_display_toggle_redraws_the_still_frame_without_boxes() -> None:
    from bas_har.perception.types import BBox, Detection, PerceptionResult

    plan = load_plan(Path("experiments/red_blue_box/experiment_plan.yaml"))
    state = WebState(plan)
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    result = PerceptionResult(
        frame_id=7,
        ts_ms=0,
        width=160,
        height=120,
        detections=[Detection(cls="tray", conf=0.9, bbox=BBox(40, 40, 120, 100))],
    )
    state.remember_render(frame, result, 7)
    server = DashboardServer(("127.0.0.1", 0), state, "models/yolo11n.pt", "cpu")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def post_display(show_boxes: bool) -> dict:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/display",
            data=json.dumps({"show_boxes": show_boxes}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode("utf-8"))

    def still_brightness() -> float:
        jpeg, frame_id = state.frame_snapshot()
        assert jpeg is not None and frame_id == 7
        return float(cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR).mean())

    try:
        assert post_display(False) == {"show_boxes": False}
        assert state.snapshot()["show_boxes"] is False
        hidden = still_brightness()
        assert post_display(True) == {"show_boxes": True}
        shown = still_brightness()
        assert hidden < 1.0 < shown
        assert frame.max() == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
