from solar_diagnosis.evaluation import (
    CitationCheckMetric,
    EvaluationTrace,
    LedgerEntry,
    ToolSelectionMetric,
    classification_metrics,
    load_golden_dataset,
    trace_to_test_case,
)


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
