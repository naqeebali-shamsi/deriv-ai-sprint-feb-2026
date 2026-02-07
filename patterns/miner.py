"""Pattern mining module using networkx graph analysis.

Builds sender-receiver transaction graphs and discovers:
1. Fraud rings (SCC-based cycle detection for wash trading)
2. Hub accounts (HITS algorithm + z-score on degree distribution)
3. Velocity clusters (sliding window two-pointer)
4. Dense subgraphs (SCC + flow-weighted directed density)
"""
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import logging

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PatternCard:
    """Discovered fraud pattern."""
    pattern_id: str
    name: str
    description: str
    discovered_at: str
    status: str = "active"
    pattern_type: str = "behavioral"
    confidence: float = 0.0
    detection_rule: dict | None = None
    stats: dict | None = None
    related_txn_ids: list[str] | None = None


def build_transaction_graph(transactions: list[dict]) -> nx.DiGraph:
    """Build a directed graph from transactions.

    Nodes = user IDs (senders and receivers)
    Edges = transactions between them, with weight = total amount
    """
    G = nx.DiGraph()

    for txn in transactions:
        sender = txn.get("sender_id", "")
        receiver = txn.get("receiver_id", "")
        amount = txn.get("amount", 0)
        txn_id = txn.get("txn_id", "")

        if not sender or not receiver:
            continue

        if G.has_edge(sender, receiver):
            G[sender][receiver]["weight"] += amount
            G[sender][receiver]["count"] += 1
            G[sender][receiver]["txn_ids"].append(txn_id)
        else:
            G.add_edge(sender, receiver, weight=amount, count=1, txn_ids=[txn_id])

    return G


def detect_rings(G: nx.DiGraph, min_size: int = 3, max_size: int = 20) -> list[PatternCard]:
    """Detect circular fund flows (fraud rings / wash trading).

    Uses Tarjan's SCC algorithm to find strongly connected components,
    then extracts representative cycles from each SCC subgraph.
    SCCs of size >= min_size and <= max_size are ring candidates.
    Confidence is inverted: shorter cycles = higher confidence.
    Ranked by total edge weight (flow).
    """
    patterns = []

    # Use Tarjan's SCC — O(V+E) — to find ring candidates
    sccs = []
    for scc in nx.strongly_connected_components(G):
        if len(scc) < min_size:
            continue
        if len(scc) > max_size:
            logger.info("SCC of %d members filtered by max_size=%d in detect_rings", len(scc), max_size)
            continue
        sccs.append(scc)

    if not sccs:
        return patterns

    # Rank SCCs by total flow weight
    scc_data = []
    for scc in sccs:
        subgraph = G.subgraph(scc)
        total_flow = sum(d.get("weight", 0) for _, _, d in subgraph.edges(data=True))
        scc_data.append((scc, subgraph, total_flow))

    scc_data.sort(key=lambda x: -x[2])

    for scc, subgraph, total_flow in scc_data[:5]:
        member_ids = sorted(scc)

        # Extract one representative cycle from the SCC subgraph (bounded)
        representative_cycle = None
        try:
            for cycle in nx.simple_cycles(subgraph, length_bound=min(len(scc), 6)):
                if len(cycle) >= min_size:
                    representative_cycle = cycle
                    break
        except Exception:
            pass

        # Collect all txn_ids within the SCC
        txn_ids = []
        for u, v, data in subgraph.edges(data=True):
            txn_ids.extend(data.get("txn_ids", []))

        cycle_len = len(representative_cycle) if representative_cycle else len(scc)
        # Inverted confidence: shorter cycles = higher confidence
        confidence = min(0.95 - (cycle_len - min_size) * 0.1, 0.95)
        confidence = max(confidence, 0.4)

        if representative_cycle:
            members_str = " -> ".join(n[:12] for n in representative_cycle) + " -> " + representative_cycle[0][:12]
        else:
            members_str = ", ".join(n[:12] for n in member_ids[:8])

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"Circular Flow Ring ({len(scc)} members)",
            description=f"Circular fund flow detected: {members_str}. "
                        f"Total amount: ${total_flow:,.2f}. "
                        f"Possible wash trading or layering.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=confidence,
            detection_rule={
                "type": "cycle",
                "min_size": min_size,
                "cycle_length": cycle_len,
                "member_ids": member_ids,
            },
            stats={"members": len(scc), "total_amount": round(total_flow, 2),
                   "txn_count": len(txn_ids)},
            related_txn_ids=txn_ids[:20],
        ))

    return patterns


