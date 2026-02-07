#!/usr/bin/env python3
"""Initialize SQLite database with schema.

Thin wrapper around backend.db.init_db_tables() — the single source
of truth for all table definitions.  Respects DATABASE_PATH env var.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import init_db_tables, DB_PATH


def main() -> None:
    os.makedirs(DB_PATH.parent, exist_ok=True)
    print(f"Initializing database: {DB_PATH}")
    asyncio.run(init_db_tables())
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
