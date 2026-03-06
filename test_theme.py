import streamlit as st

# Function matching dashboard/theme.py logic
THEMES = {
    "light": {
        "bg_primary": "#ffffff",
        "text_primary": "#1a1a1a",
    },
    "dark": {
        "bg_primary": "#0f172a",
        "text_primary": "#f1f5f9",
    },
}

def get_theme_name():
    return st.session_state.get("theme", "light")

def get_theme():
    return THEMES.get(get_theme_name(), THEMES["light"])

def get_color(key):
    return get_theme()[key]

def apply_theme():
    colors = get_theme()
    css = f"""
        <style>
            .stApp {{
                background-color: {colors["bg_primary"]};
                color: {colors["text_primary"]};
            }}
             h1, h2, h3, p, div {{
                color: {colors["text_primary"]} !important;
            }}
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Initialize session state
if "theme" not in st.session_state:
    st.session_state.theme = "light"

apply_theme()

st.set_page_config(layout="wide")

st.title("Theme Toggle Reproduction")

# Sidebar toggle
st.sidebar.header("Settings")
is_dark = st.sidebar.toggle(
    "Dark Mode",
    value=st.session_state.theme == "dark",
    key="theme_toggle"
)

# Logic from dashboard/app.py
new_theme = "dark" if is_dark else "light"
if st.session_state.theme != new_theme:
    st.session_state.theme = new_theme
    st.rerun()

# Display current state
current_theme = get_theme_name()
colors = get_theme()

st.write(f"Current Theme in Session State: **{current_theme}**")
st.write(f"Toggle Value: **{is_dark}**")

# Visual verification
st.markdown(
    f"""
    <div style="
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
        padding: 20px;
        border: 1px solid #ccc;
        border-radius: 10px;
    ">
        <h2>This box should change colors</h2>
        <p>Background: {colors['bg_primary']}</p>
        <p>Text: {colors['text_primary']}</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("Debug Info:")
st.json(st.session_state)
