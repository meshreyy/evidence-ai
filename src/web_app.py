"""Native two-page Streamlit application backed by Firebase Firestore."""
import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import FirebaseConfigurationError, database_counts
from src.ui import apply_visual_theme

# Streamlit can unload imported modules after a source reload. Initialize the
# explicitly requested offline data in the app run, rather than only at startup.
OFFLINE_DEMO = os.getenv("SUPPLYCHAIN_DEMO_MODE") == "1"
if OFFLINE_DEMO:
    from tests.support import seeded_fake_firestore
    from src.database import set_firestore_client_for_testing
    set_firestore_client_for_testing(seeded_fake_firestore())

st.set_page_config(
    page_title="SupplyChain Copilot",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_visual_theme()

try:
    counts = database_counts()
except FirebaseConfigurationError as exc:
    st.error("Firebase Firestore is not configured for this app yet.")
    st.info(str(exc))
    st.code(
        "export FIREBASE_PROJECT_ID=your-firebase-project-id\n"
        "export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json"
    )
    st.stop()

if not counts["shipments"]:
    st.info("No shipment data found. Seed the demo database before opening the workspace.")
    st.code("python scripts/build_database.py")
    st.stop()

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">◈</span> SupplyChain Copilot</div>',
        unsafe_allow_html=True,
    )
    st.caption("OPERATIONS INTELLIGENCE")
    if OFFLINE_DEMO:
        st.info("Offline demo · seeded in-memory data · no Firebase connection")
    st.divider()
    st.markdown("**Workspace data**")
    st.caption(
        f"{counts['shipments']} shipments · {counts['items']} SKUs\n\n"
        f"{counts['orders']} order lines · Firebase Firestore"
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
