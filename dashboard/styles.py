"""Global CSS injection and UI helper components.

Provides inject_global_styles() which every page calls after sidebar setup.
Also provides Python helper functions for consistent section headers,
metric cards, empty states, loading skeletons, and page footers.
"""

import streamlit as st

from dashboard.theme import THEME, SEMANTIC_COLORS


def inject_global_styles() -> None:
    """Inject global CSS that transforms all Streamlit elements.

    Call this once per page, after render_full_sidebar().
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


_GLOBAL_CSS = f"""<style>
/* ===== Design Tokens (CSS Custom Properties) ===== */
:root {{
    --bg-primary: {THEME["bg_primary"]};
    --bg-secondary: {THEME["bg_secondary"]};
    --bg-tertiary: {THEME["bg_tertiary"]};
    --text-primary: {THEME["text_primary"]};
    --text-secondary: {THEME["text_secondary"]};
    --border: {THEME["border"]};

    --green: {SEMANTIC_COLORS["green"]};
    --yellow: {SEMANTIC_COLORS["yellow"]};
    --red: {SEMANTIC_COLORS["red"]};
    --gray: {SEMANTIC_COLORS["gray"]};
    --blue: {SEMANTIC_COLORS["blue"]};

    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;

    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;

    --shadow-sm: 0 1px 3px rgba(0,0,0,0.25);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.3);

    --transition: 0.15s ease;

    --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
}}

/* ===== Metric Cards ===== */
[data-testid="stMetric"] {{
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-md) var(--space-md) var(--space-sm);
    box-shadow: var(--shadow-sm);
    transition: border-color var(--transition), box-shadow var(--transition);
}}
[data-testid="stMetric"]:hover {{
    border-color: var(--blue);
    box-shadow: var(--shadow-md);
}}
[data-testid="stMetric"] label {{
    text-transform: uppercase;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em;
    color: var(--text-secondary) !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-family: var(--font-mono);
    font-weight: 700;
}}

/* ===== Tabs — Pill Style ===== */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    padding: 4px;
    border: 1px solid var(--border);
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: var(--radius-md);
    padding: 8px 20px;
    font-weight: 500;
    transition: background var(--transition), color var(--transition);
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: var(--blue) !important;
    color: #fff !important;
    border-radius: var(--radius-md);
}}
.stTabs [data-baseweb="tab-highlight"] {{
    display: none;
}}
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}

/* ===== Buttons ===== */
.stButton > button {{
    border-radius: var(--radius-md);
    font-weight: 600;
    transition: all var(--transition);
    border: 1px solid var(--border);
}}
.stButton > button:hover {{
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.3);
    border-color: var(--blue);
}}
.stButton > button[kind="primary"] {{
    border-color: var(--blue);
}}

/* ===== Expanders — Card Style ===== */
.streamlit-expanderHeader {{
    background: var(--bg-secondary) !important;
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border) !important;
    font-weight: 600;
    transition: border-color var(--transition);
}}
.streamlit-expanderHeader:hover {{
    border-color: var(--blue) !important;
}}
details[data-testid="stExpander"] {{
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    background: var(--bg-secondary);
}}
details[data-testid="stExpander"] summary {{
    transition: border-color var(--transition);
}}
details[data-testid="stExpander"]:hover {{
    border-color: var(--blue) !important;
}}

/* ===== DataFrames ===== */
[data-testid="stDataFrame"] {{
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
}}
[data-testid="stDataFrame"] th {{
    text-transform: uppercase;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em;
    background: var(--bg-tertiary) !important;
}}
[data-testid="stDataFrame"] td {{
    font-family: var(--font-mono);
    font-size: 0.85rem;
}}

/* ===== Forms ===== */
[data-testid="stForm"] {{
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: var(--space-md) !important;
    background: var(--bg-secondary);
}}

/* ===== Bordered Containers ===== */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border-color: var(--border) !important;
    border-radius: var(--radius-md) !important;
    background: var(--bg-secondary);
    transition: border-color var(--transition);
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: color-mix(in srgb, var(--border) 70%, var(--blue) 30%) !important;
}}

/* ===== Input Fields ===== */
.stTextInput input, .stNumberInput input, .stTextArea textarea {{
    border-radius: var(--radius-sm) !important;
    border-color: var(--border) !important;
    transition: border-color var(--transition);
}}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2) !important;
}}

/* ===== Progress Bars ===== */
.stProgress > div > div {{
    border-radius: 4px;
    background: var(--blue);
}}

