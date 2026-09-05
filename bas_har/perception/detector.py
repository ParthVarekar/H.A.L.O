"""YOLO object detector wrapper.

Default model: YOLOv11-nano (COCO-pretrained). Phase 1 will fine-tune on the
red/blue box dataset and swap in a custom `.pt` via `model_path`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bas_har.perception.types import BBox, Detection


class ObjectDetector:
    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str = "auto",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        target_classes: list[str] | None = None,
    ) -> None:
        from ultralytics import YOLO

        if model_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            cached = project_root / "models" / "yolo11n.pt"
            model_path = cached if cached.exists() else "yolo11n.pt"
        self._model = YOLO(str(model_path))
        self._device = self.resolve_device(device)
        self._conf = conf_threshold
        self._iou = iou_threshold
        self._target = set(c.lower() for c in target_classes) if target_classes else None
        self._class_names: dict[int, str] = self._model.names

    @property
    def class_names(self) -> dict[int, str]:
        return dict(self._class_names)

    @property
    def device(self) -> str:
        return self._device

    @staticmethod
    def resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch
        except ImportError:
            return "cpu"
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame_bgr,
            device=self._device,
            conf=self._conf,
            iou=self._iou,
            verbose=False,
        )
        detections: list[Detection] = []
        if not results:
            return detections
        result = results[0]
        if result.boxes is None:
            return detections
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            conf = float(box.conf[0].cpu().numpy())
            cls_idx = int(box.cls[0].cpu().numpy())
            cls_name = self._class_names.get(cls_idx, str(cls_idx)).lower()
            if self._target and cls_name not in self._target:
                continue
            detections.append(
                Detection(
                    cls=cls_name,
                    conf=conf,
                    bbox=BBox(x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3]),
                )
            )
        return detections
