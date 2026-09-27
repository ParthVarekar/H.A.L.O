"""Plan-driven sequence recognition for color-coded object procedures."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from bas_har.perception.types import Detection, PerceptionResult
from bas_har.schema.event_schema import EventRecord, StepStatus
from bas_har.schema.plan_schema import ExperimentPlan, StepSpec


@dataclass(slots=True)
class SequenceObservation:
    current_step_id: str
    state: str
    confidence: float
    completed_step_ids: list[str]
    events: list[EventRecord] = field(default_factory=list)


class ColorSequenceTracker:
    def __init__(self, plan: ExperimentPlan, stable_frames: int = 4) -> None:
        self.plan = plan
        self.stable_frames = stable_frames
        self._steps = self._resolve_sequence()
        self._inside_polygon = self._resolve_inside_polygon()
        self._colors = self._resolve_tracked_colors()
        self._histories = {color: deque(maxlen=stable_frames) for color in self._colors}
        self._stage = 0
        self._completed: list[str] = []

    def update(self, result: PerceptionResult) -> SequenceObservation:
        states = self._object_states(result.detections)
        first_color, second_color = self._colors
        for color, state in states.items():
            self._histories[color].append(state)

        event: EventRecord | None = None
        if self._stage == 0 and self._all_stable(states, "inside"):
            event = self._complete(
                result, self._steps[0], 0.95, "both colored blocks visible inside the open box"
            )
        elif (
            self._stage == 1
            and self._stable(first_color, "outside")
            and self._other_inside(states, first_color)
        ):
            event = self._complete(
                result,
                self._steps[1],
                self._confidence(states, first_color),
                f"{first_color} block outside the box",
            )
        elif (
            self._stage == 2
            and self._stable(first_color, "inside")
            and self._other_inside(states, first_color)
        ):
            event = self._complete(
                result,
                self._steps[2],
                self._confidence(states, first_color),
                f"{first_color} block returned inside the box",
            )
        elif (
            self._stage == 3
            and self._stable(second_color, "outside")
            and self._other_inside(states, second_color)
        ):
            event = self._complete(
                result,
                self._steps[3],
                self._confidence(states, second_color),
                f"{second_color} block outside the box",
            )
        elif (
            self._stage == 4
            and self._stable(second_color, "inside")
            and self._other_inside(states, second_color)
        ):
            event = self._complete(
                result,
                self._steps[4],
                self._confidence(states, second_color),
                f"{second_color} block returned inside the box",
            )
        elif self._stage == 5 and self._all_stable(states, "missing"):
            event = self._complete(
                result, self._steps[5], 0.95, "both blocks no longer visible under the closed lid"
            )

        current = self._steps[min(self._stage, len(self._steps) - 1)]
        return SequenceObservation(
            current_step_id="" if self._stage >= len(self._steps) else current.id,
            state="completed" if self._stage >= len(self._steps) else "in_progress",
            confidence=event.confidence if event is not None else self._confidence(states),
            completed_step_ids=list(self._completed),
            events=[event] if event is not None else [],
        )

    def _complete(
        self,
        result: PerceptionResult,
        step: StepSpec,
        confidence: float,
        summary: str,
    ) -> EventRecord:
        event = EventRecord(
            ts_utc=EventRecord.now_utc(),
            exp_id=self.plan.experiment_id,
            step_id=step.id,
            step_status=StepStatus.COMPLETED,
            confidence=max(0.0, min(1.0, confidence)),
            evidence_summary=summary,
            extra={
                "recognizer": "color_sequence",
                "frame_id": result.frame_id,
                "video_ts_ms": result.ts_ms,
                "video_time_s": round(result.ts_ms / 1000.0, 3),
            },
        )
        self._completed.append(step.id)
        self._stage += 1
        return event

    def _object_states(self, detections: list[Detection]) -> dict[str, str]:
        states = {color: "missing" for color in self._colors}
        for detection in detections:
            if detection.color not in states:
                continue
            states[detection.color] = "inside" if self._inside(detection) else "outside"
        return states

    def _resolve_sequence(self) -> list[StepSpec]:
        opening = self._find_step(label="opening")
        closing = self._find_step(label="closing")
        grasp_steps = self._find_steps(label="grasping")
        place_steps = self._find_steps(label="placing")
        if opening is None or closing is None or len(grasp_steps) != 2 or len(place_steps) != 2:
            raise ValueError(
                "plan does not describe an opening, two pick/return pairs, and a closing"
            )
        ordered: list[StepSpec] = [opening]
        for grasp in grasp_steps:
            object_id = self._rule_object(grasp, "grasping")
            place = next(
                (step for step in place_steps if self._rule_object(step, "placing") == object_id),
                None,
            )
            if place is None:
                raise ValueError(f"no placing step matches object {object_id!r}")
            ordered.extend([grasp, place])
        ordered.append(closing)
        return ordered

    def _resolve_inside_polygon(self) -> list[tuple[float, float]]:
        for step in self.plan.steps:
            for rule in step.evidence:
                if rule.in_region is not None:
                    polygon = self.plan.region_geometries.get(rule.in_region)
                    if polygon is not None:
                        return polygon
        raise ValueError("plan has no region geometry for block return detection")

    def _resolve_tracked_colors(self) -> list[str]:
        colors: list[str] = []
        for step in self._steps[1:-1:2]:
            object_id = self._rule_object(step, "grasping")
            spec = self.plan.objects_dict.get(object_id or "")
            color = (
                next(
                    (
                        candidate.lower()
                        for candidate in spec.colors_any
                        if candidate.lower() in {"red", "blue"}
                    ),
                    None,
                )
                if spec is not None
                else None
            )
            if color is None:
                raise ValueError(f"object {object_id!r} has no supported red or blue color")
            colors.append(color)
        if len(colors) != 2 or len(set(colors)) != 2:
            raise ValueError("plan must define one red object and one blue object")
        return colors

    def _find_step(self, label: str) -> StepSpec | None:
        steps = self._find_steps(label=label)
        return steps[0] if steps else None

    def _find_steps(self, label: str) -> list[StepSpec]:
        return [
            step
            for step in self.plan.steps
            if any(
                rule.kind == "hand_object_interaction" and rule.label == label
                for rule in step.evidence
            )
        ]

    @staticmethod
    def _rule_object(step: StepSpec, label: str) -> str | None:
        for rule in step.evidence:
            if rule.kind == "hand_object_interaction" and rule.label == label:
                return rule.object
        return None

    def _inside(self, detection: Detection) -> bool:
        return self._point_in_polygon(detection.bbox.center(), self._inside_polygon)

    def _stable(self, color: str, expected: str) -> bool:
        history = self._histories.get(color)
        return (
            history is not None
            and len(history) == self.stable_frames
            and all(state == expected for state in history)
        )

    def _all_stable(self, states: dict[str, str], expected: str) -> bool:
        return bool(states) and all(self._stable(color, expected) for color in states)

    def _other_inside(self, states: dict[str, str], moving_color: str) -> bool:
        return all(state == "inside" for color, state in states.items() if color != moving_color)

    def _confidence(self, states: dict[str, str], color: str | None = None) -> float:
        if color is not None and states.get(color) == "missing":
            return 0.0
        visible = sum(state != "missing" for state in states.values())
        return 0.9 if visible == len(states) else 0.7

    @classmethod
    def _point_in_polygon(
        cls, point: tuple[float, float], polygon: list[tuple[float, float]]
    ) -> bool:
        x, y = point
        inside = False
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]
            x1, y1 = start
            x2, y2 = end
            if (y1 > y) != (y2 > y):
                crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < crossing_x:
                    inside = not inside
        return inside


__all__ = ["ColorSequenceTracker", "SequenceObservation"]
