"""Transaction simulator - generates synthetic transactions with realistic fraud typologies."""
import asyncio
import math
import random
from datetime import datetime
from uuid import uuid4

import httpx
from faker import Faker

from config import get_settings

fake = Faker()

_settings = get_settings()
API_URL = _settings.backend_url

# Fraud injection rate (from env, default 10% for demo visibility)
FRAUD_RATE = _settings.FRAUD_RATE

# --- User Pools (for consistent behavior patterns) ---
NORMAL_USERS = [f"user_{i}" for i in range(1, 801)]
FRAUD_RING_A = [f"ring_a_{i}" for i in range(1, 6)]  # 5-member ring
FRAUD_RING_B = [f"ring_b_{i}" for i in range(1, 4)]  # 3-member ring
STRUCTURERS = [f"smurfer_{i}" for i in range(1, 4)]
VELOCITY_ABUSERS = [f"velocity_{i}" for i in range(1, 4)]
BONUS_ABUSERS = [f"bonus_{i}" for i in range(1, 6)]

# Shared devices/IPs for bonus abuse detection
SHARED_DEVICES = [f"dev_{uuid4().hex[:6]}" for _ in range(2)]
SHARED_IPS = [fake.ipv4() for _ in range(2)]

# Fraud typology weights (how often each type appears when fraud is chosen)
FRAUD_TYPES = {
    "structuring": 0.25,      # Many small txns below thresholds
    "velocity_abuse": 0.20,   # Rapid-fire from same sender
    "wash_trading": 0.20,     # Circular A->B->C->A flows (Deriv-specific)
    "spoofing": 0.15,         # Large amounts, transfer type (Deriv-specific)
    "bonus_abuse": 0.20,      # Multiple linked accounts, small deposits
}


def _pick_fraud_type() -> str:
    """Pick a fraud type based on weights."""
    types = list(FRAUD_TYPES.keys())
    weights = list(FRAUD_TYPES.values())
    return random.choices(types, weights=weights, k=1)[0]


def _lognormal_amount(mean: float, sigma: float, min_val: float = 1.0, max_val: float = 100000.0) -> float:
    """Generate log-normal distributed amount."""
    raw = random.lognormvariate(math.log(mean), sigma)
    return round(max(min_val, min(max_val, raw)), 2)


def _generate_enterprise_metadata(txn_type: str, channel: str) -> dict:
    """Generate realistic enterprise-grade metadata (ISO 20022 / Fintech style)."""
    meta = {}
    
    # 1. Geo / Network Telemetry
    country = random.choices(["US", "GB", "DE", "FR", "SG", "NG", "BR"], weights=[40, 20, 10, 5, 10, 10, 5])[0]
    meta["ip_country"] = country
    meta["user_agent"] = fake.user_agent()
    meta["session_id"] = f"sess_{uuid4().hex[:12]}"
    meta["login_hash"] = uuid4().hex[:8]
    
    # 2. Payment Rails (Mocking ISO 20022 fields)
    if txn_type in ("transfer", "payment"):
        meta["remittance_info"] = fake.sentence(nb_words=3)
        meta["instruction_id"] = f"instr_{uuid4().hex[:16]}"
        meta["end_to_end_id"] = f"e2e_{uuid4().hex[:16]}"
        meta["clearing_system"] = random.choice(["ACH", "SEPA", "SWIFT", "RTP"])
    
    # 3. Card Data (if relevant)
    if txn_type == "deposit":
        meta["card_bin"] = str(random.randint(400000, 499999))
        meta["card_last4"] = str(random.randint(1000, 9999))
        meta["3ds_version"] = "2.1.0"
        
    return meta


def generate_legit_transaction() -> dict:
    """Generate a legitimate transaction with realistic distribution.

    Amount distribution: log-normal centered ~$200, with long tail up to $20K.
    This means legit transactions CAN be high-value (business payments, etc.).
    """
    amount = _lognormal_amount(mean=200, sigma=1.2, min_val=5, max_val=25000)
    sender = random.choice(NORMAL_USERS)
    receiver = random.choice(NORMAL_USERS)
    # Avoid self-transfer
    while receiver == sender:
        receiver = random.choice(NORMAL_USERS)

    return {
        "amount": amount,
        "currency": random.choice(["USD", "USD", "USD", "EUR", "GBP"]),  # mostly USD
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": random.choice(["transfer", "deposit", "withdrawal", "payment"]),
        "channel": random.choices(["web", "mobile", "api", "branch"], weights=[40, 35, 15, 10])[0],
        "ip_address": fake.ipv4(),
        "device_id": str(uuid4())[:8],
        "is_fraud_ground_truth": False,
        "metadata": _generate_enterprise_metadata("transfer", "web"),
    }


