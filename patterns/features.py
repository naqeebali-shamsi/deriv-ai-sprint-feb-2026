"""Pattern-derived features for risk scoring.

Queries stored pattern cards to compute graph-based features
for a given sender/receiver pair. These feed into the ML model,
creating a discovery-to-detection feedback loop.

Uses an inverted index (entity_id -> [pattern_cards]) built from
member_ids stored in each pattern card's detection_rule.
Pattern type classification uses detection_rule["type"] instead
of parsing description text.
"""
import json

# Module-level cache for pattern lookup.
# Refreshed each time compute_pattern_features is called with fresh DB data.
_pattern_cache: dict[str, list[dict]] | None = None
_pattern_cache_version: int = 0


def _build_inverted_index(rows: list[tuple]) -> dict[str, list[dict]]:
    """Build inverted index: {entity_id: [pattern_card_dicts]}.

    Each pattern_card_dict contains: pattern_type, rule_type, stats, confidence.
    """
    index: dict[str, list[dict]] = {}

    for pattern_type, detection_rule_json, stats_json, confidence in rows:
        rule = {}
        stats = {}
        if detection_rule_json:
            try:
                rule = json.loads(detection_rule_json)
            except (json.JSONDecodeError, TypeError):
                pass
        if stats_json:
            try:
                stats = json.loads(stats_json)
            except (json.JSONDecodeError, TypeError):
                pass

        member_ids = rule.get("member_ids", [])
        rule_type = rule.get("type", "")

        card_info = {
            "pattern_type": pattern_type,
            "rule_type": rule_type,
            "stats": stats,
            "confidence": confidence or 0.0,
            "rule": rule,
        }

        for entity_id in member_ids:
            if entity_id not in index:
                index[entity_id] = []
            index[entity_id].append(card_info)

    return index


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
        """SELECT pattern_type, detection_rule, stats, confidence
           FROM pattern_cards
           WHERE status = 'active'"""
    )
    rows = await cursor.fetchall()

    if not rows:
        return result

    # Build inverted index from member_ids
    index = _build_inverted_index(rows)

    # Lookup sender's patterns via inverted index — O(1) per entity
    sender_cards = index.get(sender_id, [])
    receiver_cards = index.get(receiver_id, [])

    sender_pattern_count = len(sender_cards)

    for card in sender_cards:
        rule_type = card["rule_type"]
        stats = card["stats"]

        if rule_type == "cycle":
            result["sender_in_ring"] = 1.0
        elif rule_type in ("hub_out", "hub_in"):
            degree = stats.get("out_degree") or stats.get("in_degree") or 0
            normalized_degree = min(degree / 20.0, 1.0)
            result["sender_is_hub"] = max(result["sender_is_hub"], normalized_degree)
        elif rule_type == "velocity":
            result["sender_in_velocity_cluster"] = 1.0
        elif rule_type == "dense_subgraph":
            result["sender_in_dense_cluster"] = 1.0

    for card in receiver_cards:
        rule_type = card["rule_type"]
        stats = card["stats"]

        if rule_type == "cycle":
            result["receiver_in_ring"] = 1.0
        elif rule_type in ("hub_out", "hub_in"):
            degree = stats.get("out_degree") or stats.get("in_degree") or 0
            normalized_degree = min(degree / 20.0, 1.0)
            result["receiver_is_hub"] = max(result["receiver_is_hub"], normalized_degree)

    # Normalize pattern count (cap at 5 patterns)
    result["pattern_count_sender"] = min(sender_pattern_count / 5.0, 1.0)

    return result
