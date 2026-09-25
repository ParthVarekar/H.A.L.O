"""Pydantic contract for how the dashboard renders the analysed video."""

from bas_har.schema.plan_schema import StrictModel


class DisplaySettings(StrictModel):
    show_boxes: bool = True
