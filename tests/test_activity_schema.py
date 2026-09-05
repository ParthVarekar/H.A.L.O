"""Tests for activity package and training data contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bas_har.schema.activity_schema import (
    ActivityKind,
    ActivityLifecycle,
    ActivityManifest,
    AnnotationKind,
    BoundingBox,
    DatasetVersion,
    GroundTruthStatus,
    TimelineRecord,
    VisualAnnotation,
)


def test_activity_manifest_minimal_valid() -> None:
    manifest = ActivityManifest(
        id="capillary_action",
        name="Capillary Action",
        kind=ActivityKind.EXPERIMENT,
    )

    assert manifest.activity_id == "capillary_action"
    assert manifest.lifecycle is ActivityLifecycle.DRAFT


def test_activity_manifest_rejects_invalid_id() -> None:
    with pytest.raises(ValidationError):
        ActivityManifest(id="Capillary Action", name="Invalid", kind=ActivityKind.EXPERIMENT)


def test_timeline_record_accepts_point_interval() -> None:
    record = TimelineRecord(
        id="event-1",
        take_id="take-1",
        start_s=2.0,
        end_s=2.0,
        expected_step_id="open_box",
        observed_action="opens the box",
        result=GroundTruthStatus.COMPLETED,
    )

    assert record.end_s == record.start_s


def test_timeline_record_rejects_reverse_interval() -> None:
    with pytest.raises(ValidationError):
        TimelineRecord(
            id="event-1",
            take_id="take-1",
            start_s=3.0,
            end_s=2.0,
            expected_step_id="open_box",
            observed_action="opens the box",
            result=GroundTruthStatus.COMPLETED,
        )


def test_bounding_box_rejects_zero_area() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x1=10, y1=10, x2=10, y2=20)


def test_visual_annotation_requires_geometry_for_object_box() -> None:
    with pytest.raises(ValidationError):
        VisualAnnotation(
            id="annotation-1",
            take_id="take-1",
            frame_id=1,
            time_s=0.1,
            kind=AnnotationKind.OBJECT_BOX,
            label="sample_container",
        )


def test_visual_annotation_accepts_object_box() -> None:
    annotation = VisualAnnotation(
        id="annotation-1",
        take_id="take-1",
        frame_id=1,
        time_s=0.1,
        kind=AnnotationKind.OBJECT_BOX,
        label="sample_container",
        bbox=BoundingBox(x1=1, y1=2, x2=10, y2=20),
    )

    assert annotation.bbox is not None


def test_dataset_version_requires_ratios_to_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        DatasetVersion(
            id="dataset-1",
            activity_id="capillary_action",
            take_ids=["take-1"],
            session_ids=["session-1"],
            train_ratio=0.8,
            validation_ratio=0.2,
            test_ratio=0.2,
        )
