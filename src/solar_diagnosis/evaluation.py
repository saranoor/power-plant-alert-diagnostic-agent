"""Evaluation pipeline for solar diagnosis alerts."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from deepeval.metrics import (
    AnswerRelevancyMetric,
    BaseMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
    ToolCorrectnessMetric,
)
from deepeval.test_case import LLMTestCase, ToolCall


DEFAULT_METRIC_NAMES = (
    "faithfulness",
    "hallucination",
    "answer_relevancy",
    "contextual_precision",
    "contextual_recall",
    "contextual_relevancy",
    "tool_correctness",
)


@dataclass(frozen=True)
class GoldenCase:
    id: str
    alert: Mapping[str, object]
    expected_cause: str
    expected_diagnosis: str
    expected_tools: tuple[str, ...]


@dataclass(frozen=True)
class LedgerEntry:
    evidence_id: str
    tool_name: str
    result: object


@dataclass(frozen=True)
class EvaluationTrace:
    case_id: str
    alert_input: str
    actual_output: str
    predicted_cause: str
    expected_cause: str
    tools_called: tuple[str, ...]
    expected_tools: tuple[str, ...]
    ledger: tuple[LedgerEntry, ...] = ()
    retrieval_context: tuple[str, ...] = ()
    expected_diagnosis: str = ""


@dataclass
class ClassificationMetrics:
    accuracy: float
    failure_rate: float
    macro_f1: float
    per_cause: dict[str, dict[str, float | int]]
    failure_count: int
    sample_count: int


def load_golden_dataset(
    path: str | Path | None = None,
) -> tuple[GoldenCase, ...]:
    if path is None:
        path = Path(__file__).parent / "data" / "golden_alerts.json"

    with Path(path).open("r", encoding="utf-8") as file:
        rows = json.load(file)

    return tuple(
        GoldenCase(
            id=row["id"],
            alert=row["alert"],
            expected_cause=row["expected_cause"],
            expected_diagnosis=row["expected_diagnosis"],
            expected_tools=tuple(row["expected_tools"]),
        )
        for row in rows
    )


def build_gemini_judge_model(model_name: str | None = None):
    """Create DeepEval's Gemini judge from the project's existing Gemini key."""
    from deepeval.models import GeminiModel

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY or GOOGLE_API_KEY is required for LLM-based evaluation."
        )
    model_name = (
        model_name
        or os.getenv("GEMINI_EVALUATION_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-2.5-flash"
    )
    return GeminiModel(model=model_name, api_key=api_key)


def build_default_metrics(*, model=None, threshold: float = 0.5) -> list[BaseMetric]:
    """Create DeepEval's standard LLM, retrieval, and tool metrics."""
    if model is None and (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ):
        model = build_gemini_judge_model()
    if model is None:
        raise RuntimeError(
            "Pass a DeepEval model or configure GEMINI_API_KEY/GOOGLE_API_KEY "
            "to run LLM-based DeepEval metrics."
        )
    return [
        FaithfulnessMetric(threshold=threshold, model=model),
        HallucinationMetric(threshold=threshold, model=model),
        AnswerRelevancyMetric(threshold=threshold, model=model),
        ContextualPrecisionMetric(threshold=threshold, model=model),
        ContextualRecallMetric(threshold=threshold, model=model),
        ContextualRelevancyMetric(threshold=threshold, model=model),
        ToolCorrectnessMetric(threshold=threshold, model=model),
    ]


def build_llm_judge(*, model=None, threshold: float = 0.7) -> GEval:
    if model is None and (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ):
        model = build_gemini_judge_model()
    return GEval(
        name="Solar Diagnosis Quality Judge",
        evaluation_params=["INPUT", "ACTUAL_OUTPUT", "RETRIEVAL_CONTEXT"],
        criteria=(
            "Judge whether the diagnosis is relevant to the alert, grounded only in "
            "the supplied evidence, identifies the expected engineering failure mode, "
            "and gives a practical recommended action. Penalize unsupported claims, "
            "invented evidence IDs, omitted likely faults, and unsafe recommendations."
        ),
        model=model,
        threshold=threshold,
    )


class ToolSelectionMetric(BaseMetric):
    """Compare the tool names selected by the agent with the golden tools."""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        actual = tuple(tool.name for tool in (test_case.tools_called or []))
        expected = tuple(tool.name for tool in (test_case.expected_tools or []))
        actual_set, expected_set = set(actual), set(expected)
        false_positives = actual_set - expected_set
        false_negatives = expected_set - actual_set
        correct = len(expected_set & actual_set)
        union = len(actual_set | expected_set)
        self.score = correct / union if union else 1.0
        self.reason = (
            f"Missing tools: {sorted(false_negatives)}; "
            f"unexpected tools: {sorted(false_positives)}"
        )
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)


