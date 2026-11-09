from .utils import get_plant_coordinates

REFERENCE_MODULE_TEMP_C = 25.0
HIGH_MODULE_TEMP_C = 45.0
# Mock coefficient; replace with the module manufacturer's datasheet value.
POWER_TEMPERATURE_COEFFICIENT_PER_C = -0.004
MOCK_MODULE_TEMPERATURES = {
    "SOLAR-01": [
        {"module_id": "MOD-01", "module_temp_c": 42.0},
        {"module_id": "MOD-02", "module_temp_c": 48.0},
        {"module_id": "MOD-03", "module_temp_c": 51.0},
        {"module_id": "MOD-04", "module_temp_c": 39.0},
    ],
}


def get_weather_data(plant_id: str):
    """Return a simple weather snapshot for the registered plant area."""
    print(f"I am in weather function")
    latitude, longitude = get_plant_coordinates(plant_id)
    return {
        "plant_id": plant_id,
        "latitude": latitude,
        "longitude": longitude,
        "condition": "clear",
        "temperature_c": 28.5,
        "irradiance_w_m2": 850.0,
        "source": "synthetic-weather-api",
    }


def get_number_of_units_working(plant_id: str):
    """Return the number of working units for a plant."""
    working_units = {
        "plant_id": plant_id,
        "working_units": 18,
        "total_units": 20,
        "offline_units": 2,
        "source": "synthetic-plant-telemetry",
    }
    return working_units


def get_panels_temperature(plant_id: str):
    """Return mock temperature and estimated relative efficiency per module."""
    try:
        modules = MOCK_MODULE_TEMPERATURES[plant_id]
    except KeyError as error:
        raise ValueError(
            f"No module temperature data is registered for plant '{plant_id}'."
        ) from error

    module_results = []
    for module in modules:
        temperature_delta_c = module["module_temp_c"] - REFERENCE_MODULE_TEMP_C
        estimated_efficiency_percent = max(
            0.0,
            100.0 + POWER_TEMPERATURE_COEFFICIENT_PER_C * 100 * temperature_delta_c,
        )
        module_results.append(
            {
                **module,
                "is_module_temperature_high": (
                    module["module_temp_c"] >= HIGH_MODULE_TEMP_C
                ),
                "estimated_efficiency_percent": round(estimated_efficiency_percent, 1),
                "estimated_efficiency_loss_percent": round(
                    100.0 - estimated_efficiency_percent, 1
                ),
            }
        )

    return {
        "plant_id": plant_id,
        "modules": module_results,
        "reference_module_temp_c": REFERENCE_MODULE_TEMP_C,
        "high_temperature_threshold_c": HIGH_MODULE_TEMP_C,
        "temperature_coefficient_per_c": POWER_TEMPERATURE_COEFFICIENT_PER_C,
        "source": "synthetic-module-telemetry; estimated efficiency",
    }


"""Mock inverter-level tools for an agent investigating inverter trip alerts.

Scenario baked into the mock data for SOLAR-20 / INV-20 (matches the alert):
  - INV-20 tripped on F32 (DC overvoltage), DC voltage 1012 V vs 1000 V limit.
  - STR-02 has 24 modules instead of the expected 22 after a module
    replacement 40 hours ago, so its string voltage is too high.
  - Temperatures and fan are normal, so the agent should not blame heat.
"""

