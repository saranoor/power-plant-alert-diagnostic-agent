def get_weather_data(latitude: float, longitude: float):
    """Return a simple weather snapshot for the plant area."""
    return {
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
