"""Database utilities for async SQLite."""
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path

from config import get_settings

DB_PATH = Path(get_settings().DATABASE_PATH)


@asynccontextmanager
async def get_db():
    """Get async database connection."""
    db = await aiosqlite.connect(DB_PATH)
    # WAL mode gives better concurrent read/write performance
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    try:
        yield db
    finally:
        await db.close()


async def init_db_tables():
    """Ensure tables exist (idempotent)."""
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                txn_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                txn_type TEXT NOT NULL,
                channel TEXT,
                ip_address TEXT,
                device_id TEXT,
                is_fraud_ground_truth INTEGER,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS risk_results (
                txn_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                risk_score REAL NOT NULL,
                flagged INTEGER NOT NULL,
                threshold_used REAL,
                model_version TEXT,
                features TEXT,
                matched_patterns TEXT
            );

            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                txn_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                closed_at TEXT,
                assigned_to TEXT,
                priority TEXT DEFAULT 'medium',
                risk_score REAL,
                matched_patterns TEXT
            );

            CREATE TABLE IF NOT EXISTS analyst_labels (
                label_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                txn_id TEXT,
                decision TEXT NOT NULL,
                confidence TEXT DEFAULT 'medium',
                labeled_at TEXT NOT NULL,
                labeled_by TEXT,
                fraud_type TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS pattern_cards (
                pattern_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                discovered_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                pattern_type TEXT,
                confidence REAL,
                detection_rule TEXT,
                stats TEXT,
                related_txn_ids TEXT
            );

            CREATE TABLE IF NOT EXISTS metric_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                model_version TEXT,
                metrics TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_decisions (
                decision_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                reasoning TEXT,
                context TEXT NOT NULL,
                outcome TEXT,
                model_version_before TEXT,
                model_version_after TEXT,
                source TEXT DEFAULT 'guardian'
            );

            -- Indexes for velocity queries (critical for scoring performance)
            CREATE INDEX IF NOT EXISTS idx_agent_decisions_ts
                ON agent_decisions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_txn_sender_ts
                ON transactions(sender_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_txn_receiver
                ON transactions(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_cases_status
                ON cases(status);
            CREATE INDEX IF NOT EXISTS idx_risk_results_flagged
                ON risk_results(flagged);

            -- Compound indexes for consolidated velocity queries
            CREATE INDEX IF NOT EXISTS idx_txn_receiver_ts
                ON transactions(receiver_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_txn_sender_receiver
                ON transactions(sender_id, receiver_id);
            CREATE INDEX IF NOT EXISTS idx_txn_device_ts
                ON transactions(device_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_txn_ip_ts
                ON transactions(ip_address, timestamp);
        """)
        await db.commit()
