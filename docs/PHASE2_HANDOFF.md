# Phase 2 Handoff Report — Audit Remediation & UX Overhaul

**Date:** 2026-02-14
**Session:** Comprehensive audit → critical bug fix → data model cleanup → UX refactor
**Tests:** 1185 passed, 0 failed, 73 skipped

---

## What Was Done

### Phase A: Critical Accounting Bug Fix

**Problem:** `add_sell()` calculated `Transaction.realized_gain` using the holding's weighted average cost regardless of FIFO/LIFO/HIFO selection. The tax lot system was effectively cosmetic — lot consumption happened but the P&L on the Transaction was always average-cost.

**Fix (3 parts):**

1. **Restructured `add_sell()` in [manager.py](../asymmetric/core/portfolio/manager.py)**
   - Lots are now consumed FIRST via `_consume_lots()`
   - `Transaction.realized_gain` is derived from the actual lot costs consumed
   - `Transaction.cost_basis_per_share` reflects the effective cost from consumed lots
   - Key invariant enforced: `Transaction.realized_gain == sum(LotDisposition.realized_gain)`

2. **Fixed fee allocation in `_consume_lots()`**
   - Now accepts `fee_per_share` parameter
   - Returns `tuple[list[LotDisposition], Decimal]` (dispositions + total cost consumed)
   - Each disposition uses `net_proceeds_per_share = proceeds_per_share - fee_per_share`
   - Fees proportionally allocated across dispositions

3. **Fixed holding cost basis on partial sell**
   - Old: `holding.cost_basis_total = new_quantity * avg_cost_basis` (wrong — uses average)
   - New: `holding.cost_basis_total -= lots_cost_total` (correct — subtracts actual consumed cost)

### Phase B: Data Model Cleanup

1. **PortfolioSnapshot float → Decimal** ([portfolio_models.py](../asymmetric/db/portfolio_models.py))
   - `total_value`, `total_cost_basis`, `unrealized_pnl`, `unrealized_pnl_percent`, `realized_pnl_ytd`, `realized_pnl_total`, `cash_flow_on_date` all changed to `Decimal`
   - `take_snapshot()` updated to pass `_to_decimal()` values
   - `get_performance_stats()` converts Decimal→float at extraction for math operations

2. **UTC-naive datetime helper** ([manager.py](../asymmetric/core/portfolio/manager.py))
   - Added `_to_naive_utc()` — converts timezone-aware datetimes to naive UTC for SQLite
   - Replaced 4 manual timezone-stripping blocks throughout manager

3. **Ticker symbol validation**
   - `_validate_ticker()` with regex `^[A-Z0-9.\-]{1,10}$`
   - Called at `add_buy()` and `add_sell()` entry points in manager
   - Also added to MCP server ([server.py](../asymmetric/mcp/server.py)) — replaces all `.upper()` calls
   - MCP server now catches `ValueError` separately → returns validation error to client (not generic error)

### Phase C: Dashboard UX

1. **Portfolio page: 6 tabs → 3 tabs** ([1_Portfolio.py](../dashboard/pages/1_Portfolio.py))
   - **Overview** — Holdings table + allocation charts + collapsible Portfolio Health
   - **Performance** — Winners/losers, P&L chart, metrics + historical charts
   - **Transactions** — Add transaction form + transaction history
   - Error recovery: `st.stop()` replaced with "Go to Watchlist" / "Retry" buttons

2. **Decisions page: 614 → 129 lines** ([6_Decisions.py](../dashboard/pages/6_Decisions.py))
   - Extracted into `dashboard/components/decisions/` package:
     - [cards.py](../dashboard/components/decisions/cards.py) — card/form/detail rendering components
     - [decisions_tab.py](../dashboard/components/decisions/decisions_tab.py) — My Decisions tab
     - [theses_tab.py](../dashboard/components/decisions/theses_tab.py) — Theses Library tab
     - [outcomes_tab.py](../dashboard/components/decisions/outcomes_tab.py) — Review Outcomes tab
     - [analytics_tab.py](../dashboard/components/decisions/analytics_tab.py) — Analytics tab
   - `__init__.py` re-exports all symbols for backward compatibility
   - Old flat `decisions.py` deleted

### Phase D: Tests

