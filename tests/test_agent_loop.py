from types import SimpleNamespace

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
        output_text="Two units are offline, reducing plant output.",
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
    assert len(interactions.requests) == 2
    continuation = interactions.requests[1]
    assert continuation["previous_interaction_id"] == "interaction-1"
    assert continuation["input"] == [
        {
            "type": "function_result",
            "call_id": "call-1",
            "name": "get_number_of_units_working",
            "result": {"plant_id": "plant-1", "working_units": 18, "total_units": 20},
            "is_error": False,
        }
    ]
