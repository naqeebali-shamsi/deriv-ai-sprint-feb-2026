"""ML model training for fraud detection.

Trains an XGBClassifier on labeled transaction data,
evaluates performance, and saves versioned models.

Why XGBoost over sklearn GradientBoosting:
- Built-in L1/L2 regularization (reg_alpha, reg_lambda) prevents overfitting
- Native sparse data handling — ideal for fraud features with many zeros
- Better handling of feature interactions without manual engineering
- Faster training via histogram-based splits
- Same API surface (sklearn-compatible), drop-in replacement
"""
import json
import math
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Feature names in order (must match compute_features output)
FEATURE_NAMES = [
    "amount_normalized",
    "amount_log",
    "amount_high",
    "amount_small",
    "is_transfer",
    "is_withdrawal",
    "is_deposit",
    "is_payment",
    "is_small_deposit",
    "channel_web",
    "channel_api",
    "hour_of_day",
    "is_weekend",
    "hour_risky",
    "sender_txn_count_1h",
    "sender_txn_count_24h",
    "sender_amount_sum_1h",
    "sender_unique_receivers_24h",
    "time_since_last_txn_minutes",
    "device_reuse_count_24h",
    "ip_reuse_count_24h",
    "receiver_txn_count_24h",
    "receiver_amount_sum_24h",
    "receiver_unique_senders_24h",
    "first_time_counterparty",
    "ip_country_risk",
    "card_bin_risk",
    # Pattern-derived features (from graph mining feedback loop)
    "sender_in_ring",
    "sender_is_hub",
    "sender_in_velocity_cluster",
    "sender_in_dense_cluster",
    "receiver_in_ring",
    "receiver_is_hub",
    "pattern_count_sender",
]

MIN_SAMPLES_PER_CLASS = 10  # Minimum labeled samples per class to train


def _version_sort_key(path: Path) -> tuple[int, ...]:
    """Parse vX.Y.Z from filename into tuple for numeric sorting."""
    stem = path.stem.replace("model_", "").lstrip("v")
    try:
        return tuple(int(p) for p in stem.split("."))
    except (ValueError, TypeError):
        return (0, 0, 0)


def get_latest_model_path() -> Path | None:
    """Find the latest trained model file (by semantic version, not string sort)."""
    if not MODEL_DIR.exists():
        return None
    models = sorted(MODEL_DIR.glob("model_v*.joblib"), key=_version_sort_key)
    return models[-1] if models else None


def get_model_version() -> str:
    """Get the current model version string."""
    latest = get_latest_model_path()
    if latest:
        # Extract version from filename: model_v0.2.0.joblib -> v0.2.0
        return latest.stem.replace("model_", "")
    return "missing"


def load_model():
    """Load the latest trained model, or return None for rule-based fallback."""
    path = get_latest_model_path()
    if path and path.exists():
        return joblib.load(path)
    return None


def features_from_row(txn_row: dict) -> list[float]:
    """Extract feature vector from a transaction + velocity data dict.

    This is used for training — the dict should contain all feature fields.
    """
    return [txn_row.get(name, 0.0) for name in FEATURE_NAMES]


