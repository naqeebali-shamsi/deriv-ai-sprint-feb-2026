"""Pattern mining module using networkx graph analysis.

Builds sender-receiver transaction graphs and discovers:
1. Fraud rings (dense subgraphs / connected components)
2. Hub accounts (high-degree nodes)
3. Velocity clusters (temporal bursts from same sender)
4. Circular flows (cycle detection for wash trading)
"""
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from uuid import uuid4

import networkx as nx


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


def detect_rings(G: nx.DiGraph, min_size: int = 3) -> list[PatternCard]:
    """Detect circular fund flows (fraud rings / wash trading).

    Looks for cycles in the transaction graph where money flows
    A -> B -> C -> A (or longer).
    """
    patterns = []
    try:
        # Find all simple cycles up to length 6
        cycles = list(nx.simple_cycles(G, length_bound=6))
    except Exception:
        cycles = []

    # Filter to meaningful cycles
    significant_cycles = [c for c in cycles if len(c) >= min_size]

    if not significant_cycles:
        return patterns

    # Group by cycle length
    for cycle in significant_cycles[:5]:  # Limit to top 5
        # Collect transaction IDs involved
        txn_ids = []
        total_amount = 0
        for i in range(len(cycle)):
            src = cycle[i]
            dst = cycle[(i + 1) % len(cycle)]
            if G.has_edge(src, dst):
                edge_data = G[src][dst]
                txn_ids.extend(edge_data.get("txn_ids", []))
                total_amount += edge_data.get("weight", 0)

        members = " -> ".join(n[:12] for n in cycle) + " -> " + cycle[0][:12]

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"Circular Flow Ring ({len(cycle)} members)",
            description=f"Circular fund flow detected: {members}. "
                        f"Total amount: ${total_amount:,.2f}. "
                        f"Possible wash trading or layering.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=min(0.5 + len(cycle) * 0.1, 0.95),
            detection_rule={"type": "cycle", "min_size": min_size, "cycle_length": len(cycle)},
            stats={"members": len(cycle), "total_amount": round(total_amount, 2),
                   "txn_count": len(txn_ids)},
            related_txn_ids=txn_ids[:20],
        ))

    return patterns


def detect_hubs(G: nx.DiGraph, threshold: int = 5) -> list[PatternCard]:
    """Detect hub accounts with unusually high connectivity.

    High out-degree = sending to many accounts (possible structuring)
    High in-degree = receiving from many accounts (possible money mule)
    """
    patterns = []

    # Out-degree hubs (senders to many receivers)
    out_hubs = [(node, deg) for node, deg in G.out_degree() if deg >= threshold]
    out_hubs.sort(key=lambda x: -x[1])

    for node, degree in out_hubs[:3]:
        txn_ids = []
        total_amount = 0
        receivers = []
        for _, receiver, data in G.out_edges(node, data=True):
            txn_ids.extend(data.get("txn_ids", []))
            total_amount += data.get("weight", 0)
            receivers.append(receiver[:12])

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"High-Activity Sender: {node[:15]}",
            description=f"Account {node[:15]} sent to {degree} unique receivers. "
                        f"Total outflow: ${total_amount:,.2f}. "
                        f"Possible structuring or fund distribution.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=min(0.4 + degree * 0.05, 0.9),
            detection_rule={"type": "hub_out", "threshold": threshold, "degree": degree},
            stats={"out_degree": degree, "total_amount": round(total_amount, 2),
                   "receivers_sample": receivers[:5]},
            related_txn_ids=txn_ids[:20],
        ))

    # In-degree hubs (receivers from many senders)
    in_hubs = [(node, deg) for node, deg in G.in_degree() if deg >= threshold]
    in_hubs.sort(key=lambda x: -x[1])

    for node, degree in in_hubs[:3]:
        txn_ids = []
        total_amount = 0
        senders = []
        for sender, _, data in G.in_edges(node, data=True):
            txn_ids.extend(data.get("txn_ids", []))
            total_amount += data.get("weight", 0)
            senders.append(sender[:12])

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"High-Activity Receiver: {node[:15]}",
            description=f"Account {node[:15]} received from {degree} unique senders. "
                        f"Total inflow: ${total_amount:,.2f}. "
                        f"Possible money mule or collection point.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="graph",
            confidence=min(0.4 + degree * 0.05, 0.9),
            detection_rule={"type": "hub_in", "threshold": threshold, "degree": degree},
            stats={"in_degree": degree, "total_amount": round(total_amount, 2),
                   "senders_sample": senders[:5]},
            related_txn_ids=txn_ids[:20],
        ))

    return patterns