- Created [test_tax_lot_sell.py](../tests/test_tax_lot_sell.py) — 20 new tests:
  - `TestFIFOSell` (3) — single lot, multi-lot different costs, remaining holding cost basis
  - `TestLIFOSell` (2) — newest-first consumption, LIFO vs FIFO gain comparison
  - `TestHIFOSell` (2) — highest-cost-first consumption, remaining lots are cheaper
  - `TestFeeSell` (3) — fees reduce gain, fees allocated to dispositions, zero fees
  - `TestPartialFill` (3) — partial lot consumption, full lot → closed status, spans multiple lots
  - `TestHoldingPeriod` (3) — short-term <365 days, long-term >365, mixed periods
  - `TestAverageCostMethod` (1) — average method still creates dispositions
  - `TestInvariant` (3) — gain reconciliation single/multi-lot/with-fees
- Fixed `test_performance_analytics.py` — `float()` cast for Decimal comparison after snapshot migration

---

## Files Modified

| File | Change |
|------|--------|
| `asymmetric/core/portfolio/manager.py` | `add_sell()` restructured, `_consume_lots()` fee allocation, `_validate_ticker()`, `_to_naive_utc()`, `get_performance_stats()` Decimal→float |
| `asymmetric/db/portfolio_models.py` | PortfolioSnapshot fields → Decimal |
| `asymmetric/mcp/server.py` | `_validate_ticker()`, ValueError catch for validation errors |
| `dashboard/pages/1_Portfolio.py` | 6 tabs → 3 tabs, error recovery |
| `dashboard/pages/6_Decisions.py` | 614 → 129 lines (tab logic extracted) |
| `dashboard/components/decisions/` | NEW package (cards.py + 4 tab modules + __init__.py) |
| `dashboard/components/decisions.py` | DELETED (replaced by package) |
| `tests/test_tax_lot_sell.py` | NEW — 20 tests |
| `tests/test_performance_analytics.py` | float() cast for Decimal comparison |

---

## Current State

- **All 1185 tests pass** (1165 original + 20 new)
- **No uncommitted migrations** — PortfolioSnapshot Decimal change is backward-compatible (SQLite stores as TEXT)
- **`scripts/migrate_v2.py`** exists for upgrading existing databases (from Phase 1)
- **Git status:** Many modified files across the audit, none committed yet

---

## What's Next (Phases 3-6)

### Phase 3: Cash Flow & Performance
- Populate `CashFlow` model on deposits/withdrawals
- Implement Time-Weighted Return (TWR) using `CashFlow` + `PortfolioSnapshot.cash_flow_on_date`
- Dividend income tracking (new transaction type handling)

### Phase 4: UX Overhaul
- Hero card with sparkline for portfolio value
- Onboarding flow for empty portfolio
- Closed positions view (leverage `status='closed'` holdings)
- Portfolio page polish (sparklines, mini-charts in holdings table)

### Phase 5: Visualizations
- Performance attribution chart (what drove returns)
- Sector allocation treemap
- Gain/loss heatmap by holding
- P&L waterfall chart (cost basis → current value breakdown)

### Phase 6: Tax Planning
- Wash sale detection (IRS 30-day rule — `TaxLot.is_wash_sale` fields ready)
- Capital gains summary (short-term vs long-term using `LotDisposition.is_long_term`)
- Tax-loss harvesting suggestions
- CSV export for tax filing

### Other Backlog
- DuckDB compound index on `(cik, concept, fiscal_year)` for query performance
- `@st.cache_data` for performance calculations
- Corporate action handler (stock splits — `CorporateAction` model ready, handler not implemented)
- Dashboard smoke tests for Portfolio and Research pages

---

## Key Architectural Decisions

1. **Decimal boundary:** DB stores `Decimal`, dataclass outputs use `float`. Performance stats convert Decimal→float internally. This avoids `Decimal ** 0.5` and similar math issues.

2. **Lot consumption before Transaction creation:** `add_sell()` creates a Transaction stub (with `realized_gain=None`), flushes to get an ID, consumes lots, then updates the Transaction with lot-derived values. This ensures the Transaction ID exists for `LotDisposition.sell_transaction_id`.

3. **Decisions package:** The `dashboard/components/decisions/` package uses `__init__.py` re-exports so existing imports (`from dashboard.components.decisions import render_decision_card`) continue to work unchanged.

4. **MCP validation errors:** `ValueError` is caught separately from `Exception` in the MCP tool dispatcher, so ticker validation errors return a helpful message to the client instead of the generic "internal error" response.

---

## How to Verify

```bash
# Run all tests
pytest tests/ -v

# Run just the new tax lot tests
pytest tests/test_tax_lot_sell.py -v

# Launch dashboard
streamlit run dashboard/app.py

# CLI test: buy then sell with FIFO
asymmetric portfolio add AAPL 10 150
asymmetric portfolio add AAPL 10 200
asymmetric portfolio sell AAPL 10 250 --method fifo
# Should show realized gain based on $150 cost (first lot), not $175 average
```
