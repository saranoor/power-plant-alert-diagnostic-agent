"""Read-only diagnostic tools exposed to the investigation model."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "compare_inverters",
            "description": "Compare inverter output against peer inverters.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_grid_curtailment",
            "description": "Check whether a grid export limit was active.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_sensor_health",
            "description": "Check the status of plant measurement sensors.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_irradiance",
            "description": "Compare measured and expected irradiance.",
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
            "name": "lookup_fault_codes",
            "description": (
                "Look up reported equipment fault codes in supplied manuals."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_maintenance_history",
            "description": ("Search supplied maintenance tickets for this plant."),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _unavailable(source_name):
    return {
        "available": False,
        "reason": f"Required source missing: {source_name}",
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
    source = data.get("inverter_source_id", "synthetic inverter readings")
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


def check_grid_curtailment(data):
    grid = data.get("grid")
    if not isinstance(grid, dict) or "export_limit_active" not in grid:
        return _unavailable("grid export-limit status")
    source = grid.get("source_id", "synthetic grid status")
    return {
        "available": True,
        "evidence_id": f"grid:{source}",
        "source": source,
        "result": ("curtailed" if grid["export_limit_active"] else "not_curtailed"),
    }


def check_sensor_health(data):
    sensors = data.get("sensors")
    if not isinstance(sensors, dict) or "status" not in sensors:
        return _unavailable("sensor health status")
    source = sensors.get("source_id", "synthetic sensor status")
    return {
        "available": True,
        "evidence_id": f"sensors:{source}",
        "source": source,
        "result": sensors["status"],
    }


def compare_irradiance(data):
    irradiance = data.get("irradiance")
    if not isinstance(irradiance, dict):
        return _unavailable("irradiance measurements")
    expected = irradiance.get("expected_w_m2", 0)
    measured = irradiance.get("measured_w_m2")
    if not expected or measured is None:
        return _unavailable("measured and expected irradiance")
    ratio = measured / expected
    source = irradiance.get("source_id", "synthetic irradiance")
    return {
        "available": True,
        "evidence_id": f"irradiance:{source}",
        "source": source,
        "result": "below_expected" if ratio < 0.9 else "as_expected",
        "details": {"measured_to_expected_ratio": round(ratio, 3)},
    }


def check_panel_condition(data):
    panels = data.get("panel_observation")
    if not isinstance(panels, dict) or "condition" not in panels:
        return _unavailable("panel inspection or observation")
    source = panels.get("source_id", "synthetic panel observation")
    return {
        "available": True,
        "evidence_id": f"panels:{source}",
        "source": source,
        "result": panels["condition"],
    }


def lookup_fault_codes(data):
    faults = data.get("fault_events")
    if faults is None:
        return _unavailable("equipment fault events")

    source = data.get("fault_source_id", "fault event records")
    if not faults:
        return {
            "available": True,
            "evidence_id": f"faults:{source}",
            "source": source,
            "result": "no_fault_codes",
        }

    manuals = data.get("fault_manuals")
    if not isinstance(manuals, dict):
        return {
            "available": True,
            "evidence_id": f"faults:{source}",
            "source": source,
            "result": "fault_codes_present_manual_unavailable",
            "fault_codes": [event.get("code") for event in faults],
            "manual_lookup_available": False,
        }

    return {
        "available": True,
        "evidence_id": f"faults:{source}",
        "source": source,
        "result": "fault_codes_present" if faults else "no_fault_codes",
        "manual_lookup_available": True,
        "faults": [
            {
                "code": event.get("code"),
                "equipment_id": event.get("equipment_id"),
                "manual_entry": manuals.get(event.get("code")),
            }
            for event in faults
        ],
    }


def search_maintenance_history(data):
    tickets = data.get("maintenance_tickets")
    if tickets is None:
        return _unavailable("maintenance ticket history")

    source = data.get("ticket_source_id", "maintenance ticket records")
    return {
        "available": True,
        "evidence_id": f"tickets:{source}",
        "source": source,
        "result": "tickets_found" if tickets else "no_matching_tickets",
        "tickets": tickets,
    }


TOOL_FUNCTIONS = {
    "compare_inverters": compare_inverters,
    "check_grid_curtailment": check_grid_curtailment,
    "check_sensor_health": check_sensor_health,
    "compare_irradiance": compare_irradiance,
    "check_panel_condition": check_panel_condition,
    "lookup_fault_codes": lookup_fault_codes,
    "search_maintenance_history": search_maintenance_history,
}
