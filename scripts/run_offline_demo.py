"""Launch the unchanged Streamlit UI against an ephemeral, seeded Firestore fake."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.support import seeded_fake_firestore
from src.database import set_firestore_client_for_testing
from streamlit.web import bootstrap

if __name__ == "__main__":
    os.environ["SUPPLYCHAIN_DEMO_MODE"] = "1"
    set_firestore_client_for_testing(seeded_fake_firestore())
    bootstrap.run(str(ROOT / "src/web_app.py"), False, [], {
        "server.address": "127.0.0.1", "server.port": 8501,
        "server.headless": True, "browser.gatherUsageStats": False,
    })
