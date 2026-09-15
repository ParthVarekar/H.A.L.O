"""Evidence signature evaluator.

A `StepSpec.evidence` is a list of rules. A step is "satisfied for a frame"
when every rule matches. The `EvidenceAccumulator` keeps a per-rule
consecutive-match count and a cumulative count, so the step transition
fires only after `min_frames` consecutive matches for every rule.

Region geometry coordinates use image pixels in clockwise or counter-clockwise
polygon order. An object location rule matches only when all four detection
bounding-box corners are inside its configured polygon.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace

from bas_har.perception.types import BBox, PerceptionResult
from bas_har.schema.plan_schema import (
    EvidenceRule,
    ExperimentPlan,
    ObjectSpec,
    StepSpec,
    base_class,
    state_class,
)

INSIDE_MIN_FRACTION = 0.8
STATE_CONFLICT_IOU = 0.5
COMPLETION_RATIO = 0.8


def _iou(first: BBox, second: BBox) -> float:
    width = max(0.0, min(first.x2, second.x2) - max(first.x1, second.x1))
    height = max(0.0, min(first.y2, second.y2) - max(first.y1, second.y1))
    overlap = width * height
    union = (
        max(0.0, first.x2 - first.x1) * max(0.0, first.y2 - first.y1)
        + max(0.0, second.x2 - second.x1) * max(0.0, second.y2 - second.y1)
        - overlap
    )
    return overlap / union if union > 0 else 0.0


def resolve_state_conflicts(result: PerceptionResult) -> PerceptionResult:
    detections = result.detections
    kept = [
        det
        for det in detections
        if not any(
            other is not det
            and other.cls != det.cls
            and base_class(other.cls) == base_class(det.cls)
            and other.conf > det.conf
            and _iou(other.bbox, det.bbox) >= STATE_CONFLICT_IOU
            for other in detections
        )
    ]
    if len(kept) == len(detections):
        return result
    return replace(result, detections=kept)


def perception_needs(plan: ExperimentPlan) -> tuple[bool, bool]:
    kinds = {rule.kind for step in plan.steps for rule in step.evidence}
    return "actor_visible" in kinds, "hand_object_interaction" in kinds


@dataclass(slots=True)
class EvidenceVerdict:
    """Per-rule verdict for one frame."""

    step_id: str
    rule_index: int
    matched: bool
    conf: float
    consecutive: int
    cumulative: int
    reason: str = ""


@dataclass(slots=True)
class EvidenceAccumulator:
    objects_by_id: dict[str, ObjectSpec] = field(default_factory=dict)
    regions: set[str] = field(default_factory=set)
    region_geometries: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    _consecutive: dict[tuple[str, int], int] = field(default_factory=lambda: defaultdict(int))
    _cumulative: dict[tuple[str, int], int] = field(default_factory=lambda: defaultdict(int))
    _recent: dict[tuple[str, int], deque[bool]] = field(default_factory=dict)

    def reset(self) -> None:
        self._consecutive.clear()
        self._cumulative.clear()
        self._recent.clear()

    def reset_step(self, step_id: str) -> None:
        for store in (self._consecutive, self._cumulative, self._recent):
            for key in list(store):
                if key[0] == step_id:
                    store.pop(key, None)

    def evaluate_step(
        self, step: StepSpec, result: PerceptionResult
    ) -> tuple[bool, list[EvidenceVerdict]]:
        verdicts: list[EvidenceVerdict] = []
        all_matched = True
        result = resolve_state_conflicts(result)
        for idx, rule in enumerate(step.evidence):
            matched, conf, reason = self._eval_rule(rule, result)
            key = (step.id, idx)
            if matched:
                self._consecutive[key] += 1
                self._cumulative[key] += 1
            else:
                self._consecutive[key] = 0
            consec = self._consecutive[key]
            cumu = self._cumulative[key]
            recent = self._recent.get(key)
            if recent is None or recent.maxlen != rule.min_frames:
                recent = deque(recent or (), maxlen=rule.min_frames)
                self._recent[key] = recent
            recent.append(matched)
            needed = math.ceil(COMPLETION_RATIO * rule.min_frames - 1e-9)
            rule_satisfied = matched and len(recent) == rule.min_frames and sum(recent) >= needed
            verdicts.append(
                EvidenceVerdict(
                    step_id=step.id,
                    rule_index=idx,
                    matched=matched,
                    conf=conf,
                    consecutive=consec,
                    cumulative=cumu,
                    reason=reason,
                )
            )
            all_matched = all_matched and rule_satisfied
        return all_matched, verdicts

    def _eval_rule(self, rule: EvidenceRule, result: PerceptionResult) -> tuple[bool, float, str]:
        if rule.kind == "hand_object_interaction":
            return self._eval_hoi(rule, result)
        if rule.kind == "object_visible":
            return self._eval_visible(rule, result)
        if rule.kind == "object_state":
            return self._eval_state(rule, result)
        if rule.kind == "object_location":
            return self._eval_location(rule, result)
        if rule.kind == "actor_visible":
            return self._eval_actor(result)
        return False, 0.0, f"unknown rule kind: {rule.kind}"

    def _eval_hoi(self, rule: EvidenceRule, result: PerceptionResult) -> tuple[bool, float, str]:
        if not rule.object or not rule.label:
            return False, 0.0, "rule missing object/label"
        for hoi in result.hoi:
            spec = self.objects_by_id.get(rule.object)
            if spec and hoi.object_cls not in spec.classes:
                continue
            if hoi.label == rule.label:
                return True, hoi.score, "ok"
        return False, 0.0, "no matching HOI"

    def _eval_visible(
        self, rule: EvidenceRule, result: PerceptionResult
    ) -> tuple[bool, float, str]:
        if not rule.object:
            return False, 0.0, "rule missing object"
        spec = self.objects_by_id.get(rule.object)
        target_classes = spec.classes if spec else [rule.object]
        for det in result.detections:
            if base_class(det.cls) not in target_classes:
                continue
            if self._placement_ok(rule, det.bbox, result):
                return True, det.conf, "ok"
        return False, 0.0, "object not visible"

    def _placement_ok(self, rule: EvidenceRule, bbox: BBox, result: PerceptionResult) -> bool:
        if rule.outside_of:
            outside_spec = self.objects_by_id.get(rule.outside_of)
            if outside_spec and self._inside(bbox, outside_spec, result, 1.0):
                return False
        if rule.inside_of:
            inside_spec = self.objects_by_id.get(rule.inside_of)
            if inside_spec is None or not self._inside(
                bbox, inside_spec, result, INSIDE_MIN_FRACTION
            ):
                return False
        return True

    @classmethod
    def _inside(
        cls,
        bbox: BBox,
        container_spec: ObjectSpec,
        result: PerceptionResult,
        min_fraction: float,
    ) -> bool:
        for det in result.detections:
            if base_class(det.cls) not in container_spec.classes:
                continue
            if cls._inside_fraction(bbox, det.bbox) >= min_fraction:
                return True
        return False

    @staticmethod
    def _inside_fraction(inner: BBox, outer: BBox) -> float:
        area = max(0.0, inner.x2 - inner.x1) * max(0.0, inner.y2 - inner.y1)
        if area <= 0:
            return 0.0
        width = max(0.0, min(inner.x2, outer.x2) - max(inner.x1, outer.x1))
        height = max(0.0, min(inner.y2, outer.y2) - max(inner.y1, outer.y1))
        return width * height / area

    def _eval_state(self, rule: EvidenceRule, result: PerceptionResult) -> tuple[bool, float, str]:
        if not rule.object or not rule.state:
            return False, 0.0, "rule missing object/state"
        spec = self.objects_by_id.get(rule.object)
        base_classes = spec.classes if spec else [rule.object]
        wanted = {state_class(name, rule.state) for name in base_classes}
        seen_other = False
        for det in result.detections:
            if det.cls not in wanted:
                seen_other = seen_other or base_class(det.cls) in base_classes
                continue
            if self._placement_ok(rule, det.bbox, result):
                return True, det.conf, "ok"
        return False, 0.0, "object in another state" if seen_other else "object not visible"

    def _eval_location(
        self, rule: EvidenceRule, result: PerceptionResult
    ) -> tuple[bool, float, str]:
        if not rule.object or not rule.in_region:
            return False, 0.0, "rule missing object/in_region"
        polygon = self.region_geometries.get(rule.in_region)
        if polygon is None:
            return False, 0.0, f"region {rule.in_region!r} has no polygon"
        spec = self.objects_by_id.get(rule.object)
        target_classes = spec.classes if spec else [rule.object]
        for det in result.detections:
            if det.cls in target_classes and self._bbox_within_region(det.bbox, polygon):
                return True, det.conf, "ok"
        return False, 0.0, "object not visible"

    @classmethod
    def _bbox_within_region(cls, bbox: BBox, polygon: Sequence[tuple[float, float]]) -> bool:
        corners = (
            (bbox.x1, bbox.y1),
            (bbox.x2, bbox.y1),
            (bbox.x2, bbox.y2),
            (bbox.x1, bbox.y2),
        )
        return all(cls._point_in_polygon(point, polygon) for point in corners)

    @staticmethod
    def _point_on_segment(
        point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
    ) -> bool:
        px, py = point
        x1, y1 = start
        x2, y2 = end
        cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
        if abs(cross) > 1e-9:
            return False
        return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)

    @classmethod
    def _point_in_polygon(
        cls, point: tuple[float, float], polygon: Sequence[tuple[float, float]]
    ) -> bool:
        x, y = point
        inside = False
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]
            if cls._point_on_segment(point, start, end):
                return True
            x1, y1 = start
            x2, y2 = end
            if (y1 > y) != (y2 > y):
                crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < crossing_x:
                    inside = not inside
        return inside

    def _eval_actor(self, result: PerceptionResult) -> tuple[bool, float, str]:
        if result.pose is None:
            return False, 0.0, "no pose"
        return True, result.pose.score, "ok"


def rule_summary(verdicts: Iterable[EvidenceVerdict]) -> str:
    return ", ".join(
        f"{v.rule_index}:{'Y' if v.matched else 'n'}{v.consecutive}/{v.reason}" for v in verdicts
    )
