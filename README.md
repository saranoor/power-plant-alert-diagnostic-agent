# AI Diagnostic Agents for Solar Power Plants
## Problem
Modern solar installations face numerous operational challenges that can significantly impact performance and profitability. Traditional diagnostic approaches often fail to identify problems until they've already caused substantial energy losses or equipment damage. An AI Agent can diagnose the issue of Solar Power Plant and share its diagnostic finding with a human Engineer for resolving the issue.

A leightweight prototype that checks timestamped plant readings for underperformance, then lets an LLM choose among read-only diagnostic tools. The demo uses synthetic plant data, not live plant data. The agent can be explained as shown below:
![ScreenShot](/design.png)

## Run

Install the local package into the project virtual environment, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
$env:GEMINI_API_KEY = "your-api-key"
.\.venv\Scripts\python.exe main.py
```

Set `GEMINI_MODEL` to use a different supported Gemini model. The agent can
choose among three read-only tools: weather, panel condition, and inverter
comparison. It can make up to six tool calls per investigation. Missing source
data is reported as unavailable, and the model may skip checks based on prior
results. It returns `unknown` when evidence is insufficient, conflicting, or
uncited.

Run tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the golden-alert agent evaluation from the project root with Gemini
credentials set in `.env` (`GEMINI_API_KEY` or `GOOGLE_API_KEY`). Set
`GEMINI_MODEL` to configure the diagnosis model; optionally set
`GEMINI_EVALUATION_MODEL` to select a separate DeepEval judge model.

```powershell
.\.venv\Scripts\python.exe -m solar_diagnosis.run_evaluation
```

This runs the diagnosis agent for each golden alert, prints classification
metrics, and runs the configured DeepEval judge metrics. It makes live Gemini
API calls and may incur usage charges.

## HTTP API

Start the long-running API locally:

```powershell
.\.venv\Scripts\python.exe -m solar_diagnosis.api
```

The API provides `GET /health` and `POST /alerts/{alert_id}/diagnoses`.
The POST body is an alert JSON object; its `alert_id` must match the path.
Successful responses contain the diagnosis, predicted cause, confidence,
evidence, recommended action, and tool results. The endpoint calls Gemini
synchronously, so the request remains open while the agent investigates. The
service uses Python's built-in HTTP server and listens on `0.0.0.0:8000` by
default; configure `HOST` or `PORT` to change the bind address.

## Docker

Build and run the API container from the project root:

```powershell
docker build -t solar-diagnosis .
docker run --rm -p 8000:8000 --env-file .env solar-diagnosis
```

The image excludes `.env`; credentials are supplied at runtime. For Fargate,
provide `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) through ECS task secrets rather
than baking credentials into the image. The root `main.py` one-shot sample
remains available locally with `python main.py`.