"""
Database migration v2: Add tax lot tracking, Decimal precision, and soft-delete.

This script:
1. Backs up the current database
2. Creates new tables (tax_lots, lot_dispositions, corporate_actions, cash_flows)
3. Adds 'status' column to holdings (soft-delete support)
4. Adds 'cash_flow_on_date' column to portfolio_snapshots
5. Back-populates TaxLots from existing buy transactions
6. Validates data integrity

Run: python scripts/migrate_v2.py
"""

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from asymmetric.config import config


def backup_database(db_path: Path) -> Path:
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    print(f"  Backup created: {backup_path}")
    return backup_path


def migrate(db_path: Path) -> None:
    """Run the v2 migration."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # --- Step 1: Add status column to holdings ---
        print("  Adding 'status' column to holdings...")
        try:
            cursor.execute("ALTER TABLE holdings ADD COLUMN status VARCHAR(10) DEFAULT 'open'")
            print("    Added status column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("    status column already exists, skipping")
            else:
                raise

        # --- Step 2: Add cash_flow_on_date to portfolio_snapshots ---
        print("  Adding 'cash_flow_on_date' column to portfolio_snapshots...")
        try:
            cursor.execute(
                "ALTER TABLE portfolio_snapshots ADD COLUMN cash_flow_on_date FLOAT DEFAULT 0.0"
            )
            print("    Added cash_flow_on_date column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("    cash_flow_on_date column already exists, skipping")
            else:
                raise

        # --- Step 3: Create tax_lots table ---
        print("  Creating tax_lots table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tax_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id INTEGER NOT NULL REFERENCES holdings(id),
                buy_transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                purchase_date DATETIME NOT NULL,
                quantity_original DECIMAL(14,6) NOT NULL,
                quantity_remaining DECIMAL(14,6) NOT NULL,
                cost_per_share DECIMAL(14,4) NOT NULL,
                fees DECIMAL(10,2) DEFAULT 0,
                is_wash_sale BOOLEAN DEFAULT 0,
                wash_sale_disallowed DECIMAL(14,2) DEFAULT 0,
                wash_sale_adjusted_basis DECIMAL(14,2) DEFAULT 0,
                status VARCHAR(10) DEFAULT 'open',
                closed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_tax_lots_holding_id ON tax_lots(holding_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_tax_lots_buy_transaction_id ON tax_lots(buy_transaction_id)"
        )
        print("    tax_lots table created")

        # --- Step 4: Create lot_dispositions table ---
        print("  Creating lot_dispositions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lot_dispositions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_lot_id INTEGER NOT NULL REFERENCES tax_lots(id),
                sell_transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                quantity_disposed DECIMAL(14,6) NOT NULL,
                proceeds_per_share DECIMAL(14,4) NOT NULL,
                cost_basis_per_share DECIMAL(14,4) NOT NULL,
                realized_gain DECIMAL(14,2) NOT NULL,
                is_long_term BOOLEAN DEFAULT 0,
                disposed_date DATETIME NOT NULL,
                is_wash_sale BOOLEAN DEFAULT 0,
                wash_sale_loss_disallowed DECIMAL(14,2) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_lot_dispositions_tax_lot_id ON lot_dispositions(tax_lot_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_lot_dispositions_sell_txn_id ON lot_dispositions(sell_transaction_id)"
        )
        print("    lot_dispositions table created")

        # --- Step 5: Create corporate_actions table ---
        print("  Creating corporate_actions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corporate_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL REFERENCES stocks(id),
                action_type VARCHAR(20) NOT NULL,
                ratio_numerator INTEGER NOT NULL,
                ratio_denominator INTEGER NOT NULL,
                effective_date DATETIME NOT NULL,
                notes VARCHAR(500),
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                lots_adjusted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_corporate_actions_stock_id ON corporate_actions(stock_id)"
        )
        print("    corporate_actions table created")

        # --- Step 6: Create cash_flows table ---
        print("  Creating cash_flows table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_type VARCHAR(20) NOT NULL,
                amount DECIMAL(14,2) NOT NULL,
                flow_date DATETIME NOT NULL,
                notes VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_cash_flows_flow_date ON cash_flows(flow_date)")
        print("    cash_flows table created")

        # --- Step 7: Back-populate TaxLots from existing buy transactions ---
        print("  Back-populating tax lots from existing buy transactions...")

        # Check if we already have tax lots (idempotent)
        cursor.execute("SELECT COUNT(*) FROM tax_lots")
        existing_lots = cursor.fetchone()[0]
        if existing_lots > 0:
            print(f"    {existing_lots} tax lots already exist, skipping back-population")
        else:
            # Get all buy transactions with their holding IDs
            cursor.execute("""
                SELECT t.id, t.stock_id, t.transaction_date, t.quantity, t.price_per_share, t.fees,
                       h.id as holding_id
                FROM transactions t
                JOIN holdings h ON h.stock_id = t.stock_id
                WHERE t.transaction_type = 'buy'
                ORDER BY t.transaction_date ASC
            """)
            buy_txns = cursor.fetchall()

            lots_created = 0
            for txn in buy_txns:
                txn_id, stock_id, txn_date, qty, price, fees, holding_id = txn
                qty = abs(float(qty))
                price = float(price)
                fees = float(fees)
                cost_per_share = price + (fees / qty) if qty > 0 else price

                cursor.execute(
                    """
                    INSERT INTO tax_lots
                    (holding_id, buy_transaction_id, purchase_date, quantity_original,
                     quantity_remaining, cost_per_share, fees, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                    (
                        holding_id,
                        txn_id,
                        txn_date,
                        qty,
                        qty,  # All shares still remaining (we'll adjust below for sells)
                        cost_per_share,
                        fees,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                lots_created += 1

            print(f"    Created {lots_created} tax lots from buy transactions")

            # Now process sells to consume lots (FIFO order)
            cursor.execute("""
                SELECT t.stock_id, t.quantity, t.transaction_date
                FROM transactions t
                WHERE t.transaction_type = 'sell'
                ORDER BY t.transaction_date ASC
            """)
            sell_txns = cursor.fetchall()

            for sell in sell_txns:
                stock_id, sell_qty, sell_date = sell
                remaining_to_consume = abs(float(sell_qty))

                # Get open lots for this stock in FIFO order
                cursor.execute(
                    """
                    SELECT tl.id, tl.quantity_remaining
                    FROM tax_lots tl
                    JOIN holdings h ON h.id = tl.holding_id
                    WHERE h.stock_id = ? AND tl.quantity_remaining > 0
                    ORDER BY tl.purchase_date ASC
                """,
                    (stock_id,),
                )
                lots = cursor.fetchall()

                for lot_id, lot_remaining in lots:
                    if remaining_to_consume <= 0:
                        break
                    take = min(float(lot_remaining), remaining_to_consume)
                    new_remaining = float(lot_remaining) - take
                    status = "closed" if new_remaining <= 0.000001 else "partial"

                    cursor.execute(
                        """
                        UPDATE tax_lots
                        SET quantity_remaining = ?, status = ?,
                            closed_at = CASE WHEN ? = 'closed' THEN ? ELSE closed_at END
                        WHERE id = ?
                    """,
                        (max(new_remaining, 0), status, status, sell_date, lot_id),
                    )
                    remaining_to_consume -= take

            print("    Adjusted lot quantities for existing sell transactions")

        # --- Step 8: Validate ---
        print("  Validating migration...")

        cursor.execute("SELECT COUNT(*) FROM tax_lots")
        lot_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM holdings WHERE status = 'open' AND quantity > 0")
        open_holdings = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_type = 'buy'")
        buy_count = cursor.fetchone()[0]

        print(f"    Tax lots: {lot_count}")
        print(f"    Open holdings: {open_holdings}")
        print(f"    Buy transactions: {buy_count}")

        if lot_count > 0 and lot_count >= buy_count:
            print("    Validation: PASS (lots >= buy transactions)")
        elif lot_count == 0 and buy_count == 0:
            print("    Validation: PASS (no transactions to migrate)")
        else:
            print(f"    WARNING: lot_count ({lot_count}) < buy_count ({buy_count})")
            print("    Some lots may not have been created (check for missing holdings)")

        conn.commit()
        print("  Migration committed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"  ERROR: Migration failed: {e}")
        raise
    finally:
        conn.close()


def main():
    db_path = config.db_path
    print(f"Database migration v2: {db_path}")
    print("=" * 60)

    if not db_path.exists():
        print("Database does not exist yet. Migration will run on first init_db().")
        print("Creating tables via SQLModel...")
        from asymmetric.db.database import init_db

        init_db()
        print("Done. New tables created with correct schema.")
        return

    print("\nStep 1: Backup")
    backup_path = backup_database(db_path)

    print("\nStep 2: Migrate")
    try:
        migrate(db_path)
    except Exception:
        print(f"\nMigration failed! Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, db_path)
        print("Database restored to pre-migration state.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Migration v2 complete!")
    print(f"Backup at: {backup_path}")


if __name__ == "__main__":
    main()
