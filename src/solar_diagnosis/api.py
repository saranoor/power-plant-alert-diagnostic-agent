"""Standard-library HTTP service for solar alert diagnosis."""

from __future__ import annotations

import json
import logging
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError

from .agent import diagnose
from .errors import GeminiRateLimitError
from .models import Alert, Diagnosis

logger = logging.getLogger(__name__)
MAX_REQUEST_BYTES = 1_048_576
DIAGNOSIS_PATH = re.compile(r"^/alerts/([^/]+)/diagnoses$")


class DiagnosisRequestHandler(BaseHTTPRequestHandler):
    server_version = "SolarDiagnosis/1.0"

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Endpoint not found.")

    def do_POST(self) -> None:
        match = DIAGNOSIS_PATH.fullmatch(urlsplit(self.path).path)
        if match is None:
            self._send_error(HTTPStatus.NOT_FOUND, "Endpoint not found.")
            return

        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type.lower() != "application/json":
            self._send_error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Content-Type must be application/json.",
            )
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_error(HTTPStatus.LENGTH_REQUIRED, "A valid Content-Length is required.")
            return

        if content_length < 0:
            self._send_error(HTTPStatus.BAD_REQUEST, "Content-Length cannot be negative.")
            return
        if content_length > MAX_REQUEST_BYTES:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large.")
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
            alert = Alert.model_validate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON.")
            return
        except ValidationError as error:
            self._send_error(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                error.errors(include_context=False),
            )
            return

        alert_id = unquote(match.group(1))
        if alert_id != alert.alert_id:
            self._send_error(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "The alert_id in the URL must match the request body.",
            )
            return

        try:
            result = diagnose(alert)
        except GeminiRateLimitError as error:
            logger.warning(
                "Diagnosis provider rate-limited alert %s: %s",
                alert.alert_id,
                error,
            )
            self._send_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "The diagnosis provider is temporarily rate-limited. Retry later.",
            )
            return
        except RuntimeError as error:
            if "GEMINI_API_KEY is required" in str(error):
                self._send_error(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "The diagnosis model is not configured.",
                )
                return
            logger.exception("Diagnosis agent failed.")
            self._send_error(
                HTTPStatus.BAD_GATEWAY,
                "The diagnosis provider could not complete the request.",
            )
            return
        except Exception:
            logger.exception("Diagnosis request failed unexpectedly.")
            self._send_error(
                HTTPStatus.BAD_GATEWAY,
                "The diagnosis provider could not complete the request.",
            )
            return

        self._send_json(HTTPStatus.OK, result.model_dump(mode="json"))

    def _send_error(self, status: HTTPStatus, detail: Any) -> None:
        self._send_json(status, {"detail": detail})

    def _send_json(self, status: HTTPStatus, body: Any) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)


class DiagnosisHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(host: str = "127.0.0.1", port: int = 8000) -> DiagnosisHTTPServer:
    return DiagnosisHTTPServer((host, port), DiagnosisRequestHandler)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    server = create_server(host, port)
    logger.info("Solar Diagnosis API listening on %s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Solar Diagnosis API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main()
