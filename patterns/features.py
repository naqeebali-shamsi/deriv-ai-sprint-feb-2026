"""Pattern-derived features for risk scoring.

Queries stored pattern cards to compute graph-based features
for a given sender/receiver pair. These feed into the ML model,
creating a discovery-to-detection feedback loop.
"""
import json


async def compute_pattern_features(db, sender_id: str, receiver_id: str) -> dict:
    """Compute pattern-based features from stored pattern cards.

    Returns dict with 7 features derived from active pattern cards:
    - sender_in_ring: 1.0 if sender appears in any ring pattern, else 0.0
    - sender_is_hub: normalized hub degree if sender is a hub, else 0.0
    - sender_in_velocity_cluster: 1.0 if sender has velocity spike, else 0.0
    - sender_in_dense_cluster: 1.0 if sender is in dense subgraph, else 0.0
    - receiver_in_ring: same for receiver
    - receiver_is_hub: same for receiver
    - pattern_count_sender: number of distinct patterns involving sender, normalized
    """
    result = {
        "sender_in_ring": 0.0,
        "sender_is_hub": 0.0,
        "sender_in_velocity_cluster": 0.0,
        "sender_in_dense_cluster": 0.0,
        "receiver_in_ring": 0.0,
        "receiver_is_hub": 0.0,
        "pattern_count_sender": 0.0,
    }

    cursor = await db.execute(
        """SELECT pattern_type, description, stats, confidence
           FROM pattern_cards
           WHERE status = 'active'"""
    )
    rows = await cursor.fetchall()

    if not rows:
        return result

    sender_pattern_count = 0

    for pattern_type, description, stats_json, confidence in rows:
        desc = description or ""
        stats = {}
        if stats_json:
            try:
                stats = json.loads(stats_json)
            except (json.JSONDecodeError, TypeError):
                pass

        sender_in = sender_id in desc
        receiver_in = receiver_id in desc

        if sender_in:
            sender_pattern_count += 1

        if pattern_type == "graph":
            # Check for ring patterns (cycle / circular flow)
            if "circular" in desc.lower() or "ring" in desc.lower():
                if sender_in:
                    result["sender_in_ring"] = 1.0
                if receiver_in:
                    result["receiver_in_ring"] = 1.0

            # Check for hub patterns
            elif "hub" in desc.lower() or "high-activity" in desc.lower():
                degree = stats.get("out_degree") or stats.get("in_degree") or 0
                normalized_degree = min(degree / 20.0, 1.0)
                if sender_in:
                    result["sender_is_hub"] = max(result["sender_is_hub"], normalized_degree)
                if receiver_in:
                    result["receiver_is_hub"] = max(result["receiver_is_hub"], normalized_degree)

            # Check for dense cluster patterns
            elif "dense" in desc.lower() or "cluster" in desc.lower():
                if sender_in:
                    result["sender_in_dense_cluster"] = 1.0

        elif pattern_type == "velocity":
            if sender_in:
                result["sender_in_velocity_cluster"] = 1.0

    # Normalize pattern count (cap at 5 patterns)
    result["pattern_count_sender"] = min(sender_pattern_count / 5.0, 1.0)

    return result
