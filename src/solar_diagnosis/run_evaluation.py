"""Run the golden-alert benchmark against the live diagnosis agent."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .evaluation import (
    ClassificationMetrics,
    EvaluationTrace,
    GoldenCase,
    LedgerEntry,
    evaluate_traces,
    load_golden_dataset,
)
from .models import Alert, Diagnosis


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _build_trace(case: GoldenCase, diagnosis: Diagnosis) -> EvaluationTrace:
    ledger = tuple(
        LedgerEntry(
            evidence_id=result.evidence_id,
            tool_name=result.tool_name,
            result={
                "arguments": result.arguments,
                "result": result.result,
                "is_error": result.is_error,
            },
        )
        for result in diagnosis.tool_results
    )
    retrieval_context = tuple(
        f"{entry.evidence_id} ({entry.tool_name}): "
        f"{json.dumps(entry.result, sort_keys=True, default=str)}"
        for entry in ledger
    )
    return EvaluationTrace(
        case_id=case.id,
        alert_input=Alert.model_validate(case.alert).model_dump_json(),
        actual_output=diagnosis.model_dump_json(exclude={"tool_results"}),
        predicted_cause=diagnosis.predicted_cause,
        expected_cause=case.expected_cause,
        tools_called=tuple(result.tool_name for result in diagnosis.tool_results),
        expected_tools=case.expected_tools,
        ledger=ledger,
        retrieval_context=retrieval_context,
        expected_diagnosis=case.expected_diagnosis,
    )


def run_evaluation() -> ClassificationMetrics:
    load_dotenv(PROJECT_ROOT / ".env")
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        raise RuntimeError(
            f"Set GEMINI_API_KEY or GOOGLE_API_KEY in {PROJECT_ROOT / '.env'} "
            "to run the diagnosis agent and DeepEval judge."
        )

    from .agent import diagnose

    cases = load_golden_dataset()
    traces = [
        _build_trace(case, diagnose(Alert.model_validate(case.alert)))
        for case in cases
    ]
    classification, _ = evaluate_traces(traces, include_deepeval_metrics=True)
    print(json.dumps(asdict(classification), indent=2, sort_keys=True))
    return classification


def main() -> int:
    run_evaluation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