/* ===== Hide Streamlit Default Page Navigation ===== */
[data-testid="stSidebarNav"] {{
    display: none !important;
}}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {{
    border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] [data-testid="stMetric"] {{
    background: transparent;
    border: none;
    box-shadow: none;
    padding: var(--space-xs) 0;
}}
[data-testid="stSidebar"] [data-testid="stMetric"]:hover {{
    border-color: transparent;
    box-shadow: none;
}}

/* ===== Dividers ===== */
hr {{
    border-color: var(--border) !important;
    opacity: 0.5;
}}

/* ===== Utility Classes ===== */
.asym-card {{
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
    transition: border-color var(--transition), box-shadow var(--transition);
}}
.asym-card:hover {{
    border-color: var(--blue);
    box-shadow: var(--shadow-md);
}}
.asym-card-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-sm);
    padding-bottom: var(--space-sm);
    border-bottom: 1px solid var(--border);
}}
.asym-section-header {{
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin: var(--space-lg) 0 var(--space-md);
}}
.asym-section-header .asym-section-title {{
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
}}
.asym-section-header .count-badge {{
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: var(--font-mono);
}}
.asym-metric {{
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    text-align: center;
    transition: border-color var(--transition);
}}
.asym-metric:hover {{
    border-color: var(--blue);
}}
.asym-metric .label {{
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    margin-bottom: var(--space-xs);
}}
.asym-metric .value {{
    font-family: var(--font-mono);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
}}
.asym-metric .delta {{
    font-family: var(--font-mono);
    font-size: 0.85rem;
    margin-top: 2px;
}}
.asym-metric .delta.positive {{ color: var(--green); }}
.asym-metric .delta.negative {{ color: var(--red); }}
.asym-metric .delta.neutral {{ color: var(--text-secondary); }}
.asym-metric .sparkline {{
    margin-top: var(--space-sm);
}}

.asym-empty-state {{
    text-align: center;
    padding: var(--space-xl) var(--space-md);
    color: var(--text-secondary);
}}
.asym-empty-state .icon {{
    margin-bottom: var(--space-md);
    opacity: 0.5;
}}
.asym-empty-state .title {{
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-sm);
}}
.asym-empty-state .message {{
    font-size: 0.9rem;
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.5;
}}

@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}
.asym-skeleton {{
    background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--border) 50%, var(--bg-tertiary) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: var(--radius-sm);
}}

.asym-footer {{
    text-align: center;
    padding: var(--space-lg) 0 var(--space-md);
    color: var(--text-secondary);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: var(--space-xl);
}}

.asym-badge-row {{
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    flex-wrap: wrap;
}}

/* ===== Mover Rows ===== */
.asym-mover-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-sm);
    transition: background var(--transition);
}}
.asym-mover-row:hover {{
    background: var(--bg-tertiary);
}}
.asym-mover-row .ticker {{
    font-weight: 700;
    font-family: var(--font-mono);
    font-size: 0.95rem;
}}
.asym-mover-row .pct {{
    font-family: var(--font-mono);
    font-weight: 600;
}}
.asym-mover-row .value {{
    color: var(--text-secondary);
    font-size: 0.85rem;
}}

/* ===== Stock Card (Watchlist) ===== */
.asym-stock-card {{
    border-left: 3px solid var(--border);
    transition: border-left-color var(--transition);
}}
.asym-stock-card.safe {{ border-left-color: var(--green); }}
.asym-stock-card.grey {{ border-left-color: var(--yellow); }}
.asym-stock-card.distress {{ border-left-color: var(--red); }}

/* ===== Decision Card Borders ===== */
.asym-decision-card {{
    border-left: 3px solid var(--gray);
}}
.asym-decision-card.buy {{ border-left-color: var(--green); }}
.asym-decision-card.sell {{ border-left-color: var(--red); }}
.asym-decision-card.hold {{ border-left-color: var(--yellow); }}
.asym-decision-card.pass {{ border-left-color: var(--gray); }}

/* ===== Alert Severity Borders ===== */
.asym-alert-card {{
    border-left: 3px solid var(--blue);
}}
.asym-alert-card.critical {{ border-left-color: var(--red); }}
.asym-alert-card.warning {{ border-left-color: var(--yellow); }}
.asym-alert-card.info {{ border-left-color: var(--blue); }}

