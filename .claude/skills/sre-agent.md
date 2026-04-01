---
name: sre-agent
description: "Use this skill to interact with the PagerDuty Advance SRE Agent for incident response, troubleshooting, runbook generation, log search. Invoke when the user asks about incidents, triage, root cause analysis, or operational issues."
user-invocable: true
argument-hint: "[incident_id] [your question]"
---

# PagerDuty Advance SRE Agent

Use the PagerDuty Advance MCP Server to call the `sre_agent_tool` for incident response and technical troubleshooting.

## Prerequisites

This skill requires the `pagerduty-advance-mcp` MCP server to be configured. If it is not already set up, tell the user to add the following to their MCP configuration:

**For Claude Code** (`~/.claude.json` under `mcpServers`):
```json
{
  "pagerduty-advance-mcp": {
    "type": "http",
    "url": "https://mcp.pagerduty.com/pagerduty-advance-mcp",
    "headers": {
      "Authorization": "Token token=<your-pagerduty-api-key>"
    }
  }
}
```

**For VS Code / MCP-compatible clients** (`mcp.json`):
```json
{
  "servers": {
    "pagerduty-advance-mcp": {
      "url": "https://mcp.pagerduty.com/pagerduty-advance-mcp",
      "headers": {
        "Authorization": "Token token=${input:pagerduty-api-key}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "pagerduty-api-key",
      "description": "PagerDuty API Key",
      "password": true
    }
  ]
}
```

## Workflow

1. Parse `$ARGUMENTS` to extract the incident ID and question. The first argument should be the PagerDuty incident ID (e.g., `Q1FHWIKLRMPEI0`), and the rest is the question. If no arguments were provided, ask the user for both the incident ID and their question.

2. Call the `sre_agent_tool` from the `pagerduty-advance-mcp` MCP server with:
   - `message`: the user's natural language question
   - `incident_id`: the PagerDuty incident ID

3. Present the response to the user clearly.

4. If the user has follow-up questions, continue calling `sre_agent_tool` with the same `incident_id` and a new `message`. Pass the `session_id` from the previous response to maintain conversation continuity.

## Tool Details

- **Tool name:** `sre_agent_tool`
- **MCP Server:** `pagerduty-advance-mcp`
- **Parameters:**
  - `message` (string, required) -- the user's natural language question
  - `incident_id` (string, required) -- the PagerDuty incident ID
  - `session_id` (string, optional) -- session ID for conversation continuity; reuse from previous response

## What the SRE Agent Can Help With

- Active incident analysis, triage, and resolution
- Root cause analysis and technical explanations
- Incident summaries and catch-ups ("What happened?", "Catch me up")
- Status updates for stakeholders
- Diagnostic checks and remediation recommendations
- Log interpretation and troubleshooting guidance
- Alert trigger analysis and explanations
- Change event analysis and impact assessment
- Playbook and runbook generation
- Past incident correlation and pattern recognition
- Service dependencies and related system analysis
- Customer communication and status page updates

## Example Invocations

```
/sre-agent Q1FHWIKLRMPEI0 What should I do next to triage this incident?
/sre-agent Q1FHWIKLRMPEI0 What is the root cause? What changed recently?
/sre-agent Q1FHWIKLRMPEI0 Catch me up on what happened so far.
/sre-agent Q1FHWIKLRMPEI0 Generate a runbook for resolving this type of incident.
/sre-agent Q1FHWIKLRMPEI0 Have we seen similar incidents before?
```