def compute_training_features(
    amount: float,
    txn_type: str,
    channel: str,
    velocity: dict | None = None,
) -> dict:
    """Compute features for a single training sample.

    Similar to scorer.compute_features but used during batch training.
    """
    amount_normalized = min(amount / 10000, 1.0)
    amount_log = math.log(amount + 1) / math.log(50001)
    amount_high = 1.0 if amount > 5000 else (
        amount / 5000 if amount > 2000 else 0.0
    )
    amount_small = 1.0 if amount < 100 else (
        max(0.0, (500 - amount) / 400) if amount < 500 else 0.0
    )

    v = velocity or {}
    return {
        "amount_normalized": amount_normalized,
        "amount_log": amount_log,
        "amount_high": amount_high,
        "amount_small": amount_small,
        "is_transfer": 1.0 if txn_type == "transfer" else 0.0,
        "is_withdrawal": 1.0 if txn_type == "withdrawal" else 0.0,
        "is_deposit": 1.0 if txn_type == "deposit" else 0.0,
        "is_payment": 1.0 if txn_type == "payment" else 0.0,
        "is_small_deposit": 1.0 if (
            txn_type == "deposit" and amount <= 100
        ) else 0.0,
        "channel_web": 1.0 if channel == "web" else 0.0,
        "channel_api": 1.0 if channel == "api" else 0.0,
        "hour_of_day": v.get("hour_of_day", 0.5),
        "is_weekend": v.get("is_weekend", 0.0),
        "hour_risky": v.get("hour_risky", 0.0),
        "sender_txn_count_1h": min(
            v.get("sender_txn_count_1h", 0) / 20.0, 1.0
        ),
        "sender_txn_count_24h": min(
            v.get("sender_txn_count_24h", 0) / 100.0, 1.0
        ),
        "sender_amount_sum_1h": min(
            v.get("sender_amount_sum_1h", 0) / 50000.0, 1.0
        ),
        "sender_unique_receivers_24h": min(
            v.get("sender_unique_receivers_24h", 0) / 20.0, 1.0
        ),
        "time_since_last_txn_minutes": max(
            0, 1.0 - (v.get("time_since_last_txn_minutes", 60) / 60.0)
        ),
        "device_reuse_count_24h": min(
            v.get("device_reuse_count_24h", 0) / 5.0, 1.0
        ),
        "ip_reuse_count_24h": min(
            v.get("ip_reuse_count_24h", 0) / 10.0, 1.0
        ),
        "receiver_txn_count_24h": min(
            v.get("receiver_txn_count_24h", 0) / 200.0, 1.0
        ),
        "receiver_amount_sum_24h": min(
            v.get("receiver_amount_sum_24h", 0) / 100000.0, 1.0
        ),
        "receiver_unique_senders_24h": min(
            v.get("receiver_unique_senders_24h", 0) / 40.0, 1.0
        ),
        "first_time_counterparty": 1.0 if v.get("first_time_counterparty") else 0.0,
        "ip_country_risk": v.get("ip_country_risk", 0.0),
        "card_bin_risk": v.get("card_bin_risk", 0.0),
        # Pattern-derived features (default 0.0 for training samples without pattern context)
        "sender_in_ring": v.get("sender_in_ring", 0.0),
        "sender_is_hub": v.get("sender_is_hub", 0.0),
        "sender_in_velocity_cluster": v.get("sender_in_velocity_cluster", 0.0),
        "sender_in_dense_cluster": v.get("sender_in_dense_cluster", 0.0),
        "receiver_in_ring": v.get("receiver_in_ring", 0.0),
        "receiver_is_hub": v.get("receiver_is_hub", 0.0),
        "pattern_count_sender": v.get("pattern_count_sender", 0.0),
    }


def train_model(X: np.ndarray, y: np.ndarray, version_bump: str = "minor") -> dict:
    """Train an XGBClassifier and save it.

    Args:
        X: Feature matrix (n_samples, n_features)
        y: Labels (0 = legit, 1 = fraud)
        version_bump: "minor" or "patch" version increment

    Returns:
        Dict with model path, version, and evaluation metrics.
    """
    # Check minimum samples
    fraud_count = int(np.sum(y == 1))
    legit_count = int(np.sum(y == 0))
    if fraud_count < MIN_SAMPLES_PER_CLASS or legit_count < MIN_SAMPLES_PER_CLASS:
        return {
            "error": f"Insufficient labeled data: {fraud_count} fraud, {legit_count} legit. "
                     f"Need at least {MIN_SAMPLES_PER_CLASS} of each.",
            "trained": False,
        }

    # Split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train XGBClassifier — chosen for superior regularization and sparse handling
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,      # L1 regularization — handles sparsity well
        reg_lambda=1.0,     # L2 regularization — prevents overfitting
        min_child_weight=2,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "auc_roc": round(float(roc_auc_score(y_test, y_proba)), 4) if len(set(y_test)) > 1 else None,
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "fraud_samples": fraud_count,
        "legit_samples": legit_count,
    }

    # Feature importance
    importance = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in model.feature_importances_]))
    metrics["feature_importance"] = importance

    # Version the model
    current_version = get_model_version()
    new_version = _bump_version(current_version, version_bump)

    # Save model
    model_path = MODEL_DIR / f"model_{new_version}.joblib"
    joblib.dump(model, model_path)

    # Save metrics alongside
    metrics_path = MODEL_DIR / f"metrics_{new_version}.json"
    with open(metrics_path, "w") as f:
        json.dump({**metrics, "version": new_version, "trained_at": datetime.utcnow().isoformat()}, f, indent=2)

    return {
        "trained": True,
        "version": new_version,
        "model_path": str(model_path),
        "metrics": metrics,
    }


def _bump_version(current: str, bump_type: str) -> str:
    """Increment version string."""
    # Parse vX.Y.Z
    clean = current.lstrip("v").split("-")[0]
    parts = clean.split(".")
    if len(parts) != 3:
        return "v0.1.0"

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump_type == "major":
        return f"v{major + 1}.0.0"
    elif bump_type == "minor":
        return f"v{major}.{minor + 1}.0"
    else:
        return f"v{major}.{minor}.{patch + 1}"
