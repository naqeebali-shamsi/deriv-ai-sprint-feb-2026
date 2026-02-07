#!/usr/bin/env python3
"""Seed the demo database with pre-generated transactions.

Sends ~200 transactions (mix of legit + fraud) to the running backend,
then triggers model retraining and pattern mining so the demo starts
with a populated, trained system.

Usage:
    python scripts/seed_demo.py [--url http://localhost:8000] [--count 200]
"""
import argparse
import random
import sys

import httpx

# Import the simulator generators directly
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from sim.main import FRAUD_RATE, generate_transaction


def seed(api_url: str = "http://localhost:8000", count: int = 200):
    """Seed the backend with synthetic transactions."""
    print(f"Seeding {count} transactions to {api_url} ...")
    print(f"  Fraud rate: {FRAUD_RATE * 100:.0f}%")
    print("-" * 60)

    client = httpx.Client(timeout=30)
    stats = {"total": 0, "fraud": 0, "legit": 0, "flagged": 0, "errors": 0}

    for i in range(count):
        is_fraud = random.random() < FRAUD_RATE
        txn = generate_transaction(is_fraud=is_fraud)

        try:
            resp = client.post(f"{api_url}/transactions", json=txn)
            if resp.status_code == 200:
                data = resp.json()
                stats["total"] += 1
                if is_fraud:
                    stats["fraud"] += 1
                else:
                    stats["legit"] += 1
                if data.get("decision") != "approve":
                    stats["flagged"] += 1

                # Progress indicator every 50
                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{count}] sent — "
                          f"{stats['fraud']} fraud, {stats['legit']} legit, "
                          f"{stats['flagged']} flagged")
            elif resp.status_code == 503:
                print("  [ERROR] Model missing. Run scripts/bootstrap_model.py first.")
                break
            else:
                stats["errors"] += 1
                if stats["errors"] <= 3:
                    print(f"  [ERROR] {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 3:
                print(f"  [ERROR] {e}")

    print("-" * 60)
    print(f"Seeding complete: {stats['total']} txns "
          f"({stats['fraud']} fraud, {stats['legit']} legit)")
    print(f"  Flagged: {stats['flagged']}, Errors: {stats['errors']}")

    # Step 2: Retrain model from ground truth
    print("\nRetraining model from ground truth labels...")
    try:
        resp = client.post(f"{api_url}/retrain-from-ground-truth", timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("trained"):
                m = result.get("metrics", {})
                print(f"  Model trained: {result['version']}")
                print(f"  AUC-ROC: {m.get('auc_roc', 'N/A')}, "
                      f"F1: {m.get('f1', 'N/A')}, "
                      f"Precision: {m.get('precision', 'N/A')}, "
                      f"Recall: {m.get('recall', 'N/A')}")
            else:
                print(f"  Training skipped: {result.get('error', 'unknown')}")
        else:
            print(f"  [ERROR] Retrain failed: {resp.status_code}")
    except Exception as e:
        print(f"  [ERROR] Retrain failed: {e}")

    # Step 3: Run pattern mining
    print("\nRunning pattern mining...")
    try:
        resp = client.post(f"{api_url}/mine-patterns", timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            print(f"  Patterns found: {result['patterns_found']}")
            for p in result.get("patterns", []):
                print(f"    - {p['name']} ({p['type']}, confidence: {p['confidence']:.2f})")
        else:
            print(f"  [ERROR] Mining failed: {resp.status_code}")
    except Exception as e:
        print(f"  [ERROR] Mining failed: {e}")

    # Step 4: Send a second smaller batch (post-training) to show ML model in action
    print("\nSending 50 more transactions with trained ML model...")
    post_train_stats = {"flagged": 0, "total": 0}
    for i in range(50):
        is_fraud = random.random() < FRAUD_RATE
        txn = generate_transaction(is_fraud=is_fraud)
        try:
            resp = client.post(f"{api_url}/transactions", json=txn)
            if resp.status_code == 200:
                data = resp.json()
                post_train_stats["total"] += 1
                if data.get("decision") != "approve":
                    post_train_stats["flagged"] += 1
        except Exception:
            pass

    print(f"  Post-training: {post_train_stats['flagged']}/{post_train_stats['total']} flagged")

    # Final stats
    print("\n" + "=" * 60)
    print("Demo seed complete! System is ready.")
    print(f"  Total transactions: {stats['total'] + post_train_stats['total']}")
    print("  Model: trained with ground truth")
    print("  Patterns: mined from transaction graph")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo database")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--count", type=int, default=200, help="Number of initial transactions")
    args = parser.parse_args()

    seed(api_url=args.url, count=args.count)
