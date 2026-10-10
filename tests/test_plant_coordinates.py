import pytest

from solar_diagnosis import utils
from solar_diagnosis.tools import get_weather_data


def test_solar_01_has_mock_coordinates():
    assert utils.get_plant_coordinates("SOLAR-01") == (35.0, -117.0)


def test_get_plant_coordinates_returns_registered_location(monkeypatch):
    monkeypatch.setattr(
        utils,
        "PLANT_COORDINATES",
        {"SOLAR-01": (35.123, -117.456)},
    )

    assert utils.get_plant_coordinates("SOLAR-01") == (35.123, -117.456)


def test_get_plant_coordinates_rejects_unknown_plant():
    with pytest.raises(ValueError, match="No coordinates are registered"):
        utils.get_plant_coordinates("UNKNOWN-PLANT")


def test_weather_tool_uses_coordinates_for_plant_id(monkeypatch):
    monkeypatch.setattr(
        utils,
        "PLANT_COORDINATES",
        {"SOLAR-01": (35.123, -117.456)},
    )

    result = get_weather_data("SOLAR-01")

    assert result["plant_id"] == "SOLAR-01"
    assert result["latitude"] == 35.123
    assert result["longitude"] == -117.456
