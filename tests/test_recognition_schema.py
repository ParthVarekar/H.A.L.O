import pytest
from pydantic import ValidationError

from bas_har.schema.recognition_schema import ActivityRecognition, ActivityRecognitionScore

MINIMAL = {
    "video": "take.mp4",
    "sampled_frames": 0,
    "min_score": 0.5,
    "min_margin": 0.25,
    "min_similarity": 0.9,
    "recognized": False,
}
SCORE = {
    "activity_id": "cold_stowage_melfi",
    "name": "Cold Stowage",
    "score": 0.75,
    "mean_similarity": 0.93,
    "reference_frames": 32,
    "has_detector": True,
}


def test_minimal_unrecognized_result_is_valid() -> None:
    result = ActivityRecognition.model_validate(MINIMAL)
    assert result.activity_id is None
    assert result.scores == []


def test_full_recognized_result_is_valid() -> None:
    result = ActivityRecognition(
        **{**MINIMAL, "sampled_frames": 24, "recognized": True},
        activity_id="cold_stowage_melfi",
        scores=[ActivityRecognitionScore(**SCORE)],
        reason="matched",
    )
    assert result.scores[0].reference_frames == 32


@pytest.mark.parametrize("field", sorted(MINIMAL))
def test_missing_required_recognition_field_is_invalid(field: str) -> None:
    payload = {key: value for key, value in MINIMAL.items() if key != field}
    with pytest.raises(ValidationError):
        ActivityRecognition.model_validate(payload)


@pytest.mark.parametrize("field", sorted(SCORE))
def test_missing_required_score_field_is_invalid(field: str) -> None:
    payload = {key: value for key, value in SCORE.items() if key != field}
    with pytest.raises(ValidationError):
        ActivityRecognitionScore.model_validate(payload)


def test_recognized_result_requires_activity_id() -> None:
    with pytest.raises(ValidationError):
        ActivityRecognition.model_validate({**MINIMAL, "recognized": True})


def test_unrecognized_result_rejects_activity_id() -> None:
    with pytest.raises(ValidationError):
        ActivityRecognition.model_validate({**MINIMAL, "activity_id": "cold_stowage_melfi"})


@pytest.mark.parametrize(("field", "value"), [("score", 1.5), ("mean_similarity", -1.2)])
def test_score_values_outside_range_are_invalid(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        ActivityRecognitionScore.model_validate({**SCORE, field: value})


def test_score_rejects_malformed_activity_id() -> None:
    with pytest.raises(ValidationError):
        ActivityRecognitionScore.model_validate({**SCORE, "activity_id": "Cold Stowage"})


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ActivityRecognition.model_validate({**MINIMAL, "unexpected": True})
