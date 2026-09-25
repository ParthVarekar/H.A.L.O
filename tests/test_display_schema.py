import pytest
from pydantic import ValidationError

from bas_har.schema.display_schema import DisplaySettings


def test_display_settings_default_shows_boxes() -> None:
    assert DisplaySettings().show_boxes is True


def test_display_settings_accepts_hidden_boxes() -> None:
    assert DisplaySettings.model_validate({"show_boxes": False}).show_boxes is False


def test_display_settings_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DisplaySettings.model_validate({"show_boxes": True, "labels": False})


def test_display_settings_rejects_non_boolean() -> None:
    with pytest.raises(ValidationError):
        DisplaySettings.model_validate({"show_boxes": "sometimes"})
