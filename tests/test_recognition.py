from pathlib import Path

import cv2
import numpy as np
import pytest

from bas_har.schema.activity_schema import ActivityKind, ActivityManifest
from bas_har.studio.recognition import (
    activity_detector_path,
    activity_take_paths,
    normalize_rows,
    recognize_activity,
    sample_video_frames,
    vote_activities,
)
from bas_har.studio.registry import ActivityRegistry
from bas_har.studio.takes import register_take

RED = (0, 0, 220)
BLUE = (220, 0, 0)
GREEN = (0, 220, 0)


def _video(path: Path, colours: list[tuple[int, int, int]], frames: int = 12) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (80, 60))
    for index in range(frames):
        writer.write(np.full((60, 80, 3), colours[index % len(colours)], dtype=np.uint8))
    writer.release()
    return path


class _MeanColourEmbedder:
    def embed(self, frames: list[np.ndarray]) -> np.ndarray:
        means = np.stack([frame.reshape(-1, 3).mean(axis=0) + 1.0 for frame in frames])
        return normalize_rows(means.astype(np.float32))


def _registry(
    tmp_path: Path, takes: dict[str, tuple[int, int, int]], detectors: set[str]
) -> ActivityRegistry:
    registry = ActivityRegistry(tmp_path / "activities")
    for activity_id, colour in takes.items():
        registry.create(
            ActivityManifest(id=activity_id, name=activity_id.title(), kind=ActivityKind.EXPERIMENT)
        )
        source = _video(tmp_path / f"{activity_id}.mp4", [colour])
        register_take(registry, activity_id, source, source.name, f"{activity_id}-session")
        if activity_id in detectors:
            detector = activity_detector_path(registry, activity_id)
            detector.parent.mkdir(parents=True, exist_ok=True)
            detector.write_bytes(b"weights")
    return registry


def test_normalize_rows_leaves_zero_rows_unchanged() -> None:
    result = normalize_rows(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert np.allclose(result, [[0.6, 0.8], [0.0, 0.0]])


def test_vote_activities_counts_nearest_reference_per_frame() -> None:
    references = {"tour": np.array([[1.0, 0.0]]), "foam": np.array([[0.0, 1.0]])}
    queries = normalize_rows(np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]))
    votes, mean_similarity = vote_activities(queries, references)
    assert votes == {"tour": 2, "foam": 1}
    assert mean_similarity["tour"] > mean_similarity["foam"]


def test_vote_activities_ignores_frames_below_min_similarity() -> None:
    references = {"tour": np.array([[1.0, 0.0]]), "foam": np.array([[0.0, 1.0]])}
    queries = normalize_rows(np.array([[1.0, 0.0], [1.0, 1.0]]))
    votes, _ = vote_activities(queries, references, min_similarity=0.9)
    assert votes == {"tour": 1, "foam": 0}


def test_vote_activities_requires_references() -> None:
    with pytest.raises(ValueError):
        vote_activities(np.array([[1.0, 0.0]]), {})


def test_activity_take_paths_lists_stored_takes(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {"tour": RED}, detectors=set())
    paths = activity_take_paths(registry, "tour")
    assert len(paths) == 1
    assert paths[0].is_file()


def test_recognize_matches_the_activity_with_the_same_scene(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {"tour": RED, "foam": BLUE}, detectors={"tour", "foam"})
    result = recognize_activity(
        registry,
        _video(tmp_path / "query.mp4", [BLUE]),
        sample_count=6,
        embedder_factory=_MeanColourEmbedder,
    )
    assert result.recognized
    assert result.activity_id == "foam"
    assert result.scores[0].score == 1.0
    assert result.scores[0].has_detector
    assert result.scores[1].score == 0.0


def test_recognize_rejects_scene_unlike_any_stored_take(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {"tour": RED, "foam": BLUE}, detectors={"tour", "foam"})
    result = recognize_activity(
        registry,
        _video(tmp_path / "query.mp4", [GREEN]),
        sample_count=6,
        embedder_factory=_MeanColourEmbedder,
    )
    assert not result.recognized
    assert result.activity_id is None
    assert all(score.score == 0.0 for score in result.scores)
    assert result.reason.startswith("no activity matched")


def test_recognize_reports_ambiguous_when_votes_split(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {"tour": RED, "foam": BLUE}, detectors={"tour", "foam"})
    result = recognize_activity(
        registry,
        _video(tmp_path / "query.mp4", [RED, BLUE]),
        sample_count=12,
        embedder_factory=_MeanColourEmbedder,
    )
    assert not result.recognized
    assert result.activity_id is None
    assert result.reason.startswith("ambiguous")


def test_recognize_flags_matches_without_a_trained_detector(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {"tour": RED, "foam": BLUE}, detectors={"foam"})
    result = recognize_activity(
        registry,
        _video(tmp_path / "query.mp4", [RED]),
        sample_count=6,
        embedder_factory=_MeanColourEmbedder,
    )
    assert result.recognized
    assert result.activity_id == "tour"
    assert not result.scores[0].has_detector
    assert "no trained detector" in result.reason


def test_recognize_without_stored_takes(tmp_path: Path) -> None:
    registry = ActivityRegistry(tmp_path / "activities")
    registry.create(ActivityManifest(id="tour", name="Tour", kind=ActivityKind.EXPERIMENT))
    result = recognize_activity(
        registry, _video(tmp_path / "query.mp4", [RED]), embedder_factory=_MeanColourEmbedder
    )
    assert not result.recognized
    assert result.sampled_frames == 0
    assert result.scores == []


def test_sample_video_frames_spreads_samples_across_the_video(tmp_path: Path) -> None:
    frames = sample_video_frames(_video(tmp_path / "take.mp4", [RED], frames=12), 4)
    assert len(frames) == 4


def test_sample_video_frames_rejects_missing_video(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sample_video_frames(tmp_path / "missing.mp4", 4)


def test_sample_video_frames_rejects_non_positive_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        sample_video_frames(_video(tmp_path / "take.mp4", [RED]), 0)
