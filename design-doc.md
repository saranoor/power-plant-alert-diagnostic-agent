# Solar Plant Underperformance Diagnosis Agent

## Problem

When a plant monitoring system detects production below expectation, an engineer still has to determine why. That investigation crosses several data sources: inverter telemetry, weather and irradiance, export limits, equipment fault codes, and maintenance history. The evidence is incomplete and the next useful check depends on what earlier checks show. On a large portfolio, this manual work delays repairs while energy continues to be lost.

This agent investigates an underperformance alert and produces an evidence-backed diagnostic report for an engineer. It does not operate the plant or make maintenance decisions.

## Goals and non-goals

The MVP should:

- Investigate a plant, time window, and underperformance alert using available read-only data.
- Compare production across comparable inverters and check weather, irradiance, export limits, sensor quality, fault codes, and maintenance history when those sources exist.
- Select follow-up checks based on earlier results, recording what it checked and why.
- Return a likely cause or `unknown`, with supporting and conflicting evidence, source references, and calibrated confidence.
- Draft (but never submit) a work order for human review.
- Clearly distinguish observed plant facts, calculated results, and hypotheses.

The MVP will not control equipment, change setpoints, dispatch staff, close alarms, or claim that diagnoses are validated on real plants. It supplements rather than replaces engineers.

## Why an agent

A fixed script is useful for alerting and repeatable calculations, and should remain responsible for those tasks. It is less suitable for choosing a variable investigation path: an inverter outlier calls for a different next check than a plant-wide irradiance drop, and a suspect sensor changes how production evidence should be interpreted.

A standalone LLM can summarize documents but should not be trusted to calculate performance, infer facts from missing data, or invent fault-code meanings. The proposed design combines deterministic analysis tools with an LLM that selects among approved read-only checks, interprets retrieved evidence, and writes the report. Every conclusion must be traceable to tool results or cited source material.

## User workflow

1. The monitoring system raises an alert with plant ID, interval, and expected-versus-actual production. An engineer can also start an investigation manually.
2. The agent validates the alert and data coverage, then creates a bounded investigation plan.
3. It runs relevant checks, revising its hypotheses as results arrive. It can stop early when evidence is sufficient, or report `unknown` when evidence is missing, contradictory, or inconclusive.
4. It presents a report with ranked hypotheses, confidence, evidence and gaps, and an optional draft work order.
5. An engineer reviews, edits, accepts, or rejects the findings. Any work order creation or dispatch remains a separate human action outside the agent.

## Investigation behavior

The orchestrator uses a bounded loop, not an open-ended chat. It maintains the alert, time window, data-coverage status, ranked hypotheses, completed checks, and remaining tool budget. At each step, it chooses an applicable check from an allowlisted tool catalog. Tool output is structured; the LLM cannot directly query arbitrary systems or issue control commands.

Initial checks, in approximate order:

1. **Validate the alert and telemetry.** Confirm timestamps, units, missing intervals, duplicates, stale feeds, and whether the reported shortfall can be reproduced from measured and expected energy.
2. **Check sensor plausibility.** Compare irradiance and production sensors with nearby sensors, redundant measurements, and expected physical ranges. A suspect measurement lowers confidence in downstream conclusions; it is not silently treated as ground truth.
3. **Compare inverters.** Normalize for capacity, operating status, and relevant conditions; identify persistent outliers and whether the shortfall is plant-wide or localized. Peer comparison is evidence, not proof that the majority is healthy.
4. **Check weather and irradiance.** Compare actual conditions with the expected-production baseline. Separate environmental variation from unexplained underperformance where the available measurements support that distinction.
5. **Check grid constraints.** Look for export caps, curtailment signals, grid events, and clipping. Missing grid data must be reported as an unchecked possibility, not as evidence that curtailment did not occur.
6. **Look up equipment faults.** Match fault codes to versioned, approved manuals or vendor references. Return the exact source and passage; do not infer a code meaning when no reliable reference is available.
7. **Search maintenance history.** Retrieve relevant tickets by equipment, symptom, and time. Cite ticket IDs and dates; treat old or unresolved tickets as context, not proof of the current fault.
8. **Rank causes and decide whether to stop.** Consider inverter fault, soiling, shading, curtailment, sensor fault, weather, and unknown/other. Prefer `unknown` over a forced diagnosis when evidence is insufficient or competing causes cannot be separated.

