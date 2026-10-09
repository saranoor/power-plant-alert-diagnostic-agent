# import os

# from dotenv import load_dotenv
# from google import genai
# from google.genai import types

# load_dotenv()

# http_options = types.HttpOptions(
#     client_args={"http2": False}, async_client_args={"http2": False}
# )
# client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=http_options)

# chat = client.chats.create(model="gemini-2.5-flash")

# response = chat.send_message("Say hello in one sentence.")

# print(response.text)

# from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

# # Initializes using the GEMINI_API_KEY environment variable
# client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# response = client.models.generate_content(
#     model="gemini-3.8-flash", contents="Explain black holes in one sentence."
# )

# print(response.text)


# import socket
# import ssl

# hostname = "generativelanguage.googleapis.com"
# context = ssl.create_default_context()

# with socket.create_connection(("172.217.117.4", 443), timeout=15) as sock:
#     with context.wrap_socket(sock, server_hostname=hostname) as tls:
#         print("TLS version:", tls.version())
#         print("Connected hostname:", tls.server_hostname)


# import socket
# import httpx

# original_getaddrinfo = socket.getaddrinfo


# def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
#     if host == "generativelanguage.googleapis.com":
#         family = socket.AF_INET

#     return original_getaddrinfo(host, port, family, type, proto, flags)


# socket.getaddrinfo = ipv4_getaddrinfo

# response = httpx.get(
#     "https://generativelanguage.googleapis.com",
#     timeout=20,
# )
# print("Status:", response.status_code)


import os
import socket
from google import genai

original_getaddrinfo = socket.getaddrinfo


def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "generativelanguage.googleapis.com":
        family = socket.AF_INET

    return original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = ipv4_getaddrinfo

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Explain black holes in one sentence.",
)

print(response.text)
