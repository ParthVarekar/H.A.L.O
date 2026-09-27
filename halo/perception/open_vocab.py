"""Open-vocabulary detector: finds objects from plain-text descriptions, with no training."""

from __future__ import annotations

import contextlib
from pathlib import Path

import numpy as np

from halo.config import project_root
from halo.perception.detector import ObjectDetector
from halo.perception.types import BBox, Detection

DEFAULT_WEIGHTS = "yoloe-11s-seg.pt"
TEXT_ENCODER = "mobileclip_blt.ts"


def weights_dir() -> Path:
    return project_root() / "models"


class OpenVocabDetector:
    """Same surface as ObjectDetector, but classes come from text prompts instead of training."""

    def __init__(
        self,
        prompt_classes: dict[str, str],
        model_path: str | Path | None = None,
        device: str = "auto",
        conf_threshold: float = 0.1,
        imgsz: int = 640,
    ) -> None:
        if not prompt_classes:
            raise ValueError("open-vocabulary detection needs at least one prompt")
        from ultralytics import YOLOE

        self._prompt_classes = dict(prompt_classes)
        self._prompts = list(self._prompt_classes)
        self._device = ObjectDetector.resolve_device(device)
        self._conf = conf_threshold
        self._imgsz = imgsz
        path = Path(model_path) if model_path else weights_dir() / DEFAULT_WEIGHTS
        if not path.is_file():
            raise FileNotFoundError(
                f"open-vocabulary weights not found: {path}. Download {DEFAULT_WEIGHTS} and {TEXT_ENCODER} into {weights_dir()}"
            )
        self._model = YOLOE(str(path))
        with contextlib.chdir(path.parent):
            self._model.set_classes(self._prompts, self._model.get_text_pe(self._prompts))

    @property
    def device(self) -> str:
        return self._device

    @property
    def class_names(self) -> dict[int, str]:
        return {index: self._prompt_classes[prompt] for index, prompt in enumerate(self._prompts)}

    @property
    def prompts(self) -> list[str]:
        return list(self._prompts)

    def warmup(self, width: int, height: int) -> None:
        self.detect(np.zeros((height, width, 3), dtype=np.uint8))

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame_bgr,
            device=self._device,
            conf=self._conf,
            imgsz=self._imgsz,
            verbose=False,
        )
        detections: list[Detection] = []
        if not results or results[0].boxes is None:
            return detections
        result = results[0]
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            prompt = result.names.get(int(box.cls[0].cpu().numpy()), "")
            cls_name = self._prompt_classes.get(prompt, prompt)
            detections.append(
                Detection(
                    cls=cls_name,
                    conf=float(box.conf[0].cpu().numpy()),
                    bbox=BBox(x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3]),
                )
            )
        return detections


__all__ = ["DEFAULT_WEIGHTS", "TEXT_ENCODER", "OpenVocabDetector", "weights_dir"]