Checks may be skipped when their required inputs are absent or earlier evidence makes them irrelevant. Each skip records its reason. The MVP caps tool calls and elapsed investigation time; hitting a limit returns the partial findings and remaining gaps rather than continuing indefinitely.

## Report contract

Each investigation returns a structured result and a human-readable summary containing:

- Plant, affected equipment if known, alert interval, and measured shortfall.
- Status: `investigating`, `completed`, `unknown`, or `insufficient_data`.
- Ranked likely cause(s), or an explicit unknown result.
- Confidence label (`low`, `medium`, or `high`) and the evidence rubric used. Do not present uncalibrated numeric probabilities as statistical certainty.
- Evidence items with source type, source ID, time range, observation/calculation, and a reference that a reviewer can open.
- Conflicting evidence, missing inputs, checks not run, and assumptions.
- A draft work order with proposed equipment, symptom, supporting evidence, and suggested inspection only when justified. It must be visibly marked as a draft and require approval.
- Investigation trace: checks run, checks skipped with reasons, and the basis for the final conclusion.

The narrative is generated from the structured result, not used as the record of truth. A report must not cite material that was not retrieved during that investigation.

## Data and evaluation strategy

No known public dataset is assumed to link real plant root causes to maintenance tickets and equipment manuals. Public sources can help exercise parts of the pipeline, but must not be represented as providing that missing ground truth.

Candidate public inputs to assess for the prototype:

- **NREL PVDAQ** for measured PV system performance, subject to dataset-specific coverage, access terms, and metadata.
- **NREL NSRDB** for solar irradiance and weather data; it does not establish equipment faults or ticket-confirmed causes.
- Public manufacturer documentation, where access and redistribution terms permit, for demonstrating citation-backed fault-code lookup.

The first end-to-end demo should use a documented synthetic plant dataset if public data cannot provide compatible, sufficiently granular plant and inverter telemetry. Generate normal production and weather series, then inject labeled scenarios such as one inverter derating, plant-wide soiling, a shading-like localized/time-dependent loss, export curtailment, irradiance sensor bias, and an ambiguous/no-fault case. Keep scenario labels and injection parameters separate from the agent's input so evaluation does not leak the answer. Include missing, stale, and contradictory data variants.

Evaluate on held-out scenarios and time windows. Measure cause-level precision/recall, `unknown` behavior, evidence citation validity, data-quality detection, work-order appropriateness, and investigation cost/latency. Report per-cause results and confusion cases, not only aggregate accuracy. Synthetic success demonstrates that the workflow operates mechanically; it does not show that the agent diagnoses real plants well. Real-world effectiveness requires shadow-mode evaluation against engineer-reviewed incidents before operational use.

## Guardrails and human review

- All data connectors are read-only in the MVP. No write-capable equipment, ticketing, or dispatch tools are registered.
- Validate tool arguments, plant authorization, time ranges, result sizes, and source identifiers. Enforce per-investigation call and time limits.
- Treat tickets, manuals, telemetry text, and other retrieved content as untrusted input. Retrieved instructions cannot change tool permissions or system behavior.
- Do not fill missing measurements with model-generated values. Label estimates and derived values, and retain units and transformations.
- Separate correlation from causation. The report uses “consistent with” or “likely” unless evidence supports a stronger statement.
- Require human approval before a work order is submitted or any operational action is taken. The agent itself has no such action path.
- Keep an audit record of inputs, source versions, tool calls, model/version, output, and reviewer decisions subject to retention policy.

## Engineering design

Suggested MVP components:

