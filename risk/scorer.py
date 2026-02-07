"""Risk scoring module with expanded feature engineering.

Supports two modes:
1. Rule-based (weighted features) — used before enough labels exist
2. ML-based (GradientBoostingClassifier) — used after training
"""
import math
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class RiskResult:
    """Risk scoring result."""
    txn_id: str
    score: float
    decision: str
    computed_at: str
    model_version: str = "v0.1.0"
    features: dict | None = None
    reasons: list[str] | None = None
    uncertainty: float = 0.0


# Thresholds (will be updated by learning loop)
THRESHOLDS = {
    "review": 0.5,  # score >= 0.5 -> review
    "block": 0.8,   # score >= 0.8 -> block
}

# Feature weights for rule-based scoring (replaced by ML model in Phase 3)
FEATURE_WEIGHTS = {
    "amount_normalized": 0.18,
    "amount_log": 0.04,
    "amount_high": 0.14,
    "amount_small": 0.06,
    "is_small_deposit": 0.12,
    "is_transfer": 0.08,
    "is_withdrawal": 0.04,
    "is_deposit": -0.04,
    "channel_api": 0.08,
    "hour_risky": 0.04,
    "is_weekend": 0.02,
    "sender_txn_count_1h": 0.08,
    "sender_txn_count_24h": 0.05,
    "sender_amount_sum_1h": 0.06,
    "sender_unique_receivers_24h": 0.05,
    "time_since_last_txn_minutes": 0.06,
    "device_reuse_count_24h": 0.14,
    "ip_reuse_count_24h": 0.12,
    "receiver_txn_count_24h": 0.04,
    "receiver_amount_sum_24h": 0.04,
    "receiver_unique_senders_24h": 0.04,
    "first_time_counterparty": 0.03,
    "ip_country_risk": 0.06,
    "card_bin_risk": 0.05,
    # Pattern-derived features (from graph mining feedback loop)
    "sender_in_ring": 0.15,
    "sender_is_hub": 0.08,
    "sender_in_velocity_cluster": 0.10,
    "sender_in_dense_cluster": 0.08,
    "receiver_in_ring": 0.12,
    "receiver_is_hub": 0.06,
    "pattern_count_sender": 0.10,
}


