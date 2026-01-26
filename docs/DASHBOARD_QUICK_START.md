# Asymmetric Dashboard - Quick Start Prompt

Copy and paste this into a new Claude Code session:

---

## Prompt

```
I need you to build a Streamlit dashboard for my investment research CLI app "Asymmetric".

**Project location:** c:\stocks_app

**Existing backend (already built):**
- `core/scoring/piotroski.py` - F-Score (0-9) calculation
- `core/scoring/altman.py` - Z-Score calculation  
- `core/data/duckdb_client.py` - SEC bulk data queries (~500MB)
- `core/ai/gemini_client.py` - Gemini 2.5 analysis
- `data/asymmetric.db` - SQLite with tables: watchlist, theses, decisions

**Create this structure:**
```
dashboard/
├── app.py                 # Entry point
├── pages/
│   ├── 1_📋_Watchlist.py   # View watchlist + scores
│   ├── 2_🔍_Screener.py    # Filter by F/Z scores
│   ├── 3_📊_Compare.py     # Side-by-side comparison
│   └── 4_📝_Decisions.py   # Track theses + decisions
├── components/
│   └── score_display.py   # F-Score/Z-Score visuals
└── utils/
    └── database.py        # SQLite helpers
```

**Requirements:**
1. Watchlist shows tickers with F-Score (progress bar) and Z-Score (zone badge)
2. Screener has slider for F-Score min, radio for Z-Score zone filter
3. Compare allows 2-3 ticker selection with full Piotroski breakdown
4. Decisions shows thesis cards with chronological decision logs

**Design constraints:**
- Keep it simple - I'm a novice investor, not a day trader
- Reuse existing `core/` modules, don't rewrite scoring logic
- Use standard Streamlit components (no fancy custom CSS)
- I'm on Windows 11

**Start with Phase 1:** Create the directory structure and implement the Watchlist page end-to-end (database helpers, score display components, add/remove ticker functionality).

Read DASHBOARD_BUILD_SPEC.md in the project root for full implementation details if you need more context.
```

---

## Before Starting

1. Copy `DASHBOARD_BUILD_SPEC.md` to your project root:
   ```
   c:\stocks_app\DASHBOARD_BUILD_SPEC.md
   ```

2. Verify your existing modules exist:
   ```
   c:\stocks_app\core\scoring\piotroski.py
   c:\stocks_app\core\scoring\altman.py
   c:\stocks_app\core\data\duckdb_client.py
   c:\stocks_app\data\asymmetric.db
   ```

3. Install Streamlit if not already:
   ```bash
   pip install streamlit pandas
   ```

---

## Session Commands

After pasting the prompt, you can guide the Opus instance with:

- **"Continue to Phase 2"** - After Watchlist works
- **"/local-review"** - Before committing changes
- **"Show me the file structure"** - To verify what was created
- **"Test the watchlist page"** - To run validation

---

## Expected Outputs Per Phase

| Phase | Files Created | Validation |
|-------|---------------|------------|
| 1 | `app.py`, `1_Watchlist.py`, `database.py`, `score_display.py` | Dashboard launches, watchlist displays |
| 2 | `2_Screener.py` | Can filter and add to watchlist |
| 3 | `3_Compare.py`, `ticker_card.py` | Side-by-side works, AI button works |
| 4 | `4_Decisions.py`, `thesis_card.py` | Full thesis CRUD works |
