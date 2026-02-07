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


# Add project root to path so we can import config/risk/sim
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings

from risk.scorer import compute_features
from risk.trainer import FEATURE_NAMES, MODEL_DIR, train_model
from sim.main import generate_transaction, FRAUD_RATE


def _clear_existing_models() -> None:
    for path in MODEL_DIR.glob("model_v*.joblib"):
        path.unlink(missing_ok=True)
    for path in MODEL_DIR.glob("metrics_v*.json"):
        path.unlink(missing_ok=True)


def _inject_velocity_context(txn: dict, is_fraud: bool) -> dict:
    """Inject synthetic velocity/pattern features for bootstrap training.

    Without this, the model sees zero velocity data and learns only
    amount/type features (22% recall). Fraud samples get elevated
    velocity signals; legit samples get low/normal velocity signals.
    """
    if is_fraud:
        txn["sender_txn_count_1h"] = random.randint(4, 18)
        txn["sender_txn_count_24h"] = random.randint(10, 60)
        txn["sender_amount_sum_1h"] = random.uniform(5000, 40000)
        txn["sender_unique_receivers_24h"] = random.randint(3, 15)
        txn["time_since_last_txn_minutes"] = random.uniform(0.2, 5)
        txn["device_reuse_count_24h"] = random.randint(0, 3)
        txn["ip_reuse_count_24h"] = random.randint(0, 5)
        txn["receiver_txn_count_24h"] = random.randint(5, 80)
        txn["receiver_amount_sum_24h"] = random.uniform(3000, 60000)
        txn["receiver_unique_senders_24h"] = random.randint(2, 20)
        txn["first_time_counterparty"] = random.random() < 0.7
        # Pattern features — some fraud is in known patterns
        if random.random() < 0.4:
            txn["sender_in_ring"] = 1.0
            txn["receiver_in_ring"] = random.choice([0.0, 1.0])
        if random.random() < 0.3:
            txn["sender_is_hub"] = 1.0
        if random.random() < 0.3:
            txn["sender_in_velocity_cluster"] = 1.0
        if random.random() < 0.2:
            txn["sender_in_dense_cluster"] = 1.0
        txn["pattern_count_sender"] = random.uniform(0, 3)
    else:
        # Legit: low/normal velocity with realistic overlap
        # ~15% of legit users are "power users" with moderate velocity
        power_user = random.random() < 0.15
        if power_user:
            txn["sender_txn_count_1h"] = random.randint(3, 10)
            txn["sender_txn_count_24h"] = random.randint(8, 30)
            txn["sender_amount_sum_1h"] = random.uniform(2000, 15000)
            txn["sender_unique_receivers_24h"] = random.randint(2, 8)
            txn["time_since_last_txn_minutes"] = random.uniform(2, 20)
        else:
            txn["sender_txn_count_1h"] = random.randint(0, 3)
            txn["sender_txn_count_24h"] = random.randint(0, 10)
            txn["sender_amount_sum_1h"] = random.uniform(0, 4000)
            txn["sender_unique_receivers_24h"] = random.randint(0, 3)
            txn["time_since_last_txn_minutes"] = random.uniform(10, 180)
        txn["device_reuse_count_24h"] = random.randint(0, 1)
        txn["ip_reuse_count_24h"] = random.randint(0, 2)
        txn["receiver_txn_count_24h"] = random.randint(0, 30)
        txn["receiver_amount_sum_24h"] = random.uniform(0, 15000)
        txn["receiver_unique_senders_24h"] = random.randint(0, 8)
        txn["first_time_counterparty"] = random.random() < 0.35
        # ~20% of legit users get flagged by patterns innocuously (power users)
        if random.random() < 0.20:
            txn["pattern_count_sender"] = random.uniform(0, 0.5)
        # Small chance legit users appear in pattern structures
        if power_user and random.random() < 0.10:
            txn["sender_is_hub"] = 1.0
        if random.random() < 0.05:
            txn["sender_in_velocity_cluster"] = 1.0
    return txn


def bootstrap(count: int, fraud_rate: float, force: bool) -> int:
    if force:
        _clear_existing_models()

    random.seed(42)
    samples = []
    labels = []

    for _ in range(count):
        is_fraud = random.random() < fraud_rate
        txn = generate_transaction(is_fraud=is_fraud)
        txn = _inject_velocity_context(txn, is_fraud)
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
        f"  CV F1: {metrics.get('cv_f1_mean')} +/- {metrics.get('cv_f1_std')}, "
        f"Full-data F1: {metrics.get('f1')}, "
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
