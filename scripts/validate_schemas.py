#!/usr/bin/env python3
"""Validate all JSON schemas in /schemas directory."""
import json
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft7Validator

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

REQUIRED_SCHEMAS = [
    "transaction.schema.json",
    "risk_result.schema.json",
    "case.schema.json",
    "analyst_label.schema.json",
    "pattern_card.schema.json",
    "metric_snapshot.schema.json",
]


def validate_schema(schema_path: Path) -> tuple[bool, str]:
    """Validate a single schema file."""
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        # Check it's valid JSON Schema
        Draft7Validator.check_schema(schema)

        # Check required fields
        if "$schema" not in schema:
            return False, "Missing $schema field"
        if "$id" not in schema:
            return False, "Missing $id field"
        if "type" not in schema:
            return False, "Missing type field"

        return True, "OK"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except jsonschema.exceptions.SchemaError as e:
        return False, f"Invalid schema: {e.message}"
    except Exception as e:
        return False, str(e)


def main() -> int:
    """Main entry point."""
    print("=" * 50)
    print("Schema Validation")
    print("=" * 50)

    if not SCHEMAS_DIR.exists():
        print(f"ERROR: Schemas directory not found: {SCHEMAS_DIR}")
        return 1

    # Check all required schemas exist
    missing = []
    for name in REQUIRED_SCHEMAS:
        if not (SCHEMAS_DIR / name).exists():
            missing.append(name)

    if missing:
        print(f"ERROR: Missing required schemas: {missing}")
        return 1

    # Validate all schemas
    errors = []
    for schema_file in sorted(SCHEMAS_DIR.glob("*.schema.json")):
        valid, msg = validate_schema(schema_file)
        status = "[OK]" if valid else "[FAIL]"
        print(f"  {status} {schema_file.name}: {msg}")
        if not valid:
            errors.append(schema_file.name)

    print("-" * 50)
    if errors:
        print(f"FAILED: {len(errors)} schema(s) invalid")
        return 1

    print(f"PASSED: All {len(REQUIRED_SCHEMAS)} schemas valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
