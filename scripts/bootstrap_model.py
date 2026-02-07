#!/usr/bin/env python3
"""Bootstrap a baseline ML model from synthetic data.

Creates a minimal trained model so scoring is available before
the database has any labels.
"""
import argparse
import random
import sys
from pathlib import Path

import numpy as np

from config import get_settings
from risk.scorer import compute_features
from risk.trainer import FEATURE_NAMES, MODEL_DIR, train_model
from sim.main import generate_transaction, FRAUD_RATE


def _clear_existing_models() -> None:
    for path in MODEL_DIR.glob("model_v*.joblib"):
        path.unlink(missing_ok=True)
    for path in MODEL_DIR.glob("metrics_v*.json"):
        path.unlink(missing_ok=True)


def bootstrap(count: int, fraud_rate: float, force: bool) -> int:
    if force:
        _clear_existing_models()

    random.seed(42)
    samples = []
    labels = []

    for _ in range(count):
        is_fraud = random.random() < fraud_rate
        txn = generate_transaction(is_fraud=is_fraud)
        features = compute_features(txn)
        samples.append([features.get(name, 0.0) for name in FEATURE_NAMES])
        labels.append(1 if is_fraud else 0)

    X = np.array(samples)
    y = np.array(labels)
    result = train_model(X, y)
    if not result.get("trained"):
        print(f"[ERROR] Bootstrap training failed: {result.get('error')}")
        return 1

    metrics = result.get("metrics", {})
    print(f"Bootstrap model trained: {result['version']}")
    print(
        f"  F1: {metrics.get('f1')}, "
        f"Precision: {metrics.get('precision')}, "
        f"Recall: {metrics.get('recall')}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap ML model")
    parser.add_argument(
        "--count", type=int, default=400, help="Synthetic samples"
    )
    parser.add_argument("--fraud-rate", type=float, default=FRAUD_RATE)
    parser.add_argument(
        "--force", action="store_true", help="Overwrite models"
    )
    args = parser.parse_args()

    settings = get_settings()
    Path(settings.MODELS_DIR).mkdir(parents=True, exist_ok=True)
    return bootstrap(
        count=args.count,
        fraud_rate=args.fraud_rate,
        force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
