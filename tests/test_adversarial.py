"""Adversarial evaluation tests.

Tests the fraud detection model against evasion-designed transactions.
Reports detection rates on both standard and adversarial test sets.
"""
import re

from risk.scorer import score_transaction
from sim.adversarial import (
    generate_bonus_abuse_evasion,
    generate_legit_looking_fraud,
    generate_mixed_evasion_batch,
    generate_slow_velocity_abuse,
    generate_stealth_wash_trade,
    generate_subtle_structuring,
)

# Named fraud pool patterns from sim/main.py that adversarial txns must NOT use
_NAMED_POOL_PATTERN = re.compile(
    r"^(ring_[ab]_|smurfer_|velocity_|spoofer_|bonus_)"
)


def _score_batch(txns: list[dict]) -> list[tuple[dict, object]]:
    """Score a list of transactions and return (txn, result) pairs."""
    return [(txn, score_transaction(txn)) for txn in txns]


def _detection_rate(results: list[tuple[dict, object]]) -> float:
    """Fraction of transactions flagged (review or block)."""
    if not results:
        return 0.0
    flagged = sum(1 for _, r in results if r.decision in ("review", "block"))
    return flagged / len(results)


class TestAdversarialDetection:
    """Score adversarial transactions and report detection rates.

    These tests assert the pipeline does not crash. Detection rates are
    reported via print() for human review -- the model may or may not
    catch these evasion-designed transactions.
    """

    def test_subtle_structuring_scored(self):
        txns = [generate_subtle_structuring() for _ in range(20)]
        results = _score_batch(txns)
        rate = _detection_rate(results)
        print(f"\n[Subtle Structuring] Detection rate: {rate:.0%} "
              f"({int(rate*20)}/20 flagged)")
        for txn, r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.decision in ("approve", "review", "block")

    def test_stealth_wash_trade_scored(self):
        txns = [generate_stealth_wash_trade() for _ in range(20)]
        results = _score_batch(txns)
        rate = _detection_rate(results)
        print(f"\n[Stealth Wash Trade] Detection rate: {rate:.0%} "
              f"({int(rate*20)}/20 flagged)")
        for txn, r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.decision in ("approve", "review", "block")

    def test_slow_velocity_scored(self):
        txns = [generate_slow_velocity_abuse() for _ in range(20)]
        results = _score_batch(txns)
        rate = _detection_rate(results)
        print(f"\n[Slow Velocity Abuse] Detection rate: {rate:.0%} "
              f"({int(rate*20)}/20 flagged)")
        for txn, r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.decision in ("approve", "review", "block")

    def test_legit_looking_fraud_scored(self):
        txns = [generate_legit_looking_fraud() for _ in range(20)]
        results = _score_batch(txns)
        rate = _detection_rate(results)
        print(f"\n[Legit-Looking Fraud] Detection rate: {rate:.0%} "
              f"({int(rate*20)}/20 flagged)")
        for txn, r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.decision in ("approve", "review", "block")

    def test_bonus_abuse_evasion_scored(self):
        txns = [generate_bonus_abuse_evasion() for _ in range(20)]
        results = _score_batch(txns)
        rate = _detection_rate(results)
        print(f"\n[Bonus Abuse Evasion] Detection rate: {rate:.0%} "
              f"({int(rate*20)}/20 flagged)")
        for txn, r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.decision in ("approve", "review", "block")


class TestAdversarialReport:
    """Compare detection rates between standard and adversarial fraud."""

    def test_adversarial_vs_standard_detection_rates(self):
        from sim.main import generate_transaction

        # Generate 50 adversarial fraud transactions
        adv_txns = generate_mixed_evasion_batch(n=50)
        adv_results = _score_batch(adv_txns)
        adv_rate = _detection_rate(adv_results)

        # Generate 50 standard fraud transactions (from sim.main pools)
        std_txns = [generate_transaction(is_fraud=True) for _ in range(50)]
        std_results = _score_batch(std_txns)
        std_rate = _detection_rate(std_results)

        # Print comparison report
        print("\n" + "=" * 70)
        print("ADVERSARIAL vs STANDARD FRAUD DETECTION REPORT")
        print("=" * 70)
        print(f"  Standard fraud detection rate:    {std_rate:.0%} "
              f"({int(std_rate*50)}/50 flagged)")
        print(f"  Adversarial fraud detection rate:  {adv_rate:.0%} "
              f"({int(adv_rate*50)}/50 flagged)")
        print(f"  Detection gap:                     "
              f"{(std_rate - adv_rate):.0%}")
        print("-" * 70)

        # Per-strategy breakdown from adversarial batch
        strategy_counts: dict[str, list[str]] = {}
        for txn, r in adv_results:
            strategy = txn.get("metadata", {}).get("evasion_strategy", "unknown")
            strategy_counts.setdefault(strategy, []).append(r.decision)

        print("  Per-strategy breakdown:")
        for strategy, decisions in sorted(strategy_counts.items()):
            flagged = sum(1 for d in decisions if d in ("review", "block"))
            total = len(decisions)
            pct = flagged / total if total else 0
            print(f"    {strategy:<30s} {pct:>5.0%}  ({flagged}/{total})")

        print("=" * 70)

        # Assert pipeline didn't crash -- we do NOT assert specific rates
        assert len(adv_results) == 50
        assert len(std_results) == 50


class TestEvasionCharacteristics:
    """Verify structural properties of adversarial transactions."""

    def test_adversarial_txns_have_ground_truth(self):
        """All adversarial txns should have is_fraud_ground_truth = True."""
        batch = generate_mixed_evasion_batch(n=30)
        for txn in batch:
            assert txn["is_fraud_ground_truth"] is True, (
                f"Missing ground truth on txn {txn.get('txn_id')}"
            )

    def test_adversarial_txns_have_strategy_metadata(self):
        """All adversarial txns should have evasion_strategy in metadata."""
        batch = generate_mixed_evasion_batch(n=30)
        for txn in batch:
            meta = txn.get("metadata", {})
            assert "evasion_strategy" in meta, (
                f"Missing evasion_strategy in metadata for {txn.get('txn_id')}"
            )
            assert meta["evasion_strategy"] in (
                "subtle_structuring",
                "stealth_wash_trade",
                "slow_velocity_abuse",
                "legit_looking_fraud",
                "bonus_abuse_evasion",
            )

    def test_no_named_fraud_pools(self):
        """No adversarial txn should use named fraud pool sender IDs."""
        batch = generate_mixed_evasion_batch(n=50)
        for txn in batch:
            sender = txn.get("sender_id", "")
            receiver = txn.get("receiver_id", "")
            assert not _NAMED_POOL_PATTERN.match(sender), (
                f"Sender '{sender}' uses a named fraud pool ID"
            )
            assert not _NAMED_POOL_PATTERN.match(receiver), (
                f"Receiver '{receiver}' uses a named fraud pool ID"
            )

    def test_all_generators_produce_valid_txns(self):
        """Each individual generator should produce scorer-compatible dicts."""
        generators = [
            generate_subtle_structuring,
            generate_stealth_wash_trade,
            generate_slow_velocity_abuse,
            generate_legit_looking_fraud,
            generate_bonus_abuse_evasion,
        ]
        required_fields = [
            "amount", "currency", "sender_id",
            "receiver_id", "txn_type", "channel",
        ]
        for gen in generators:
            txn = gen()
            for field in required_fields:
                assert field in txn, (
                    f"{gen.__name__} missing field '{field}'"
                )
            # Should be scorable without error
            result = score_transaction(txn)
            assert 0.0 <= result.score <= 1.0