def detect_velocity_clusters(transactions: list[dict], window_minutes: int = 60,
                              threshold: int = 5) -> list[PatternCard]:
    """Detect temporal velocity anomalies — bursts of transactions from same sender."""
    patterns = []

    # Group transactions by sender
    by_sender: dict[str, list[dict]] = defaultdict(list)
    for txn in transactions:
        sender = txn.get("sender_id", "")
        if sender:
            by_sender[sender].append(txn)

    for sender, txns in by_sender.items():
        if len(txns) < threshold:
            continue

        # Sort by timestamp
        sorted_txns = sorted(txns, key=lambda t: t.get("timestamp", ""))
        txn_ids = [t.get("txn_id", "") for t in sorted_txns]
        total_amount = sum(t.get("amount", 0) for t in sorted_txns)
        avg_amount = total_amount / len(sorted_txns) if sorted_txns else 0

        patterns.append(PatternCard(
            pattern_id=str(uuid4()),
            name=f"Velocity Spike: {sender[:15]}",
            description=f"Account {sender[:15]} made {len(txns)} transactions "
                        f"(avg ${avg_amount:,.2f} each, total ${total_amount:,.2f}). "
                        f"High-frequency activity detected.",
            discovered_at=datetime.utcnow().isoformat(),
            pattern_type="velocity",
            confidence=min(0.3 + len(txns) * 0.05, 0.85),
            detection_rule={"type": "velocity", "window_minutes": window_minutes,
                          "threshold": threshold},
            stats={"txn_count": len(txns), "total_amount": round(total_amount, 2),
                   "avg_amount": round(avg_amount, 2)},
            related_txn_ids=txn_ids[:20],
        ))

    return patterns[:5]  # Limit to top 5


def detect_dense_subgraphs(G: nx.DiGraph, min_density: float = 0.5) -> list[PatternCard]:
    """Detect dense subgraphs that may indicate coordinated fraud.

    Uses connected components on the undirected version, then checks density.
    """
    patterns = []
    UG = G.to_undirected()

    for component in nx.connected_components(UG):
        if len(component) < 3:
            continue

        subgraph = G.subgraph(component)
        density = nx.density(subgraph)

        if density >= min_density:
            # Collect all transaction IDs in this component
            txn_ids = []
            total_amount = 0
            for u, v, data in subgraph.edges(data=True):
                txn_ids.extend(data.get("txn_ids", []))
                total_amount += data.get("weight", 0)

            members = [n[:12] for n in sorted(component)[:8]]

            patterns.append(PatternCard(
                pattern_id=str(uuid4()),
                name=f"Dense Cluster ({len(component)} accounts)",
                description=f"Tightly connected group of {len(component)} accounts "
                            f"with density {density:.2f}. Members: {', '.join(members)}. "
                            f"Total flow: ${total_amount:,.2f}. Possible coordinated activity.",
                discovered_at=datetime.utcnow().isoformat(),
                pattern_type="graph",
                confidence=min(density, 0.95),
                detection_rule={"type": "dense_subgraph", "min_density": min_density,
                              "density": round(density, 4)},
                stats={"members": len(component), "density": round(density, 4),
                       "total_amount": round(total_amount, 2), "edge_count": subgraph.number_of_edges()},
                related_txn_ids=txn_ids[:20],
            ))

    return sorted(patterns, key=lambda p: p.confidence, reverse=True)[:5]


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
    """
    now = datetime.utcnow().isoformat()

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

    # Store new patterns (skip duplicates by checking pattern_type + name prefix)
    existing_cursor = await db.execute(
        "SELECT name FROM pattern_cards WHERE status = 'active'"
    )
    existing_names = {r[0] for r in await existing_cursor.fetchall()}

    new_count = 0
    for pattern in patterns:
        if pattern.name not in existing_names:
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
