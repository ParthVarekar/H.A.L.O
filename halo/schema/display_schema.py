"""Pydantic contract for how the dashboard renders the analysed video."""

from pydantic import Field

from halo.schema.plan_schema import StrictModel


class DisplaySettings(StrictModel):
    show_boxes: bool = True
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Detections below this confidence are not drawn; the engine still uses them.",
    )
