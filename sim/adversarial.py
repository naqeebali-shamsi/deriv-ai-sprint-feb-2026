"""Adversarial transaction generators for model evaluation.

Generates transactions designed to evade the fraud detection model
using realistic evasion techniques. These do NOT use named fraud pools
(ring_a_*, smurfer_*, velocity_*, unauth_*, bonus_*) since those leak
identity through velocity features.

Each generator produces transactions that ARE fraud (ground truth)
but are designed to look legitimate to the scorer.

Stateful generators (stealth_wash_trade, subtle_structuring, slow_velocity_abuse)
use persistent ID pools so that patterns and velocity signals build up across
repeated calls, which is necessary for the backend's server-side velocity
computation to register meaningful signals.
"""
import random
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


# --- Persistent ID pools for stateful adversarial generators ---
_STEALTH_RING = [f"stealth_wt_{i}" for i in range(5)]
_stealth_ring_idx = 0

_SUBTLE_STRUCT_SENDERS = [f"struct_adv_{i}" for i in range(5)]

_SLOW_VELOCITY_SENDERS = [f"slowvel_adv_{i}" for i in range(5)]


def generate_subtle_structuring() -> dict:
    """Structuring that varies amounts near $10K threshold, uses persistent sender pool.

    Evasion tactics:
    - Amount between $8000-$9800 clustering near BSA $10K threshold
    - Persistent sender pool (5 IDs) so velocity builds across calls
    - Unique receiver_id each call (no velocity buildup on receiver side)
    - Web/mobile channels (not API)
    """
    sender = random.choice(_SUBTLE_STRUCT_SENDERS)
    amount = random.gauss(9200, 400)
    amount = max(7500, min(amount, 9800))

    return {
        "amount": round(amount, 2),
        "currency": random.choice(["USD", "EUR", "GBP"]),
        "sender_id": sender,
        "receiver_id": _random_id(),
        "txn_type": "transfer",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "evasion_strategy": "subtle_structuring",
            "fraud_type": "structuring",
            **_low_risk_metadata(),
        },
    }


def generate_stealth_wash_trade() -> dict:
    """Wash trading with persistent ring of 5 IDs creating circular flows.

    Evasion tactics:
    - Persistent ring of 5 accounts cycling sender->receiver
    - Small amounts $50-$500 (below amount_high threshold)
    - Varied channels (web, mobile, branch -- not API)
    - Circular flow builds graph patterns across calls
    """
    global _stealth_ring_idx
    sender = _STEALTH_RING[_stealth_ring_idx % len(_STEALTH_RING)]
    receiver = _STEALTH_RING[(_stealth_ring_idx + 1) % len(_STEALTH_RING)]
    _stealth_ring_idx += 1

    return {
        "amount": round(random.uniform(50, 500), 2),
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "transfer",
        "channel": random.choice(["web", "mobile", "branch"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "evasion_strategy": "stealth_wash_trade",
            "fraud_type": "wash_trading",
            **_low_risk_metadata(),
        },
    }


def generate_slow_velocity_abuse() -> dict:
    """Velocity abuse with persistent sender pool so velocity builds across calls.

    Evasion tactics:
    - Persistent pool of 5 sender IDs so server-side velocity counters accumulate
    - Moderate amounts $500-$2000 (not flagged as high)
    - Different receiver each time
    - Web channel (not API)
    """
    sender = random.choice(_SLOW_VELOCITY_SENDERS)

    return {
        "amount": round(random.uniform(500, 2000), 2),
        "currency": random.choice(["USD", "EUR"]),
        "sender_id": sender,
        "receiver_id": _random_id(),
        "txn_type": random.choice(["transfer", "withdrawal"]),
        "channel": "web",
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
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
    - Low-risk IP country (US/GB/DE)
    """
    return {
        "amount": round(random.uniform(5000, 15000), 2),
        "currency": "USD",
        "sender_id": _random_id(),
        "receiver_id": _random_id(),
        "txn_type": "transfer",
        "channel": "web",
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "evasion_strategy": "legit_looking_fraud",
            "fraud_type": "unauthorized_transfer",
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
        "amount": round(random.uniform(20, 80), 2),
        "currency": "USD",
        "sender_id": _random_id(),
        "receiver_id": f"platform_{random.randint(1, 50)}",
        "txn_type": "deposit",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "device_id": uuid4().hex[:8],
        "is_fraud_ground_truth": True,
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