def detect_hubs(G: nx.DiGraph, threshold: int = 5) -> list[PatternCard]:
    """Detect hub accounts with unusually high connectivity.

    Uses HITS algorithm (Kleinberg) for hub/authority scores,
    combined with z-score on weighted degree distribution for adaptive thresholding.
    """
    patterns = []

    if G.number_of_nodes() < 2:
        return patterns

    # Compute HITS hub and authority scores — textbook algorithm for this problem
    try:
        hubs, authorities = nx.hits(G, max_iter=100, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        hubs = {n: 0.0 for n in G.nodes()}
        authorities = {n: 0.0 for n in G.nodes()}

    # Compute weighted out-degree (strength) and z-scores for adaptive thresholding
    out_strengths = {}
    in_strengths = {}
    for node in G.nodes():
        out_strengths[node] = sum(d.get("weight", 0) for _, _, d in G.out_edges(node, data=True))
        in_strengths[node] = sum(d.get("weight", 0) for _, _, d in G.in_edges(node, data=True))

    out_degrees = np.array([G.out_degree(n) for n in G.nodes()])
    in_degrees = np.array([G.in_degree(n) for n in G.nodes()])
    nodes_list = list(G.nodes())

    # Z-score thresholding: flag outliers > mean + 2*std
    def get_outliers(degrees, direction):
        if len(degrees) < 2 or np.std(degrees) == 0:
            return []
        mean_d = np.mean(degrees)
        std_d = np.std(degrees)
        z_threshold = mean_d + 2 * std_d
        return [
            (nodes_list[i], int(degrees[i]))
            for i in range(len(degrees))
            if degrees[i] >= z_threshold and degrees[i] >= 2  # minimum sanity
        ]

    # Out-degree hubs (senders to many receivers)
    out_hub_candidates = get_outliers(out_degrees, "out")
    # Sort by HITS hub score descending
    out_hub_candidates.sort(key=lambda x: -hubs.get(x[0], 0))

    for node, degree in out_hub_candidates[:3]:
        txn_ids = []
        total_amount = 0
        receivers = []
        for _, receiver, data in G.out_edges(node, data=True):
            txn_ids.extend(data.get("txn_ids", []))
            total_amount += data.get("weight", 0)
            receivers.append(receiver[:12])

        hub_score = hubs.get(node, 0)
        member_ids = sorted([node] + [r for _, r in G.out_edges(node)])
        # Confidence from HITS hub score, clamped
        confidence = min(0.4 + hub_score * 5.0, 0.95)

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"High-Activity Sender: {node[:15]}",
            description=f"Account {node[:15]} sent to {degree} unique receivers. "
                        f"Total outflow: ${total_amount:,.2f}. "
                        f"HITS hub score: {hub_score:.4f}. "
                        f"Possible structuring or fund distribution.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=confidence,
            detection_rule={
                "type": "hub_out",
                "threshold": threshold,
                "degree": degree,
                "hub_score": round(hub_score, 6),
                "member_ids": member_ids,
            },
            stats={"out_degree": degree, "total_amount": round(total_amount, 2),
                   "hub_score": round(hub_score, 6),
                   "weighted_degree": round(out_strengths.get(node, 0), 2),
                   "receivers_sample": receivers[:5]},
            related_txn_ids=txn_ids[:20],
        ))

    # In-degree hubs (receivers from many senders)
    in_hub_candidates = get_outliers(in_degrees, "in")
    # Sort by HITS authority score descending
    in_hub_candidates.sort(key=lambda x: -authorities.get(x[0], 0))

    for node, degree in in_hub_candidates[:3]:
        txn_ids = []
        total_amount = 0
        senders = []
        for sender, _, data in G.in_edges(node, data=True):
            txn_ids.extend(data.get("txn_ids", []))
            total_amount += data.get("weight", 0)
            senders.append(sender[:12])

        auth_score = authorities.get(node, 0)
        member_ids = sorted([node] + [s for s, _ in G.in_edges(node)])
        confidence = min(0.4 + auth_score * 5.0, 0.95)

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"High-Activity Receiver: {node[:15]}",
            description=f"Account {node[:15]} received from {degree} unique senders. "
                        f"Total inflow: ${total_amount:,.2f}. "
                        f"HITS authority score: {auth_score:.4f}. "
                        f"Possible money mule or collection point.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=confidence,
            detection_rule={
                "type": "hub_in",
                "threshold": threshold,
                "degree": degree,
                "authority_score": round(auth_score, 6),
                "member_ids": member_ids,
            },
            stats={"in_degree": degree, "total_amount": round(total_amount, 2),
                   "authority_score": round(auth_score, 6),
                   "weighted_degree": round(in_strengths.get(node, 0), 2),
                   "senders_sample": senders[:5]},
            related_txn_ids=txn_ids[:20],
        ))

    return patterns


