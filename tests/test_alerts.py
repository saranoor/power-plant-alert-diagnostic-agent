import unittest
from datetime import datetime, timedelta, timezone

from solar_diagnosis.alerts import detect_alert


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.records = [
            {
                "plant_id": "plant-test",
                "timestamp": (self.now - timedelta(minutes=index)).isoformat(),
                "energy_kwh": 40,
                "expected_energy_kwh": 46,
            }
            for index in range(6)
        ]

    def test_underproduction_creates_alert(self):
        result = detect_alert(self.records, "plant-test", self.now)

        self.assertEqual(result["status"], "alert")
        self.assertEqual(result["shortfall_percent"], 13.0)

    def test_too_few_valid_records_returns_insufficient_data(self):
        result = detect_alert(self.records[:2], "plant-test", self.now)

        self.assertEqual(result["status"], "insufficient_data")

    def test_malformed_records_are_ignored(self):
        records = [dict(self.records[0], timestamp="bad timestamp")]

        result = detect_alert(records, "plant-test", self.now)

        self.assertEqual(result["status"], "insufficient_data")


if __name__ == "__main__":
    unittest.main()
