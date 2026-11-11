from types import SimpleNamespace

import pytest

from solar_diagnosis import agent
from solar_diagnosis.models import Alert


def _alert():
    return Alert(
        alert_id="alert-1",
        timestamp_utc="2026-10-09T12:00:00Z",
        plant="plant-1",
        asset="inverter-1",
        alarm={"code": "LOW_POWER", "text": "Power below expected", "severity": "high"},
        state={"mode": "producing", "curtailed": False},
        weather={"poa_w_m2": 850, "module_temp_c": 35, "ambient_c": 28},
        readings={
            "ac_power_kw": 80,
            "expected_ac_power_kw": 100,
            "dc_voltage_v": 900,
            "strings_below_expected": ["string-2"],
        },
        data_quality="good",
        related_alarms_last_30min=[],
        recent_events=[],
    )


def test_diagnose_executes_function_call_and_returns_tool_result(monkeypatch):
    first_response = SimpleNamespace(
        id="interaction-1",
        output_text=None,
        steps=[
            SimpleNamespace(
                type="function_call",
                id="call-1",
                name="get_number_of_units_working",
                arguments={"plant_id": "plant-1"},
            )
        ],
    )
    final_response = SimpleNamespace(
        id="interaction-2",
        output_text=(
            '{"diagnosis":"Two units are offline, reducing plant output.",'
            '"predicted_cause":"offline_units",'
            '"confidence":0.72,'
            '"evidence":["[EV-001] get_number_of_units_working: '
            '18 of 20 units are working."],'
            '"recommended_action":"Have a qualified engineer assess the offline units."}'
        ),
        steps=[],
    )

    class FakeInteractions:
        def __init__(self):
            self.responses = [first_response, final_response]
            self.requests = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            return self.responses.pop(0)

    interactions = FakeInteractions()
    monkeypatch.setattr(
        agent,
        "client",
        SimpleNamespace(interactions=interactions),
    )
    monkeypatch.setattr(
        agent,
        "get_number_of_units_working",
        lambda plant_id: {"plant_id": plant_id, "working_units": 18, "total_units": 20},
    )

    result = agent.diagnose(_alert())

    assert result.diagnosis == "Two units are offline, reducing plant output."
    assert result.predicted_cause == "offline_units"
    assert result.confidence == 0.72
    assert result.evidence == [
        "[EV-001] get_number_of_units_working: 18 of 20 units are working."
    ]
    assert result.recommended_action == (
        "Have a qualified engineer assess the offline units."
    )
    assert [entry.model_dump() for entry in result.tool_results] == [
        {
            "call_id": "call-1",
            "evidence_id": "EV-001",
            "tool_name": "get_number_of_units_working",
            "arguments": {"plant_id": "plant-1"},
            "result": {
                "plant_id": "plant-1",
                "working_units": 18,
                "total_units": 20,
            },
            "is_error": False,
        }
    ]
    assert len(interactions.requests) == 2
    continuation = interactions.requests[1]
    assert continuation["previous_interaction_id"] == "interaction-1"
    assert continuation["input"] == [
        {
            "type": "function_result",
            "call_id": "call-1",
            "name": "get_number_of_units_working",
            "result": {
                "evidence_id": "EV-001",
                "data": {
                    "plant_id": "plant-1",
                    "working_units": 18,
                    "total_units": 20,
                },
            },
            "is_error": False,
        }
    ]


@pytest.mark.parametrize(
    ("output_text", "error_message"),
    [
        (None, "Gemini returned no final diagnosis"),
        ("not JSON", "Gemini returned an invalid structured diagnosis"),
        (
            '{"diagnosis":"x","predicted_cause":"offline_units","confidence":1.1,'
            '"evidence":[],"recommended_action":"x"}',
            "Gemini returned an invalid structured diagnosis",
        ),
        (
            '{"diagnosis":"x","predicted_cause":"inverter_fault","confidence":0.5,'
            '"evidence":[],"recommended_action":"x"}',
            "Gemini returned an invalid structured diagnosis",
        ),
    ],
)
def test_diagnose_rejects_missing_or_invalid_structured_output(
    monkeypatch, output_text, error_message
):
    class FakeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(output_text=output_text, steps=[])

    monkeypatch.setattr(
        agent,
        "client",
        SimpleNamespace(interactions=FakeInteractions()),
    )

    with pytest.raises(RuntimeError, match=error_message):
        agent.diagnose(_alert())


def test_call_tool_dispatches_inverter_tools_with_alert_ids(monkeypatch):
    alert = _alert()
    tool_names = (
        "get_inverter_status",
        "get_inverter_string_data",
        "get_inverter_temperatures",
        "get_inverter_alarms",
        "get_inverter_events",
    )
    calls = []

    def make_fake_tool(tool_name):
        def fake_tool(*, plant_id, asset_id, **kwargs):
            calls.append((plant_id, asset_id, kwargs))
            return tool_name

        return fake_tool

    for name in tool_names:
        monkeypatch.setattr(agent, name, make_fake_tool(name))

    for name in tool_names:
        assert agent._call_tool(name, {}, alert) == name

    assert calls == [
        ("plant-1", "inverter-1", {}),
        ("plant-1", "inverter-1", {}),
        ("plant-1", "inverter-1", {}),
        ("plant-1", "inverter-1", {"window_minutes": 30}),
        ("plant-1", "inverter-1", {"window_hours": 72}),
    ]