/* ===== Wizard Steps ===== */
.asym-wizard-steps {{
    display: flex;
    align-items: center;
    gap: 0;
    margin: var(--space-md) 0 var(--space-lg);
}}
.asym-wizard-step {{
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    flex: 1;
}}
.asym-wizard-step .circle {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
    flex-shrink: 0;
    transition: all var(--transition);
}}
.asym-wizard-step .circle.completed {{
    background: var(--green);
    color: #fff;
}}
.asym-wizard-step .circle.active {{
    background: var(--blue);
    color: #fff;
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.3);
}}
.asym-wizard-step .circle.pending {{
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 2px solid var(--border);
}}
.asym-wizard-step .step-label {{
    font-size: 0.85rem;
    font-weight: 600;
}}
.asym-wizard-step .step-label.completed {{ color: var(--green); }}
.asym-wizard-step .step-label.active {{ color: var(--blue); }}
.asym-wizard-step .step-label.pending {{ color: var(--text-secondary); }}
.asym-wizard-connector {{
    flex: 1;
    height: 2px;
    margin: 0 var(--space-sm);
}}
.asym-wizard-connector.completed {{ background: var(--green); }}
.asym-wizard-connector.pending {{ background: var(--border); }}

/* ===== Best Candidate Card ===== */
.asym-best-candidate {{
    background: var(--bg-secondary);
    border: 2px solid var(--green);
    border-radius: var(--radius-md);
    padding: var(--space-md) var(--space-lg);
    display: flex;
    align-items: center;
    gap: var(--space-md);
}}
.asym-best-candidate .trophy {{ flex-shrink: 0; }}
.asym-best-candidate .info {{ flex: 1; }}
.asym-best-candidate .ticker {{
    font-size: 1.3rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--green);
}}
.asym-best-candidate .detail {{
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-top: 2px;
}}
</style>"""


# ===== Python Helper Functions =====


def section_header(
    title: str,
    count: int | None = None,
    icon_html: str = "",
    right_html: str = "",
) -> None:
    """Render a styled section header with optional count badge.

    Args:
        title: Section title text.
        count: Optional count to show as badge.
        icon_html: Optional SVG icon HTML to prepend.
        right_html: Optional HTML for right-aligned content.
    """
    count_badge = (
        f'<span class="count-badge">{count}</span>' if count is not None else ""
    )
    right_part = f'<div style="margin-left:auto">{right_html}</div>' if right_html else ""

    html = (
        f'<div class="asym-section-header">'
        f'{icon_html}'
        f'<div class="asym-section-title">{title}</div>'
        f'{count_badge}'
        f'{right_part}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    delta: str = "",
    delta_type: str = "neutral",
    sparkline_svg: str = "",
) -> str:
    """Return HTML for an enhanced metric card.

    Args:
        label: Metric label (uppercase automatically).
        value: Main value to display.
        delta: Optional delta/change text.
        delta_type: 'positive', 'negative', or 'neutral'.
        sparkline_svg: Optional sparkline SVG HTML.

    Returns:
        HTML string. Render with st.markdown(..., unsafe_allow_html=True).
    """
    delta_html = ""
    if delta:
        delta_html = f'<div class="delta {delta_type}">{delta}</div>'

    sparkline_html = ""
    if sparkline_svg:
        sparkline_html = f'<div class="sparkline">{sparkline_svg}</div>'

    return (
        f'<div class="asym-metric">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f"{delta_html}"
        f"{sparkline_html}"
        f"</div>"
    )


def empty_state(icon_html: str, title: str, message: str) -> None:
    """Render a centered empty state with large icon.

    Args:
        icon_html: SVG icon HTML (will be rendered large).
        title: Main heading text.
        message: Descriptive message text.
    """
    html = (
        f'<div class="asym-empty-state">'
        f'<div class="icon">{icon_html}</div>'
        f'<div class="title">{title}</div>'
        f'<div class="message">{message}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def loading_skeleton(height: int = 20, width: str = "100%", count: int = 3) -> None:
    """Render animated placeholder bars.

    Args:
        height: Height of each skeleton bar in pixels.
        width: CSS width (e.g., '100%', '200px').
        count: Number of skeleton bars.
    """
    bars = "".join(
        f'<div class="asym-skeleton" style="height:{height}px;width:{width};margin-bottom:8px"></div>'
        for _ in range(count)
    )
    st.markdown(bars, unsafe_allow_html=True)


def page_footer(text: str = "Asymmetric v1.0 — Investment Research Workstation") -> None:
    """Render a consistent page footer.

    Args:
        text: Footer text.
    """
    st.markdown(f'<div class="asym-footer">{text}</div>', unsafe_allow_html=True)
