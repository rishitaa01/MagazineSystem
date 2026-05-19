"""
database.py — SQLite3 connection helper and schema initialization
Digital Magazine Management System
"""

import sqlite3
import os

# Path to the SQLite database file (sits next to this script)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'magazine_system.db')
SCHEMA   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')


def get_db():
    """
    Returns a new SQLite3 connection with:
      - PRAGMA foreign_keys = ON  (enforce referential integrity)
      - row_factory = sqlite3.Row (dict-like row access)
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Initializes the database by executing schema.sql.
    Drops nothing — uses IF NOT EXISTS so it's safe to re-run.
    """
    conn = get_db()
    with open(SCHEMA, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized at {DATABASE}")


if __name__ == '__main__':
    init_db()
