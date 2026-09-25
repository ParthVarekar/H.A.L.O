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


def test_display_settings_minimum_confidence_defaults_to_showing_everything() -> None:
    assert DisplaySettings().min_confidence == 0.0
    assert DisplaySettings.model_validate({"min_confidence": 0.6}).min_confidence == 0.6


def test_display_settings_rejects_confidence_outside_zero_to_one() -> None:
    for value in (-0.1, 1.5):
        with pytest.raises(ValidationError):
            DisplaySettings.model_validate({"min_confidence": value})