def detect_velocity_clusters(transactions: list[dict], window_minutes: int = 60,
                              threshold: int = 5) -> list[PatternCard]:
    """Detect temporal velocity anomalies — bursts of transactions from same sender.

    Uses sliding window two-pointer: for each sender's sorted transactions,
    finds the maximum transaction count within any window_minutes window.
    Flags senders where max_count >= threshold.
    """
    patterns = []

    # Group transactions by sender
    by_sender: dict[str, list[dict]] = defaultdict(list)
    for txn in transactions:
        sender = txn.get("sender_id", "")
        if sender:
            by_sender[sender].append(txn)

    window_seconds = window_minutes * 60

    for sender, txns in by_sender.items():
        if len(txns) < threshold:
            continue

        # Sort by timestamp and parse to epoch seconds
        sorted_txns = sorted(txns, key=lambda t: t.get("timestamp", ""))
        timestamps = []
        for t in sorted_txns:
            ts_str = t.get("timestamp", "")
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamps.append(dt.timestamp())
            except (ValueError, TypeError):
                continue

        if len(timestamps) < threshold:
            continue

        # Sliding window two-pointer to find max count in any window
        max_count = 0
        max_window_start = 0
        left = 0
        for right in range(len(timestamps)):
            # Shrink window from left while it exceeds window_seconds
            while timestamps[right] - timestamps[left] > window_seconds:
                left += 1
            window_count = right - left + 1
            if window_count > max_count:
                max_count = window_count
                max_window_start = left

        if max_count < threshold:
            continue

        # Collect txn_ids from the densest window
        window_txns = sorted_txns[max_window_start:max_window_start + max_count]
        txn_ids = [t.get("txn_id", "") for t in window_txns]
        total_amount = sum(t.get("amount", 0) for t in window_txns)
        avg_amount = total_amount / max_count if max_count else 0

        member_ids = [sender]

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"Velocity Spike: {sender[:15]}",
            description=f"Account {sender[:15]} made {max_count} transactions "
                        f"within {window_minutes} minutes "
                        f"(avg ${avg_amount:,.2f} each, total ${total_amount:,.2f}). "
                        f"High-frequency activity detected.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="velocity",
            confidence=min(0.3 + max_count * 0.05, 0.85),
            detection_rule={
                "type": "velocity",
                "window_minutes": window_minutes,
                "threshold": threshold,
                "max_count_in_window": max_count,
                "member_ids": member_ids,
            },
            stats={"txn_count": max_count, "total_amount": round(total_amount, 2),
                   "avg_amount": round(avg_amount, 2),
                   "total_sender_txns": len(txns)},
            related_txn_ids=txn_ids[:20],
        ))

    # Sort by confidence descending, limit to top 5
    patterns.sort(key=lambda p: -p.confidence)
    return patterns[:5]


