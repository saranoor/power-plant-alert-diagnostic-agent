import json
import unittest
from types import SimpleNamespace

from solar_diagnosis.investigation import investigate


def response_for(name, arguments, call_id="call-1"):
    function_call = SimpleNamespace(id=call_id, name=name, args=arguments)
    part = SimpleNamespace(function_call=function_call)
    content = SimpleNamespace(parts=[part])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)])


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, **request):
        self.requests.append(request)
        return next(self.responses)


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.alert = {
            "status": "alert",
            "plant_id": "plant-test",
            "shortfall_percent": 12.0,
        }
        self.plant_data = {
            "inverter_source_id": "inv-test",
            "inverters": [
                {"inverter_id": "INV-01", "actual_kw": 70, "expected_kw": 100},
                {"inverter_id": "INV-02", "actual_kw": 99, "expected_kw": 100},
            ],
        }

    def test_model_calls_tool_then_returns_evidence_backed_cause(self):
        client = FakeClient(
            [
                response_for("compare_inverters", {}),
                response_for(
                    "finish_investigation",
                    {
                        "status": "likely_cause",
                        "cause": "Inverter underperformance",
                        "confidence": "medium",
                        "summary": "INV-01 is below its peer.",
                        "evidence_ids": ["inverters:inv-test"],
                        "missing_inputs": ["Grid data was not checked."],
                    },
                    call_id="call-2",
                ),
            ]
        )

        report = investigate(self.alert, self.plant_data, client=client)

        self.assertEqual(report["status"], "likely_cause")
        self.assertEqual(report["evidence_ids"], ["inverters:inv-test"])
        self.assertEqual(len(client.requests), 2)
        exposed_tools = {
            tool.name
            for tool in client.requests[0]["config"].tools[0].function_declarations
        }
        self.assertIn("check_panel_condition", exposed_tools)

    def test_missing_source_is_reported_and_agent_can_return_unknown(self):
        client = FakeClient(
            [
                response_for("check_panel_condition", {}),
                response_for(
                    "finish_investigation",
                    {
                        "status": "unknown",
                        "cause": None,
                        "confidence": "low",
                        "summary": "Panel condition cannot be assessed.",
                        "evidence_ids": [],
                        "missing_inputs": ["panel inspection"],
                    },
                    call_id="call-2",
                ),
            ]
        )

        report = investigate(self.alert, {}, client=client)

        self.assertEqual(report["status"], "unknown")
        self.assertFalse(report["checks"][0]["available"])

    def test_forged_evidence_reference_is_rejected(self):
        client = FakeClient(
            [
                response_for(
                    "finish_investigation",
                    {
                        "status": "likely_cause",
                        "cause": "Inverter failure",
                        "confidence": "high",
                        "summary": "Unsupported statement.",
                        "evidence_ids": ["not-a-real-evidence-id"],
                        "missing_inputs": [],
                    },
                )
            ]
        )

        report = investigate(self.alert, self.plant_data, client=client)

        self.assertEqual(report["status"], "unknown")
        self.assertIn("not returned by a tool", report["summary"])

    def test_tool_call_budget_stops_repeated_unsupported_calls(self):
        client = FakeClient(
            [
                response_for("not_a_tool", {}),
                response_for("not_a_tool", {}, call_id="call-2"),
            ]
        )

        report = investigate(
            self.alert,
            self.plant_data,
            client=client,
            max_tool_calls=1,
        )

        self.assertEqual(report["status"], "unknown")
        self.assertIn("tool limit", report["summary"])

    def test_non_alert_does_not_call_model(self):
        client = FakeClient([])

        report = investigate({"status": "normal"}, {}, client=client)

        self.assertEqual(report["status"], "not_needed")
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()
