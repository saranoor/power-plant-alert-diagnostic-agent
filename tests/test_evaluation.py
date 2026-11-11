import pytest

from solar_diagnosis.evaluation import (
    CitationCheckMetric,
    EvaluationTrace,
    LedgerEntry,
    ToolSelectionMetric,
    classification_metrics,
    load_golden_dataset,
    trace_to_test_case,
)
from solar_diagnosis import agent
from solar_diagnosis.models import Alert, Diagnosis, ToolResult
from solar_diagnosis import run_evaluation


def test_golden_dataset_has_engineered_labels():
    cases = load_golden_dataset()
    print(f"cases: {cases}")
    assert len(cases) == 5
    assert {case.expected_cause for case in cases} >= {
        "offline_units",
        "hot_modules",
        "low_irradiance",
        "string_underperformance",
        "grid_curtailment",
    }
    for case in cases:
        alert = Alert.model_validate(case.alert)
        assert alert.timestamp_utc
        assert alert.weather is not None
        assert alert.readings.expected_ac_power_kw is not None


def test_classification_reports_macro_f1_and_per_cause():
    report = classification_metrics(
        ["hot_modules", "hot_modules", "offline_units", "offline_units"],
        ["hot_modules", "offline_units", "offline_units", "offline_units"],
    )
    assert report.accuracy == 0.75
    assert report.failure_rate == 0.25
    assert report.failure_count == 1
    assert report.per_cause["hot_modules"]["precision"] == 1.0
    assert report.per_cause["hot_modules"]["recall"] == 0.5
    assert round(report.macro_f1, 4) == 0.7333


def test_tool_selection_metric_detects_missing_and_extra_tools():
    trace = EvaluationTrace(
        case_id="case-1",
        alert_input="alert",
        actual_output="diagnosis",
        predicted_cause="hot_modules",
        expected_cause="hot_modules",
        tools_called=("get_weather_data",),
        expected_tools=("get_panels_temperature",),
    )
    metric = ToolSelectionMetric()
    metric.measure(trace_to_test_case(trace))
    print("score:", metric.score)
    print("reason:", metric.reason)
    print("success:", metric.success)
    print("all attrs:", vars(metric))
    assert metric.score == 0.0


def test_citation_check_rejects_unknown_tool_ledger_id():
    trace = EvaluationTrace(
        case_id="case-2",
        alert_input="alert",
        actual_output="The evidence EV-999 shows high temperature.",
        predicted_cause="hot_modules",
        expected_cause="hot_modules",
        tools_called=("get_panels_temperature",),
        expected_tools=("get_panels_temperature",),
        ledger=(LedgerEntry("EV-001", "get_panels_temperature", {}),),
    )
    metric = CitationCheckMetric()
    metric.measure(trace_to_test_case(trace))
    assert metric.score == 0.0
    assert "EV-999" in metric.reason


def test_citation_check_accepts_matching_tool_evidence_id():
    trace = EvaluationTrace(
        case_id="case-3",
        alert_input="alert",
        actual_output="Evidence [EV-001] supports this diagnosis.",
        predicted_cause="hot_modules",
        expected_cause="hot_modules",
        tools_called=("get_panels_temperature",),
        expected_tools=("get_panels_temperature",),
        ledger=(LedgerEntry("EV-001", "get_panels_temperature", {}),),
    )
    metric = CitationCheckMetric()
    metric.measure(trace_to_test_case(trace))
    assert metric.score == 1.0


def test_citation_check_rejects_uncited_tool_evidence():
    trace = EvaluationTrace(
        case_id="case-4",
        alert_input="alert",
        actual_output="Diagnosis without a tool citation.",
        predicted_cause="hot_modules",
        expected_cause="hot_modules",
        tools_called=("get_panels_temperature",),
        expected_tools=("get_panels_temperature",),
        ledger=(LedgerEntry("EV-001", "get_panels_temperature", {}),),
    )
    metric = CitationCheckMetric()
    metric.measure(trace_to_test_case(trace))
    assert metric.score == 0.0
    assert "No tool evidence IDs" in metric.reason


def test_evaluation_trace_uses_agent_evidence_ids_for_citations():
    case = load_golden_dataset()[1]
    diagnosis = Diagnosis(
        diagnosis="Elevated temperatures explain the output loss.",
        predicted_cause="hot_modules",
        confidence=0.8,
        evidence=["[EV-001] get_panels_temperature: module temperatures are elevated."],
        recommended_action="Have a qualified engineer inspect the modules.",
        tool_results=[
            ToolResult(
                call_id="call-1",
                evidence_id="EV-001",
                tool_name="get_panels_temperature",
                arguments={"plant_id": "SOLAR-01"},
                result={"average_temperature_c": 51},
                is_error=False,
            )
        ],
    )

    trace = run_evaluation._build_trace(case, diagnosis)
    test_case = trace_to_test_case(trace)
    metric = CitationCheckMetric()

    assert trace.ledger[0].evidence_id == "EV-001"
    assert "EV-001 (get_panels_temperature)" in trace.retrieval_context[0]
    assert metric.measure(test_case) == 1.0


@pytest.mark.live
def test_agent_can_run_live_diagnosis():
    if agent.client is None:
        pytest.skip("Set GEMINI_API_KEY or GOOGLE_API_KEY to run the live agent test.")

    case = load_golden_dataset()[0]
    result = agent.diagnose(Alert.model_validate(case.alert))
    assert isinstance(result, Diagnosis)


def test_run_evaluation_loads_dotenv_and_evaluates_golden_cases(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    loaded_dotenv = []
    evaluated = {}
    monkeypatch.setattr(
        run_evaluation,
        "load_dotenv",
        lambda path: loaded_dotenv.append(path),
    )
    monkeypatch.setattr(
        agent,
        "diagnose",
        lambda alert: Diagnosis(
            diagnosis="No confirmed cause.",
            predicted_cause="unknown",
            confidence=0.1,
            evidence=[],
            recommended_action="Have a qualified engineer review the alert.",
        ),
    )

    def fake_evaluate_traces(traces, *, include_deepeval_metrics):
        evaluated["traces"] = list(traces)
        evaluated["include_deepeval_metrics"] = include_deepeval_metrics
        return (
            classification_metrics(
                [trace.expected_cause for trace in evaluated["traces"]],
                [trace.predicted_cause for trace in evaluated["traces"]],
            ),
            [],
        )

    monkeypatch.setattr(run_evaluation, "evaluate_traces", fake_evaluate_traces)

    report = run_evaluation.run_evaluation()

    assert loaded_dotenv == [run_evaluation.PROJECT_ROOT / ".env"]
    assert report.sample_count == 5
    assert len(evaluated["traces"]) == 5
    assert evaluated["include_deepeval_metrics"] is True
