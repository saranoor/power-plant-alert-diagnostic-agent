from solar_diagnosis.agent import _tool_declarations


def test_tool_schema_matches_interactions_function_tool_format():
    tools = _tool_declarations()

    assert len(tools) == 3
    assert all(tool["type"] == "function" for tool in tools)
    assert all("function" not in tool for tool in tools)
    names = {tool["name"] for tool in tools}
    assert names == {
        "get_weather_data",
        "get_number_of_units_working",
        "get_panels_temperature",
    }
    assert all(tool["parameters"]["type"] == "object" for tool in tools)
    weather_tool = next(tool for tool in tools if tool["name"] == "get_weather_data")
    assert weather_tool["parameters"]["required"] == ["plant_id"]
