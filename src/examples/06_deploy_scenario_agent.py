#!/usr/bin/env python3
"""
Example 06 — Deploy a scenario-embedded AI Agent
=================================================

This example demonstrates the NEW Make AI Agent pattern:
  - The entire scenario is a single module: ai-local-agent:RunLocalAIAgent
  - Tools are defined as inline flow[] arrays INSIDE that module
  - The LLM decides which tools to call at runtime (not a fixed chain)
  - Contrast with the OLD pattern: multiple modules wired linearly in a scenario

The agent in this example can:
  1. Search the web for information (web_search tool)
  2. Write results to a Make data store (datastore_write tool)

Prerequisites:
  - A Make.com API token (set as MAKE_API_TOKEN in .env or environment)
  - A team ID (set as MAKE_TEAM_ID)
  - A data store already created (set its ID as MAKE_DATA_STORE_ID)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running from the repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient, MakeDeployer  # noqa: E402

load_dotenv()

API_TOKEN = os.environ["MAKE_API_TOKEN"]
ZONE = os.getenv("MAKE_ZONE", "eu1.make.com")
TEAM_ID = int(os.environ["MAKE_TEAM_ID"])
DATA_STORE_ID = int(os.environ["MAKE_DATA_STORE_ID"])

# ---------------------------------------------------------------------------
# Define the tools the agent can use.
#
# Each tool has:
#   name        — identifier the LLM uses when calling the tool
#   description — natural-language hint; the LLM reads this to decide WHEN
#                 to call the tool
#   flow        — a list of Make modules, exactly like a scenario's flow[]
#
# This is fundamentally different from the old linear-chain pattern.
# In the old pattern you would chain these modules directly in the scenario
# flow and they would always execute in order. Here, the LLM decides:
#   - Whether to call a tool at all
#   - How many times to call it
#   - In what order relative to other tools
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information on a topic. "
            "Input: query (string). "
            "Returns a JSON response with search results including title, url, and snippet fields."
        ),
        "flow": [
            {
                "id": 10,
                "module": "http:ActionSendData",
                "version": 3,
                "mapper": {
                    "url": "https://api.search.example.com/v1/search",
                    "method": "GET",
                    "qs": [
                        {"key": "q", "value": "{{parameters.query}}"},
                        {"key": "limit", "value": "5"},
                    ],
                    "headers": [
                        {"key": "Accept", "value": "application/json"},
                    ],
                    "bodyType": "raw",
                    "contentType": "application/json",
                    "parseResponse": True,
                },
                "parameters": {},
                "metadata": {"designer": {"x": 0, "y": 0}},
            }
        ],
    },
    {
        "name": "datastore_write",
        "description": (
            "Write a key-value record to the team data store for later retrieval. "
            "Input: key (string, unique identifier), value (string, content to store). "
            "Use this to persist information the user wants saved."
        ),
        "flow": [
            {
                "id": 20,
                # datastore:AddRecord — the standard Make data store write module
                "module": "datastore:AddRecord",
                "version": 1,
                "mapper": {
                    "dataStoreId": DATA_STORE_ID,
                    "key": "{{parameters.key}}",
                    "data": {
                        "value": "{{parameters.value}}",
                    },
                },
                "parameters": {},
                "metadata": {"designer": {"x": 0, "y": 150}},
            }
        ],
    },
]

SYSTEM_PROMPT = """\
You are a research assistant with access to two tools:
- web_search: find current information on any topic
- datastore_write: persist information the user explicitly asks to save

When answering questions:
1. Use web_search to find accurate, current information.
2. Summarise findings clearly.
3. Only call datastore_write if the user asks you to save or remember something.

Be concise. Cite sources when possible.\
"""


def main():
    client = MakeClient(api_token=API_TOKEN, zone=ZONE, team_id=TEAM_ID)
    deployer = MakeDeployer(client)

    print("Deploying scenario-embedded AI agent...")
    print("(This creates ONE scenario with ONE module: ai-local-agent:RunLocalAIAgent)")
    print()

    scenario_id = deployer.deploy_scenario_agent(
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        model="large",           # "large" | "medium" | "small"
        reasoning_effort="low",  # only valid value currently
        recursion_limit=50,      # max LLM tool-call iterations per run
        history_count=10,        # number of past conversation turns the LLM sees
        output_type="text",      # "text" | "make-schema"
        # scheduling defaults to on-demand — run via POST /scenarios/{id}/run
    )

    print()
    print(f"Deployed. Scenario ID: {scenario_id}")
    print(f"Run it on-demand:")
    print(f"  POST https://{ZONE}/api/v2/scenarios/{scenario_id}/run")
    print(f"  Body: {{\"responsive\": true, \"data\": {{\"input\": \"Your question here\"}}}}")
    print()
    print("Or trigger it from another scenario, a webhook, or a schedule.")


if __name__ == "__main__":
    main()
