#!/usr/bin/env python3
"""
Example 08 — MCP Toolbox: wrap a multi-step scenario as a single governed tool
===============================================================================

MCP Toolboxes are team-level curated collections of Make scenarios exposed as
MCP tools to external AI clients (Claude, Cursor, ChatGPT).

They solve a core problem with raw MCP connections:
  - Raw MCP: AI sees every API surface, must infer multi-step workflows,
    wastes tokens, and has no access control
  - MCP Toolbox: AI sees exactly the tools you publish, each backed by a
    deterministic Make scenario that executes the full workflow internally

This example demonstrates the recommended design pattern:
  Instead of exposing 5 separate tools (validate_customer, create_contact,
  associate_company, create_deal, send_notification), expose ONE tool:
  "onboard_customer" — Make runs the full sequence internally.

The result:
  - The LLM makes one tool call instead of five
  - Business logic lives in Make, not in the LLM's reasoning
  - Credentials never leave Make
  - Every call is logged in the Toolbox audit trail

What this example does:
  1. Deploys the multi-step "Onboard Customer" scenario
  2. Sets its interface (inputs/outputs) so it appears as an MCP tool
  3. Activates it
  4. Prints the Toolbox configuration instructions

Prerequisites:
  - A Make.com API token (set as MAKE_API_TOKEN in .env or environment)
  - A team ID (set as MAKE_TEAM_ID)
  - A CRM connection ID (set as MAKE_CRM_CONNECTION_ID)
  - A notification webhook URL (set as MAKE_NOTIFY_WEBHOOK)
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
CRM_CONNECTION_ID = int(os.getenv("MAKE_CRM_CONNECTION_ID", "0"))
NOTIFY_WEBHOOK = os.getenv("MAKE_NOTIFY_WEBHOOK", "https://hook.eu1.make.com/your-webhook")

# ---------------------------------------------------------------------------
# The blueprint for the "Onboard Customer" scenario.
#
# This is the KEY pattern for MCP Toolboxes:
#   One tool call from the AI → Make executes a complete, deterministic workflow
#
# The scenario has 4 modules chained linearly (the OLD pattern is correct here —
# this is a fixed workflow, not an agent loop):
#   1. Webhook trigger — receives the tool input from the MCP call
#   2. HubSpot — create/update contact
#   3. HubSpot — create deal and associate to contact
#   4. HTTP — post notification to Slack/Teams
#
# The LLM never sees these steps. It only sees: "onboard_customer(name, email, company, deal_value)"
# ---------------------------------------------------------------------------

ONBOARD_CUSTOMER_BLUEPRINT = {
    "name": "Onboard Customer",
    "flow": [
        # Module 1: Webhook trigger — receives input from the MCP tool call
        {
            "id": 1,
            "module": "gateway:CustomWebHook",
            "version": 1,
            "parameters": {"hook": 0},  # replace with real webhook ID after creation
            "mapper": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        },
        # Module 2: Create/update CRM contact
        {
            "id": 2,
            "module": "hubspot:ActionCreateContact",
            "version": 1,
            "parameters": {"accountId": CRM_CONNECTION_ID},
            "mapper": {
                "email":     "{{1.email}}",
                "firstname": "{{1.name}}",
                "company":   "{{1.company}}",
            },
            "metadata": {"designer": {"x": 200, "y": 0}},
        },
        # Module 3: Create deal linked to contact
        {
            "id": 3,
            "module": "hubspot:ActionCreateDeal",
            "version": 1,
            "parameters": {"accountId": CRM_CONNECTION_ID},
            "mapper": {
                "dealname":  "New Business — {{1.company}}",
                "amount":    "{{1.deal_value}}",
                "pipeline":  "default",
                "dealstage": "appointmentscheduled",
                "associations": [{"objectType": "contact", "id": "{{2.id}}"}],
            },
            "metadata": {"designer": {"x": 400, "y": 0}},
        },
        # Module 4: Post notification
        {
            "id": 4,
            "module": "http:ActionSendData",
            "version": 3,
            "parameters": {},
            "mapper": {
                "url":         NOTIFY_WEBHOOK,
                "method":      "POST",
                "bodyType":    "raw",
                "contentType": "application/json",
                "body": (
                    '{"text": "New customer onboarded: {{1.name}} ({{1.company}})'
                    ' — Deal: ${{1.deal_value}} — CRM contact {{2.id}}, deal {{3.id}}"}'
                ),
            },
            "metadata": {"designer": {"x": 600, "y": 0}},
        },
    ],
    "metadata": {"version": 1},
}

# ---------------------------------------------------------------------------
# MCP tool interface — what the AI client sees
#
# The AI sees ONLY these inputs and outputs.
# It has no visibility into the 4-module chain above.
# This is the governance boundary.
# ---------------------------------------------------------------------------

TOOL_INPUTS = [
    {"name": "name",       "label": "Customer full name",   "type": "text",   "required": True},
    {"name": "email",      "label": "Customer email",       "type": "email",  "required": True},
    {"name": "company",    "label": "Company name",         "type": "text",   "required": True},
    {"name": "deal_value", "label": "Estimated deal value (USD)", "type": "number", "required": False},
]

TOOL_OUTPUTS = [
    {"name": "contact_id", "label": "CRM Contact ID", "type": "text"},
    {"name": "deal_id",    "label": "CRM Deal ID",    "type": "text"},
    {"name": "status",     "label": "Status",         "type": "text"},
]


def main():
    client = MakeClient(api_token=API_TOKEN, zone=ZONE, team_id=TEAM_ID)
    deployer = MakeDeployer(client)

    print("Deploying 'Onboard Customer' as a single MCP Toolbox tool...")
    print()
    print("Pattern: 4-module scenario → 1 tool call from the AI")
    print("The AI calls onboard_customer(name, email, company, deal_value)")
    print("Make executes: create contact → create deal → notify")
    print()

    scenario_id = deployer.deploy_mcp_tool(
        blueprint=ONBOARD_CUSTOMER_BLUEPRINT,
        inputs=TOOL_INPUTS,
        outputs=TOOL_OUTPUTS,
        activate=True,
    )

    print(f"Deployed and activated. Scenario ID: {scenario_id}")
    print()
    print("=" * 60)
    print("NEXT STEPS — Configure your MCP Toolbox in Make:")
    print("=" * 60)
    print()
    print("1. In Make, go to: Left sidebar > MCP Toolboxes > Create toolbox")
    print(f"2. Add this scenario (ID {scenario_id}) as a tool")
    print("3. Label it: 'Onboard Customer'")
    print("4. Set access: read-and-write (it creates CRM records)")
    print("5. Click Create — copy and save the access key shown")
    print("6. Copy the unique Toolbox server URL")
    print()
    print("Connect Claude Code (.claude/settings.json):")
    print("""
{
  "mcpServers": {
    "make-crm": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<YOUR_TOOLBOX_URL>/sse"],
      "env": {
        "MCP_TOKEN": "<YOUR_TOOLBOX_KEY>"
      }
    }
  }
}
""")
    print("Claude can now call: onboard_customer(name=..., email=..., company=...)")
    print("Every call is logged in the Toolbox audit trail.")
    print()
    print("Governance notes:")
    print("  - Claude never touches your CRM credentials directly")
    print("  - Read-only tools (lookups, searches) vs read-write (this one) are separate")
    print("  - Generate a separate Toolbox key for each AI client or team")
    print("  - Revoke a key without affecting other clients or the scenario itself")


if __name__ == "__main__":
    main()
