from datetime import datetime, timedelta, timezone


def get_sample_records(plant_id, now=None):
    """Return synthetic records shaped like the expected plant API response."""
    now = now or datetime.now(timezone.utc)
    return [
        {
            "plant_id": plant_id,
            "timestamp": (now - timedelta(minutes=15 * index)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "energy_kwh": 42.0,
            "expected_energy_kwh": 46.0,
        }
        for index in range(6)
    ]


def get_sample_investigation_data():
    """Return synthetic raw inputs used by the agent's read-only tools."""
    return {
        "inverter_source_id": "synthetic-inverter-telemetry",
        "inverters": [
            {"inverter_id": "INV-01", "actual_kw": 76, "expected_kw": 100},
            {"inverter_id": "INV-02", "actual_kw": 99, "expected_kw": 100},
            {"inverter_id": "INV-03", "actual_kw": 98, "expected_kw": 100},
        ],
        "grid": {
            "export_limit_active": False,
            "source_id": "synthetic-grid-status",
        },
        "sensors": {
            "status": "healthy",
            "source_id": "synthetic-sensor-status",
        },
        "irradiance": {
            "measured_w_m2": 780,
            "expected_w_m2": 800,
            "source_id": "synthetic-irradiance",
        },
        # No panel observation: the agent should leave that cause unchecked.
    }
