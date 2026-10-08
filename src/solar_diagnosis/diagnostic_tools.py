from solar_diagnosis.tools import (
    TOOL_FUNCTIONS,
    TOOL_SCHEMAS,
    check_panel_condition,
    check_weather,
    compare_inverters,
)


def _unavailable(source_name):
    return {"available": False, "reason": f"Required source missing: {source_name}"}


def check_grid_curtailment(data):
    grid = data.get("grid")
    if not isinstance(grid, dict) or "export_limit_active" not in grid:
        return _unavailable("grid export-limit status")
    source = grid.get("source_id", "synthetic grid status")
    return {
        "available": True,
        "evidence_id": f"grid:{source}",
        "source": source,
        "result": "curtailed" if grid["export_limit_active"] else "not_curtailed",
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


__all__ = [
    "TOOL_FUNCTIONS",
    "TOOL_SCHEMAS",
    "compare_inverters",
    "check_weather",
    "check_panel_condition",
    "check_grid_curtailment",
    "check_sensor_health",
    "compare_irradiance",
    "lookup_fault_codes",
    "search_maintenance_history",
]
