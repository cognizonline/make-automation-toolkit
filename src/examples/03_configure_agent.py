#!/usr/bin/env python3
"""
Example 03 — Create and run a Make AI Agent (Beta).

The agent uses two scenarios as tools:
  - order_lookup_scenario_id: called automatically (auto-run)
  - return_scenario_id: requires manual approval

Usage:
    export MAKE_API_TOKEN="your-token"
    export MAKE_ZONE="eu1.make.com"
    export MAKE_TEAM_ID="123"
    export ORDER_LOOKUP_SCENARIO_ID="456"
    export RETURN_SCENARIO_ID="789"
    python 03_configure_agent.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient

MAKE_API_TOKEN = os.environ["MAKE_API_TOKEN"]
MAKE_ZONE = os.environ.get("MAKE_ZONE", "eu1.make.com")
MAKE_TEAM_ID = int(os.environ["MAKE_TEAM_ID"])
ORDER_SCENARIO_ID = int(os.environ["ORDER_LOOKUP_SCENARIO_ID"])
RETURN_SCENARIO_ID = int(os.environ["RETURN_SCENARIO_ID"])

client = MakeClient(MAKE_API_TOKEN, MAKE_ZONE, MAKE_TEAM_ID)

agent_config = {
    "name": "Customer Support Agent",
    "systemPrompt": (
        "You are a helpful customer support assistant. "
        "You can look up order information and process returns on behalf of customers. "
        "Always confirm the customer's identity before accessing order details."
    ),
    "defaultModel": "gpt-4o-mini",
    "llmConfig": {
        "maxTokens": 2000,
        "temperature": 0.7,
        "topP": 1.0,
    },
    "invocationConfig": {
        "recursionLimit": 10,
        "timeout": 60000,
    },
    "scenarios": [
        {"makeScenarioId": ORDER_SCENARIO_ID, "approvalMode": "auto-run"},
        {"makeScenarioId": RETURN_SCENARIO_ID, "approvalMode": "manual-approval"},
    ],
    "historyConfig": {
        "iterationsFromHistoryCount": 5,
    },
    "outputParserFormat": {
        "type": "make-schema",
        "schema": [
            {"name": "response",     "type": "text", "label": "Agent Response", "required": True},
            {"name": "action_taken", "type": "text", "label": "Action Taken",   "required": False},
        ],
    },
}

print("Creating AI Agent...")
agent_id = client.create_agent(agent_config)
print(f"Agent created: {agent_id}")

# Run a test conversation
print("\nRunning test conversation...")
result = client.run_agent(
    agent_id=agent_id,
    messages=[
        {"role": "user", "content": "I need to return order #ORD-12345. Can you help?"}
    ],
    thread_id="test-thread-001",
)

print("Agent response:")
print(result)
