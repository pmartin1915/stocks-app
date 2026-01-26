# Asymmetric Dashboard Build Specification

**Target:** Claude Opus via Claude Code  
**Project:** `c:\stocks_app`  
**Framework:** Streamlit  
**Duration:** ~4 implementation phases

---

## Executive Summary

Build a Streamlit dashboard for Asymmetric, a CLI-first investment research workstation. The user is a 27-year-old DNP student and junior developer with a 30+ year investment horizon. Design for simplicity and maintainability—no advanced trader features.

---

## Existing Backend Architecture

```
c:\stocks_app/
├── core/
│   ├── data/
│   │   ├── rate_limiter.py      # Token bucket for SEC EDGAR (5 req/s)
│   │   ├── edgar_client.py      # SEC EDGAR API client
│   │   └── duckdb_client.py     # Bulk SEC data (~500MB companyfacts.zip)
│   ├── scoring/
│   │   ├── piotroski.py         # F-Score (0-9) calculation
│   │   └── altman.py            # Z-Score calculation
│   └── ai/
│       └── gemini_client.py     # Gemini 2.5 integration
├── cli/
│   └── main.py                  # Click-based CLI
├── data/
│   ├── companyfacts/            # DuckDB SEC bulk data
│   └── asymmetric.db            # SQLite: theses, decisions, watchlist
└── tests/
```

### Database Schemas (SQLite: `asymmetric.db`)

```sql
-- Watchlist
CREATE TABLE watchlist (
    ticker TEXT PRIMARY KEY,
    added_date TEXT,
    notes TEXT
);

-- Investment Theses
CREATE TABLE theses (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    title TEXT,
    thesis_text TEXT,
    status TEXT,  -- 'watching', 'active', 'archived'
    created_date TEXT,
    updated_date TEXT
);

-- Decision Log
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    thesis_id INTEGER,
    ticker TEXT,
    decision_type TEXT,  -- 'add_watch', 'buy', 'sell', 'update_thesis'
    notes TEXT,
    decision_date TEXT,
    FOREIGN KEY (thesis_id) REFERENCES theses(id)
);
```

### Existing Functions to Reuse

```python
# From core/scoring/piotroski.py
def calculate_fscore(ticker: str, data: dict) -> dict:
    """Returns {'score': int, 'components': dict, 'breakdown': list}"""

# From core/scoring/altman.py  
def calculate_zscore(ticker: str, data: dict) -> dict:
    """Returns {'score': float, 'zone': str, 'components': dict}"""
    # zone: 'safe' (>2.99), 'gray' (1.81-2.99), 'distress' (<1.81)

# From core/data/duckdb_client.py
def query_company_facts(ticker: str) -> dict:
    """Fetch SEC filing data from bulk DuckDB store"""

def screen_companies(fscore_min: int, zscore_zone: str) -> list[dict]:
    """Screen all companies by score thresholds"""

# From core/ai/gemini_client.py
def generate_analysis(ticker: str, context: dict) -> str:
    """Generate AI analysis summary via Gemini 2.5"""

def compare_stocks(tickers: list[str]) -> str:
    """Generate comparative analysis of 2-3 stocks"""
```

---

## Dashboard Requirements

### Views to Implement

#### 1. Watchlist (Home) — Priority 1
- Display all watchlist tickers with current F-Score and Z-Score
- Visual indicators: F-Score as progress bar (0-9), Z-Score with zone badge
- Expandable rows showing AI summary and full score breakdown
- Add/remove tickers from watchlist
- Sort by any column

#### 2. Screener — Priority 2
- F-Score threshold slider (0-9)
- Z-Score zone filter (Safe only / Include Gray / All)
- Results table from DuckDB bulk data
- One-click "Add to Watchlist" button per result
- Show result count

#### 3. Compare — Priority 3
- Select 2-3 tickers via dropdowns (populated from watchlist + recent)
- Side-by-side comparison table
- Full Piotroski 9-component breakdown with ✓/✗ indicators
- Z-Score comparison
- "Generate AI Comparison" button → Gemini analysis

#### 4. Decisions & Theses — Priority 4
- Card-based display of active theses
- Chronological decision log per thesis
- Create new thesis form
- Add decision entry form
- Archive thesis functionality

### Design Constraints

1. **No clutter** — User is a novice investor, not a day trader
2. **Minimal dependencies** — Standard Streamlit components preferred
3. **Reuse existing code** — Import from `core/` modules, don't rewrite
4. **Windows compatibility** — User is on Windows 11
5. **Maintainable** — User is a junior developer maintaining this long-term

---

## Implementation Specification

### Project Structure to Create

