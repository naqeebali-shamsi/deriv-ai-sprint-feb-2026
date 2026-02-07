"""Tests for JSON schema validation."""
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft7Validator, ValidationError, validate

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(name: str) -> dict:
    """Load a schema by name."""
    path = SCHEMAS_DIR / name
    with open(path) as f:
        return json.load(f)


class TestSchemaValidity:
    """Test that all schemas are valid JSON Schema."""

    @pytest.mark.parametrize("schema_name", [
        "transaction.schema.json",
        "risk_result.schema.json",
        "case.schema.json",
        "analyst_label.schema.json",
        "pattern_card.schema.json",
        "metric_snapshot.schema.json",
    ])
    def test_schema_is_valid(self, schema_name: str):
        """Each schema should be valid JSON Schema."""
        schema = load_schema(schema_name)
        Draft7Validator.check_schema(schema)


class TestTransactionSchema:
    """Test transaction schema validation."""

    @pytest.fixture
    def schema(self):
        return load_schema("transaction.schema.json")

    def test_valid_transaction(self, schema):
        """Valid transaction should pass."""
        txn = {
            "txn_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "amount": 100.50,
            "currency": "USD",
            "sender_id": "user_1",
            "receiver_id": "user_2",
            "txn_type": "transfer",
        }
        validate(txn, schema)

    def test_missing_required_field(self, schema):
        """Missing required field should fail."""
        txn = {
            "txn_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "amount": 100.50,
            # missing currency, sender_id, receiver_id, txn_type
        }
        with pytest.raises(ValidationError):
            validate(txn, schema)

    def test_invalid_txn_type(self, schema):
        """Invalid enum value should fail."""
        txn = {
            "txn_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "amount": 100.50,
            "currency": "USD",
            "sender_id": "user_1",
            "receiver_id": "user_2",
            "txn_type": "invalid_type",
        }
        with pytest.raises(ValidationError):
            validate(txn, schema)


class TestRiskResultSchema:
    """Test risk_result schema validation."""

    @pytest.fixture
    def schema(self):
        return load_schema("risk_result.schema.json")

    def test_valid_risk_result(self, schema):
        """Valid risk result should pass."""
        result = {
            "txn_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "risk_score": 0.75,
            "flagged": True,
        }
        validate(result, schema)

    def test_score_out_of_range(self, schema):
        """Score > 1 should fail."""
        result = {
            "txn_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "risk_score": 1.5,
            "flagged": True,
        }
        with pytest.raises(ValidationError):
            validate(result, schema)


class TestCaseSchema:
    """Test case schema validation."""

    @pytest.fixture
    def schema(self):
        return load_schema("case.schema.json")

    def test_valid_case(self, schema):
        """Valid case should pass."""
        case = {
            "case_id": str(uuid4()),
            "txn_id": str(uuid4()),
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        }
        validate(case, schema)


class TestPatternCardSchema:
    """Test pattern_card schema validation."""

    @pytest.fixture
    def schema(self):
        return load_schema("pattern_card.schema.json")

    def test_valid_pattern_card(self, schema):
        """Valid pattern card should pass."""
        card = {
            "pattern_id": str(uuid4()),
            "name": "High Velocity Transfer",
            "discovered_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        validate(card, schema)


class TestMetricSnapshotSchema:
    """Test metric_snapshot schema validation."""

    @pytest.fixture
    def schema(self):
        return load_schema("metric_snapshot.schema.json")

    def test_valid_metric_snapshot(self, schema):
        """Valid metric snapshot should pass."""
        snapshot = {
            "snapshot_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_txns": 1000,
                "flagged_txns": 50,
                "cases_open": 10,
                "cases_closed": 40,
            },
        }
        validate(snapshot, schema)
