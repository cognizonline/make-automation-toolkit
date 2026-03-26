#!/usr/bin/env python3
"""Validate a Make.com blueprint JSON file against the schema."""
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parent / "blueprints" / "schema.json"


def validate(blueprint_path: str) -> bool:
    schema = json.loads(SCHEMA_PATH.read_text())
    blueprint = json.loads(Path(blueprint_path).read_text())
    try:
        jsonschema.validate(blueprint, schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"INVALID: {e.message} at {list(e.path)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_blueprint.py <path>")
        sys.exit(1)
    ok = validate(sys.argv[1])
    sys.exit(0 if ok else 1)
