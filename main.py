from src.solar_diagnosis.agent import diagnose
from src.solar_diagnosis.models import Alert

alert = {
    "alert_id": "A-20261008-0091",
    "timestamp_utc": "2026-10-08T07:12:40Z",
    "plant": "SOLAR-01",
    "asset": "INV-07",
    "alarm": {
        "code": "F32",
        "text": "DC overcurrent",
        "severity": "high",
    },
    "state": {
        "mode": "running",
        "curtailed": False,
    },
    "weather": {
        "poa_w_m2": 812,
        "module_temp_c": 51,
        "ambient_c": 34,
    },
    "readings": {
        "ac_power_kw": 410,
        "expected_ac_power_kw": 780,
        "dc_voltage_v": 912,
        "strings_below_expected": [
            "CB-07-03",
            "CB-07-04",
        ],
    },
    "data_quality": "good",
    "related_alarms_last_30min": ["CB-07-03 low current"],
    "recent_events": ["Cleaning crew on block 7, 06:30-07:00"],
}


alert = Alert(**alert)

result = diagnose(alert)

print(f"Result: {result}")