def compute_features(txn: dict) -> dict:
    """Compute all features from a transaction dict.

    The transaction dict may include optional pre-computed velocity fields
    from the backend (prefixed with sender_*). If absent, velocity features
    default to 0 (cold start).

    Features (25 total):
    - amount_normalized: amount / 10000, capped at 1.0
    - amount_log: log(amount + 1) / log(50001), normalized to [0,1]
    - amount_small: small amounts are relevant for bonus abuse
    - is_transfer: 1.0 if transfer, else 0.0
    - is_withdrawal: 1.0 if withdrawal, else 0.0
    - is_deposit: 1.0 if deposit, else 0.0
    - is_payment: 1.0 if payment, else 0.0
    - is_small_deposit: 1.0 if deposit <= $100
    - channel_web: 1.0 if web
    - channel_api: 1.0 if api (higher risk for automated transactions)
    - hour_of_day: normalized hour (0-1), based on timestamp or current time
    - is_weekend: 1.0 if Saturday/Sunday
    - hour_risky: 1.0 if between 00:00-05:00 (risky hours)
    - sender_txn_count_1h: number of txns from sender in last hour (velocity)
    - sender_txn_count_24h: number of txns from sender in last 24h (velocity)
    - sender_amount_sum_1h: total amount from sender in last hour (velocity)
    - sender_unique_receivers_24h: unique receivers in last 24h (breadth)
    - device_reuse_count_24h: distinct other senders on same device (bonus abuse)
    - ip_reuse_count_24h: distinct other senders on same IP (bonus abuse)
    - receiver_txn_count_24h: inbound txns to receiver in last 24h
    - receiver_amount_sum_24h: inbound amount to receiver in last 24h
    - receiver_unique_senders_24h: distinct senders to receiver in last 24h
    - first_time_counterparty: first time sender->receiver pair
    - ip_country_risk: simple geo risk score from metadata
    - card_bin_risk: simple bin risk score for deposits
    """
    amount = txn.get("amount", 0)
    txn_type = txn.get("txn_type", "")
    channel = txn.get("channel", "")
    metadata = txn.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            import json
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    # Parse hour from timestamp if available
    now = datetime.utcnow()
    hour = now.hour
    day_of_week = now.weekday()

    # Amount features
    amount_normalized = min(amount / 10000, 1.0)
    amount_log = math.log(amount + 1) / math.log(50001)  # normalize to ~[0,1]
    amount_high = 1.0 if amount > 5000 else (
        amount / 5000 if amount > 2000 else 0.0
    )
    amount_small = 1.0 if amount < 100 else (
        max(0.0, (500 - amount) / 400) if amount < 500 else 0.0
    )

    # Transaction type one-hot
    is_transfer = 1.0 if txn_type == "transfer" else 0.0
    is_withdrawal = 1.0 if txn_type == "withdrawal" else 0.0
    is_deposit = 1.0 if txn_type == "deposit" else 0.0
    is_payment = 1.0 if txn_type == "payment" else 0.0
    is_small_deposit = 1.0 if (
        txn_type == "deposit" and amount <= 100
    ) else 0.0

    # Channel features
    channel_web = 1.0 if channel == "web" else 0.0
    channel_api = 1.0 if channel == "api" else 0.0

    # Temporal features
    hour_of_day = hour / 23.0  # normalize to [0,1]
    is_weekend = 1.0 if day_of_week >= 5 else 0.0
    hour_risky = 1.0 if hour < 5 else 0.0  # late night / early morning

    # Velocity features (pre-computed by backend, default to 0 for cold start)
    sender_txn_count_1h = min(
        txn.get("sender_txn_count_1h", 0) / 20.0, 1.0
    )
    sender_txn_count_24h = min(
        txn.get("sender_txn_count_24h", 0) / 100.0, 1.0
    )
    sender_amount_sum_1h = min(
        txn.get("sender_amount_sum_1h", 0) / 50000.0, 1.0
    )
    sender_unique_receivers_24h = min(
        txn.get("sender_unique_receivers_24h", 0) / 20.0, 1.0
    )
    device_reuse_count_24h = min(
        txn.get("device_reuse_count_24h", 0) / 5.0, 1.0
    )
    ip_reuse_count_24h = min(
        txn.get("ip_reuse_count_24h", 0) / 10.0, 1.0
    )
    receiver_txn_count_24h = min(
        txn.get("receiver_txn_count_24h", 0) / 200.0, 1.0
    )
    receiver_amount_sum_24h = min(
        txn.get("receiver_amount_sum_24h", 0) / 100000.0, 1.0
    )
    receiver_unique_senders_24h = min(
        txn.get("receiver_unique_senders_24h", 0) / 40.0, 1.0
    )
    first_time_counterparty = 1.0 if txn.get("first_time_counterparty") else 0.0

    # Time since last transaction (shorter = more suspicious for velocity)
    time_since_last = txn.get("time_since_last_txn_minutes", 60)
    # Invert: shorter time = higher feature value
    time_since_last_txn_minutes = max(0, 1.0 - (time_since_last / 60.0))

    ip_country = str(metadata.get("ip_country") or "").upper()
    ip_country_risk_map = {
        "NG": 1.0,
        "BR": 0.8,
        "SG": 0.6,
        "FR": 0.3,
        "DE": 0.2,
        "GB": 0.1,
        "US": 0.1,
    }
    ip_country_risk = ip_country_risk_map.get(
        ip_country, 0.4 if ip_country else 0.0
    )

    card_bin_raw = metadata.get("card_bin")
    card_bin_risk = 0.0
    if card_bin_raw:
        try:
            card_bin = int(card_bin_raw)
            if 460000 <= card_bin <= 499999:
                card_bin_risk = 0.7
            elif 430000 <= card_bin <= 459999:
                card_bin_risk = 0.4
            else:
                card_bin_risk = 0.1
        except (ValueError, TypeError):
            card_bin_risk = 0.0

    return {
        "amount_normalized": round(amount_normalized, 6),
        "amount_log": round(amount_log, 6),
        "amount_high": round(amount_high, 6),
        "amount_small": round(amount_small, 6),
        "is_transfer": is_transfer,
        "is_withdrawal": is_withdrawal,
        "is_deposit": is_deposit,
        "is_payment": is_payment,
        "is_small_deposit": is_small_deposit,
        "channel_web": channel_web,
        "channel_api": channel_api,
        "hour_of_day": round(hour_of_day, 4),
        "is_weekend": is_weekend,
        "hour_risky": hour_risky,
        "sender_txn_count_1h": round(sender_txn_count_1h, 6),
        "sender_txn_count_24h": round(sender_txn_count_24h, 6),
        "sender_amount_sum_1h": round(sender_amount_sum_1h, 6),
        "sender_unique_receivers_24h": round(sender_unique_receivers_24h, 6),
        "time_since_last_txn_minutes": round(time_since_last_txn_minutes, 6),
        "device_reuse_count_24h": round(device_reuse_count_24h, 6),
        "ip_reuse_count_24h": round(ip_reuse_count_24h, 6),
        "receiver_txn_count_24h": round(receiver_txn_count_24h, 6),
        "receiver_amount_sum_24h": round(receiver_amount_sum_24h, 6),
        "receiver_unique_senders_24h": round(receiver_unique_senders_24h, 6),
        "first_time_counterparty": first_time_counterparty,
        "ip_country_risk": round(ip_country_risk, 4),
        "card_bin_risk": round(card_bin_risk, 4),
        # Pattern-derived features (populated by backend when DB context available)
        "sender_in_ring": txn.get("sender_in_ring", 0.0),
        "sender_is_hub": txn.get("sender_is_hub", 0.0),
        "sender_in_velocity_cluster": txn.get("sender_in_velocity_cluster", 0.0),
        "sender_in_dense_cluster": txn.get("sender_in_dense_cluster", 0.0),
        "receiver_in_ring": txn.get("receiver_in_ring", 0.0),
        "receiver_is_hub": txn.get("receiver_is_hub", 0.0),
        "pattern_count_sender": txn.get("pattern_count_sender", 0.0),
    }


