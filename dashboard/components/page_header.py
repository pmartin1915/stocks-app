"""Page header component with breadcrumbs.

Replaces st.title() + st.caption() on every page with a consistent
branded header that includes breadcrumb navigation.
"""

import streamlit as st

from dashboard.theme import THEME, SEMANTIC_COLORS


def render_page_header(
    title: str,
    subtitle: str = "",
    breadcrumbs: list[tuple[str, str]] | None = None,
) -> None:
    """Render a styled page header with optional breadcrumbs.

    Args:
        title: Page title (displayed large).
        subtitle: Optional subtitle in muted text.
        breadcrumbs: Optional list of (label, page_path) tuples.
            The last item is the current page (not clickable).
            Example: [("Home", "app.py"), ("Portfolio", "")]
    """
    parts = []

    if breadcrumbs:
        crumb_items = []
        for i, (label, path) in enumerate(breadcrumbs):
            is_last = i == len(breadcrumbs) - 1
            if is_last or not path:
                crumb_items.append(
                    f'<span style="color:{THEME["text_secondary"]}">{label}</span>'
                )
            else:
                crumb_items.append(
                    f'<span style="color:{SEMANTIC_COLORS["blue"]};cursor:default">{label}</span>'
                )
        separator = f' <span style="color:{THEME["text_secondary"]};margin:0 6px">/</span> '
        crumb_html = separator.join(crumb_items)
        parts.append(
            f'<div style="font-size:0.8rem;margin-bottom:4px">{crumb_html}</div>'
        )

    parts.append(
        f'<div style="font-size:2rem;font-weight:700;color:{THEME["text_primary"]};'
        f'line-height:1.2;margin-bottom:4px">{title}</div>'
    )

    if subtitle:
        parts.append(
            f'<div style="font-size:0.9rem;color:{THEME["text_secondary"]};'
            f'margin-bottom:16px">{subtitle}</div>'
        )

    st.markdown(
        f'<div style="margin-bottom:20px">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )
