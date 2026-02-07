"""Adversarial transaction generators for model evaluation.

Generates transactions designed to evade the fraud detection model
using realistic evasion techniques. These do NOT use named fraud pools
(ring_a_*, smurfer_*, velocity_*, spoofer_*, bonus_*) since those leak
identity through velocity features.

Each generator produces transactions that ARE fraud (ground truth)
but are designed to look legitimate to the scorer.
"""
import random
from datetime import datetime
from uuid import uuid4


def _random_id() -> str:
    """Generate a random user ID that looks like a normal user."""
    return f"user_{random.randint(10000, 99999)}"


def _low_risk_metadata() -> dict:
    """Generate metadata that avoids triggering geo/card risk features."""
    return {
        "ip_country": random.choice(["US", "GB", "DE"]),
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "session_id": f"sess_{uuid4().hex[:12]}",
        "login_hash": uuid4().hex[:8],
    }


def generate_subtle_structuring() -> dict:
    """Structuring that varies amounts randomly, uses different receivers,
    spaces transactions apart, and uses common channels.

    Evasion tactics:
    - Amount between $200-$900 with random variation (not fixed pattern)
    - Unique receiver_id each call (no velocity buildup on receiver side)
    - No velocity fields set (simulates spaced-apart transactions)
    - Web/mobile channels (not API)
    - Unique sender_id per call (no sender velocity buildup)
    """
    return {
        "txn_id": str(uuid4()),
        "amount": round(random.uniform(200, 900), 2),
        "currency": random.choice(["USD", "EUR", "GBP"]),
        "sender_id": _random_id(),
        "receiver_id": _random_id(),
        "txn_type": "transfer",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "time_since_last_txn_minutes": random.randint(30, 120),
        "metadata": {
            "evasion_strategy": "subtle_structuring",
            "fraud_type": "structuring",
            **_low_risk_metadata(),
        },
    }


def generate_stealth_wash_trade() -> dict:
    """Wash trading with random account IDs, small amounts, different
    channels per leg, and delays between legs.

    Evasion tactics:
    - Random sender/receiver IDs (not ring_a_* pools)
    - Small amounts $50-$500 (below amount_high threshold)
    - Varied channels (web, mobile, branch -- not API)
    - No velocity signals (time_since_last_txn_minutes set high)
    """
    return {
        "txn_id": str(uuid4()),
        "amount": round(random.uniform(50, 500), 2),
        "currency": "USD",
        "sender_id": _random_id(),
        "receiver_id": _random_id(),
        "txn_type": "transfer",
        "channel": random.choice(["web", "mobile", "branch"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "time_since_last_txn_minutes": random.randint(15, 60),
        "metadata": {
            "evasion_strategy": "stealth_wash_trade",
            "fraud_type": "wash_trading",
            **_low_risk_metadata(),
        },
    }


def generate_slow_velocity_abuse() -> dict:
    """Velocity abuse that stays under velocity thresholds by spacing
    transactions 10-15 minutes apart with moderate amounts.

    Evasion tactics:
    - time_since_last_txn_minutes = 10-15 (feature value ~0.75-0.83,
      but below the 1.0 spike that rapid-fire produces)
    - Moderate amounts $500-$2000 (not flagged as high)
    - Different receiver each time
    - Web channel (not API)
    - No sender velocity counters set (cold start)
    """
    return {
        "txn_id": str(uuid4()),
        "amount": round(random.uniform(500, 2000), 2),
        "currency": random.choice(["USD", "EUR"]),
        "sender_id": _random_id(),
        "receiver_id": _random_id(),
        "txn_type": random.choice(["transfer", "withdrawal"]),
        "channel": "web",
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "time_since_last_txn_minutes": random.randint(10, 15),
        "metadata": {
            "evasion_strategy": "slow_velocity_abuse",
            "fraud_type": "velocity_abuse",
            **_low_risk_metadata(),
        },
    }


def generate_legit_looking_fraud() -> dict:
    """High-value fraud disguised as legitimate business transaction.

    Evasion tactics:
    - Single large transfer $5000-$15000 from a 'new' sender_id
    - No prior history means no velocity signals fire
    - Web channel (lower risk than API)
    - Business hours (not risky hours)
    - Low-risk IP country (US/GB/DE)
    - first_time_counterparty not set (defaults to 0)
    """
    return {
        "txn_id": str(uuid4()),
        "amount": round(random.uniform(5000, 15000), 2),
        "currency": "USD",
        "sender_id": _random_id(),
        "receiver_id": _random_id(),
        "txn_type": "transfer",
        "channel": "web",
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "time_since_last_txn_minutes": 60,
        "metadata": {
            "evasion_strategy": "legit_looking_fraud",
            "fraud_type": "spoofing",
            **_low_risk_metadata(),
        },
    }


def generate_bonus_abuse_evasion() -> dict:
    """Bonus abuse with unique device_ids and ip_addresses per transaction.

    Evasion tactics:
    - Unique device_id per transaction (no device_reuse_count_24h signal)
    - Unique ip_address per transaction (no ip_reuse_count_24h signal)
    - Small deposits $20-$80
    - Different sender_ids (no velocity buildup)
    """
    return {
        "txn_id": str(uuid4()),
        "amount": round(random.uniform(20, 80), 2),
        "currency": "USD",
        "sender_id": _random_id(),
        "receiver_id": f"platform_{random.randint(1, 50)}",
        "txn_type": "deposit",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "time_since_last_txn_minutes": random.randint(60, 180),
        "metadata": {
            "evasion_strategy": "bonus_abuse_evasion",
            "fraud_type": "bonus_abuse",
            **_low_risk_metadata(),
            "card_bin": str(random.choice([411111, 520000, 370000])),
            "card_last4": str(random.randint(1000, 9999)),
        },
    }


def generate_mixed_evasion_batch(n: int = 50) -> list[dict]:
    """Generate a batch of n adversarial transactions using a random
    mix of all evasion strategies.

    Returns:
        List of n adversarial transaction dicts, each with
        is_fraud_ground_truth=True and metadata.evasion_strategy set.
    """
    generators = [
        generate_subtle_structuring,
        generate_stealth_wash_trade,
        generate_slow_velocity_abuse,
        generate_legit_looking_fraud,
        generate_bonus_abuse_evasion,
    ]
    return [random.choice(generators)() for _ in range(n)]