```
c:\stocks_app/
├── dashboard/
│   ├── __init__.py
│   ├── app.py                   # Streamlit entry point
│   ├── config.py                # Dashboard configuration
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── 1_📋_Watchlist.py
│   │   ├── 2_🔍_Screener.py
│   │   ├── 3_📊_Compare.py
│   │   └── 4_📝_Decisions.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── score_display.py     # F-Score/Z-Score visualization
│   │   ├── ticker_card.py       # Expandable ticker info card
│   │   └── thesis_card.py       # Thesis display card
│   └── utils/
│       ├── __init__.py
│       ├── database.py          # SQLite helper functions
│       └── formatting.py        # Display formatting helpers
└── run_dashboard.py             # Convenience launcher script
```

### File Specifications

#### `dashboard/app.py`

```python
"""
Asymmetric Dashboard - Main Entry Point

Run with: streamlit run dashboard/app.py
Or use: python run_dashboard.py
"""
import streamlit as st

st.set_page_config(
    page_title="Asymmetric",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar branding
st.sidebar.title("📊 Asymmetric")
st.sidebar.caption("Long-term value investing research")
st.sidebar.divider()

# Main page content (redirects to Watchlist by default)
st.title("Welcome to Asymmetric")
st.markdown("""
Navigate using the sidebar to:
- **📋 Watchlist** — View your tracked stocks
- **🔍 Screener** — Find new opportunities  
- **📊 Compare** — Side-by-side analysis
- **📝 Decisions** — Track your investment theses
""")
```

#### `dashboard/pages/1_📋_Watchlist.py`

Implement these features:
1. `get_watchlist()` → fetch from SQLite
2. For each ticker: display F-Score (progress bar), Z-Score (badge), actions
3. `st.expander()` for each row → full score breakdown + AI summary
4. Add ticker form with `st.text_input()` + `st.button()`
5. Remove button per ticker with confirmation

Key Streamlit components:
- `st.columns()` for layout
- `st.progress()` for F-Score visualization
- `st.expander()` for expandable details
- `st.metric()` for key numbers
- `st.dataframe()` for tabular data (sortable)

#### `dashboard/pages/2_🔍_Screener.py`

Implement these features:
1. `st.slider()` for F-Score minimum (0-9, default 5)
2. `st.radio()` for Z-Score zone filter
3. `st.button("Run Screen")` → query DuckDB
4. Results in `st.dataframe()` with selection
5. "Add Selected to Watchlist" button

Performance note: Cache DuckDB queries with `@st.cache_data`

#### `dashboard/pages/3_📊_Compare.py`

Implement these features:
1. Three `st.selectbox()` dropdowns for ticker selection
2. Comparison table using `st.columns()` or `st.dataframe()`
3. Piotroski breakdown with ✓ (🟢) and ✗ (🔴) indicators
4. `st.button("Generate AI Comparison")` → calls Gemini
5. AI response in `st.info()` or `st.markdown()`

#### `dashboard/pages/4_📝_Decisions.py`

Implement these features:
1. Fetch theses from SQLite, display as cards
2. Each card shows: title, status badge, thesis summary, decision log
3. `st.form()` for new thesis creation
4. `st.form()` for new decision entry (linked to thesis)
5. Archive button per thesis

#### `dashboard/components/score_display.py`

```python
"""Reusable score visualization components"""
import streamlit as st

def render_fscore(score: int, show_label: bool = True):
    """
    Render F-Score as a colored progress bar.
    
    Args:
        score: Piotroski F-Score (0-9)
        show_label: Whether to show "F-Score: X" label
    """
    color = "green" if score >= 7 else "orange" if score >= 4 else "red"
    if show_label:
        st.caption(f"F-Score: {score}/9")
    st.progress(score / 9)

def render_zscore(score: float, show_components: bool = False):
    """
    Render Z-Score with zone badge.
    
    Args:
        score: Altman Z-Score
        show_components: Whether to show component breakdown
    """
    if score > 2.99:
        zone, color = "Safe", "🟢"
    elif score > 1.81:
        zone, color = "Gray", "🟡"
    else:
        zone, color = "Distress", "🔴"
    
    st.metric(label="Z-Score", value=f"{score:.2f}", delta=f"{color} {zone}")

def render_fscore_breakdown(components: dict):
    """
    Render full Piotroski 9-component breakdown.
    
    Args:
        components: Dict with keys for each Piotroski criterion
    """
    criteria = [
        ("Positive ROA", "roa"),
        ("Positive Operating CF", "cfo"),
        ("ROA Improvement", "delta_roa"),
        ("CFO > Net Income", "accruals"),
        ("Lower Leverage", "delta_leverage"),
        ("Higher Liquidity", "delta_liquidity"),
        ("No Share Dilution", "shares"),
        ("Higher Gross Margin", "delta_margin"),
        ("Higher Asset Turnover", "delta_turnover"),
    ]
    
    for label, key in criteria:
        passed = components.get(key, False)
        icon = "✅" if passed else "❌"
        st.write(f"{icon} {label}")
```

