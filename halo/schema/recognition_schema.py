"""Pydantic contracts for recognising which activity package a video shows."""

from pydantic import Field, model_validator

from halo.schema.activity_schema import ActivityId
from halo.schema.plan_schema import StrictModel


class ActivityRecognitionScore(StrictModel):
    activity_id: ActivityId
    name: str = Field(min_length=1, max_length=160)
    score: float = Field(ge=0.0, le=1.0)
    mean_similarity: float = Field(ge=-1.0, le=1.0)
    reference_frames: int = Field(ge=0)
    has_detector: bool


class ActivityRecognition(StrictModel):
    video: str = Field(min_length=1)
    sampled_frames: int = Field(ge=0)
    min_score: float = Field(ge=0.0, le=1.0)
    min_margin: float = Field(ge=0.0, le=1.0)
    min_similarity: float = Field(ge=-1.0, le=1.0)
    recognized: bool
    activity_id: ActivityId | None = None
    scores: list[ActivityRecognitionScore] = Field(default_factory=list)
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_recognized_activity(self) -> "ActivityRecognition":
        if self.recognized and self.activity_id is None:
            raise ValueError("a recognized video must name its activity_id")
        if not self.recognized and self.activity_id is not None:
            raise ValueError("an unrecognized video must not name an activity_id")
        return self


__all__ = ["ActivityRecognition", "ActivityRecognitionScore"]
