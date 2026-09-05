import json
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.schema.cli import load_plan
from bas_har.studio.registry import ActivityRegistry
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
