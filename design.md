# Problem:
If a power plant output drops, under performs or some problem happen then an Engineer has to manually check the logs, inverter, weather, equipment. This manual process may take days. An agent is developed that does the whole analysis, create a report. 

# Architect:
Following is a the design flow of how this agentic system would work.

- System receives an alert
- Starts investigation by using tools
    - checks weather
    - missing grid data
    - equipment failure
    - Cause of fault
        unknown fault
    - Stops checks may be skipped when their required inputs are absent or earlier evidence makes them irrelevant. 

## Create a report 
    report output:
        - Status: `investigating`, `completed`, `unknown`, or `insufficient_data`.
        - Conflicting evidence, missing inputs, checks not run, and assumptions.
        - report must  cite 

# Agent Design:
- Single Agent
- Max loop iteration
    - prototype: 5
    - in production should depends on investigation ?
- Agent Pattern Re-Act? 
    - I am using bounded ReAct-style loop because the agent can choose targeted telemetry queries as evidence emerges, without the extra planning step and overhead of a planner–executor design.
- Memory: investigation specific include alert, status, tool results, timestamp,  failures, compact summary and report. It is needed because what if Faragate crashses, or job is retried. For large telemetry records S3 and for status, compact summaries, and reports in PostgreSQL

# endpoint
POST /alerts/{alert_id}/diagnoses 
    returns the diagnosis id
GET  /diagnoses/{diagnosis_id}
GET  /diagnoses/{diagnosis_id}/report
POST /diagnoses/{diagnosis_id}/cancel

# Flow
- when a POST diagnose/<alert-id> request arrives it reaches ->
- API Gateway: rate limiting, throttling, verify API keys, validate OAuth ->
- FastAPI on lambda: data validation using Pydantic + advance authentication ->
- SQS: to handle request synchronously ->
- trigger mechanism lambda/eventbridge/step function->
    - event bridge is good for scheduled jobs
    - lambda function is when we need pre check
    - step function: High-reliability industrial pipelines where you need  built-in retry logic, state tracking, and failure notifications for - multi-step AI reasoning.
- Fargate
    run the agent
- S3
    store the diagnostic report
- Email notification
    email notification send to plant manager
    
# Engineering Design
why agent why not a script/set of rules?

## Latency 
    - p50, p95, and p99
    - alert-to-accepted latency - 1 sec p95 why?
    - alert-to-report-ready - 30 - 20 minutes -why?
        depends on:
            queue wait time  
            gemini call
            telemetry calls
    initail req -> response
## Throughput
    aws bedrock?
    load test
## Cloud?
-    aws strand? 
-    lambda? 
-    Faragate:Fargate should be used because our diagnostic data may need to run more than 15 minutes. It is higher in cost compare to lambda I plan to start Fargate when needed and shut it down. However Fargate is still serverless.
## LLM model? cost, latency, and tool-calling accuracy
How do you give the model the right context from time-series data without blowing up the context window? Did you pre-aggregate, summarize, or let the agent query ranges?

-## Evaluate the agent? 
-    The goal was to avoid the wrong diagnosis. especially confident but unsupported root cause.
-    past alert | same data/telemetry | same tool |root cause (unknown,insufficient_data)
-    Tool quality is not just measured on right root cause but on tool use quality too. If a alert cause unkownn but tools were not called that could be a problem. 
-    Failure rate, especially F1 macros(), report per cause
-    For eg: take 100 historical incident
-    tool recall? incorrect tool call, unnecessary tool call
-    faithfulness: is the root cause support by tool output
-    Validation with Engineer
-    diagnosis accuracy

## How did you test regressions when changing prompts, tools, or models?
    I would maintain a versioned, engineer-labeled incident set and retest it whenever prompts, tools, or models change. Compare diagnosis accuracy, tool-use quality, evidence grounding, abstention behavior, latency, and cost against the current baseline; Also, investigate regressions with engineer review before release.

## observability?
    cloudwatch
    Xray
    AWS Distro for OpenTelemtry
    each investigation has correlation id i.e investigation_id

release new?

## baseline of agent?
cost?
duplicate alerts, or concurrent investigations?
    idempotency
    concurrent investigation
        multiple Faragate worker -> autoscaling
        how many concurrent Faragate worker?
what if agent is wrong?
8. Reflection

What would you do differently?
What limitations does it still have?
What would you build next (auto-remediation, ticket creation, learning from past incidents, multi-plant correlation)?
If you had to scale this to 10x more plants, what breaks first?