class CitationCheckMetric(BaseMetric):
    """Require every evidence ID cited by the diagnosis to exist in the tool ledger."""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        ledger_ids = set(
            (test_case.metadata or {}).get("ledger_evidence_ids", [])
        )
        cited_ids = _extract_citation_ids(test_case.actual_output or "")
        invalid = sorted(cited_ids - ledger_ids)
        cited_count = len(cited_ids)
        invalid_count = len(invalid)
        if ledger_ids and not cited_ids:
            self.score = 0.0
            self.reason = "No tool evidence IDs were cited."
        else:
            self.score = (
                1.0
                if invalid_count == 0
                else (cited_count - invalid_count) / cited_count
            )
            self.reason = (
                "All citations exist in the tool ledger."
                if not invalid
                else f"Unknown citation IDs: {invalid}"
            )
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)


def _extract_citation_ids(text: str) -> set[str]:
    import re

    return {match.upper() for match in re.findall(r"\b(?:EV|LEDGER)[-_]?\d+\b", text, re.I)}


def classification_metrics(
    expected_labels: Sequence[str],
    predicted_labels: Sequence[str],
) -> ClassificationMetrics:
    if len(expected_labels) != len(predicted_labels):
        raise ValueError("Expected and predicted label lists must have equal lengths.")

    labels = sorted(set(expected_labels) | set(predicted_labels))
    per_cause: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []

    correct = 0
    for label in labels:
        tp = sum(
            expected == label and predicted == label
            for expected, predicted in zip(expected_labels, predicted_labels)
        )
        fp = sum(
            expected != label and predicted == label
            for expected, predicted in zip(expected_labels, predicted_labels)
        )
        fn = sum(
            expected == label and predicted != label
            for expected, predicted in zip(expected_labels, predicted_labels)
        )
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        support = sum(expected == label for expected in expected_labels)
        per_cause[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "failure_rate": fn / support if support else 0.0,
        }
        f1_values.append(f1)
        correct += tp

    sample_count = len(expected_labels)
    accuracy = correct / sample_count if sample_count else 0.0
    return ClassificationMetrics(
        accuracy=accuracy,
        failure_rate=1.0 - accuracy,
        macro_f1=sum(f1_values) / len(f1_values) if f1_values else 0.0,
        per_cause=per_cause,
        failure_count=sample_count - correct,
        sample_count=sample_count,
    )


def trace_to_test_case(trace: EvaluationTrace) -> LLMTestCase:
    ledger_ids = [entry.evidence_id for entry in trace.ledger]
    return LLMTestCase(
        input=trace.alert_input,
        actual_output=trace.actual_output,
        expected_output=(
            f"Cause: {trace.expected_cause}. "
            f"Diagnosis: {trace.expected_diagnosis}"
        ).strip(),
        context=list(trace.retrieval_context),
        retrieval_context=list(trace.retrieval_context),
        tools_called=[ToolCall(name=name) for name in trace.tools_called],
        expected_tools=[ToolCall(name=name) for name in trace.expected_tools],
        metadata={"ledger_evidence_ids": ledger_ids, "case_id": trace.case_id},
    )


def evaluate_traces(
    traces: Iterable[EvaluationTrace],
    *,
    include_deepeval_metrics: bool = True,
    metrics: Sequence[BaseMetric] | None = None,
    model=None,
) -> tuple[ClassificationMetrics, list[LLMTestCase]]:
    """Run custom and optional DeepEval metrics, then return classification metrics."""
    from deepeval import evaluate

    trace_list = list(traces)
    test_cases = [trace_to_test_case(trace) for trace in trace_list]
    classification = classification_metrics(
        [trace.expected_cause for trace in trace_list],
        [trace.predicted_cause for trace in trace_list],
    )

    selected_metrics: list[BaseMetric] = [
        ToolSelectionMetric(),
        CitationCheckMetric(),
    ]
    if include_deepeval_metrics:
        selected_metrics.extend(metrics or build_default_metrics(model=model))
        selected_metrics.append(build_llm_judge(model=model))

    if trace_list:
        evaluate(test_cases, selected_metrics, show_indicator=True)

    return classification, test_cases