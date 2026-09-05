"""Export an Ultralytics detector to ONNX for deployment."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _export(args: argparse.Namespace) -> int:
    if not args.model.is_file():
        raise FileNotFoundError(f"model not found: {args.model}")

    from ultralytics import YOLO

    model = YOLO(str(args.model))
    export_options = {
        "format": "onnx",
        "imgsz": args.imgsz,
        "opset": args.opset,
        "simplify": args.simplify,
        "dynamic": args.dynamic,
    }
    if args.device is not None:
        export_options["device"] = args.device
    exported = Path(model.export(**export_options))
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        destination = args.output_dir / exported.name
        if destination.resolve() != exported.resolve():
            shutil.copy2(exported, destination)
        exported = destination
    print(f"exported ONNX model -> {exported}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="export-onnx", description=__doc__)
    parser.add_argument("model", type=Path, help="Trained Ultralytics .pt model.")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--device", default=None, help="Ultralytics device, such as 0 or cpu.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--simplify", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dynamic", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    return _export(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
