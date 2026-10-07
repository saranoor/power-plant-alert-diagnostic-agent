"""Three read-only tools exposed to the investigation model."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_weather",
            "description": ("Compare measured weather irradiance with expected."),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_panel_condition",
            "description": ("Check recorded panel soiling or shading observations."),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_inverters",
            "description": "Compare inverter output against peer inverters.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _unavailable(source_name):
    return {
        "available": False,
        "reason": f"Required source missing: {source_name}",
    }


def check_weather(data):
    weather = data.get("weather")
    if not isinstance(weather, dict):
        return _unavailable("weather measurements")

    expected = weather.get("expected_irradiance_w_m2", 0)
    measured = weather.get("measured_irradiance_w_m2")
    if not expected or measured is None:
        return _unavailable("measured and expected weather irradiance")

    ratio = measured / expected
    source = weather.get("source_id", "weather measurements")
    return {
        "available": True,
        "evidence_id": f"weather:{source}",
        "source": source,
        "result": "below_expected" if ratio < 0.9 else "as_expected",
        "details": {"measured_to_expected_ratio": round(ratio, 3)},
    }


def check_panel_condition(data):
    panels = data.get("panel_observation")
    if not isinstance(panels, dict) or "condition" not in panels:
        return _unavailable("panel inspection or observation")

    source = panels.get("source_id", "panel observation")
    return {
        "available": True,
        "evidence_id": f"panels:{source}",
        "source": source,
        "result": panels["condition"],
    }


def compare_inverters(data):
    inverters = data.get("inverters")
    if not inverters or len(inverters) < 2:
        return _unavailable("at least two inverter readings")

    ratios = [
        (item["actual_kw"] / item["expected_kw"], item["inverter_id"])
        for item in inverters
        if item.get("expected_kw", 0) > 0
    ]
    if len(ratios) < 2:
        return _unavailable("valid inverter expected-output readings")

    ratios.sort()
    weakest_ratio, weakest_id = ratios[0]
    peer_ratio = sum(ratio for ratio, _ in ratios[1:]) / (len(ratios) - 1)
    is_outlier = weakest_ratio < peer_ratio * 0.9
    source = data.get("inverter_source_id", "inverter readings")
    return {
        "available": True,
        "evidence_id": f"inverters:{source}",
        "source": source,
        "result": "outlier" if is_outlier else "no_outlier",
        "details": {
            "lowest_output_inverter": weakest_id,
            "lowest_output_ratio": round(weakest_ratio, 3),
            "peer_output_ratio": round(peer_ratio, 3),
        },
    }


TOOL_FUNCTIONS = {
    "check_weather": check_weather,
    "check_panel_condition": check_panel_condition,
    "compare_inverters": compare_inverters,
}
