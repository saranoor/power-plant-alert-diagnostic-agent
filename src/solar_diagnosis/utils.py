import re

# Synthetic demo coordinates; replace with each plant's actual location.
PLANT_COORDINATES: dict[str, tuple[float, float]] = {
    "SOLAR-01": (35.0, -117.0),
}


def get_plant_coordinates(plant_id: str) -> tuple[float, float]:
    """Return the registered latitude and longitude for a plant ID."""
    try:
        return PLANT_COORDINATES[plant_id]
    except KeyError as error:
        raise ValueError(
            f"No coordinates are registered for plant '{plant_id}'."
        ) from error


def extract_json(text: str) -> str:
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrapper
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: grab the outermost {...} if there's extra prose around it
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text
