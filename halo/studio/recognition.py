"""Recognise which activity package a video shows by matching scenes against stored takes.

Each sampled frame of the uploaded video is embedded with a pretrained YOLO backbone. A frame votes
for the activity whose stored take contains its most similar frame, but only when that similarity
reaches `min_similarity`; frames that resemble no stored take cast no vote, so unrelated videos are
rejected instead of being assigned to the nearest activity. Per-activity object detectors are not
used for recognition: each is trained on a single activity and labels unrelated scenes with its own
classes, so their outputs cannot be compared across activities.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np

from halo.config import project_root
from halo.schema.activity_schema import ActivityId, ActivityManifest
from halo.schema.recognition_schema import ActivityRecognition, ActivityRecognitionScore
from halo.studio.registry import ActivityRegistry
from halo.studio.takes import list_takes

DETECTOR_FILENAME = "detector.pt"
REFERENCE_FRAMES_PER_TAKE = 32


class FrameEmbedder(Protocol):
    def embed(self, frames: list[np.ndarray]) -> np.ndarray: ...


EmbedderFactory = Callable[[], FrameEmbedder]


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1.0, norms)


class YoloBackboneEmbedder:
    def __init__(
        self, model_path: Path | None = None, device: str = "auto", imgsz: int = 320
    ) -> None:
        from ultralytics import YOLO

        from halo.perception.detector import ObjectDetector

        self._model = YOLO(str(model_path or project_root() / "models" / "yolo11n.pt"))
        self._device = ObjectDetector.resolve_device(device)
        self._imgsz = imgsz

    def embed(self, frames: list[np.ndarray]) -> np.ndarray:
        if not frames:
            raise ValueError("at least one frame is required to compute embeddings")
        vectors = self._model.embed(frames, imgsz=self._imgsz, device=self._device, verbose=False)
        matrix = np.stack([vector.detach().cpu().numpy().ravel() for vector in vectors])
        return normalize_rows(matrix.astype(np.float32))


def activity_detector_path(registry: ActivityRegistry, activity_id: ActivityId | str) -> Path:
    manifest = registry.load(activity_id)
    return registry.package_dir(manifest.activity_id) / "models" / DETECTOR_FILENAME


def activity_take_paths(registry: ActivityRegistry, activity_id: ActivityId | str) -> list[Path]:
    package_dir = registry.package_dir(activity_id)
    paths = [
        package_dir / Path(take.filename.replace("\\", "/"))
        for take in list_takes(registry, activity_id)
    ]
    return [path for path in paths if path.is_file()]


def sample_video_frames(video: Path, count: int) -> list[np.ndarray]:
    import cv2

    if count <= 0:
        raise ValueError("sample count must be positive")
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise FileNotFoundError(f"video could not be opened: {video}")
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            raise ValueError(f"video has no readable frames: {video}")
        positions = sorted({int(total * (index + 0.5) / count) for index in range(count)})
        frames: list[np.ndarray] = []
        for position in positions:
            capture.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, frame = capture.read()
            if ok:
                frames.append(frame)
    finally:
        capture.release()
    if not frames:
        raise ValueError(f"video has no readable frames: {video}")
    return frames


def vote_activities(
    queries: np.ndarray,
    references: dict[str, np.ndarray],
    min_similarity: float = -1.0,
) -> tuple[dict[str, int], dict[str, float]]:
    if not references:
        raise ValueError("at least one activity reference set is required")
    votes = dict.fromkeys(references, 0)
    similarity_sums = dict.fromkeys(references, 0.0)
    for query in queries:
        best = {activity: float(np.max(matrix @ query)) for activity, matrix in references.items()}
        winner = max(best, key=best.__getitem__)
        if best[winner] >= min_similarity:
            votes[winner] += 1
        for activity, similarity in best.items():
            similarity_sums[activity] += similarity
    count = max(1, len(queries))
    return votes, {activity: total / count for activity, total in similarity_sums.items()}


def recognize_activity(
    registry: ActivityRegistry,
    video: Path,
    sample_count: int = 24,
    min_score: float = 0.5,
    min_margin: float = 0.25,
    min_similarity: float = 0.9,
    embedder_factory: EmbedderFactory = YoloBackboneEmbedder,
) -> ActivityRecognition:
    candidates: list[tuple[ActivityManifest, list[Path]]] = [
        (manifest, activity_take_paths(registry, manifest.activity_id))
        for manifest in registry.list_activities()
    ]
    candidates = [(manifest, takes) for manifest, takes in candidates if takes]
    if not candidates:
        return ActivityRecognition(
            video=str(video),
            sampled_frames=0,
            min_score=min_score,
            min_margin=min_margin,
            min_similarity=min_similarity,
            recognized=False,
            reason="no activity package has a stored take to compare against",
        )
    embedder = embedder_factory()
    queries = embedder.embed(sample_video_frames(video, sample_count))
    references: dict[str, np.ndarray] = {}
    manifests: dict[str, ActivityManifest] = {}
    for manifest, takes in candidates:
        frames = [
            frame
            for take in takes
            for frame in sample_video_frames(take, REFERENCE_FRAMES_PER_TAKE)
        ]
        references[manifest.activity_id] = embedder.embed(frames)
        manifests[manifest.activity_id] = manifest
    votes, mean_similarity = vote_activities(queries, references, min_similarity)
    scores = sorted(
        (
            ActivityRecognitionScore(
                activity_id=activity_id,
                name=manifests[activity_id].name,
                score=round(votes[activity_id] / len(queries), 3),
                mean_similarity=round(min(1.0, max(-1.0, mean_similarity[activity_id])), 3),
                reference_frames=len(references[activity_id]),
                has_detector=activity_detector_path(registry, activity_id).is_file(),
            )
            for activity_id in references
        ),
        key=lambda item: (item.score, item.mean_similarity),
        reverse=True,
    )
    best = scores[0]
    runner_up = scores[1] if len(scores) > 1 else None
    runner_score = runner_up.score if runner_up is not None else 0.0
    if best.score < min_score:
        recognized = False
        reason = (
            f"no activity matched: best was {best.name} with {best.score:.0%} of frames "
            f"at similarity {min_similarity:.2f} or higher (needs {min_score:.0%})"
        )
    elif best.score - runner_score < min_margin:
        recognized = False
        reason = (
            f"ambiguous: {best.name} {best.score:.0%} vs "
            f"{runner_up.name if runner_up else 'none'} {runner_score:.0%}"
        )
    else:
        recognized = True
        reason = (
            f"{best.name} matched {best.score:.0%} of sampled frames (next best {runner_score:.0%})"
        )
        if not best.has_detector:
            reason += "; step monitoring unavailable because this activity has no trained detector"
    return ActivityRecognition(
        video=str(video),
        sampled_frames=len(queries),
        min_score=min_score,
        min_margin=min_margin,
        min_similarity=min_similarity,
        recognized=recognized,
        activity_id=best.activity_id if recognized else None,
        scores=scores,
        reason=reason,
    )


__all__ = [
    "DETECTOR_FILENAME",
    "REFERENCE_FRAMES_PER_TAKE",
    "EmbedderFactory",
    "FrameEmbedder",
    "YoloBackboneEmbedder",
    "activity_detector_path",
    "activity_take_paths",
    "normalize_rows",
    "recognize_activity",
    "sample_video_frames",
    "vote_activities",
]
