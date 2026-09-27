"""Pydantic schema for experiment_plan.yaml.

This is the single source of truth for what an experiment looks like to the engine.
The procedure engine in `bas_har/procedure/` is generic over this schema; the only
experiment-specific knowledge lives in YAML files under `experiments/<demo>/`.
"""

from __future__ import annotations

import datetime
import re
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


StepId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=_ID_PATTERN.pattern),
]
ObjectId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=_ID_PATTERN.pattern),
]
HoiLabel = Annotated[
    str,
    StringConstraints(min_length=1, max_length=32, pattern=_NAME_PATTERN.pattern),
]
RegionId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=_ID_PATTERN.pattern),
]
RegionPolygon = Annotated[list[tuple[float, float]], Field(min_length=3)]
SpokenText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class SpeechLanguage(StrEnum):
    ENGLISH = "en"
    HINDI = "hi"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )


class CameraConfig(StrictModel):
    source: int | str = Field(
        default=0,
        description="OpenCV capture source. Integer index or RTSP URL.",
    )
    fps: int = Field(default=30, ge=1, le=120)
    resolution: list[int] = Field(
        default_factory=lambda: [1920, 1080],
        min_length=2,
        max_length=2,
        description="[width, height] in pixels.",
    )

    @field_validator("resolution")
    @classmethod
    def check_resolution(cls, value: list[int]) -> list[int]:
        w, h = value
        if w <= 0 or h <= 0:
            raise ValueError("resolution must be positive integers")
        return value


class FiducialConfig(StrictModel):
    type: Literal["apriltag", "dict6x6", "none"] = "none"
    family: str = "tag36h11"
    size_mm: float = Field(default=120.0, gt=0)


STATE_SEPARATOR = "__"


def state_class(class_name: str, state: str) -> str:
    return f"{class_name}{STATE_SEPARATOR}{state}"


def base_class(detector_class: str) -> str:
    return detector_class.split(STATE_SEPARATOR, 1)[0]


