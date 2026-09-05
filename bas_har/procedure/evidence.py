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

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from bas_har.perception.types import BBox, PerceptionResult
from bas_har.schema.plan_schema import EvidenceRule, ObjectSpec, StepSpec


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

    def reset(self) -> None:
        self._consecutive.clear()
        self._cumulative.clear()

    def reset_step(self, step_id: str) -> None:
        for key in list(self._consecutive):
            if key[0] == step_id:
                self._consecutive.pop(key, None)
        for key in list(self._cumulative):
            if key[0] == step_id:
                self._cumulative.pop(key, None)

    def evaluate_step(
        self, step: StepSpec, result: PerceptionResult
    ) -> tuple[bool, list[EvidenceVerdict]]:
        verdicts: list[EvidenceVerdict] = []
        all_matched = True
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
            all_matched = all_matched and consec >= rule.min_frames
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
            if det.cls not in target_classes:
                continue
            if rule.outside_of:
                outside_spec = self.objects_by_id.get(rule.outside_of)
                if outside_spec and self._inside(det.bbox, outside_spec, result):
                    continue
            return True, det.conf, "ok"
        return False, 0.0, "object not visible"

    @classmethod
    def _inside(cls, bbox: BBox, container_spec: ObjectSpec, result: PerceptionResult) -> bool:
        for det in result.detections:
            if det.cls not in container_spec.classes:
                continue
            if cls._bbox_inside_bbox(bbox, det.bbox):
                return True
        return False

    @staticmethod
    def _bbox_inside_bbox(inner: BBox, outer: BBox) -> bool:
        return (
            inner.x1 >= outer.x1
            and inner.y1 >= outer.y1
            and inner.x2 <= outer.x2
            and inner.y2 <= outer.y2
        )

    def _eval_state(self, rule: EvidenceRule, result: PerceptionResult) -> tuple[bool, float, str]:
        return False, 0.0, "object_state not yet implemented (Phase 3)"

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
