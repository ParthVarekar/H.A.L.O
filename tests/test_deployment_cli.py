"""Tests for deployment command-line validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.export_onnx import build_parser as build_export_parser
from scripts.export_onnx import main as export_main
from scripts.train_yolo import build_parser as build_train_parser
from scripts.train_yolo import main as train_main


def test_train_parser_defaults() -> None:
    args = build_train_parser().parse_args(["data.yaml"])

    assert args.data == Path("data.yaml")
    assert args.epochs == 100
    assert args.name == "red_blue_box"
    assert args.device == "auto"


def test_train_main_rejects_missing_dataset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dataset YAML not found"):
        train_main([str(tmp_path / "missing.yaml")])


def test_export_parser_defaults() -> None:
    args = build_export_parser().parse_args(["best.pt"])

    assert args.model == Path("best.pt")
    assert args.opset == 17
    assert args.simplify


def test_export_main_rejects_missing_model(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="model not found"):
        export_main([str(tmp_path / "missing.pt")])
