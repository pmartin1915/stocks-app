"""Dashboard configuration settings."""

from pathlib import Path

# Watchlist file location (same as CLI)
WATCHLIST_FILE = Path.home() / ".asymmetric" / "watchlist.json"

# Database paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQLITE_DB_PATH = DATA_DIR / "asymmetric.db"
BULK_DB_PATH = DATA_DIR / "bulk" / "sec_data.duckdb"

# Caching
SCORE_CACHE_TTL = 300  # 5 minutes

# Display settings
FSCORE_THRESHOLDS = {
    "strong": 7,   # >= 7 is green
    "moderate": 4,  # >= 4 is orange, < 4 is red
}

ZSCORE_ZONES = {
    "Safe": {"color": "green", "icon": "safe"},
    "Grey": {"color": "orange", "icon": "grey"},
    "Distress": {"color": "red", "icon": "distress"},
}

# Comparison settings
MAX_COMPARE_STOCKS = 3
MIN_COMPARE_STOCKS = 2

# AI Analysis settings
AI_QUICK_MODEL = "flash"
AI_DEEP_MODEL = "pro"
AI_COST_WARNING_THRESHOLD = 0.10  # Warn if estimated cost > $0.10

# Decision settings
DECISION_ACTIONS = {
    "buy": {"color": "green", "icon": "buy", "label": "BUY"},
    "hold": {"color": "orange", "icon": "hold", "label": "HOLD"},
    "sell": {"color": "red", "icon": "sell", "label": "SELL"},
    "pass": {"color": "gray", "icon": "pass", "label": "PASS"},
}

THESIS_STATUS = {
    "draft": {"color": "yellow", "icon": "draft", "label": "Draft"},
    "active": {"color": "green", "icon": "active", "label": "Active"},
    "archived": {"color": "gray", "icon": "archived", "label": "Archived"},
}

CONFIDENCE_LEVELS = {
    1: {"label": "Very Low", "rating": 1},
    2: {"label": "Low", "rating": 2},
    3: {"label": "Medium", "rating": 3},
    4: {"label": "High", "rating": 4},
    5: {"label": "Very High", "rating": 5},
}

# Decision page settings
DECISIONS_PAGE_LIMIT = 20
THESES_PAGE_LIMIT = 20
