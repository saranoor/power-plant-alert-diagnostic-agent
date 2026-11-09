from solar_diagnosis.agent import _tool_declarations


def test_tool_schema_matches_interactions_function_tool_format():
    tools = _tool_declarations()

    assert len(tools) == 8
    assert all(tool["type"] == "function" for tool in tools)
    assert all("function" not in tool for tool in tools)
    names = {tool["name"] for tool in tools}
    assert names == {
        "get_weather_data",
        "get_number_of_units_working",
        "get_panels_temperature",
        "get_inverter_status",
        "get_inverter_string_data",
        "get_inverter_temperatures",
        "get_inverter_alarms",
        "get_inverter_events",
    }
    assert all(tool["parameters"]["type"] == "object" for tool in tools)
    weather_tool = next(tool for tool in tools if tool["name"] == "get_weather_data")
    assert weather_tool["parameters"]["required"] == ["plant_id"]

    inverter_tools = {
        tool["name"]: tool
        for tool in tools
        if tool["name"].startswith("get_inverter_")
    }
    for tool in inverter_tools.values():
        assert tool["parameters"]["required"] == ["plant_id", "asset_id"]

    alarms_tool = inverter_tools["get_inverter_alarms"]
    assert alarms_tool["parameters"]["properties"]["window_minutes"] == {
        "type": "integer"
    }
    events_tool = inverter_tools["get_inverter_events"]
    assert events_tool["parameters"]["properties"]["window_hours"] == {
        "type": "integer"
    }