MOCK_INVERTERS = {
    "SOLAR-20": {
        "INV-20": {
            "status": {
                "mode": "fault",
                "active_fault_code": "F32",
                "fault_text": "Inverter trip: DC overvoltage",
                "last_trip_utc": "2025-11-08T07:12:40Z",
                "trip_count_24h": 2,
                "restart_attempts": 1,
                "ac_power_kw": 0.0,
                "dc_voltage_v": 1012.0,
                "max_dc_input_voltage_v": 1000.0,
            },
            "temperatures": {
                "heatsink_temp_c": 52.0,
                "internal_temp_c": 47.0,
                "ambient_temp_c": 28.5,
                "overtemp_threshold_c": 85.0,
                "fan_status": "ok",
                "derating_active": False,
            },
            "strings": [
                {
                    "string_id": "STR-01",
                    "voltage_v": 908.0,
                    "current_a": 9.1,
                    "modules_in_string": 22,
                    "expected_modules_in_string": 22,
                },
                {
                    "string_id": "STR-02",
                    "voltage_v": 1012.0,
                    "current_a": 9.0,
                    "modules_in_string": 24,
                    "expected_modules_in_string": 22,
                },
                {
                    "string_id": "STR-03",
                    "voltage_v": 910.0,
                    "current_a": 9.2,
                    "modules_in_string": 22,
                    "expected_modules_in_string": 22,
                },
                {
                    "string_id": "STR-04",
                    "voltage_v": 906.0,
                    "current_a": 9.1,
                    "modules_in_string": 22,
                    "expected_modules_in_string": 22,
                },
            ],
            "alarms": [
                {"code": "W05", "text": "High DC voltage warning", "minutes_ago": 9},
                {
                    "code": "F32",
                    "text": "Inverter trip: DC overvoltage",
                    "minutes_ago": 1,
                },
            ],
            "events": [
                {
                    "event": "module_replacement_string_reconfigured",
                    "detail": "STR-02 now has 24 modules",
                    "hours_ago": 40,
                },
                {"event": "inverter_restart", "detail": "manual reset", "hours_ago": 1},
            ],
        },
    },
}


def _get_inverter(plant_id: str, asset_id: str):
    try:
        return MOCK_INVERTERS[plant_id][asset_id]
    except KeyError as error:
        raise ValueError(
            f"No inverter data is registered for plant '{plant_id}', asset '{asset_id}'."
        ) from error


def get_inverter_status(plant_id: str, asset_id: str):
    """Return the current mode, active fault code, last trip time and DC/AC readings for one inverter."""
    inverter = _get_inverter(plant_id, asset_id)
    return {
        "plant_id": plant_id,
        "asset_id": asset_id,
        **inverter["status"],
        "source": "synthetic-inverter-telemetry",
    }


def get_inverter_string_data(plant_id: str, asset_id: str):
    """Return per-string DC voltage, current and module count for one inverter, flagging strings over the inverter's max DC input voltage."""
    inverter = _get_inverter(plant_id, asset_id)
    max_voltage_v = inverter["status"]["max_dc_input_voltage_v"]
    results = []
    for string in inverter["strings"]:
        results.append(
            {
                **string,
                "is_over_max_voltage": string["voltage_v"] >= max_voltage_v,
                "has_unexpected_module_count": (
                    string["modules_in_string"] != string["expected_modules_in_string"]
                ),
            }
        )
    return {
        "plant_id": plant_id,
        "asset_id": asset_id,
        "max_dc_input_voltage_v": max_voltage_v,
        "strings": results,
        "source": "synthetic-string-monitoring",
    }


def get_inverter_temperatures(plant_id: str, asset_id: str):
    """Return heatsink and internal temperature, fan status and derating state for one inverter."""
    inverter = _get_inverter(plant_id, asset_id)
    temps = inverter["temperatures"]
    return {
        "plant_id": plant_id,
        "asset_id": asset_id,
        **temps,
        "is_overtemperature": temps["heatsink_temp_c"] >= temps["overtemp_threshold_c"],
        "source": "synthetic-inverter-telemetry",
    }


def get_inverter_alarms(plant_id: str, asset_id: str, window_minutes: int = 30):
    """Return other alarms raised on the same inverter within the given time window."""
    inverter = _get_inverter(plant_id, asset_id)
    alarms = [a for a in inverter["alarms"] if a["minutes_ago"] <= window_minutes]
    return {
        "plant_id": plant_id,
        "asset_id": asset_id,
        "window_minutes": window_minutes,
        "alarms": alarms,
        "source": "synthetic-scada-alarm-log",
    }


def get_inverter_events(plant_id: str, asset_id: str, window_hours: int = 72):
    """Return maintenance, reconfiguration, restart and parameter-change events for one inverter."""
    inverter = _get_inverter(plant_id, asset_id)
    events = [e for e in inverter["events"] if e["hours_ago"] <= window_hours]
    return {
        "plant_id": plant_id,
        "asset_id": asset_id,
        "window_hours": window_hours,
        "events": events,
        "source": "synthetic-event-log",
    }