#### `dashboard/utils/database.py`

```python
"""SQLite database helpers for dashboard"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "asymmetric.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_watchlist() -> list[dict]:
    """Fetch all watchlist tickers"""
    conn = get_connection()
    cursor = conn.execute("SELECT ticker, added_date, notes FROM watchlist ORDER BY added_date DESC")
    results = [{"ticker": r[0], "added_date": r[1], "notes": r[2]} for r in cursor.fetchall()]
    conn.close()
    return results

def add_to_watchlist(ticker: str, notes: str = "") -> bool:
    """Add ticker to watchlist"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO watchlist (ticker, added_date, notes) VALUES (?, date('now'), ?)",
            (ticker.upper(), notes)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Already exists
    finally:
        conn.close()

def remove_from_watchlist(ticker: str) -> bool:
    """Remove ticker from watchlist"""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_theses(status: str = None) -> list[dict]:
    """Fetch theses, optionally filtered by status"""
    conn = get_connection()
    if status:
        cursor = conn.execute(
            "SELECT id, ticker, title, thesis_text, status, created_date, updated_date FROM theses WHERE status = ?",
            (status,)
        )
    else:
        cursor = conn.execute(
            "SELECT id, ticker, title, thesis_text, status, created_date, updated_date FROM theses ORDER BY updated_date DESC"
        )
    results = [
        {"id": r[0], "ticker": r[1], "title": r[2], "thesis_text": r[3], 
         "status": r[4], "created_date": r[5], "updated_date": r[6]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return results

def get_decisions_for_thesis(thesis_id: int) -> list[dict]:
    """Fetch decision log for a thesis"""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT id, ticker, decision_type, notes, decision_date FROM decisions WHERE thesis_id = ? ORDER BY decision_date DESC",
        (thesis_id,)
    )
    results = [
        {"id": r[0], "ticker": r[1], "type": r[2], "notes": r[3], "date": r[4]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return results

def create_thesis(ticker: str, title: str, thesis_text: str) -> int:
    """Create new thesis, return ID"""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO theses (ticker, title, thesis_text, status, created_date, updated_date) VALUES (?, ?, ?, 'watching', date('now'), date('now'))",
        (ticker.upper(), title, thesis_text)
    )
    conn.commit()
    thesis_id = cursor.lastrowid
    conn.close()
    return thesis_id

def add_decision(thesis_id: int, ticker: str, decision_type: str, notes: str) -> int:
    """Add decision to thesis"""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO decisions (thesis_id, ticker, decision_type, notes, decision_date) VALUES (?, ?, ?, ?, date('now'))",
        (thesis_id, ticker.upper(), decision_type, notes)
    )
    # Update thesis updated_date
    conn.execute("UPDATE theses SET updated_date = date('now') WHERE id = ?", (thesis_id,))
    conn.commit()
    decision_id = cursor.lastrowid
    conn.close()
    return decision_id
```

#### `run_dashboard.py`

```python
#!/usr/bin/env python
"""Convenience script to launch the Asymmetric dashboard"""
import subprocess
import sys
from pathlib import Path

def main():
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])

if __name__ == "__main__":
    main()
```

---

## Implementation Phases

### Phase 1: Foundation (First Session)

**Goal:** Working dashboard skeleton with Watchlist view

**Tasks:**
1. Create directory structure (`dashboard/`, `pages/`, `components/`, `utils/`)
2. Implement `dashboard/app.py` entry point
3. Implement `dashboard/utils/database.py` with SQLite helpers
4. Implement `dashboard/components/score_display.py`
5. Implement `dashboard/pages/1_📋_Watchlist.py`
6. Create `run_dashboard.py` launcher
7. Test: Can view watchlist, add/remove tickers

**Validation:**
- [ ] `python run_dashboard.py` launches without errors
- [ ] Watchlist displays tickers from SQLite
- [ ] Can add new ticker to watchlist
- [ ] Can remove ticker from watchlist
- [ ] F-Score and Z-Score display correctly

### Phase 2: Screener (Second Session)

**Goal:** Query DuckDB bulk data interactively

**Tasks:**
1. Implement `dashboard/pages/2_🔍_Screener.py`
2. Add caching with `@st.cache_data` for DuckDB queries
3. Wire up score threshold filters
4. Implement "Add to Watchlist" from results

**Validation:**
- [ ] Screener loads without timeout
- [ ] Filter changes update results
- [ ] Can add screener results to watchlist
- [ ] Results count displays correctly

### Phase 3: Compare + AI (Third Session)

**Goal:** Side-by-side analysis with Gemini integration

