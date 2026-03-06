# Audit Remediation Handoff Report

**Date:** 2026-02-15
**Commit:** `f4375cf` on `main`
**Test baseline:** 1244 passed / 73 skipped / 0 failed
**Prior baseline:** 1202 passed (42 net new tests added)

---

## What Was Done

A comprehensive audit of the entire codebase identified 5 High, 8 Medium, and 6 Low severity issues across core logic, dashboard, CLI, MCP server, and tests. All critical/medium fixes were implemented across 4 batches spanning 72 files (+4910/-1538 lines).

### Batch 1 — Quick Wins (6 fixes)

| ID | Severity | Fix | File |
|----|----------|-----|------|
| H2 | High | MCP prompt length validation (empty, whitespace, >50K) | `asymmetric/mcp/server.py` |
| H5 | High | Portfolio cache returns `{}` on yfinance failure | `dashboard/utils/portfolio_cache.py` |
| M7 | Medium | Filing section response includes `truncated` + `original_char_count` | `asymmetric/mcp/server.py` |
| M3 | Medium | Per-ticker `confirm_remove_{ticker}` state keys | `dashboard/pages/2_Watchlist.py` |
| M8 | Medium | Score refresh shows count breakdown, not just first 3 errors | `dashboard/pages/2_Watchlist.py` |
| L2 | Low | Sort sentinel `-999` → `-float('inf')` | `asymmetric/core/portfolio/manager.py` |

### Batch 2 — Dashboard Reliability (4 fixes)

| ID | Severity | Fix | File |
|----|----------|-----|------|
| H1 | High | Bare `except Exception` → specific handling + `st.error()` | `dashboard/app.py` |
| H3 | High | Screener pagination key computed from filter widgets only | `dashboard/pages/3_Screener.py` |
| H4 | High | Compare page: separate `watchlist_select` vs `manual_ticker_N` keys | `dashboard/pages/5_Compare.py` |
| M2 | Medium | `PortfolioSummary.missing_prices: list[str]` field for UI warnings | `asymmetric/core/portfolio/manager.py` |

### Batch 3 — Structural Improvements (3 changes)

| ID | Change | Files |
|----|--------|-------|
| M5 | Narrowed composite scorer catches to `ValueError` + `InsufficientDataError` | `asymmetric/core/scoring/composite.py` |
| 3c | `@handle_cli_errors` decorator eliminates ~150 lines of duplicate SEC error handling | New: `asymmetric/cli/error_handler.py`; Updated: 8 CLI command files |
| 3d | Ticker regex converged to `^[A-Z0-9.\-]{1,10}$` across CLI, dashboard, manager | `asymmetric/cli/validators.py`, `dashboard/utils/validators.py` |

### Batch 4 — Test Coverage (42 new tests)

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_mcp_responses.py` | 12 | MCP tool response schemas (calculate_scores, get_filing_section, analyze_filing, screen_universe) |
| `tests/test_watchlist_workflows.py` | 14 | CLI add/remove/clear/list cycle via CliRunner |
| `tests/dashboard/test_compare_state.py` | 13 | Session state isolation, clear button, watchlist vs manual priority |
| `tests/dashboard/test_csv_export.py` | 3 | CSV export sanitization |

---

## What Was NOT Changed (Deferred)

### Withdrawn
- **M6 (Config validation):** After review, current approach is correct — `__post_init__()` warns, `validate()` blocks. Dashboard doesn't need SEC access, so blocking in `__post_init__()` would break dashboard-only usage.

### Deferred to Future Phases
- **L1:** Holding reopening resets `first_purchase_date` — requires schema migration
- **L3:** Content hash collision risk in `ai_content.py` — low probability
- **L4:** ScoreHistory allows multiple NULL `fiscal_year` entries — SQLite limitation
- **L5:** Alert threshold state leaks between form submissions
- **L6:** Research page state initialization fragile
- **M4:** Sector data N+1 queries (yfinance calls per ticker) — works at current scale
- **M1:** Holding.stock_id unique constraint fragility — low risk with single code path

### Architectural Debt (Not Addressed)
1. Screener pagination in Python (full result set in memory) — works for 500 companies
2. Single-threaded yfinance calls — sequential, noticeable at 50+ holdings
3. No cache invalidation broadcast between pages
4. CLI error handling decorator not applied to `decision`, `thesis`, `portfolio`, `status` commands (they don't have SEC-specific error handling, only generic catches)

---

## Remaining Work (Phases 3-6)

### Phase 3: Cash Flow & Performance
- Cash flow tracking (CashFlow model exists, unused)
- Time-Weighted Return (TWR) performance calculation
- Dividend income tracking
- Wire up CorporateAction model (stock splits)

### Phase 4: UX Overhaul
- Hero card for portfolio summary
- Sparklines for holdings table
- Onboarding wizard for first-time users
- Closed positions view (soft-deleted holdings)

### Phase 5: Visualizations
- Performance attribution chart
- Sector treemap
- Gain/loss heatmap
- P&L waterfall chart

### Phase 6: Tax Planning
- Wash sale detection (fields exist on TaxLot, always None)
- Capital gains summary
- Tax-loss harvesting suggestions
- CSV export for accountant

---

## Key Files Modified

### New Files
- `asymmetric/cli/error_handler.py` — Central `@handle_cli_errors` decorator
- `tests/test_mcp_responses.py` — MCP tool response schema validation
- `tests/test_watchlist_workflows.py` — CLI watchlist integration tests
- `tests/dashboard/test_compare_state.py` — Compare page state isolation tests

### Critical Modified Files
- `asymmetric/mcp/server.py` — Prompt validation, truncation indicator
- `asymmetric/core/portfolio/manager.py` — `missing_prices` field, sort sentinel
- `asymmetric/core/scoring/composite.py` — Narrowed exception handling
- `dashboard/app.py` — Specific exception handling with user-facing errors
- `dashboard/utils/session_state.py` — Compare page state defaults
- `asymmetric/cli/validators.py` — Unified ticker regex

---

## How to Verify

```bash
# Full test suite
pytest tests/ -v --tb=short
# Expected: 1244 passed, 73 skipped, 0 failed

# Quick smoke tests for specific fixes
pytest tests/test_mcp_responses.py -v          # MCP schemas
pytest tests/test_watchlist_workflows.py -v    # Watchlist CLI
pytest tests/dashboard/test_compare_state.py -v # Compare state

# Manual verification
streamlit run dashboard/app.py                 # Dashboard loads
python -m asymmetric.cli.main score AAPL       # CLI error handler works
```

---

## Patterns Established

1. **CLI error handling:** Use `@handle_cli_errors` decorator on Click commands that call SEC/external APIs. Don't apply to simple commands (status, launch) that don't make external calls.

2. **Ticker validation:** Single regex `^[A-Z0-9.\-]{1,10}$` used everywhere. Import from `asymmetric.cli.validators.TICKER_PATTERN` or use `TickerType()` for Click params.

3. **MCP response contracts:** Every tool response must include error indication (`"error"` key) on failure. Truncated responses include `"truncated": true` + `"original_char_count"`.

4. **Dashboard state:** Use `init_page_state("pagename")` for session state initialization. Per-widget keys (not shared keys) for interactive elements. `reset_page_state()` clears everything except theme.

5. **Test mocking for CLI:** Use `CliRunner` with `patch("asymmetric.cli.commands.X._load_...", side_effect=_load)` + `copy.deepcopy` for in-memory stores (avoids reference aliasing bugs).
