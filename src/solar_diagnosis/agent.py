import os
import socket

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from .models import Alert, Diagnosis, ToolResult
from .prompts import DIAGNOSTIC_PROMPT
from .utils import extract_json
from .tools import (
    get_number_of_units_working,
    get_panels_temperature,
    get_weather_data,
    get_inverter_alarms,
    get_inverter_events,
    get_inverter_status,
    get_inverter_string_data,
    get_inverter_temperatures,
    get_plant_coordinates,
)

load_dotenv()

original_getaddrinfo = socket.getaddrinfo


def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "generativelanguage.googleapis.com":
        family = socket.AF_INET
    return original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = ipv4_getaddrinfo

_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=_api_key) if _api_key else None
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_TOOL_ROUNDS = 5


def _tool_declarations():
    return [
        {
            "type": "function",
            "name": "get_weather_data",
            "description": "Look up a plant's registered location and return a weather snapshot. Pass the plant ID from the alert.",
            "parameters": {
                "type": "object",
                "properties": {"plant_id": {"type": "string"}},
                "required": ["plant_id"],
            },
        },
        {
            "type": "function",
            "name": "get_number_of_units_working",
            "description": "Return the number of working units for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                },
                "required": ["plant_id"],
            },
        },
        {
            "type": "function",
            "name": "get_panels_temperature",
            "description": "For the given plant ID, return each registered module's mock temperature and simple estimated relative efficiency.",
            "parameters": {
                "type": "object",
                "properties": {"plant_id": {"type": "string"}},
                "required": ["plant_id"],
            },
        },
        {
            "type": "function",
            "name": "get_inverter_status",
            "description": "Return operating status, active fault, trip history and DC/AC readings for the inverter identified by the alert's plant and asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                },
                "required": ["plant_id", "asset_id"],
            },
        },
        {
            "type": "function",
            "name": "get_inverter_string_data",
            "description": "Return per-string DC voltage, current and module counts for the inverter identified by the alert's plant and asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                },
                "required": ["plant_id", "asset_id"],
            },
        },
        {
            "type": "function",
            "name": "get_inverter_temperatures",
            "description": "Return temperatures, fan status and derating state for the inverter identified by the alert's plant and asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                },
                "required": ["plant_id", "asset_id"],
            },
        },
        {
            "type": "function",
            "name": "get_inverter_alarms",
            "description": "Return recent alarms for the inverter identified by the alert's plant and asset. Optionally set the lookback window in minutes (default 30).",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "window_minutes": {"type": "integer"},
                },
                "required": ["plant_id", "asset_id"],
            },
        },
        {
            "type": "function",
            "name": "get_inverter_events",
            "description": "Return recent maintenance, reconfiguration, restart and parameter-change events for the inverter identified by the alert's plant and asset. Optionally set the lookback window in hours (default 72).",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "window_hours": {"type": "integer"},
                },
                "required": ["plant_id", "asset_id"],
            },
        },
    ]


