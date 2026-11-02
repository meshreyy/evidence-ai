"""Native two-page Streamlit application for SupplyChain Copilot."""
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import database_counts
from src.ui import apply_visual_theme

st.set_page_config(
    page_title="SupplyChain Copilot",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_visual_theme()

counts = database_counts()
with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">◈</span> SupplyChain Copilot</div>',
        unsafe_allow_html=True,
    )
    st.caption("OPERATIONS INTELLIGENCE")
    st.divider()
    st.markdown("**Workspace data**")
    st.caption(
        f"{counts['shipments']} shipments · {counts['items']} SKUs\n\n"
        f"{counts['orders']} order lines · SQLite"
    )
    st.markdown('<div class="pill">SYNTHETIC SCENARIO</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("Read-only analysis · analyst retains control")

pages = [
    st.Page(
        APP_DIR / "pages" / "overview.py",
        title="Overview",
        icon="📊",
        default=True,
    ),
    st.Page(
        APP_DIR / "pages" / "shipment_analysis.py",
        title="Shipment analysis",
        icon="🔎",
    ),
]
page = st.navigation(pages, position="sidebar")
page.run()