def generate_structuring_transaction() -> dict:
    """Structuring (smurfing): many small transactions below reporting thresholds.

    Key signals: amount clustering just below $1000, same sender, many receivers.
    Overlaps with legit: amount range $200-$950 (overlaps with normal user range).
    """
    amount = random.uniform(200, 950)
    sender = random.choice(STRUCTURERS)
    receiver = random.choice(NORMAL_USERS)

    return {
        "amount": round(amount, 2),
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "transfer",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": fake.ipv4(),
        "device_id": str(uuid4())[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "structuring",
            **_generate_enterprise_metadata("transfer", "web")
        },
    }


def generate_velocity_abuse_transaction() -> dict:
    """Velocity abuse: rapid-fire transactions from the same sender.

    Key signals: same sender, varied amounts, high frequency (simulated via metadata).
    Overlaps with legit: amounts can be any range.
    """
    amount = _lognormal_amount(mean=500, sigma=0.8, min_val=50, max_val=15000)
    sender = random.choice(VELOCITY_ABUSERS)
    receiver = random.choice(NORMAL_USERS)

    return {
        "amount": amount,
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": random.choice(["transfer", "withdrawal"]),
        "channel": "api",  # Automated = typically API channel
        "ip_address": fake.ipv4(),
        "device_id": str(uuid4())[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "velocity_abuse",
            **_generate_enterprise_metadata("transfer", "api")
        },
    }


def generate_wash_trading_transaction() -> dict:
    """Wash trading (Deriv-specific): circular fund flows within a ring.

    Key signals: ring members trading with each other, similar amounts round-tripping.
    Overlaps with legit: amounts can be moderate.
    """
    ring = random.choice([FRAUD_RING_A, FRAUD_RING_B])
    idx = random.randint(0, len(ring) - 1)
    sender = ring[idx]
    receiver = ring[(idx + 1) % len(ring)]  # Next person in ring

    # Ring amounts cluster around a base (round-tripping the same money)
    base_amount = random.choice([1000, 2500, 5000, 10000])
    amount = round(base_amount * random.uniform(0.95, 1.05), 2)  # Small variation

    return {
        "amount": amount,
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "transfer",
        "channel": random.choice(["web", "api"]),
        "ip_address": fake.ipv4(),
        "device_id": str(uuid4())[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "wash_trading",
            **_generate_enterprise_metadata("transfer", "web")
        },
    }


def generate_spoofing_transaction() -> dict:
    """Spoofing/Layering (Deriv-specific): large deceptive orders.

    Key signals: large amounts, transfer type, often via API.
    Overlaps with legit: high-value transactions exist in normal trading too.
    """
    amount = _lognormal_amount(mean=8000, sigma=0.6, min_val=2000, max_val=50000)
    sender = f"spoofer_{random.randint(1, 5)}"
    receiver = random.choice(NORMAL_USERS)

    return {
        "amount": amount,
        "currency": random.choice(["USD", "EUR"]),
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "transfer",
        "channel": "api",
        "ip_address": fake.ipv4(),
        "device_id": str(uuid4())[:8],
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "spoofing",
            **_generate_enterprise_metadata("transfer", "api")
        },
    }


def generate_bonus_abuse_transaction() -> dict:
    """Bonus abuse (Deriv-specific): multiple accounts from same device/IP claiming bonuses.

    Key signals: shared device_id or ip_address, small deposit amounts, deposit type.
    Overlaps with legit: small deposits are normal behavior.
    """
    amount = random.uniform(10, 100)  # Small deposits to trigger bonuses
    sender = random.choice(BONUS_ABUSERS)
    receiver = f"platform_bonus_{random.randint(1, 3)}"

    return {
        "amount": round(amount, 2),
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "deposit",
        "channel": random.choice(["web", "mobile"]),
        "ip_address": random.choice(SHARED_IPS),  # Shared IP across accounts
        "device_id": random.choice(SHARED_DEVICES),  # Shared device
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "bonus_abuse",
            **_generate_enterprise_metadata("deposit", "web")
        },
    }


