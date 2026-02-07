"""Tests for the Retrain Guardian agent deterministic logic.

Tests pure functions only — no LLM, no DB, no async.
"""
import tempfile
from pathlib import Path

import pytest

from risk.guardian import (
    _deterministic_decision,
    _deterministic_eval,
    _parse_guardian_response,
    _parse_eval_response,
    _rollback_model,
)


# =============================================================================
# Deterministic retrain decision tests
# =============================================================================

class TestDeterministicDecision:

    def test_retrain_on_labels(self):
        ctx = {"total_labels": 30, "labels_since": 7, "drift": 0.01,
               "txns_since_retrain": 40, "minutes_since_retrain": 3}
        decision, reasoning, confidence = _deterministic_decision(ctx)
        assert decision == "RETRAIN"
        assert "7" in reasoning

    def test_skip_insufficient_total(self):
        ctx = {"total_labels": 5, "labels_since": 3, "drift": 0.0,
               "txns_since_retrain": 10, "minutes_since_retrain": 1}
        decision, reasoning, confidence = _deterministic_decision(ctx)
        assert decision == "SKIP"
        assert "5" in reasoning

    def test_retrain_on_drift(self):
        ctx = {"total_labels": 25, "labels_since": 2, "drift": 0.08,
               "txns_since_retrain": 100, "minutes_since_retrain": 3}
        decision, reasoning, confidence = _deterministic_decision(ctx)
        assert decision == "RETRAIN"
        assert "drift" in reasoning.lower()

    def test_skip_no_conditions_met(self):
        ctx = {"total_labels": 25, "labels_since": 2, "drift": 0.01,
               "txns_since_retrain": 30, "minutes_since_retrain": 2}
        decision, reasoning, confidence = _deterministic_decision(ctx)
        assert decision == "SKIP"

    def test_retrain_on_staleness(self):
        ctx = {"total_labels": 25, "labels_since": 1, "drift": 0.02,
               "txns_since_retrain": 250, "minutes_since_retrain": 10}
        decision, reasoning, confidence = _deterministic_decision(ctx)
        assert decision == "RETRAIN"
        assert "250" in reasoning


# =============================================================================
# Deterministic eval decision tests
# =============================================================================

class TestDeterministicEval:

    def test_keep_improved(self):
        old = {"f1": 0.80, "precision": 0.85, "recall": 0.75}
        new = {"f1": 0.85, "precision": 0.88, "recall": 0.82}
        decision, reasoning = _deterministic_eval(old, new)
        assert decision == "KEEP"

    def test_rollback_f1_drop(self):
        old = {"f1": 0.80, "precision": 0.85, "recall": 0.75}
        new = {"f1": 0.60, "precision": 0.85, "recall": 0.50}
        decision, reasoning = _deterministic_eval(old, new)
        assert decision == "ROLLBACK"
        assert "F1" in reasoning

    def test_rollback_precision_drop(self):
        old = {"f1": 0.80, "precision": 0.90, "recall": 0.72}
        new = {"f1": 0.78, "precision": 0.70, "recall": 0.88}
        decision, reasoning = _deterministic_eval(old, new)
        assert decision == "ROLLBACK"
        assert "Precision" in reasoning or "precision" in reasoning.lower()

    def test_keep_slight_decline(self):
        old = {"f1": 0.80, "precision": 0.85, "recall": 0.75}
        new = {"f1": 0.78, "precision": 0.83, "recall": 0.73}
        decision, reasoning = _deterministic_eval(old, new)
        assert decision == "KEEP"


# =============================================================================
# LLM output parsing tests
# =============================================================================

class TestParsing:

    def test_parse_guardian_response(self):
        text = """DECISION: RETRAIN
REASONING: 7 new labels accumulated since last retrain
CONFIDENCE: HIGH"""
        decision, reasoning, confidence = _parse_guardian_response(text)
        assert decision == "RETRAIN"
        assert "7 new labels" in reasoning
        assert confidence == "HIGH"

    def test_parse_guardian_skip(self):
        text = """DECISION: SKIP
REASONING: Not enough new data
CONFIDENCE: MEDIUM"""
        decision, reasoning, confidence = _parse_guardian_response(text)
        assert decision == "SKIP"
        assert confidence == "MEDIUM"

    def test_parse_eval_keep(self):
        text = """DECISION: KEEP
REASONING: F1 improved from 0.75 to 0.82"""
        decision, reasoning = _parse_eval_response(text)
        assert decision == "KEEP"
        assert "F1" in reasoning

    def test_parse_eval_rollback(self):
        text = """DECISION: ROLLBACK
REASONING: F1 dropped significantly"""
        decision, reasoning = _parse_eval_response(text)
        assert decision == "ROLLBACK"


# =============================================================================
# Rollback safety tests
# =============================================================================

class TestRollback:

    def test_rollback_safe_with_single_model(self, tmp_path):
        """Cannot rollback when only one model exists."""
        import risk.guardian as guardian
        original_dir = guardian.MODEL_DIR

        try:
            guardian.MODEL_DIR = tmp_path
            # Create single model
            (tmp_path / "model_v0.1.0.joblib").write_bytes(b"fake_model")
            (tmp_path / "metrics_v0.1.0.json").write_text('{"f1": 0.8}')

            result = _rollback_model("v0.1.0")
            assert result is False
            # Original file still exists
            assert (tmp_path / "model_v0.1.0.joblib").exists()
        finally:
            guardian.MODEL_DIR = original_dir

    def test_rollback_renames_files(self, tmp_path):
        """Rollback renames (not deletes) the new model files."""
        import risk.guardian as guardian
        original_dir = guardian.MODEL_DIR

        try:
            guardian.MODEL_DIR = tmp_path
            # Create two models
            (tmp_path / "model_v0.1.0.joblib").write_bytes(b"old_model")
            (tmp_path / "model_v0.2.0.joblib").write_bytes(b"new_model")
            (tmp_path / "metrics_v0.2.0.json").write_text('{"f1": 0.5}')

            result = _rollback_model("v0.2.0")
            assert result is True
            # New model renamed, not deleted
            assert not (tmp_path / "model_v0.2.0.joblib").exists()
            assert (tmp_path / "model_v0.2.0.joblib.rolled_back").exists()
            assert not (tmp_path / "metrics_v0.2.0.json").exists()
            assert (tmp_path / "metrics_v0.2.0.json.rolled_back").exists()
            # Old model untouched
            assert (tmp_path / "model_v0.1.0.joblib").exists()
        finally:
            guardian.MODEL_DIR = original_dir
