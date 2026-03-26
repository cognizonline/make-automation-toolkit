#!/usr/bin/env python3
"""
Example 01 — Deploy a scenario from a blueprint file.

Usage:
    export MAKE_API_TOKEN="your-token"
    export MAKE_ZONE="eu1.make.com"
    export MAKE_TEAM_ID="123"
    python 01_deploy_scenario.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient

MAKE_API_TOKEN = os.environ["MAKE_API_TOKEN"]
MAKE_ZONE = os.environ.get("MAKE_ZONE", "eu1.make.com")
MAKE_TEAM_ID = int(os.environ["MAKE_TEAM_ID"])

client = MakeClient(MAKE_API_TOKEN, MAKE_ZONE, MAKE_TEAM_ID)

# Load blueprint from file
blueprint_path = Path(__file__).parent.parent / "blueprints" / "basic_webhook.json"
blueprint = json.loads(blueprint_path.read_text())

# Deploy
scenario_id = client.create_scenario(
    blueprint=blueprint,
    scheduling={"type": "indefinitely", "interval": 900},
)
print(f"Created scenario: {scenario_id}")

# Activate it
client.activate_scenario(scenario_id)
print(f"Scenario {scenario_id} is now active.")

# Retrieve and print details
details = client.get_scenario(scenario_id)
print(f"Name: {details.get('name')}")
print(f"Status: {'active' if details.get('isActive') else 'inactive'}")