- **Alert/API layer:** accepts an alert or engineer-initiated investigation and returns a run ID and report.
- **Data adapters:** normalize plant telemetry, weather, grid/export, asset metadata, fault events, manuals, and tickets into timestamped, typed records. Adapters report coverage and provenance.
- **Deterministic analysis tools:** compute shortfall, data-quality checks, peer comparisons, and rule-based indicators. Unit-test these independently of the LLM.
- **Document retrieval:** search only approved manuals and ticket stores; return snippets with stable source IDs and locations.
- **Investigation orchestrator:** manages state, hypothesis updates, tool selection, budgets, stopping criteria, and structured report validation.
- **Report/review surface:** exposes findings, evidence, gaps, trace, and draft work order for engineer review.

Keep the tool interface provider-neutral and the analysis logic independent of prompts. Store timestamps in UTC, retain original units and raw-source references, and make all derived calculations reproducible. A small single-service implementation is sufficient for the prototype; split services only when deployment, access control, or workload requires it.

## Technology choices

Proposed prototype stack, subject to the repository and deployment environment:

- Python for data adapters, analysis, and orchestration.
- Pandas or Polars for time-series processing, chosen after checking expected data volume.
- Pydantic models for validated tool inputs, outputs, and report schema.
- DuckDB and Parquet for local synthetic-data experiments; use the plant's approved database/object store for production data rather than copying sensitive records unnecessarily.
- A provider-neutral LLM client for bounded planning and report synthesis; keep calculations and cause checks in tested Python functions.
- FastAPI only if an HTTP interface is needed; the first demo can use a command-line entry point if that better fits the project.

Do not add a vector database, agent framework, or multi-agent architecture until a concrete retrieval or deployment need justifies it. For a small manual/ticket corpus, a conventional indexed search may be enough.

## Observability and operations

Emit one correlated investigation trace with alert/run ID, tool name, duration, input/output validation status, source references, retry/error status, and token usage. Record hypothesis changes and stopping reasons. Track runs by outcome and cause, including unknown/insufficient-data rates, source coverage, citation validity, latency, tool failures, and reviewer agreement. Avoid logging credentials or unrestricted raw telemetry; apply access controls and retention limits to traces and reports.

Alert on connector failures, schema/unit changes, repeated missing sources, invalid report citations, budget exhaustion, and unusual changes in unknown rate. Model or prompt changes require regression evaluation on the fixed scenario suite before release.

## Cost controls

Use deterministic calculations and ordinary search before calling the LLM. Pass only relevant aggregates and retrieved excerpts, cap investigation steps and context size, and stop when the evidence threshold or budget is reached. Cache versioned manual retrieval and reusable weather data where permitted. Track cost per investigation alongside latency and evidence quality; do not optimize cost by dropping checks required for a defensible conclusion.

## Data handling

Plant telemetry, asset inventories, maintenance records, and operational schedules may be commercially sensitive. Use synthetic data by default in development. For real data, use least-privilege credentials, plant-level access controls, encryption in transit and at rest, and approved storage and model-processing locations. Do not send real tickets or telemetry to an external model unless the data owner has approved that processing path. Minimize retained raw data, define retention/deletion rules, and redact personal information from tickets where it is not needed for diagnosis.

## Risks and open questions

- **Expected-production baseline quality:** confirm how expected energy is calculated and whether its assumptions and uncertainty are available to the agent.
- **Data integration:** identify actual telemetry formats, sampling rates, asset hierarchy, units, and connector permissions.
- **Confounding causes:** soiling, shading, equipment degradation, and sensor bias can produce similar patterns; some diagnoses need site inspection.
- **Coverage bias:** public and synthetic datasets may not reflect the target fleet, climates, equipment, or operational practices.
- **Confidence calibration:** confidence labels must be calibrated against engineer-reviewed incidents before being used for prioritization.
- **Operational acceptance:** define who reviews reports, what evidence is enough for a site visit, and how engineer feedback is recorded.

The prototype is successful when it produces reproducible calculations and source-grounded reports on the scenario suite, correctly abstains on ambiguous or insufficient data, and never initiates an operational action. Production readiness is a separate decision requiring shadow-mode evidence from real incidents.