class ObjectSpec(StrictModel):
    id: ObjectId
    classes: list[str] = Field(min_length=1)
    colors_any: list[str] = Field(default_factory=list)
    states: list[HoiLabel] = Field(default_factory=list)
    prompts: list[str] = Field(
        default_factory=list,
        description="Plain-text descriptions for an open-vocabulary detector, so the object can be found without training.",
    )

    @field_validator("prompts")
    @classmethod
    def check_prompts(cls, value: list[str]) -> list[str]:
        cleaned = [prompt.strip().lower() for prompt in value]
        if any(not prompt for prompt in cleaned):
            raise ValueError("prompts must be non-empty strings")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("prompts must be unique")
        return cleaned

    @field_validator("classes")
    @classmethod
    def check_classes(cls, value: list[str]) -> list[str]:
        if not all(c.strip() for c in value):
            raise ValueError("classes must be non-empty strings")
        lowered = [c.lower() for c in value]
        if any(STATE_SEPARATOR in c for c in lowered):
            raise ValueError(f"classes must not contain {STATE_SEPARATOR!r}")
        return lowered

    @field_validator("states")
    @classmethod
    def check_states(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("states must be unique")
        if any(STATE_SEPARATOR in state for state in value):
            raise ValueError(f"states must not contain {STATE_SEPARATOR!r}")
        return value

    def detector_classes(self) -> list[str]:
        if not self.states:
            return list(self.classes)
        return [state_class(name, state) for name in self.classes for state in self.states]


class EvidenceRule(StrictModel):
    """One evidence signature that must hold for some minimum duration to count.

    `kind` selects which fields are required. The discriminator is explicit
    rather than a Union so YAML authors can read the schema without Pydantic magic.
    """

    kind: Literal[
        "hand_object_interaction",
        "object_visible",
        "object_state",
        "object_location",
        "actor_visible",
        "visual_question",
    ]
    object: ObjectId | None = None
    label: HoiLabel | None = None
    state: str | None = None
    outside_of: ObjectId | None = None
    inside_of: ObjectId | None = None
    in_region: RegionId | None = None
    question: str | None = Field(
        default=None,
        min_length=8,
        max_length=300,
        description="Yes/no question about the current frame, answered by a vision-language model.",
    )
    expect: Literal["yes", "no"] = Field(
        default="yes",
        description="Which answer satisfies the rule. Ask questions positively and use `no` for the "
        "closed/removed/finished state; models answer absence questions poorly.",
    )
    min_frames: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def check_kind_fields(self) -> EvidenceRule:
        required: dict[str, tuple[str, ...]] = {
            "hand_object_interaction": ("object", "label"),
            "object_visible": ("object",),
            "object_state": ("object", "state"),
            "object_location": ("object", "in_region"),
            "visual_question": ("question",),
        }
        for field in required.get(self.kind, ()):
            if getattr(self, field) is None:
                raise ValueError(f"{self.kind} requires `{field}`")
        return self


class StepSpec(StrictModel):
    id: StepId
    description: str = Field(min_length=1, max_length=500)
    evidence: list[EvidenceRule] = Field(min_length=1)
    next: list[StepId] = Field(default_factory=list)
    timeout_s: float | None = Field(
        default=None,
        gt=0,
        description="Seconds the step may stay current before a STEP_OVERDUE alert is raised.",
    )
    expected_duration_s: float | None = Field(default=None, gt=0)
    instruction: dict[SpeechLanguage, SpokenText] = Field(
        default_factory=dict,
        description="What the crew should do, spoken as the next step. Keyed by language code.",
    )


class AlertPolicy(StrictModel):
    skip_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    skip_persistence_frames: int = Field(default=5, ge=1)
    rate_limit_s: float = Field(default=5.0, ge=0)
    silence_window_s: float = Field(default=60.0, gt=0)
    pause_tolerance_s: float = Field(default=30.0, gt=0)


class ExperimentPlan(StrictModel):
    experiment_id: str = Field(min_length=1, max_length=64, alias="id")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(default="0.1.0")
    author: str = Field(default="unknown")
    created: str = Field(default="")
    description: str = Field(default="")
    spoken_name: dict[SpeechLanguage, SpokenText] = Field(
        default_factory=dict,
        description="How voice announcements name the procedure. Keyed by language code.",
    )

    @field_validator("created", mode="before")
    @classmethod
    def coerce_created(cls, value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, datetime.datetime):
            return value.date().isoformat()
        raise ValueError("created must be a string or ISO date")

    camera: CameraConfig = Field(default_factory=CameraConfig)
    fiducial: FiducialConfig = Field(default_factory=FiducialConfig)

    objects: list[ObjectSpec] = Field(default_factory=list)
    regions: list[RegionId] = Field(default_factory=list)
    region_geometries: dict[RegionId, RegionPolygon] = Field(default_factory=dict)
    steps: list[StepSpec] = Field(min_length=1)

    alert_policy: AlertPolicy = Field(default_factory=AlertPolicy)

    @model_validator(mode="after")
    def check_internal_refs(self) -> ExperimentPlan:
        if not self.steps:
            raise ValueError("at least one step is required")

        step_ids = {step.id for step in self.steps}
        if len(step_ids) != len(self.steps):
            seen: set[str] = set()
            for step in self.steps:
                if step.id in seen:
                    raise ValueError(f"duplicate step id: {step.id}")
                seen.add(step.id)

        object_ids = {obj.id for obj in self.objects}
        region_ids = set(self.regions)
        if len(region_ids) != len(self.regions):
            raise ValueError("duplicate region id")

        unknown_geometry_regions = set(self.region_geometries) - region_ids
        if unknown_geometry_regions:
            raise ValueError(
                f"region geometries reference unknown region(s): {sorted(unknown_geometry_regions)}"
            )

        for step in self.steps:
            for ref in step.next:
                if ref not in step_ids:
                    raise ValueError(f"step {step.id!r} references unknown next step {ref!r}")
            for rule in step.evidence:
                if rule.object is not None and rule.object not in object_ids:
                    raise ValueError(
                        f"step {step.id!r} evidence references unknown object {rule.object!r}"
                    )
                if rule.outside_of is not None and rule.outside_of not in object_ids:
                    raise ValueError(
                        f"step {step.id!r} evidence references unknown "
                        f"outside_of object {rule.outside_of!r}"
                    )
                if rule.inside_of is not None and rule.inside_of not in object_ids:
                    raise ValueError(
                        f"step {step.id!r} evidence references unknown "
                        f"inside_of object {rule.inside_of!r}"
                    )
                if rule.kind == "object_state" and rule.object in object_ids:
                    states = next(obj.states for obj in self.objects if obj.id == rule.object)
                    if rule.state not in states:
                        raise ValueError(
                            f"step {step.id!r} evidence state {rule.state!r} is not one of "
                            f"object {rule.object!r} states {states}"
                        )
                if rule.in_region is not None and rule.in_region not in region_ids:
                    raise ValueError(
                        f"step {step.id!r} evidence references unknown region {rule.in_region!r}"
                    )
                if rule.in_region is not None and rule.in_region not in self.region_geometries:
                    raise ValueError(
                        f"step {step.id!r} evidence region {rule.in_region!r} has no geometry"
                    )

        terminals = [step.id for step in self.steps if not step.next]
        if not terminals and len(self.steps) > 1:
            raise ValueError(
                "no terminal step (every step has a `next`); at least one step "
                "should mark the end of the procedure"
            )

        reachable: set[str] = set()
        if self.steps:
            start = self.steps[0].id
            stack = [start]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                step = next(s for s in self.steps if s.id == current)
                stack.extend(step.next)
            unreachable = step_ids - reachable
            if unreachable:
                raise ValueError(f"unreachable step(s) from start {start!r}: {sorted(unreachable)}")

        return self

    @property
    def steps_dict(self) -> dict[str, StepSpec]:
        return {step.id: step for step in self.steps}

    @property
    def objects_dict(self) -> dict[str, ObjectSpec]:
        return {obj.id: obj for obj in self.objects}

    def detector_classes(self) -> list[str]:
        names: list[str] = []
        for obj in self.objects:
            for name in obj.detector_classes():
                if name not in names:
                    names.append(name)
        return names

    def prompt_classes(self) -> dict[str, str]:
        """Detector prompt -> class name, for running without a trained detector."""
        mapping: dict[str, str] = {}
        for obj in self.objects:
            for name in obj.classes:
                for prompt in obj.prompts or [name.replace("_", " ")]:
                    mapping.setdefault(prompt, name)
        return mapping

    def visual_questions(self) -> list[str]:
        questions: list[str] = []
        for step in self.steps:
            for rule in step.evidence:
                if (
                    rule.kind == "visual_question"
                    and rule.question
                    and rule.question not in questions
                ):
                    questions.append(rule.question)
        return questions

    def class_states(self) -> dict[str, list[str]]:
        states: dict[str, list[str]] = {}
        for obj in self.objects:
            for name in obj.classes:
                for state in obj.states:
                    if state not in states.setdefault(name, []):
                        states[name].append(state)
        return states
