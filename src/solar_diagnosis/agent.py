from google import genai

from .models import Alert, Diagnosis
from .prompts import DIAGNOSTIC_PROMPT
from .tools import (
    get_number_of_units_working,
    get_weather_data,
)
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
import httpx
import socket

load_dotenv()

original_getaddrinfo = socket.getaddrinfo


def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "generativelanguage.googleapis.com":
        family = socket.AF_INET

    return original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = ipv4_getaddrinfo
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def diagnose(alert: Alert) -> Diagnosis:
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config={
            "tools": [get_weather_data, get_number_of_units_working],
            "response_schema": Diagnosis,
        },
    )

    response = chat.send_message(
        [
            DIAGNOSTIC_PROMPT,
            alert.model_dump_json(),
        ]
    )

    print("Response text:", response.text)
    print("Parsed response:", response.parsed)

    return response.parsed
