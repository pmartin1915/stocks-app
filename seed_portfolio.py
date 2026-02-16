"""
Seed portfolio with real Fidelity positions.

Creates holdings, buy transactions, and 30 days of synthetic snapshots.
Re-runnable: clears existing portfolio data before seeding.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlmodel import delete

from asymmetric.db.database import ensure_stock, get_session
from asymmetric.db.portfolio_models import Holding, PortfolioSnapshot, Transaction

# Real positions as of Feb 2026
POSITIONS = [
    {"ticker": "AWK", "company": "American Water Works", "quantity": 2, "avg_cost": 129.61},
    {"ticker": "CHKP", "company": "Check Point Software", "quantity": 5, "avg_cost": 176.00},
    {"ticker": "DLR", "company": "Digital Realty Trust", "quantity": 4, "avg_cost": 162.51},
    {"ticker": "ET", "company": "Energy Transfer LP", "quantity": 20, "avg_cost": 18.39},
    {"ticker": "PCG", "company": "PG&E Corp", "quantity": 12, "avg_cost": 15.69},
    {"ticker": "PLAB", "company": "Photronics Inc", "quantity": 2, "avg_cost": 34.12},
    {"ticker": "SPAXX", "company": "Fidelity Money Market", "quantity": 1060.83, "avg_cost": 1.00},
]


def clear_portfolio():
    """Delete all portfolio data for a clean re-seed."""
    with get_session() as session:
        session.exec(delete(Transaction))
        session.exec(delete(Holding))
        session.exec(delete(PortfolioSnapshot))
        session.flush()
    print("Cleared existing portfolio data")


def seed_portfolio():
    """Create stocks, holdings, and buy transactions from POSITIONS."""
    print(f"Seeding {len(POSITIONS)} positions:\n")

    # Step 1: Create stocks in DB
    for pos in POSITIONS:
        stock = ensure_stock(pos["ticker"], cik="0000000", company_name=pos["company"])
        print(f"  {pos['ticker']}: {stock.company_name} (id={stock.id})")

    # Step 2: Record buy transactions
    print("\n--- Recording buy transactions ---")
    from asymmetric.core.portfolio.manager import PortfolioManager
    manager = PortfolioManager()

    for pos in POSITIONS:
        try:
            existing = manager.get_holding(pos["ticker"])
            if existing:
                print(f"  {pos['ticker']}: Already has holding, skipping")
                continue

            total = pos["quantity"] * pos["avg_cost"]
            manager.add_buy(
                ticker=pos["ticker"],
                quantity=pos["quantity"],
                price_per_share=pos["avg_cost"],
                transaction_date=datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
                fees=0.0,
                notes="Imported from Fidelity",
            )
            print(f"  {pos['ticker']}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f} = ${total:,.2f}")
        except Exception as e:
            print(f"  {pos['ticker']}: ERROR - {e}")

    # Step 3: Create 30 days of synthetic snapshots
    print("\n--- Creating historical snapshots ---")
    total_cost = sum(p["quantity"] * p["avg_cost"] for p in POSITIONS)
    # Assume current value ~2% above cost basis
    total_current = total_cost * 1.02
    position_count = len(POSITIONS)

    base_date = datetime.now(timezone.utc) - timedelta(days=30)

    for day in range(30):
        snapshot_date = base_date + timedelta(days=day)
        progress = day / 29.0
        base_value = total_cost + (total_current - total_cost) * progress
        noise = random.gauss(0, base_value * 0.002)
        daily_value = max(base_value + noise, total_cost * 0.9)

        unrealized = daily_value - total_cost
        unrealized_pct = (unrealized / total_cost * 100) if total_cost > 0 else 0

        with get_session() as session:
            snapshot = PortfolioSnapshot(
                snapshot_date=snapshot_date,
                total_value=round(daily_value, 2),
                total_cost_basis=round(total_cost, 2),
                unrealized_pnl=round(unrealized, 2),
                unrealized_pnl_percent=round(unrealized_pct, 2),
                realized_pnl_ytd=0.0,
                realized_pnl_total=0.0,
                position_count=position_count,
                weighted_fscore=round(random.uniform(5.0, 7.5), 1),
                weighted_zscore=round(random.uniform(2.0, 4.0), 2),
            )
            session.add(snapshot)
            session.flush()

        if day % 10 == 0 or day == 29:
            print(f"  Day {day+1}: ${daily_value:,.2f} ({unrealized_pct:+.1f}%)")

    print(f"\nCreated 30 historical snapshots")

    # Step 4: Take a live snapshot
    print("\n--- Taking live snapshot ---")
    try:
        snapshot = manager.take_snapshot()
        print(f"  Live snapshot: ${snapshot.total_value:,.2f} | Unrealized: ${snapshot.unrealized_pnl:,.2f}")
    except Exception as e:
        print(f"  Live snapshot failed: {e}")

    print("\nDone! Run 'streamlit run dashboard/app.py' to verify.")


if __name__ == "__main__":
    clear_portfolio()
    seed_portfolio()
