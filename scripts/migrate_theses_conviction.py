"""Add conviction columns to theses table.

Migration script to add:
- conviction (INTEGER, nullable, 1-5)
- conviction_rationale (VARCHAR(200), nullable)
"""

import sqlite3
from pathlib import Path


def run_migration(db_path: str = "data/asymmetric.db") -> None:
    """Add conviction columns to theses table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(theses)")
        columns = [row[1] for row in cursor.fetchall()]

        # Add conviction column if missing
        if "conviction" not in columns:
            print("Adding conviction column...")
            cursor.execute("""
                ALTER TABLE theses
                ADD COLUMN conviction INTEGER
                CHECK (conviction IS NULL OR (conviction >= 1 AND conviction <= 5))
            """)
            print("[OK] Added conviction column")
        else:
            print("[OK] conviction column already exists")

        # Add conviction_rationale column if missing
        if "conviction_rationale" not in columns:
            print("Adding conviction_rationale column...")
            cursor.execute("""
                ALTER TABLE theses
                ADD COLUMN conviction_rationale VARCHAR(200)
            """)
            print("[OK] Added conviction_rationale column")
        else:
            print("[OK] conviction_rationale column already exists")

        conn.commit()
        print("\n[SUCCESS] Migration completed successfully")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/asymmetric.db"

    if not Path(db_path).exists():
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)

    print(f"Migrating database: {db_path}\n")
    run_migration(db_path)
