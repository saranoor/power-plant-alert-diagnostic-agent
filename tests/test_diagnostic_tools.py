import unittest

from solar_diagnosis.diagnostic_tools import (
    lookup_fault_codes,
    search_maintenance_history,
)


class DiagnosticToolTests(unittest.TestCase):
    def test_missing_fault_source_is_unavailable(self):
        result = lookup_fault_codes({})

        self.assertFalse(result["available"])

    def test_empty_fault_list_means_no_faults_observed(self):
        result = lookup_fault_codes({"fault_events": []})

        self.assertTrue(result["available"])
        self.assertEqual(result["result"], "no_fault_codes")

    def test_fault_code_is_returned_with_manual_evidence(self):
        result = lookup_fault_codes(
            {
                "fault_source_id": "fault-feed-1",
                "fault_events": [{"code": "F12", "equipment_id": "INV-01"}],
                "fault_manuals": {"F12": "DC insulation fault"},
            }
        )

        self.assertEqual(result["faults"][0]["manual_entry"], "DC insulation fault")

    def test_missing_ticket_source_is_unavailable(self):
        result = search_maintenance_history({})

        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main()
