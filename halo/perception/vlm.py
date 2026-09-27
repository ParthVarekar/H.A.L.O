"""Vision-language answers: yes/no questions about the current frame, so steps can be checked by description."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

DEFAULT_MODEL = "Qwen/Qwen3-VL-2B-Instruct"
PROMPT_HEADER = "Answer each question about THIS video frame with yes or no."
ANSWER_FILLS = ("yes", "no")


def build_prompt(questions: list[str], context: str = "") -> str:
    lines = [f'"q{index}": {question}' for index, question in enumerate(questions)]
    intro = f"{context.strip()}\n" if context.strip() else ""
    example = '{"q0": "yes"}'
    return (
        f"{intro}{PROMPT_HEADER}\n"
        + "\n".join(lines)
        + f"\nReply with only JSON like {example}. No other text."
    )


def filled_answer(count: int, fill: str) -> tuple[str, list[str]]:
    """The JSON answer with every slot set to `fill`, plus the text just before each slot."""
    slots = [f'"q{index}": "' for index in range(count)]
    body = "{" + ", ".join(f'{slot}{fill}"' for slot in slots) + "}"
    prefixes = [
        "{" + "".join(f'{slot}{fill}", ' for slot in slots[:index]) + slots[index]
        for index in range(count)
    ]
    return body, prefixes


def load_cached_first(loader: Callable[..., Any], model_id: str, **kwargs: Any) -> Any:
    """Load from the local model cache without touching the network; download only if not cached."""
    try:
        return loader(model_id, local_files_only=True, **kwargs)
    except OSError:
        return loader(model_id, **kwargs)


class FrameQuestioner(Protocol):
    def ask(self, frame_bgr: np.ndarray, questions: list[str]) -> dict[str, float]: ...


class VisualQuestionAnswerer:
    """Local vision-language model answering yes/no questions about a frame."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        device: str = "auto",
        max_side: int = 768,
        context: str = "",
    ) -> None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self._torch = torch
        resolved = (
            "cuda:0"
            if device == "auto" and torch.cuda.is_available()
            else ("cpu" if device == "auto" else device)
        )
        self._processor = load_cached_first(AutoProcessor.from_pretrained, model_id)
        self._model = load_cached_first(
            AutoModelForImageTextToText.from_pretrained,
            model_id,
            dtype=torch.bfloat16 if resolved.startswith("cuda") else torch.float32,
            device_map=resolved,
        )
        self._model.eval()
        self._processor.tokenizer.padding_side = "left"
        self._yes_ids = self._answer_ids(("yes", "Yes"))
        self._no_ids = self._answer_ids(("no", "No"))
        self._device = resolved
        self._max_side = max_side
        self._context = context

    def _answer_ids(self, words: tuple[str, ...]) -> list[int]:
        tokenizer = self._processor.tokenizer
        return sorted({tokenizer.encode(word, add_special_tokens=False)[0] for word in words})

    @property
    def device(self) -> str:
        return self._device

    def ask(self, frame_bgr: np.ndarray, questions: list[str]) -> dict[str, float]:
        """Probability of "yes" for every question, read from one forward pass over a pre-filled answer."""
        if not questions:
            return {}
        import cv2
        from PIL import Image

        scale = self._max_side / max(frame_bgr.shape[:2])
        frame = cv2.resize(frame_bgr, None, fx=scale, fy=scale) if scale < 1 else frame_bgr
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": build_prompt(questions, self._context)},
                ],
            }
        ]
        head = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        filled = [filled_answer(len(questions), fill) for fill in ANSWER_FILLS]
        inputs = self._processor(
            text=[head + body for body, _ in filled],
            images=[image] * len(filled),
            return_tensors="pt",
            padding=True,
        ).to(self._model.device)
        with self._torch.inference_mode():
            logits = self._model(**inputs).logits.float()
        width = inputs["input_ids"].shape[1]
        votes: list[list[float]] = []
        for row, (body, prefixes) in enumerate(filled):
            body_start = width - len(self._tokens(body))
            row_votes = []
            for prefix in prefixes:
                step = logits[row, body_start + len(self._tokens(prefix)) - 1]
                yes = self._torch.logsumexp(step[self._yes_ids], 0)
                no = self._torch.logsumexp(step[self._no_ids], 0)
                row_votes.append(float(self._torch.sigmoid(yes - no)))
            votes.append(row_votes)
        return {
            question: round(sum(column) / len(column), 4)
            for question, column in zip(questions, zip(*votes, strict=True), strict=True)
        }

    def _tokens(self, text: str) -> list[int]:
        return self._processor.tokenizer(text, add_special_tokens=False)["input_ids"]


class AsyncVisualQuestioner:
    """Answers questions about the newest frame on a background thread, so capture never waits."""

    def __init__(
        self,
        answerer: FrameQuestioner,
        questions: list[str],
        min_interval_s: float = 0.0,
    ) -> None:
        self._answerer = answerer
        self._questions = list(questions)
        self._min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._pending: np.ndarray | None = None
        self._answers: dict[str, float] = {}
        self._answered_at: float | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._last_started = 0.0
        self.answered = 0
        self._thread = threading.Thread(target=self._loop, name="bas-har-vlm", daemon=True)
        self._thread.start()

    def submit(self, frame_bgr: np.ndarray, now: float | None = None) -> None:
        moment = time.perf_counter() if now is None else now
        if moment - self._last_started < self._min_interval_s:
            return
        with self._lock:
            self._pending = frame_bgr
        self._wake.set()

    def latest(self) -> dict[str, float]:
        with self._lock:
            return dict(self._answers)

    def answered_at(self) -> float | None:
        with self._lock:
            return self._answered_at

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=30)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(0.2)
            self._wake.clear()
            with self._lock:
                frame, self._pending = self._pending, None
            if frame is None:
                continue
            self._last_started = time.perf_counter()
            with self._lock:
                asking = list(self._questions)
            try:
                answers = self._answerer.ask(frame, asking)
            except Exception:
                continue
            with self._lock:
                self._answers = {**self._answers, **answers}
                self._answered_at = time.perf_counter()
                self.answered += 1


__all__ = [
    "DEFAULT_MODEL",
    "AsyncVisualQuestioner",
    "FrameQuestioner",
    "VisualQuestionAnswerer",
    "build_prompt",
    "filled_answer",
]
