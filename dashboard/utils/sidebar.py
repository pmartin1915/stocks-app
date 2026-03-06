"""Shared sidebar components for all pages.

Provides branded navigation with icon groupings, active page detection,
and consistent branding across all pages in the multi-page app.
"""

import streamlit as st

from dashboard.theme import THEME, SEMANTIC_COLORS


def render_full_sidebar(current_page: str = "") -> None:
    """Render complete sidebar with branding and navigation.

    Call this from every page to ensure consistent sidebar.

    Args:
        current_page: Identifier for the current page (e.g. "home", "portfolio").
            Used to highlight the active nav item.
    """
    _render_branding()
    _render_navigation(current_page)
    _render_footer()


def _render_branding() -> None:
    """Render sidebar branding block."""
    blue = SEMANTIC_COLORS["blue"]
    text_primary = THEME["text_primary"]
    text_secondary = THEME["text_secondary"]
    border = THEME["border"]

    brand_html = (
        f'<div style="padding:8px 0 12px">'
        f'<div style="display:flex;align-items:center;gap:10px">'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28"'
        f' fill="none" stroke="{blue}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<line x1="18" y1="20" x2="18" y2="10"/>'
        f'<line x1="12" y1="20" x2="12" y2="4"/>'
        f'<line x1="6" y1="20" x2="6" y2="14"/>'
        f'</svg>'
        f'<div>'
        f'<div style="font-size:1.3rem;font-weight:800;color:{text_primary};'
        f'letter-spacing:-0.02em;line-height:1">Asymmetric</div>'
        f'<div style="font-size:0.7rem;color:{text_secondary};margin-top:2px">'
        f'Investment Research</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div style="border-bottom:1px solid {border};margin:4px 0 12px"></div>'
    )
    st.sidebar.markdown(brand_html, unsafe_allow_html=True)


# Navigation structure: (label, page_path, icon_svg_inline, page_id)
_NAV_GROUPS = [
    (
        "OVERVIEW",
        [
            ("Home", "app.py", "home", "home"),
            ("Portfolio", "pages/1_Portfolio.py", "wallet", "portfolio"),
        ],
    ),
    (
        "RESEARCH",
        [
            ("Watchlist", "pages/2_Watchlist.py", "eye", "watchlist"),
            ("Screener", "pages/3_Screener.py", "grid", "screener"),
            ("Research", "pages/4_Research.py", "file_text", "research"),
            ("Compare", "pages/5_Compare.py", "compare", "compare"),
        ],
    ),
    (
        "TRACKING",
        [
            ("Decisions", "pages/6_Decisions.py", "target", "decisions"),
            ("Trends", "pages/7_Trends.py", "trending_up", "trends"),
            ("Alerts", "pages/8_Alerts.py", "bell", "alerts"),
        ],
    ),
]

def _render_navigation(current_page: str) -> None:
    """Render grouped navigation using st.page_link (Streamlit 1.31+)."""
    blue = SEMANTIC_COLORS["blue"]
    text_secondary = THEME["text_secondary"]

    for group_label, items in _NAV_GROUPS:
        # Section label
        st.sidebar.markdown(
            f'<div style="font-size:0.65rem;font-weight:700;color:{text_secondary};'
            f'text-transform:uppercase;letter-spacing:0.1em;padding:12px 0 4px">'
            f'{group_label}</div>',
            unsafe_allow_html=True,
        )

        for label, page_path, icon_name, page_id in items:
            is_active = current_page == page_id

            try:
                st.sidebar.page_link(
                    page_path,
                    label=label,
                    disabled=is_active,
                )
            except Exception:
                # Fallback for older Streamlit versions
                st.sidebar.markdown(f"{'**' if is_active else ''}{label}{'**' if is_active else ''}")

    # Style active page links
    st.sidebar.markdown(
        f"""<style>
        [data-testid="stSidebar"] [data-testid="stPageLink"] {{
            border-radius: 8px;
            transition: background 0.15s ease;
        }}
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover {{
            background: rgba(96, 165, 250, 0.08);
        }}
        [data-testid="stSidebar"] [data-testid="stPageLink"][disabled] {{
            background: rgba(96, 165, 250, 0.12);
            border-left: 3px solid {blue};
            opacity: 1 !important;
        }}
        [data-testid="stSidebar"] [data-testid="stPageLink"][disabled] span {{
            color: {blue} !important;
            font-weight: 700;
        }}
        </style>""",
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    """Render sidebar footer."""
    text_secondary = THEME["text_secondary"]
    border = THEME["border"]

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f'<div style="text-align:center;font-size:0.7rem;color:{text_secondary}">'
        f'Asymmetric v1.0</div>',
        unsafe_allow_html=True,
    )