def detect_dense_subgraphs(G: nx.DiGraph, min_density: float = 0.5, max_size: int = 20) -> list[PatternCard]:
    """Detect dense subgraphs that may indicate coordinated fraud.

    Uses Tarjan's SCC to preserve directionality (not converting to undirected).
    Computes directed density within each SCC.
    Ranks by density * log(total_flow + 1).
    """
    patterns = []

    for scc in nx.strongly_connected_components(G):
        if len(scc) < 3:
            continue
        if len(scc) > max_size:
            logger.info("SCC of %d members filtered by max_size=%d in detect_dense_subgraphs", len(scc), max_size)
            continue

        subgraph = G.subgraph(scc)
        density = nx.density(subgraph)

        if density < min_density:
            continue

        # Collect all transaction IDs and total flow in this SCC
        txn_ids = []
        total_amount = 0
        for u, v, data in subgraph.edges(data=True):
            txn_ids.extend(data.get("txn_ids", []))
            total_amount += data.get("weight", 0)

        member_ids = sorted(scc)
        members_str = [n[:12] for n in member_ids[:8]]

        # Rank score: density * log(total_flow + 1)
        rank_score = density * math.log(total_amount + 1)

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"Dense Cluster ({len(scc)} accounts)",
            description=f"Tightly connected group of {len(scc)} accounts "
                        f"with density {density:.2f}. Members: {', '.join(members_str)}. "
                        f"Total flow: ${total_amount:,.2f}. Possible coordinated activity.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=min(density, 0.95),
            detection_rule={
                "type": "dense_subgraph",
                "min_density": min_density,
                "density": round(density, 4),
                "member_ids": member_ids,
            },
            stats={"members": len(scc), "density": round(density, 4),
                   "total_amount": round(total_amount, 2),
                   "edge_count": subgraph.number_of_edges(),
                   "rank_score": round(rank_score, 4)},
            related_txn_ids=txn_ids[:20],
        ))

    return sorted(patterns, key=lambda p: p.stats.get("rank_score", 0) if p.stats else 0, reverse=True)[:5]


def _structural_signature(pattern: PatternCard) -> str:
    """Compute a structural dedup key from sorted member_ids."""
    member_ids = []
    if pattern.detection_rule:
        member_ids = pattern.detection_rule.get("member_ids", [])
    if not member_ids:
        return pattern.pattern_id  # unique fallback
    key = tuple(sorted(member_ids))
    return hashlib.sha256(str(key).encode()).hexdigest()[:16]


def _infer_fraud_typology(pattern: PatternCard) -> tuple[str, str]:
    """Infer fraud typology and human-readable label from pattern characteristics.

    Returns (typology_code, typology_label).
    """
    rule = pattern.detection_rule or {}
    rule_type = rule.get("type", "")
    stats = pattern.stats or {}

    if rule_type == "cycle":
        return ("wash_trading", "Wash Trading")

    if rule_type == "hub_out":
        out_degree = stats.get("out_degree", 0)
        total_amount = stats.get("total_amount", 0)
        if out_degree > 0 and total_amount > 0:
            avg_amount = total_amount / out_degree
            if avg_amount < 5000:
                return ("structuring", "Structuring")
        return ("fund_distribution", "Fund Distribution")

    if rule_type == "hub_in":
        return ("money_mule", "Money Mule")

    if rule_type == "velocity":
        return ("velocity_abuse", "Velocity Abuse")

    if rule_type == "dense_subgraph":
        return ("coordinated_fraud", "Coordinated Fraud")

    return ("unclassified", "Unclassified")


def mine_patterns(transactions: list[dict]) -> list[PatternCard]:
    """Run all pattern mining algorithms on transaction data.

    Returns a list of discovered PatternCard objects.
    """
    if not transactions or len(transactions) < 3:
        return []

    patterns = []

    # Build graph
    G = build_transaction_graph(transactions)

    # 1. Detect circular flows (rings / wash trading)
    ring_patterns = detect_rings(G)
    patterns.extend(ring_patterns)

    # 2. Detect hub accounts
    hub_patterns = detect_hubs(G, threshold=5)
    patterns.extend(hub_patterns)

    # 3. Detect velocity clusters
    velocity_patterns = detect_velocity_clusters(transactions, threshold=5)
    patterns.extend(velocity_patterns)

    # 4. Detect dense subgraphs
    dense_patterns = detect_dense_subgraphs(G, min_density=0.5)
    patterns.extend(dense_patterns)

    return patterns