def _call_tool(name: str, arguments: dict, alert: Alert | None = None):
    if name == "get_weather_data":
        return get_weather_data(**arguments)
    if name == "get_number_of_units_working":
        return get_number_of_units_working(**arguments)
    if name == "get_panels_temperature":
        plant_id = arguments.get("plant_id") or (alert.plant if alert else None)
        if not plant_id:
            raise ValueError("A plant ID is required for panel temperature analysis.")
        if alert is not None and plant_id != alert.plant:
            raise ValueError(
                "Panel temperature analysis is limited to the alert plant."
            )
        return get_panels_temperature(plant_id=plant_id)
    if name in {
        "get_inverter_status",
        "get_inverter_string_data",
        "get_inverter_temperatures",
        "get_inverter_alarms",
        "get_inverter_events",
    }:
        plant_id = arguments.get("plant_id") or (alert.plant if alert else None)
        asset_id = arguments.get("asset_id") or (alert.asset if alert else None)
        if not plant_id or not asset_id:
            raise ValueError("Plant and asset IDs are required for inverter analysis.")
        if alert is not None and (plant_id != alert.plant or asset_id != alert.asset):
            raise ValueError(
                "Inverter analysis is limited to the alert plant and asset."
            )

        if name == "get_inverter_status":
            return get_inverter_status(plant_id=plant_id, asset_id=asset_id)
        if name == "get_inverter_string_data":
            return get_inverter_string_data(plant_id=plant_id, asset_id=asset_id)
        if name == "get_inverter_temperatures":
            return get_inverter_temperatures(plant_id=plant_id, asset_id=asset_id)
        if name == "get_inverter_alarms":
            return get_inverter_alarms(
                plant_id=plant_id,
                asset_id=asset_id,
                window_minutes=arguments.get("window_minutes", 30),
            )
        return get_inverter_events(
            plant_id=plant_id,
            asset_id=asset_id,
            window_hours=arguments.get("window_hours", 72),
        )
    return {"error": f"Unsupported tool: {name}"}


def diagnose(alert: Alert) -> Diagnosis:
    if client is None or not getattr(client, "interactions", None):
        raise RuntimeError("GEMINI_API_KEY is required to run the diagnosis agent.")

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=alert.model_dump_json(),
        system_instruction=DIAGNOSTIC_PROMPT,
        tools=_tool_declarations(),
    )
    # print(f"interaction: {interaction}")
    tool_rounds = 0
    tool_results: list[ToolResult] = []
    while True:
        function_calls = [
            step
            for step in (interaction.steps or [])
            if getattr(step, "type", None) == "function_call"
        ]

        if not function_calls:
            final_text = interaction.output_text
            if not isinstance(final_text, str) or not final_text.strip():
                raise RuntimeError(
                    "Gemini returned no final diagnosis. Expected JSON with "
                    "diagnosis, predicted_cause, confidence, evidence, and "
                    "recommended_action."
                )
            final_text = extract_json(final_text)
            try:
                diagnosis = Diagnosis.model_validate_json(final_text)
            except ValidationError as error:
                print(f"Final_text: {final_text}")
                raise RuntimeError(
                    "Gemini returned an invalid structured diagnosis. Expected "
                    "JSON with diagnosis, predicted_cause, confidence (0-1), "
                    "evidence, and recommended_action."
                ) from error
            return diagnosis.model_copy(update={"tool_results": tool_results})

        if tool_rounds >= MAX_TOOL_ROUNDS:
            raise RuntimeError(
                f"Agent exceeded the limit of {MAX_TOOL_ROUNDS} tool-call rounds."
            )

        if not interaction.id:
            raise RuntimeError(
                "Gemini returned function calls without an interaction ID."
            )

        function_results = []
        print(f"function call: {function_calls}")
        for call in function_calls:
            print("calling")
            try:
                print(f"making function call to; {call.name}")
                result = _call_tool(call.name, call.arguments, alert)
                is_error = False
            except Exception as error:
                result = {"error": str(error)}
                is_error = True

            function_results.append(
                {
                    "type": "function_result",
                    "call_id": call.id,
                    "name": call.name,
                    "result": {
                        "evidence_id": f"EV-{len(tool_results) + 1:03d}",
                        "data": result,
                    },
                    "is_error": is_error,
                }
            )
            tool_results.append(
                ToolResult(
                    call_id=call.id,
                    evidence_id=f"EV-{len(tool_results) + 1:03d}",
                    tool_name=call.name,
                    arguments=call.arguments,
                    result=result,
                    is_error=is_error,
                )
            )

        interaction = client.interactions.create(
            model=MODEL_NAME,
            previous_interaction_id=interaction.id,
            input=function_results,
            system_instruction=DIAGNOSTIC_PROMPT,
            tools=_tool_declarations(),
        )
        tool_rounds += 1
        print(f"number of rounds so far: {tool_rounds}")
        print(interaction)
