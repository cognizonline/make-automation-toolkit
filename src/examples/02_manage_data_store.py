#!/usr/bin/env python3
"""
Example 02 — Create a data store and perform CRUD operations.

Usage:
    export MAKE_API_TOKEN="your-token"
    export MAKE_ZONE="eu1.make.com"
    export MAKE_TEAM_ID="123"
    python 02_manage_data_store.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.make_client import MakeClient

MAKE_API_TOKEN = os.environ["MAKE_API_TOKEN"]
MAKE_ZONE = os.environ.get("MAKE_ZONE", "eu1.make.com")
MAKE_TEAM_ID = int(os.environ["MAKE_TEAM_ID"])

client = MakeClient(MAKE_API_TOKEN, MAKE_ZONE, MAKE_TEAM_ID)

# --- 1. Define the data structure schema ---
structure_spec = [
    {"name": "customer_id", "type": "text",   "label": "Customer ID",    "required": True},
    {"name": "email",       "type": "email",  "label": "Email Address",  "required": True},
    {"name": "tier",        "type": "text",   "label": "Customer Tier",  "required": False},
    {"name": "lifetime_value", "type": "number", "label": "Lifetime Value", "required": False},
]

print("Creating data structure...")
structure_id = client.create_data_structure("Customer Records", structure_spec)
print(f"  → structure_id: {structure_id}")

# --- 2. Create the data store ---
print("Creating data store...")
store_id = client.create_data_store("Customer Database", structure_id, max_size_mb=100)
print(f"  → store_id: {store_id}")

# --- 3. Insert records ---
print("Inserting records...")
for i in range(1, 4):
    client.add_record(store_id, {
        "customer_id": f"CUST-{i:03d}",
        "email": f"customer{i}@example.com",
        "tier": "standard",
        "lifetime_value": i * 1000.0,
    }, key=f"CUST-{i:03d}")
print("  → 3 records inserted")

# --- 4. List records ---
records = client.list_records(store_id)
print(f"Records in store ({len(records)}):")
for r in records:
    print(f"  {r['key']}: {r['data']}")

# --- 5. Update a record ---
client.update_record(store_id, "CUST-001", {"tier": "premium"})
print("Updated CUST-001 tier → premium")

# --- 6. Delete records ---
client.delete_records(store_id, ["CUST-003"])
print("Deleted CUST-003")
