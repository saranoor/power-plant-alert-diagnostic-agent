import unittest

from solar_diagnosis.diagnostic_tools import (
    TOOL_FUNCTIONS,
    TOOL_SCHEMAS,
    check_panel_condition,
    check_weather,
    compare_inverters,
)


class DiagnosticToolTests(unittest.TestCase):
    def test_only_three_diagnostic_tools_are_registered(self):
        self.assertEqual(
            set(TOOL_FUNCTIONS),
            {"check_weather", "check_panel_condition", "compare_inverters"},
        )
        self.assertEqual(len(TOOL_SCHEMAS), 3)

    def test_weather_compares_measured_and_expected_irradiance(self):
        result = check_weather(
            {
                "weather": {
                    "measured_irradiance_w_m2": 700,
                    "expected_irradiance_w_m2": 800,
                    "source_id": "weather-test",
                }
            }
        )

        self.assertEqual(result["result"], "below_expected")
        self.assertEqual(result["evidence_id"], "weather:weather-test")

    def test_missing_weather_data_is_unavailable(self):
        result = check_weather({})

        self.assertFalse(result["available"])

    def test_missing_panel_observation_is_unavailable(self):
        result = check_panel_condition({})

        self.assertFalse(result["available"])

    def test_panel_observation_is_returned_as_evidence(self):
        result = check_panel_condition(
            {
                "panel_observation": {
                    "condition": "soiled",
                    "source_id": "site-1",
                }
            }
        )

        self.assertEqual(result["result"], "soiled")
        self.assertEqual(result["evidence_id"], "panels:site-1")

    def test_inverter_comparison_finds_low_output_outlier(self):
        result = compare_inverters(
            {
                "inverter_source_id": "inverters-test",
                "inverters": [
                    {
                        "inverter_id": "INV-1",
                        "actual_kw": 70,
                        "expected_kw": 100,
                    },
                    {
                        "inverter_id": "INV-2",
                        "actual_kw": 99,
                        "expected_kw": 100,
                    },
                ],
            }
        )

        self.assertEqual(result["result"], "outlier")
        self.assertEqual(result["details"]["lowest_output_inverter"], "INV-1")


if __name__ == "__main__":
    unittest.main()