async def run_mining_job_async(db) -> list[PatternCard]:
    """Run pattern mining on recent transactions from the database.

    Queries last 24h of transactions, runs all mining algorithms,
    and stores discovered patterns as pattern cards.
    Deduplicates by structural signature (sorted member_ids hash).
    """
    now = datetime.utcnow().isoformat()

    # Clean up over-sized false-positive SCC patterns (rings/dense only — NOT hubs)
    # Hubs naturally have many member_ids (hub + all connected nodes); that's expected.
    MAX_SCC_PATTERN_SIZE = 20
    SCC_TYPES = ("cycle", "dense_subgraph")
    try:
        count_cursor = await db.execute(
            """SELECT COUNT(*) FROM pattern_cards
               WHERE status = 'active'
               AND detection_rule IS NOT NULL
               AND json_extract(detection_rule, '$.type') IN ('cycle', 'dense_subgraph')
               AND json_array_length(json_extract(detection_rule, '$.member_ids')) > ?""",
            (MAX_SCC_PATTERN_SIZE,),
        )
        count_row = await count_cursor.fetchone()
        stale_count = count_row[0] if count_row else 0
        if stale_count > 0:
            logger.info("Cleaning up %d oversized SCC pattern cards (member_ids > %d)", stale_count, MAX_SCC_PATTERN_SIZE)
            await db.execute(
                """DELETE FROM pattern_cards
                   WHERE status = 'active'
                   AND detection_rule IS NOT NULL
                   AND json_extract(detection_rule, '$.type') IN ('cycle', 'dense_subgraph')
                   AND json_array_length(json_extract(detection_rule, '$.member_ids')) > ?""",
                (MAX_SCC_PATTERN_SIZE,),
            )
            await db.commit()
    except Exception:
        logger.info("json1 not available, using Python-side cleanup for oversized SCC patterns")
        cursor = await db.execute(
            "SELECT pattern_id, detection_rule FROM pattern_cards WHERE status = 'active' AND detection_rule IS NOT NULL"
        )
        rows = await cursor.fetchall()
        to_delete = []
        for pid, rule_json in rows:
            try:
                rule = json.loads(rule_json)
                rule_type = rule.get("type", "")
                if rule_type not in SCC_TYPES:
                    continue
                member_ids = rule.get("member_ids", [])
                if isinstance(member_ids, list) and len(member_ids) > MAX_SCC_PATTERN_SIZE:
                    to_delete.append(pid)
            except (json.JSONDecodeError, TypeError):
                continue
        if to_delete:
            logger.info("Cleaning up %d oversized SCC pattern cards (Python fallback)", len(to_delete))
            for pid in to_delete[:100]:
                await db.execute("DELETE FROM pattern_cards WHERE pattern_id = ?", (pid,))
            await db.commit()

    # Fetch recent transactions
    cursor = await db.execute(
        """SELECT txn_id, timestamp, amount, currency, sender_id, receiver_id,
                  txn_type, channel
           FROM transactions
           WHERE timestamp >= datetime(?, '-24 hours')
           ORDER BY timestamp DESC""",
        (now,),
    )
    rows = await cursor.fetchall()

    transactions = [
        {"txn_id": r[0], "timestamp": r[1], "amount": r[2], "currency": r[3],
         "sender_id": r[4], "receiver_id": r[5], "txn_type": r[6], "channel": r[7]}
        for r in rows
    ]

    # Mine patterns
    patterns = mine_patterns(transactions)

    # Build existing structural signatures for dedup
    existing_cursor = await db.execute(
        "SELECT name, detection_rule FROM pattern_cards WHERE status = 'active'"
    )
    existing_rows = await existing_cursor.fetchall()

    existing_signatures = set()
    for name, rule_json in existing_rows:
        if rule_json:
            try:
                rule = json.loads(rule_json)
                member_ids = rule.get("member_ids", [])
                if member_ids:
                    key = tuple(sorted(member_ids))
                    sig = hashlib.sha256(str(key).encode()).hexdigest()[:16]
                    existing_signatures.add(sig)
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
        # Fallback: use name for legacy patterns without member_ids
        existing_signatures.add(name)

    new_count = 0
    for pattern in patterns:
        sig = _structural_signature(pattern)
        if sig not in existing_signatures:
            existing_signatures.add(sig)
            # Enrich with fraud typology AFTER dedup (preserves clean names for signature matching)
            typology_code, typology_label = _infer_fraud_typology(pattern)
            if pattern.detection_rule:
                pattern.detection_rule["fraud_typology"] = typology_code
            if typology_label not in ("Unclassified",) and typology_label not in pattern.name:
                pattern.name = f"[{typology_label}] {pattern.name}"
            await db.execute(
                """INSERT INTO pattern_cards
                   (pattern_id, name, description, discovered_at, status, pattern_type,
                    confidence, detection_rule, stats, related_txn_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pattern.pattern_id, pattern.name, pattern.description,
                 pattern.discovered_at, pattern.status, pattern.pattern_type,
                 pattern.confidence,
                 json.dumps(pattern.detection_rule) if pattern.detection_rule else None,
                 json.dumps(pattern.stats) if pattern.stats else None,
                 json.dumps(pattern.related_txn_ids) if pattern.related_txn_ids else None),
            )
            new_count += 1

    await db.commit()
    return patterns
