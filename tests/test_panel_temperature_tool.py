from solar_diagnosis import agent
from solar_diagnosis.tools import get_panels_temperature


def test_panel_temperature_returns_each_modules_temperature_and_efficiency():
    result = get_panels_temperature(plant_id="SOLAR-01")

    assert result["source"].startswith("synthetic-module-telemetry")
    assert len(result["modules"]) == 4
    hot_module = next(
        module for module in result["modules"] if module["module_id"] == "MOD-03"
    )
    assert hot_module["module_temp_c"] == 51.0
    assert hot_module["is_module_temperature_high"] is True
    assert hot_module["estimated_efficiency_percent"] == 89.6
    assert hot_module["estimated_efficiency_loss_percent"] == 10.4


def test_agent_dispatches_temperature_tool_using_plant_id():
    from test_agent_loop import _alert

    alert = _alert()
    alert.plant = "SOLAR-01"

    result = agent._call_tool(
        "get_panels_temperature",
        {"plant_id": alert.plant},
        alert,
    )

    assert result["plant_id"] == alert.plant
    assert result["modules"]


def test_agent_rejects_temperature_tool_for_different_plant():
    from test_agent_loop import _alert

    alert = _alert()

    try:
        agent._call_tool("get_panels_temperature", {"plant_id": "OTHER"}, alert)
    except ValueError as error:
        assert "limited to the alert plant" in str(error)
    else:
        raise AssertionError("Expected a ValueError for a different plant ID")
