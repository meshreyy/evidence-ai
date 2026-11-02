"""Streamlit interface for the SupplyChain Copilot demo."""
import os
import sys
from pathlib import Path

import streamlit as st

# Streamlit may put the script directory, rather than the project root, on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.documents import search_documents
from src.openai_agent import answer_with_openai, execute_tool
from src.supplychain import read_csv

st.set_page_config(page_title="SupplyChain Copilot", page_icon="📦", layout="wide")
st.title("📦 SupplyChain Copilot")
st.caption(
    "A decision-support prototype: investigate a delayed shipment using fictional "
    "company records and clearly labeled reference sources."
)
st.info(
    "BrightHome, its orders, and its operations playbook are synthetic demo data. "
    "This assistant supports an analyst; it does not make or execute decisions."
)

shipments = read_csv("shipments.csv")
shipment_by_id = {row["shipment_id"]: row for row in shipments}
selected_id = st.selectbox("Select a delayed shipment", list(shipment_by_id))
shipment = shipment_by_id[selected_id]

left, right = st.columns(2)
left.metric("Shipment", shipment["shipment_id"])
right.metric("Expected arrival", shipment["expected_arrival_date"])
if not shipment.get("delay_reason", "").strip():
    st.caption("Delay cause: not recorded in the demo data.")

use_ai = st.checkbox(
    "Generate a natural-language explanation with OpenAI (uses API credits)",
    value=False,
    disabled=not bool(os.getenv("OPENAI_API_KEY")),
)

if st.button("Analyze shipment", type="primary"):
    impact = execute_tool("check_shipment_impact", {"shipment_id": selected_id})
    risks = impact["at_risk_orders"]
    st.subheader("Potential order impact")
    if risks:
        st.dataframe(risks, width="stretch", hide_index=True)
        st.metric("Total units currently uncovered", sum(r["qty_uncovered"] for r in risks))
        st.subheader("Supported next steps")
        for action in impact["allowed_next_steps"]:
            st.write(f"**{action['order_id']}:** {action['action']}")
            st.caption(action["basis"])
    else:
        st.success("No at-risk orders were found in the demo records for this shipment.")

    if use_ai:
        question = (
            f"Shipment {selected_id} is delayed. Which orders are at risk, "
            "and what should the analyst do next?"
        )
        try:
            st.subheader("AI explanation")
            st.write(answer_with_openai(question, model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")))
        except Exception as exc:
            st.warning(f"OpenAI explanation unavailable ({type(exc).__name__}); showing deterministic results above.")

    with st.expander("Evidence and assumptions"):
        st.markdown("**Business records**")
        st.write("`data/shipments.csv`, `data/inventory.csv`, `data/orders.csv`")
        st.markdown("**Demo policy (synthetic, not a website)**")
        st.caption("Local source file: `docs/sources/brighthome_demo_playbook.md`")
        policy_passages = search_documents("shortage above 10 units same-day analyst review", limit=1)
        if policy_passages:
            st.write(policy_passages[0]["text"])
        st.write(impact["note"])
        st.markdown("**Public reference sources (general import context only)**")
        st.markdown("- [CBP: Basic Importing and Exporting](https://www.cbp.gov/trade/basic-import-export)")
        st.markdown("- [CBP: Tips for New Importers and Exporters](https://www.cbp.gov/trade/basic-import-export/importer-exporter-tips)")
        st.caption("CBP pages are not evidence of this fictional shipment's status or delay cause.")

st.divider()
st.caption("Prototype only • synthetic operational data • analyst makes the final decision")
