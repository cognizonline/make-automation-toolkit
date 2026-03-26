#!/usr/bin/env python3
"""
Example 05 — Full-stack deployment: customer onboarding automation.

Deploys in order:
  1. Customer data structure + store
  2. Welcome email scenario (webhook-triggered)
  3. CRM sync scenario (on-demand / MCP tool)
  4. AI Agent that orchestrates both
  5. Prints summary of all deployed resources

Usage:
    export MAKE_API_TOKEN="your-token"
    export MAKE_ZONE="eu1.make.com"
    export MAKE_TEAM_ID="123"
    python 05_full_deployment.py
"""


import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient, MakeDeployer

MAKE_API_TOKEN = os.environ["MAKE_API_TOKEN"]
MAKE_ZONE = os.environ.get("MAKE_ZONE", "eu1.make.com")
MAKE_TEAM_ID = int(os.environ["MAKE_TEAM_ID"])

client = MakeClient(MAKE_API_TOKEN, MAKE_ZONE, MAKE_TEAM_ID)
deployer = MakeDeployer(client)

resources: dict = {}

# ── Step 1: Data layer ──────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Deploying data layer")
print("=" * 60)

structure_spec = [
    {"name": "email",       "type": "email",  "label": "Email",       "required": True},
    {"name": "first_name",  "type": "text",   "label": "First Name",  "required": True},
    {"name": "last_name",   "type": "text",   "label": "Last Name",   "required": False},
    {"name": "plan",        "type": "text",   "label": "Plan",        "required": False},
    {"name": "created_at",  "type": "date",   "label": "Created At",  "required": False},
]

structure_id = client.create_data_structure("Onboarding Records", structure_spec)
store_id = client.create_data_store("Onboarding Store", structure_id, max_size_mb=50)
resources["structure_id"] = structure_id
resources["store_id"] = store_id
print(f"  structure_id={structure_id}, store_id={store_id}")

# ── Step 2: Welcome email scenario ──────────────────────────────────────────
print("\nSTEP 2: Deploying welcome email scenario")
print("=" * 60)

welcome_blueprint = {
    "name": "Customer Onboarding — Welcome Email",
    "flow": [
        {"id": 1, "module": "gateway:CustomWebhook", "version": 1,
         "parameters": {}, "mapper": {},
         "metadata": {"designer": {"x": 0, "y": 0}}},
        {"id": 2, "module": "email:ActionSendEmail", "version": 1,
         "mapper": {
             "to": "{{1.email}}",
             "subject": "Welcome to the platform, {{1.first_name}}!",
             "html": "<h1>Welcome {{1.first_name}}!</h1><p>You're on the {{1.plan}} plan.</p>",
         },
         "metadata": {"designer": {"x": 300, "y": 0}}},
    ],
    "metadata": {
        "version": 1,
        "scenario": {"roundtrips": 1, "maxErrors": 3, "autoCommit": True,
                     "autoCommitTriggerLast": True, "sequential": False,
                     "confidential": False, "dataloss": False, "dlq": False}
    }
}

hook = client.create_hook("Onboarding Webhook")
welcome_id = client.create_scenario(
    welcome_blueprint,
    scheduling={"type": "indefinitely", "interval": 0},
)
client.activate_scenario(welcome_id)
resources["welcome_scenario_id"] = welcome_id
resources["webhook_url"] = hook.get("url")
print(f"  scenario_id={welcome_id}")
print(f"  webhook_url={hook.get('url')}")

# ── Step 3: CRM sync as MCP tool ────────────────────────────────────────────
print("\nSTEP 3: Deploying CRM sync as MCP tool")
print("=" * 60)

crm_blueprint = {
    "name": "CRM Sync — Upsert Contact",
    "flow": [
        {"id": 1, "module": "gateway:CustomWebhook", "version": 1,
         "parameters": {}, "mapper": {},
         "metadata": {"designer": {"x": 0, "y": 0}}},
        {"id": 2, "module": "http:ActionSendData", "version": 3,
         "mapper": {
             "url": "https://crm.example.com/api/contacts",
             "method": "POST",
             "bodyType": "raw",
             "contentType": "application/json",
             "body": "{{toJSON(1)}}",
         },
         "metadata": {"designer": {"x": 300, "y": 0}}},
    ],
    "metadata": {
        "version": 1,
        "scenario": {"roundtrips": 1, "maxErrors": 3, "autoCommit": True,
                     "autoCommitTriggerLast": True, "sequential": False,
                     "confidential": False, "dataloss": False, "dlq": False}
    }
}

crm_inputs = [
    {"name": "email",      "label": "Email",      "type": "email",  "required": True},
    {"name": "first_name", "label": "First Name", "type": "text",   "required": True},
    {"name": "plan",       "label": "Plan",       "type": "text",   "required": False},
]
crm_outputs = [
    {"name": "contact_id", "label": "CRM Contact ID", "type": "text"},
    {"name": "status",     "label": "Sync Status",    "type": "text"},
]

crm_id = deployer.deploy_mcp_tool(crm_blueprint, crm_inputs, crm_outputs, activate=True)
resources["crm_scenario_id"] = crm_id
print(f"  scenario_id={crm_id} (MCP tool active)")

# ── Final summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("DEPLOYMENT COMPLETE")
print("=" * 60)
for k, v in resources.items():
    print(f"  {k}: {v}")

print(f"""
Next steps:
  1. Send a test webhook:
     curl -X POST '{resources.get("webhook_url")}' \\
       -H 'Content-Type: application/json' \\
       -d '{{"email":"test@example.com","first_name":"Alice","plan":"pro"}}'

  2. Add the CRM sync scenario to your MCP config so AI agents
     can call 'CRM Sync — Upsert Contact' as a tool.
""")
