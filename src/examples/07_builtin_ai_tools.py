#!/usr/bin/env python3
"""
Example 07 — Scenario-embedded agent using Make built-in AI modules
====================================================================

Make provides built-in AI modules that require NO external connection or API key:
  - make-ai-web-search:generateAResponse  — live web search with optional JSON output
  - make-ai-extractors:extractInvoice     — structured invoice extraction (PDF/image)
  - make-ai-extractors:extractADocument   — general document extraction with custom prompt
  - make-ai-extractors:transcribeAudio    — audio transcription with speaker diarization
  - make-ai-extractors:describeImage      — custom-prompted image description

This example deploys an accounts-payable agent that can:
  1. search_web         — find vendor or pricing information
  2. extract_invoice    — extract structured data from an uploaded invoice file
  3. save_record        — write the validated invoice to a data store

Key difference from example 06:
  - The web_search tool uses make-ai-web-search (no API key, privacy-preserving)
    instead of an external HTTP search API
  - The extract_invoice tool uses make-ai-extractors (no connection required)
    instead of calling an external OCR or LLM API

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
# Tool 1: Web search using make-ai-web-search (no API key, no connection)
#
# make-ai-web-search:generateAResponse performs a live web search and returns
# a synthesised natural-language answer. Setting parseJson: true returns a
# structured JSON object the agent can read directly.
#
# Credit cost: 1 credit per 900 tokens + 1 operation credit
# ---------------------------------------------------------------------------

TOOL_SEARCH_WEB = {
    "name": "search_web",
    "description": (
        "Search the web for current information about a vendor, invoice, or pricing. "
        "Input: query (string). "
        "Returns a synthesised answer from live web results."
    ),
    "flow": [
        {
            "id": 10,
            "module": "make-ai-web-search:generateAResponse",
            "version": 1,
            "mapper": {
                "query": "{{parameters.query}}",
                "parseJson": False,
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        }
    ],
}

# ---------------------------------------------------------------------------
# Tool 2: Invoice extraction using make-ai-extractors (no connection required)
#
# make-ai-extractors:extractInvoice is pre-trained on invoice formats and returns
# a fixed schema: invoiceNumber, invoiceDate, dueDate, vendorName, vendorAddress,
# buyerName, lineItems[], subtotal, taxRate, taxAmount, total, currency.
#
# Credit cost: 10 credits per operation
# Accepts: PDF, DOCX, and image files
# ---------------------------------------------------------------------------

TOOL_EXTRACT_INVOICE = {
    "name": "extract_invoice",
    "description": (
        "Extract structured data from an invoice file (PDF, DOCX, or image). "
        "Input: file_url (string, direct download URL to the invoice file), "
        "filename (string, e.g. 'invoice.pdf'). "
        "Returns: invoiceNumber, invoiceDate, dueDate, vendorName, lineItems[], total, currency."
    ),
    "flow": [
        # Step 1: Download the file from the provided URL
        {
            "id": 10,
            "module": "http:ActionGetFile",
            "version": 3,
            "mapper": {
                "url": "{{parameters.file_url}}",
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        },
        # Step 2: Extract structured invoice fields — no API key needed
        {
            "id": 20,
            "module": "make-ai-extractors:extractInvoice",
            "version": 1,
            "mapper": {
                "file": "{{10.data}}",
                "filename": "{{parameters.filename}}",
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 150}},
        },
    ],
}

# ---------------------------------------------------------------------------
# Tool 3: Write a validated invoice record to the data store
# ---------------------------------------------------------------------------

TOOL_SAVE_INVOICE = {
    "name": "save_invoice",
    "description": (
        "Save a validated invoice record to the accounts payable data store. "
        "Input: invoice_number (string, unique key), vendor (string), "
        "total (number), currency (string), due_date (string ISO 8601), "
        "status (string: 'pending' | 'approved' | 'needs_review'). "
        "Use this only after extract_invoice has returned a complete record."
    ),
    "flow": [
        {
            "id": 10,
            "module": "datastore:AddRecord",
            "version": 1,
            "mapper": {
                "dataStoreId": DATA_STORE_ID,
                "key": "{{parameters.invoice_number}}",
                "data": {
                    "vendor":         "{{parameters.vendor}}",
                    "total":          "{{parameters.total}}",
                    "currency":       "{{parameters.currency}}",
                    "due_date":       "{{parameters.due_date}}",
                    "status":         "{{parameters.status}}",
                },
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        }
    ],
}

TOOLS = [TOOL_SEARCH_WEB, TOOL_EXTRACT_INVOICE, TOOL_SAVE_INVOICE]

SYSTEM_PROMPT = """\
You are an accounts payable agent with access to three tools:
- search_web: look up vendor information or verify pricing on the web
- extract_invoice: extract structured data from an invoice file URL
- save_invoice: save a validated invoice to the accounts payable data store

Processing rules:
1. Always call extract_invoice first on any invoice file provided.
2. If required fields (invoiceNumber, vendorName, total, currency) are missing or null,
   set status to 'needs_review' and save with what you have.
3. If total exceeds 10000, set status to 'needs_review' for manual approval.
4. Otherwise set status to 'pending'.
5. Call save_invoice only after extraction is complete.
6. Call search_web only when you need to verify vendor details or clarify ambiguous information.
7. Always report: invoice number | vendor | total | currency | status saved.\
"""


def main():
    client = MakeClient(api_token=API_TOKEN, zone=ZONE, team_id=TEAM_ID)
    deployer = MakeDeployer(client)

    print("Deploying accounts payable agent with Make built-in AI modules...")
    print("  Tools: make-ai-web-search + make-ai-extractors + datastore")
    print("  No external API keys required.")
    print()

    scenario_id = deployer.deploy_scenario_agent(
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        model="large",
        reasoning_effort="low",
        recursion_limit=30,   # invoice processing is short — 30 steps is generous
        history_count=5,
        output_type="text",
    )

    print(f"Deployed. Scenario ID: {scenario_id}")
    print()
    print("Trigger with a file URL:")
    print(f"  POST https://{ZONE}/api/v2/scenarios/{scenario_id}/run")
    print('  Body: {"responsive": true, "data": {"input": "Process invoice at https://example.com/inv-001.pdf"}}')
    print()
    print("Built-in module credit costs per run (approximate):")
    print("  make-ai-web-search: ~1 credit per search")
    print("  make-ai-extractors:extractInvoice: 10 credits per invoice")
    print("  datastore:AddRecord: 1 operation credit")


if __name__ == "__main__":
    main()
