import os
import socket

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .models import Alert, Diagnosis
from .prompts import DIAGNOSTIC_PROMPT
from .tools import (
    get_number_of_units_working,
    get_panels_temperature,
    get_weather_data,
)

load_dotenv()

original_getaddrinfo = socket.getaddrinfo


def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "generativelanguage.googleapis.com":
        family = socket.AF_INET
    return original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = ipv4_getaddrinfo

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
)
MODEL_NAME = "gemini-3.5-flash"
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
    while True:
        function_calls = [
            step
            for step in (interaction.steps or [])
            if getattr(step, "type", None) == "function_call"
        ]

        if not function_calls:
            final_text = interaction.output_text or "No function calls"
            print("NO Final answer returned")
            return Diagnosis(
                diagnosis=final_text,
                confidence=0.0,
                evidence=[],
                recommended_action="Review the model output manually.",
            )

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
                    "result": result,
                    "is_error": is_error,
                }
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