**Tasks:**
1. Implement `dashboard/pages/3_📊_Compare.py`
2. Build comparison table component
3. Wire up Gemini analysis button
4. Add loading states for AI calls
5. Implement `dashboard/components/ticker_card.py` (reusable)

**Validation:**
- [ ] Can select 2-3 stocks to compare
- [ ] Comparison table shows all Piotroski components
- [ ] AI comparison generates successfully
- [ ] Loading spinner shows during API call

### Phase 4: Decisions & Polish (Fourth Session)

**Goal:** Complete thesis tracking, overall polish

**Tasks:**
1. Implement `dashboard/pages/4_📝_Decisions.py`
2. Implement `dashboard/components/thesis_card.py`
3. Add thesis creation form
4. Add decision log form
5. Cross-view navigation (e.g., "View thesis" from watchlist)
6. Error handling and empty states
7. Final styling pass

**Validation:**
- [ ] Can create new thesis
- [ ] Can add decisions to thesis
- [ ] Decision log displays chronologically
- [ ] Can archive thesis
- [ ] All views handle empty states gracefully

---

## Technical Notes

### Streamlit Caching Strategy

```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_scores(ticker: str):
    """Cache score calculations to avoid recomputation"""
    data = query_company_facts(ticker)
    return {
        "fscore": calculate_fscore(ticker, data),
        "zscore": calculate_zscore(ticker, data)
    }

@st.cache_resource
def get_db_connection():
    """Cache database connection"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)
```

### Session State for Multi-Page State

```python
# Initialize session state
if "selected_tickers" not in st.session_state:
    st.session_state.selected_tickers = []

# Use across pages
st.session_state.selected_tickers.append("AAPL")
```

### Error Handling Pattern

```python
try:
    result = some_operation()
    st.success("Operation completed!")
except Exception as e:
    st.error(f"Error: {str(e)}")
    st.exception(e)  # Shows traceback in expander (dev mode)
```

### Windows Path Handling

```python
from pathlib import Path

# Always use Path for cross-platform compatibility
DB_PATH = Path(__file__).parent.parent.parent / "data" / "asymmetric.db"
```

---

## Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```
streamlit>=1.32.0
pandas>=2.0.0
# Existing deps already in project:
# duckdb, click, google-generativeai
```

Install: `pip install streamlit pandas`

---

## Testing the Dashboard

```bash
# From project root
cd c:\stocks_app

# Option 1: Direct streamlit command
streamlit run dashboard/app.py

# Option 2: Convenience script
python run_dashboard.py

# Dashboard will be available at http://localhost:8501
```

---

## Design Reference

### Color Scheme

- **Primary:** Streamlit default blue
- **Success/Safe:** Green (#28a745)
- **Warning/Gray Zone:** Orange (#ffc107)
- **Danger/Distress:** Red (#dc3545)

### Visual Indicators

| Metric | Display |
|--------|---------|
| F-Score 7-9 | 🟢 Green progress bar |
| F-Score 4-6 | 🟡 Orange progress bar |
| F-Score 0-3 | 🔴 Red progress bar |
| Z-Score Safe | "🟢 Safe" badge |
| Z-Score Gray | "🟡 Gray" badge |
| Z-Score Distress | "🔴 Distress" badge |

### Layout Principles

1. **Wide layout** — `layout="wide"` for more horizontal space
2. **Sidebar for navigation** — Streamlit handles this automatically with `pages/`
3. **Cards for grouped info** — Use `st.container()` with custom CSS or `st.expander()`
4. **Tables for data** — Use `st.dataframe()` with sorting enabled

---

## Questions to Resolve During Implementation

1. **Scores missing?** — How to handle tickers without SEC data in DuckDB?
   - Suggested: Display "N/A" with tooltip explaining data not available

2. **AI rate limits?** — What if Gemini quota exceeded?
   - Suggested: Cache AI responses in SQLite, show cached analysis if available

3. **Large watchlist?** — Performance with 50+ tickers?
   - Suggested: Paginate at 20 tickers, lazy-load scores

---

## Success Criteria

The dashboard is complete when:

1. ✅ User can view watchlist with scores at a glance
2. ✅ User can screen stocks by F-Score/Z-Score thresholds
3. ✅ User can read AI-generated analysis summaries
4. ✅ User can track investment decisions and theses
5. ✅ User can compare 2-3 stocks side-by-side
6. ✅ Dashboard runs reliably on Windows 11
7. ✅ Code is maintainable by a junior developer

---

## Delegation Notes

This spec is designed for implementation via Claude Code. Suggested approach:

1. **Start session:** Read this spec, verify existing `core/` modules exist
2. **Phase 1:** Create all files, focus on Watchlist working end-to-end
3. **Validate:** Run dashboard, test manually
4. **Iterate:** Phases 2-4 in subsequent sessions

Use `/local-review` before committing each phase.
