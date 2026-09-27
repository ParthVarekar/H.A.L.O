"""Hand-object interaction heuristic for v0.

Given detections + hand keypoints, label each hand with the object it is
closest to and a coarse interaction label derived from hand speed (we
approximate speed from frame-to-frame index-tip motion; the procedure engine
in Phase 3 will smooth this further).

Allowed HOI labels (also accepted in `experiment_plan.yaml` evidence):
    - grasping  : hand close to object, hand roughly stationary
    - placing   : hand close to object AND moving (placing motion)
    - opening   : hand close to a box for a sustained period (lid interaction)
    - closing   : same as opening, opposite context (set by FSM, not here)
    - near      : hand within proximity but no commitment yet

Phase 9 will replace this with a learned head.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from halo.perception.types import (
    BBox,
    Detection,
    HandKeypoints,
    HandObjectInteraction,
)


@dataclass(slots=True)
class HandState:
    last_tip: tuple[float, float, float] | None = None
    velocity_ema: float = 0.0


class HandObjectInteractionTagger:
    def __init__(
        self,
        proximity_px: float = 80.0,
        grasping_speed_px: float = 8.0,
        history_len: int = 5,
    ) -> None:
        self._proximity = proximity_px
        self._grasping_speed = grasping_speed_px
        self._history: dict[str, deque[tuple[float, float, float]]] = {}
        self._history_len = history_len

    def _nearest_object(
        self, hand: HandKeypoints, detections: list[Detection]
    ) -> tuple[Detection, float] | None:
        if not detections:
            return None
        hx, hy, _ = hand.index_tip()
        best: tuple[Detection, float] | None = None
        for det in detections:
            cx, cy = det.bbox.center()
            dx = hx - cx
            dy = hy - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if best is None or dist < best[1]:
                best = (det, dist)
        return best

    def tag(
        self,
        hands: list[HandKeypoints],
        detections: list[Detection],
    ) -> list[HandObjectInteraction]:
        out: list[HandObjectInteraction] = []
        for hand in hands:
            nearest = self._nearest_object(hand, detections)
            if nearest is None:
                continue
            det, dist = nearest
            if dist > self._proximity:
                continue
            tip = hand.index_tip()
            key = f"{hand.handedness}:{det.cls}"
            history = self._history.setdefault(key, deque(maxlen=self._history_len))
            speed = 0.0
            if history and tip is not None:
                last = history[-1]
                dx = tip[0] - last[0]
                dy = tip[1] - last[1]
                speed = (dx * dx + dy * dy) ** 0.5
            history.append(tip)
            label = "grasping" if speed < self._grasping_speed else "placing"
            score = max(0.0, 1.0 - dist / self._proximity)
            out.append(
                HandObjectInteraction(
                    hand=hand.handedness,
                    object_cls=det.cls,
                    label=label,
                    score=score,
                )
            )
        return out


def bbox_within(bbox: BBox, point: tuple[float, float]) -> bool:
    x, y = point
    return bbox.x1 <= x <= bbox.x2 and bbox.y1 <= y <= bbox.y2
