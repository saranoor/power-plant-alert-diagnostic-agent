import sys

from solar_diagnosis.agent import diagnose
from solar_diagnosis.errors import GeminiRateLimitError
from solar_diagnosis.models import Alert

# alert = {
#     "alert_id": "A-20261008-0091",
#     "timestamp_utc": "2026-10-08T07:12:40Z",
#     "plant": "SOLAR-01",
#     "asset": "INV-07",
#     "alarm": {
#         "code": "F32",
#         "text": "DC overcurrent",
#         "severity": "high",
#     },
#     "state": {
#         "mode": "running",
#         "curtailed": False,
#     },
#     "weather": {
#         "poa_w_m2": 812,
#         "module_temp_c": 51,
#         "ambient_c": 34,
#     },
#     "readings": {
#         "ac_power_kw": 410,
#         "expected_ac_power_kw": 780,
#         "dc_voltage_v": 912,
#         "strings_below_expected": [
#             "CB-07-03",
#             "CB-07-04",
#         ],
#     },
#     "data_quality": "good",
#     "related_alarms_last_30min": ["CB-07-03 low current"],
#     "recent_events": ["Cleaning crew on block 7, 06:30-07:00"],
# }


alert = {
    "alert_id": "B-20251108-0091",
    "timestamp_utc": "2025-11-08T07:12:40Z",
    "plant": "SOLAR-20",
    "asset": "INV-20",
    "alarm": {
        "code": "F32",
        "text": "AC overcurrent",
        "severity": "high",
    },
    "state": {
        "mode": "running",
        "curtailed": False,
    },
    "readings": {
        "ac_power_kw": 410,
        "dc_voltage_v": 912,
    },
}

alert = {
    "alert_id": "B-20251108-0091",
    "timestamp_utc": "2025-11-08T07:12:40Z",
    "plant": "SOLAR-20",
    "asset": "INV-20",
    "alarm": {
        "code": "F32",
        "text": "Inverter trip: DC overvoltage",
        "severity": "high",
    },
    "state": {
        "mode": "fault",
        "curtailed": False,
    },
    "readings": {
        "ac_power_kw": 0,
        "dc_voltage_v": 1012,
    },
}

# alert = {
#     "alert_id": "B-20251108-0092",
#     "timestamp_utc": "2025-11-08T04:15:30Z",
#     "plant": "SOLAR-20",
#     "asset": "INV-07",
#     "alarm": {
#         "code": "F23",
#         "text": "Ground fault: insulation resistance low",
#         "severity": "critical",
#     },
#     "state": {
#         "mode": "lockout",
#         "curtailed": False,
#     },
#     "readings": {
#         "ac_power_kw": 0,
#         "dc_voltage_v": 905,
#     },
# }

# alert = {
#     "alert_id": "B-20251108-0094",
#     "timestamp_utc": "2025-11-08T09:05:45Z",
#     "plant": "SOLAR-20",
#     "asset": "INV-12",
#     "alarm": {
#         "code": "F40",
#         "text": "Grid over-frequency (51.6 Hz)",
#         "severity": "high",
#     },
#     "state": {
#         "mode": "standby",
#         "curtailed": True,
#     },
#     "readings": {
#         "ac_power_kw": 0,
#         "dc_voltage_v": 930,
#     },
# }

# alert = {
#     "alert_id": "B-20251108-0093",
#     "timestamp_utc": "2025-11-08T07:20:00Z",
#     "plant": "SOLAR-20",
#     "asset": "INV-05",
#     "alarm": {
#         "code": "W15",
#         "text": "String underperformance: 3 strings below expected current",
#         "severity": "medium",
#     },
#     "state": {
#         "mode": "running",
#         "curtailed": False,
#     },
#     "readings": {
#         "ac_power_kw": 352,
#         "dc_voltage_v": 918,
#     },
# }
alert = Alert(**alert)

try:
    result = diagnose(alert)
except GeminiRateLimitError as error:
    print(error, file=sys.stderr)
    raise SystemExit(1) from None

print(f"Result: {result}")
