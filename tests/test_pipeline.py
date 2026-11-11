import json
import unittest
from threading import Thread
from urllib.request import Request, urlopen
from unittest.mock import patch

from solar_diagnosis import api
from solar_diagnosis.evaluation import load_golden_dataset
from solar_diagnosis.models import Alert, Diagnosis


class PipelineTests(unittest.TestCase):
    def test_alert_is_passed_to_diagnosis_agent(self):
        alert = Alert.model_validate(load_golden_dataset()[0].alert)
        server = api.create_server("127.0.0.1", 0)
        thread = Thread(target=server.serve_forever)
        thread.start()
        host, port = server.server_address

        try:
            with patch(
                "solar_diagnosis.api.diagnose",
                return_value=Diagnosis(
                    diagnosis="Two units are offline.",
                    predicted_cause="offline_units",
                    confidence=0.8,
                    evidence=[],
                    recommended_action=(
                        "Have a qualified engineer inspect the offline units."
                    ),
                ),
            ) as mock_diagnose:
                request = Request(
                    f"http://{host}:{port}/alerts/{alert.alert_id}/diagnoses",
                    data=alert.model_dump_json().encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=5) as response:
                    body = json.loads(response.read())

                mock_diagnose.assert_called_once()
                self.assertEqual(mock_diagnose.call_args.args[0], alert)
                self.assertEqual(body["predicted_cause"], "offline_units")
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
