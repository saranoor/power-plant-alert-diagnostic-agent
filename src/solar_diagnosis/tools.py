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
