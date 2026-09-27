"""Tests for described-not-trained recognition: object prompts and visual-question evidence."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest
from pydantic import ValidationError

from halo.perception.types import PerceptionResult
from halo.perception.vlm import (
    AsyncVisualQuestioner,
    build_prompt,
    filled_answer,
    load_cached_first,
)
from halo.procedure.evidence import EvidenceAccumulator, question_verdict
from halo.schema.plan_schema import EvidenceRule, ExperimentPlan, ObjectSpec, StepSpec

QUESTION = "Is a long cylindrical tray pulled out of the freezer?"
OTHER = "Is one of the round freezer doors open?"


def _plan(evidence: list[dict]) -> ExperimentPlan:
    return ExperimentPlan.model_validate(
        {
            "id": "described",
            "name": "described",
            "objects": [
                {
                    "id": "tray",
                    "classes": ["tray"],
                    "prompts": ["Long White Cylindrical Tray", "metal cylinder"],
                },
                {"id": "hatch", "classes": ["hatch"]},
            ],
            "steps": [{"id": "s0", "description": "step", "evidence": evidence}],
        }
    )


def test_prompts_map_to_class_names_and_fall_back_to_the_class() -> None:
    plan = _plan([{"kind": "visual_question", "question": QUESTION}])
    assert plan.prompt_classes() == {
        "long white cylindrical tray": "tray",
        "metal cylinder": "tray",
        "hatch": "hatch",
    }


def test_prompts_must_be_unique_and_non_empty() -> None:
    with pytest.raises(ValidationError):
        ObjectSpec(id="tray", classes=["tray"], prompts=["a tray", "A TRAY"])
    with pytest.raises(ValidationError):
        ObjectSpec(id="tray", classes=["tray"], prompts=["  "])


def test_visual_question_rule_requires_a_question() -> None:
    with pytest.raises(ValidationError, match="requires `question`"):
        _plan([{"kind": "visual_question"}])


def test_plan_collects_its_questions_once_each() -> None:
    plan = ExperimentPlan.model_validate(
        {
            "id": "described",
            "name": "described",
            "objects": [{"id": "tray", "classes": ["tray"]}],
            "steps": [
                {
                    "id": "s0",
                    "description": "a",
                    "evidence": [{"kind": "visual_question", "question": QUESTION}],
                    "next": ["s1"],
                },
                {
                    "id": "s1",
                    "description": "b",
                    "evidence": [
                        {"kind": "visual_question", "question": OTHER},
                        {"kind": "visual_question", "question": QUESTION},
                    ],
                },
            ],
        }
    )
    assert plan.visual_questions() == [QUESTION, OTHER]


def _frame(answers: dict[str, float]) -> PerceptionResult:
    return PerceptionResult(frame_id=0, ts_ms=0, width=64, height=48, questions=answers)


def test_visual_question_evidence_follows_the_answer() -> None:
    accumulator = EvidenceAccumulator()
    step = StepSpec(
        id="s0",
        description="step",
        evidence=[EvidenceRule(kind="visual_question", question=QUESTION)],
        next=[],
    )
    matched, verdicts = accumulator.evaluate_step(step, _frame({QUESTION: 1.0}))
    assert matched and verdicts[0].conf == 1.0
    accumulator.reset()
    matched, verdicts = accumulator.evaluate_step(step, _frame({QUESTION: 0.0}))
    assert not matched and verdicts[0].reason.startswith("answered no")
    accumulator.reset()
    matched, verdicts = accumulator.evaluate_step(step, _frame({}))
    assert not matched and verdicts[0].reason == "not answered yet"


def test_prompt_lists_every_question_with_its_slot() -> None:
    prompt = build_prompt([QUESTION, OTHER], context="You are watching MELFI stowage.")
    assert '"q0": ' + QUESTION in prompt and '"q1": ' + OTHER in prompt
    assert "MELFI stowage" in prompt


def test_filled_answer_prefixes_end_exactly_before_each_slot() -> None:
    body, prefixes = filled_answer(3, "no")
    assert body == '{"q0": "no", "q1": "no", "q2": "no"}'
    assert len(prefixes) == 3
    for index, prefix in enumerate(prefixes):
        assert prefix.endswith(f'"q{index}": "')
        assert body.startswith(prefix)
        assert body[len(prefix) :].startswith("no")


class _SlowAnswerer:
    def __init__(self) -> None:
        self.calls = 0
        self.seen: list[int] = []

    def ask(self, frame_bgr: np.ndarray, questions: list[str]) -> dict[str, float]:
        self.calls += 1
        self.seen.append(int(frame_bgr[0, 0, 0]))
        time.sleep(0.05)
        return {questions[0]: 1.0}


def _wait_for(check, timeout: float = 5.0) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if check():
            return True
        time.sleep(0.01)
    return False


def test_async_questioner_answers_the_newest_frame_without_blocking() -> None:
    answerer = _SlowAnswerer()
    questioner = AsyncVisualQuestioner(answerer, [QUESTION])
    try:
        started = time.perf_counter()
        for value in range(1, 11):
            questioner.submit(np.full((8, 8, 3), value, dtype=np.uint8))
        assert time.perf_counter() - started < 0.2
        assert _wait_for(lambda: questioner.latest().get(QUESTION) == 1.0)
        assert answerer.calls < 10
        assert 10 in answerer.seen or answerer.seen[-1] > 1
    finally:
        questioner.close()
    assert not any(thread.name == "halo-vlm" for thread in threading.enumerate())


def test_async_questioner_survives_a_failing_model() -> None:
    class _Broken:
        def ask(self, frame_bgr, questions):
            raise RuntimeError("model exploded")

    questioner = AsyncVisualQuestioner(_Broken(), [QUESTION])
    try:
        questioner.submit(np.zeros((8, 8, 3), dtype=np.uint8))
        time.sleep(0.2)
        assert questioner.latest() == {}
    finally:
        questioner.close()


def test_recognition_mode_names_what_is_running() -> None:
    from halo.web.server import _recognition_mode

    assert _recognition_mode(zero_shot=True, has_questions=True) == "zero_shot"
    assert _recognition_mode(zero_shot=False, has_questions=True) == "hybrid"
    assert _recognition_mode(zero_shot=False, has_questions=False) == "trained"


def test_answers_between_the_cut_offs_are_unsure_and_match_nothing() -> None:
    accumulator = EvidenceAccumulator()
    for expect in ("yes", "no"):
        step = StepSpec(
            id=f"s_{expect}",
            description="d",
            evidence=[EvidenceRule(kind="visual_question", question=QUESTION, expect=expect)],
        )
        matched, verdicts = accumulator.evaluate_step(step, _frame({QUESTION: 0.5}))
        assert not matched and verdicts[0].reason.startswith("unsure")
    assert question_verdict(0.9) == "yes"
    assert question_verdict(0.1) == "no"
    assert question_verdict(0.55) == "unsure"


def test_expect_no_matches_a_negative_answer() -> None:
    accumulator = EvidenceAccumulator()
    closed = StepSpec(
        id="s0",
        description="closed again",
        evidence=[EvidenceRule(kind="visual_question", question=QUESTION, expect="no")],
        next=[],
    )
    matched, verdicts = accumulator.evaluate_step(closed, _frame({QUESTION: 0.0}))
    assert matched and verdicts[0].reason == "ok"
    accumulator.reset()
    matched, verdicts = accumulator.evaluate_step(closed, _frame({QUESTION: 1.0}))
    assert not matched and verdicts[0].reason.startswith("answered yes")
    accumulator.reset()
    assert not accumulator.evaluate_step(closed, _frame({}))[0]


def test_a_questions_only_plan_needs_no_detector() -> None:
    from halo.procedure.evidence import detections_needed

    def plan_with(rule: dict) -> ExperimentPlan:
        return ExperimentPlan.model_validate(
            {
                "id": "p",
                "name": "p",
                "objects": [{"id": "tray", "classes": ["tray"]}],
                "steps": [{"id": "s0", "description": "d", "evidence": [rule]}],
            }
        )

    assert not detections_needed(plan_with({"kind": "visual_question", "question": QUESTION}))
    assert detections_needed(plan_with({"kind": "object_visible", "object": "tray"}))


def test_pipeline_without_a_detector_still_asks_questions() -> None:
    from halo.perception.pipeline import PerceptionPipeline

    class _Questioner:
        def submit(self, frame_bgr) -> None:
            pass

        def latest(self) -> dict[str, float]:
            return {QUESTION: 0.9}

    pipeline = PerceptionPipeline(
        run_pose=False,
        run_hands=False,
        device="cpu",
        questioner=_Questioner(),
        run_detector=False,
    )
    pipeline.warmup(8, 8)
    result = pipeline.process(np.zeros((8, 8, 3), dtype=np.uint8), frame_id=0, ts_ms=0)
    assert pipeline.device == "cpu"
    assert result.detections == [] and result.questions == {QUESTION: 0.9}


def test_model_loads_from_cache_without_network() -> None:
    calls: list[dict] = []

    def loader(model_id: str, **kwargs: object) -> str:
        calls.append(kwargs)
        return model_id

    assert load_cached_first(loader, "org/model", dtype="bf16") == "org/model"
    assert calls == [{"local_files_only": True, "dtype": "bf16"}]


def test_model_downloads_only_when_not_cached() -> None:
    calls: list[dict] = []

    def loader(model_id: str, **kwargs: object) -> str:
        calls.append(kwargs)
        if kwargs.get("local_files_only"):
            raise OSError("not cached")
        return model_id

    assert load_cached_first(loader, "org/model") == "org/model"
    assert calls == [{"local_files_only": True}, {}]