def _get_ml_model():
    """Lazy-load the ML model (cached)."""
    if not hasattr(_get_ml_model, "_cache"):
        _get_ml_model._cache = None
        _get_ml_model._version = "v0.0.0-rules"
    try:
        from risk.trainer import load_model, get_model_version
        model = load_model()
        if model is not None:
            _get_ml_model._cache = model
            _get_ml_model._version = get_model_version()
    except ImportError:
        pass
    return _get_ml_model._cache, _get_ml_model._version


def reload_model():
    """Force reload the ML model (call after retraining)."""
    if hasattr(_get_ml_model, "_cache"):
        del _get_ml_model._cache
        del _get_ml_model._version


def score_transaction(txn: dict) -> RiskResult:
    """Score a transaction for fraud risk.

    Uses ML model if available, falls back to weighted features (rule-based).
    """
    features = compute_features(txn)

    # Try ML model first
    ml_model, model_version = _get_ml_model()
    if ml_model is not None:
        from risk.trainer import FEATURE_NAMES
        feature_vector = [features.get(name, 0.0) for name in FEATURE_NAMES]
        try:
            score = float(ml_model.predict_proba([feature_vector])[0][1])
        except Exception:
            # Fallback to rule-based if ML prediction fails
            score = _rule_based_score(features)
            model_version = "v0.0.0-rules"
    else:
        score = _rule_based_score(features)
        model_version = "v0.0.0-rules"

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    # Decision based on thresholds
    if score >= THRESHOLDS["block"]:
        decision = "block"
    elif score >= THRESHOLDS["review"]:
        decision = "review"
    else:
        decision = "approve"

    # Generate reasons for flagged transactions
    reasons = []
    if features["amount_normalized"] > 0.5:
        reasons.append("High transaction amount")
    if features["is_transfer"] and features["amount_normalized"] > 0.3:
        reasons.append("Large transfer")
    if features["sender_txn_count_1h"] > 0.3:
        reasons.append("High sender velocity (1h)")
    if features["sender_txn_count_24h"] > 0.3:
        reasons.append("High sender activity (24h)")
    if features["sender_amount_sum_1h"] > 0.4:
        reasons.append("High cumulative amount (1h)")
    if features["sender_unique_receivers_24h"] > 0.3:
        reasons.append("Many unique receivers (24h)")
    if features["device_reuse_count_24h"] > 0.2:
        reasons.append("Shared device across multiple accounts")
    if features["ip_reuse_count_24h"] > 0.2:
        reasons.append("Shared IP across multiple accounts")
    if features["is_small_deposit"] and (
        features["device_reuse_count_24h"] > 0.1
        or features["ip_reuse_count_24h"] > 0.1
    ):
        reasons.append("Small deposit with shared device/IP")
    if features["ip_country_risk"] > 0.5:
        reasons.append("Higher-risk IP geography")
    if features["card_bin_risk"] > 0.5:
        reasons.append("Higher-risk card BIN")
    if features["channel_api"] and features["amount_normalized"] > 0.2:
        reasons.append("API channel with notable amount")
    if features["hour_risky"]:
        reasons.append("Transaction during risky hours")
    if features.get("sender_in_ring", 0) > 0:
        reasons.append("Sender appears in circular fund flow pattern")
    if features.get("sender_is_hub", 0) > 0:
        reasons.append("Sender is a high-activity hub account")
    if features.get("sender_in_velocity_cluster", 0) > 0:
        reasons.append("Sender flagged in velocity spike pattern")
    if features.get("receiver_in_ring", 0) > 0:
        reasons.append("Receiver appears in circular fund flow pattern")

    # Compute uncertainty (distance from 0.5 — lower = more uncertain)
    uncertainty = abs(score - 0.5)

    return RiskResult(
        txn_id=txn.get("txn_id", str(uuid4())),
        score=round(score, 4),
        decision=decision,
        computed_at=datetime.utcnow().isoformat(),
        model_version=model_version,
        features=features,
        reasons=reasons,
        uncertainty=round(uncertainty, 4),
    )


def _rule_based_score(features: dict) -> float:
    """Rule-based scoring using weighted feature sum."""
    score = 0.0
    for feat_name, weight in FEATURE_WEIGHTS.items():
        score += features.get(feat_name, 0) * weight
    return score
