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
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from xgboost import XGBClassifier

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
    "hour_sin",
    "hour_cos",
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

MIN_SAMPLES_PER_CLASS = 30  # Minimum labeled samples per class to train


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
    """Compute features for a training sample.

    Thin wrapper around scorer.compute_features to eliminate training-serving
    feature skew. Builds a txn dict from the args and delegates to the single
    source of truth.
    """
    from risk.scorer import compute_features
    v = velocity or {}
    txn = {
        "amount": amount,
        "txn_type": txn_type,
        "channel": channel,
        **v,
    }
    return compute_features(txn)


def train_model(X: np.ndarray, y: np.ndarray, version_bump: str = "minor") -> dict:
    """Train an XGBClassifier and save it.

    Uses stratified k-fold CV for evaluation, then trains the final model
    on the full dataset for deployment.

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

    # Class imbalance handling
    spw = float(legit_count) / max(float(fraud_count), 1)

    # Stratified k-fold CV for evaluation (k = min(5, smallest class count))
    n_splits = min(5, min(fraud_count, legit_count))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    cv_model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        min_child_weight=2,
        scale_pos_weight=spw,
        random_state=42,
        eval_metric="logloss",
    )
    cv_scores = cross_val_score(cv_model, X, y, cv=cv, scoring="f1")

    # Train final model on FULL dataset for deployment
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        min_child_weight=2,
        scale_pos_weight=spw,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X, y)

    # Evaluate final model on full data for reporting (CV scores are the real metric)
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    metrics = {
        "cv_f1_mean": round(float(np.mean(cv_scores)), 4),
        "cv_f1_std": round(float(np.std(cv_scores)), 4),
        "cv_f1_folds": [round(float(s), 4) for s in cv_scores],
        "cv_n_splits": n_splits,
        "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, y_pred, zero_division=0)), 4),
        "auc_roc": round(float(roc_auc_score(y, y_proba)), 4) if len(set(y)) > 1 else None,
        "total_samples": len(y),
        "fraud_samples": fraud_count,
        "legit_samples": legit_count,
        "scale_pos_weight": round(spw, 4),
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
