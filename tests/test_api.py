import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from solar_diagnosis import api
from solar_diagnosis.evaluation import load_golden_dataset
from solar_diagnosis.models import Alert, Diagnosis


@pytest.fixture
def api_url():
    server = api.create_server("127.0.0.1", 0)
    thread = Thread(target=server.serve_forever)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _request(url, *, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_health_endpoint_reports_service_is_running(api_url):
    status, body = _request(f"{api_url}/health")

    assert status == 200
    assert body == {"status": "ok"}


def test_create_diagnosis_validates_alert_id_matches_path(monkeypatch, api_url):
    monkeypatch.setattr(
        api,
        "diagnose",
        lambda alert: Diagnosis(
            diagnosis="Two units are offline.",
            predicted_cause="offline_units",
            confidence=0.8,
            evidence=[],
            recommended_action="Have a qualified engineer inspect the units.",
        ),
    )
    alert = Alert.model_validate(load_golden_dataset()[0].alert)

    status, body = _request(
        f"{api_url}/alerts/{alert.alert_id}/diagnoses",
        method="POST",
        body=alert.model_dump(mode="json"),
    )

    assert status == 200
    assert body["predicted_cause"] == "offline_units"


def test_create_diagnosis_rejects_mismatched_alert_id(api_url):
    alert = Alert.model_validate(load_golden_dataset()[0].alert)

    status, body = _request(
        f"{api_url}/alerts/different-id/diagnoses",
        method="POST",
        body=alert.model_dump(mode="json"),
    )

    assert status == 422
    assert "must match" in body["detail"]


def test_create_diagnosis_returns_gateway_error_when_agent_raises(
    monkeypatch, api_url
):
    def fail_diagnosis(alert):
        raise ValueError("Unexpected provider SDK error.")

    monkeypatch.setattr(api, "diagnose", fail_diagnosis)
    alert = Alert.model_validate(load_golden_dataset()[0].alert)

    status, body = _request(
        f"{api_url}/alerts/{alert.alert_id}/diagnoses",
        method="POST",
        body=alert.model_dump(mode="json"),
    )

    assert status == 502
    assert body["detail"] == "The diagnosis provider could not complete the request."
