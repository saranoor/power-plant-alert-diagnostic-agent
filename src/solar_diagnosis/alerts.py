from datetime import datetime, timedelta, timezone

MINIMUM_READINGS = 6
SHORTFALL_LIMIT_PERCENT = 7
WINDOW = timedelta(days=7)


def detect_alert(records, plant_id, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc)
    window_start = checked_at - WINDOW
    valid_readings = []

    for item in records:
        if item.get("plant_id") != plant_id:
            continue
        try:
            timestamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            actual = float(item["energy_kwh"])
            expected = float(item["expected_energy_kwh"])
        except (KeyError, TypeError, ValueError):
            continue

        if not window_start <= timestamp <= checked_at:
            continue
        if actual < 0 or expected <= 0:
            continue
        valid_readings.append((actual, expected))

    if len(valid_readings) < MINIMUM_READINGS:
        return {"status": "insufficient_data"}

    actual_total = sum(actual for actual, _ in valid_readings)
    expected_total = sum(expected for _, expected in valid_readings)
    shortfall = (expected_total - actual_total) / expected_total * 100

    if shortfall >= SHORTFALL_LIMIT_PERCENT:
        return {
            "status": "alert",
            "plant_id": plant_id,
            "window_start": window_start.isoformat(),
            "window_end": checked_at.isoformat(),
            "actual_kwh": actual_total,
            "expected_kwh": expected_total,
            "shortfall_percent": round(shortfall, 1),
            "readings_used": len(valid_readings),
            "checked_at": checked_at.isoformat(),
        }

    return {"status": "normal", "shortfall_percent": round(shortfall, 1)}
