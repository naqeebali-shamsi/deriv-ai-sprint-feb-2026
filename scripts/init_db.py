#!/usr/bin/env python3
"""Initialize SQLite database with schema."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "app.db"

SCHEMA = """
-- Transactions table
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

-- Risk results table
CREATE TABLE IF NOT EXISTS risk_results (
    txn_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL,
    flagged INTEGER NOT NULL,
    threshold_used REAL,
    model_version TEXT,
    features TEXT,  -- JSON
    matched_patterns TEXT,  -- JSON array
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id)
);

-- Cases table
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    txn_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    closed_at TEXT,
    risk_score REAL,
    assigned_to TEXT,
    priority TEXT DEFAULT 'medium',
    matched_patterns TEXT,  -- JSON array
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id)
);

-- Analyst labels table
CREATE TABLE IF NOT EXISTS analyst_labels (
    label_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    txn_id TEXT,
    decision TEXT NOT NULL,
    confidence TEXT DEFAULT 'medium',
    labeled_at TEXT NOT NULL,
    labeled_by TEXT,
    notes TEXT,
    fraud_type TEXT,
    FOREIGN KEY (case_id) REFERENCES cases(case_id),
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id)
);

-- Pattern cards table
CREATE TABLE IF NOT EXISTS pattern_cards (
    pattern_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    discovered_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    pattern_type TEXT,
    confidence REAL,
    detection_rule TEXT,  -- JSON
    stats TEXT,  -- JSON
    related_txn_ids TEXT  -- JSON array
);

-- Metric snapshots table
CREATE TABLE IF NOT EXISTS metric_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    model_version TEXT,
    metrics TEXT NOT NULL  -- JSON
);

-- Model state table (for threshold learning)
CREATE TABLE IF NOT EXISTS model_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    threshold REAL NOT NULL DEFAULT 0.5,
    model_version TEXT NOT NULL DEFAULT 'v1.0.0',
    last_trained_at TEXT,
    training_samples INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Initialize model state
INSERT OR IGNORE INTO model_state (id, threshold, model_version) VALUES (1, 0.5, 'v1.0.0');

-- Indexes (compound index for velocity queries is critical for performance)
CREATE INDEX IF NOT EXISTS idx_txn_sender_ts ON transactions(sender_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_txn_receiver ON transactions(receiver_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_risk_results_flagged ON risk_results(flagged);
"""


def init_db():
    """Initialize the database."""
    print(f"Initializing database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        print("Database initialized successfully.")
        
        # Print table counts
        cursor = conn.cursor()
        tables = ["transactions", "risk_results", "cases", "analyst_labels", "pattern_cards", "metric_snapshots"]
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
