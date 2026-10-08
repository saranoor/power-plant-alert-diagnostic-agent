# Problem:
If a power plant output drops, under performs or some problem happen then an Engineer has to manually check the logs, inverter, weather, equipment. This manual process may take days. An agent is developed that does the whole analysis, create a report. 

# Architect:
Following is a the design flow of how this agentic system would work.

The system reads the logs
Based upon logs it creates an alert
Starts investigation
    checks weather
    missing grid data
    equipment failure
    Cause of fault
        unknown fault
    Stops checks may be skipped when their required inputs are absent or earlier evidence makes them irrelevant. 

Create a report 
    report output:
        - Status: `investigating`, `completed`, `unknown`, or `insufficient_data`.
        - Conflicting evidence, missing inputs, checks not run, and assumptions.
        - report must not cite 

# Engineering Design

# Tech Stack