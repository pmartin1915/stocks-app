"""
Central financial threshold constants.

All scoring thresholds and zone boundaries are defined here as the single
source of truth. Import from this module instead of hardcoding values.
"""

# --- Piotroski F-Score ---
FSCORE_MAX = 9
FSCORE_STRONG_MIN = 7   # >= 7: Strong
FSCORE_MODERATE_MIN = 4  # >= 4: Moderate (below 4: Weak)

# --- Altman Z-Score Zone Boundaries ---
# Manufacturing model (original 1968 formula)
ZSCORE_MFG_SAFE = 2.99       # > 2.99: Safe zone
ZSCORE_MFG_GREY_LOW = 1.81   # >= 1.81: Grey zone (below: Distress)

# Non-manufacturing model (1993 revision)
ZSCORE_NON_MFG_SAFE = 2.60
ZSCORE_NON_MFG_GREY_LOW = 1.10

# --- Altman Formula Coefficients ---
ALTMAN_MFG_COEFFICIENTS = {
    "x1": 1.2,   # Working Capital / Total Assets
    "x2": 1.4,   # Retained Earnings / Total Assets
    "x3": 3.3,   # EBIT / Total Assets
    "x4": 0.6,   # Market Value Equity / Total Liabilities
    "x5": 1.0,   # Sales / Total Assets
}

ALTMAN_NON_MFG_COEFFICIENTS = {
    "x1": 6.56,  # Working Capital / Total Assets
    "x2": 3.26,  # Retained Earnings / Total Assets
    "x3": 6.72,  # EBIT / Total Assets
    "x4": 1.05,  # Book Value Equity / Total Liabilities
}

# Cap for equity ratio when total_liabilities is zero
ZERO_LIABILITIES_EQUITY_CAP = 10.0
