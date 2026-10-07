import unittest
from unittest.mock import patch

from solar_diagnosis.main import run


class PipelineTests(unittest.TestCase):
    @patch("solar_diagnosis.main.investigate")
    def test_alert_is_passed_to_investigation_agent(self, mock_investigate):
        mock_investigate.return_value = {"status": "unknown"}

        result = run(client=object())

        mock_investigate.assert_called_once()
        alert_argument = mock_investigate.call_args.args[0]
        self.assertEqual(alert_argument["status"], "alert")
        self.assertEqual(result["report"], {"status": "unknown"})


if __name__ == "__main__":
    unittest.main()
