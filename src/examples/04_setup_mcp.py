#!/usr/bin/env python3
"""
Example 04 — Deploy a scenario as an MCP tool and print the MCP config block.

MCP (Model Context Protocol) lets AI assistants like Claude call your Make
scenarios as native tools. To qualify, a scenario must be:
  1. Scheduled as "on-demand"
  2. Active
  3. Have explicitly defined inputs and outputs

Usage:
    export MAKE_API_TOKEN="your-token"
    export MAKE_ZONE="eu1.make.com"
    export MAKE_TEAM_ID="123"
    export MAKE_MCP_TOKEN="your-mcp-token"
    python 04_setup_mcp.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient, MakeDeployer

MAKE_API_TOKEN = os.environ["MAKE_API_TOKEN"]
MAKE_ZONE = os.environ.get("MAKE_ZONE", "eu1.make.com")
MAKE_TEAM_ID = int(os.environ["MAKE_TEAM_ID"])
MAKE_MCP_TOKEN = os.environ.get("MAKE_MCP_TOKEN", "<YOUR_MCP_TOKEN>")

client = MakeClient(MAKE_API_TOKEN, MAKE_ZONE, MAKE_TEAM_ID)
deployer = MakeDeployer(client)

# Load blueprint
blueprint_path = Path(__file__).parent.parent / "blueprints" / "basic_webhook.json"
blueprint = json.loads(blueprint_path.read_text())
blueprint["name"] = "Customer Search Tool"

# Define typed I/O for MCP exposure
inputs = [
    {"name": "query",  "label": "Search Query",   "type": "text",  "required": True},
    {"name": "limit",  "label": "Result Limit",   "type": "number","required": False},
]
outputs = [
    {"name": "results", "label": "Search Results", "type": "text"},
    {"name": "count",   "label": "Total Count",    "type": "number"},
]

scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs, activate=True)
print(f"MCP tool live at scenario: {scenario_id}")

# Print Claude Desktop / Claude Code MCP config
mcp_url = f"https://{MAKE_ZONE}/mcp/u/{MAKE_MCP_TOKEN}/sse"
mcp_config = {
    "mcpServers": {
        "make": {
            "command": "npx",
            "args": ["-y", "mcp-remote", mcp_url],
        }
    }
}
print("\n--- Add this to your Claude Desktop / Claude Code config ---")
print(json.dumps(mcp_config, indent=2))
print("------------------------------------------------------------")
print("Your Make scenarios are now callable as AI tools!")