# Fraud generators by type
_FRAUD_GENERATORS = {
    "structuring": generate_structuring_transaction,
    "velocity_abuse": generate_velocity_abuse_transaction,
    "wash_trading": generate_wash_trading_transaction,
    "spoofing": generate_spoofing_transaction,
    "bonus_abuse": generate_bonus_abuse_transaction,
}


def generate_hero_transaction() -> dict:
    """Generate the 'Hero' transaction for the demo golden path.
    
    This transaction triggers the pre-canned 'perfect' LLM response.
    """
    amount = 12500.00
    sender = "ring_leader_A1"
    receiver = "mule_B2"
    
    return {
        "amount": amount,
        "currency": "USD",
        "sender_id": sender,
        "receiver_id": receiver,
        "txn_type": "transfer",
        "channel": "api",
        "ip_address": "192.168.1.100",
        "device_id": "bad_device_x99",
        "is_fraud_ground_truth": True,
        "metadata": {
            "fraud_type": "wash_trading",
            "demo_hero": "wash_trading_hero",
            **_generate_enterprise_metadata("transfer", "api")
        },
    }


def generate_transaction(is_fraud: bool = False, fraud_type: str | None = None) -> dict:
    """Generate a synthetic transaction.

    Args:
        is_fraud: Whether to generate a fraudulent transaction.
        fraud_type: Specific fraud type (if None, randomly selected).
    """
    if is_fraud:
        ft = fraud_type or _pick_fraud_type()
        generator = _FRAUD_GENERATORS.get(ft, generate_spoofing_transaction)
        return generator()
    else:
        return generate_legit_transaction()


async def send_transaction(client: httpx.AsyncClient, txn: dict):
    """Send transaction to backend."""
    try:
        resp = await client.post(f"{API_URL}/transactions", json=txn, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            score = data.get("risk_score", 0) or 0
            decision = data.get("decision", "?")
            fraud_tag = "[FRAUD]" if txn["is_fraud_ground_truth"] else "[LEGIT]"
            score_bar = "#" * int(score * 10)
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] {fraud_tag} "
                f"${txn['amount']:>10.2f} {txn['txn_type']:<10} "
                f"score={score:.3f} [{score_bar:<10}] {decision}"
            )
        else:
            print(f"[ERROR] {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] {e}")


async def run_simulator(tps: float = 1.0, duration: int | None = None):
    """Run the transaction simulator.

    Args:
        tps: Transactions per second
        duration: Run for N seconds (None = forever)
    """
    print(f"Starting simulator: {tps} TPS, fraud rate: {FRAUD_RATE*100:.0f}%")
    print(f"Fraud typologies: {', '.join(FRAUD_TYPES.keys())}")
    print(f"Sending to: {API_URL}")
    print("-" * 80)

    interval = 1.0 / tps
    start = asyncio.get_event_loop().time()
    counts = {"total": 0, "fraud": 0, "legit": 0}

    async with httpx.AsyncClient() as client:
        while True:
            # Inject HERO transaction every 25th txn (for demo predictability)
            if counts["total"] > 0 and counts["total"] % 25 == 0:
                txn = generate_hero_transaction()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Injecting known-pattern scenario transaction")
                is_fraud = True
            else:
                is_fraud = random.random() < FRAUD_RATE
                txn = generate_transaction(is_fraud=is_fraud)
            
            await send_transaction(client, txn)

            counts["total"] += 1
            counts["fraud" if is_fraud else "legit"] += 1

            if duration and (asyncio.get_event_loop().time() - start) > duration:
                print(f"\nSimulator finished. Sent {counts['total']} txns "
                      f"({counts['fraud']} fraud, {counts['legit']} legit)")
                break

            await asyncio.sleep(interval)


def main():
    """Entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Transaction Simulator")
    parser.add_argument("--tps", type=float, default=1.0, help="Transactions per second")
    parser.add_argument("--duration", type=int, default=None, help="Run for N seconds")
    args = parser.parse_args()

    asyncio.run(run_simulator(tps=args.tps, duration=args.duration))


if __name__ == "__main__":
    main()
