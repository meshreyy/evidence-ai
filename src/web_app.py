"""Clean Streamlit dashboard for the SupplyChain Copilot demo."""
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
st.markdown(
    """
    <style>
      :root { --ink:#172b4d; --muted:#667085; --line:#e5eaf0; --accent:#176b5b; }
      .stApp { background:#f5f7fa; color:var(--ink); }
      [data-testid="stHeader"] { background:rgba(245,247,250,.92); }
      [data-testid="stAppViewContainer"] .main .block-container {
        max-width:1120px; padding-top:2.2rem; padding-bottom:3rem;
      }
      h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
      h1 { font-size:2rem !important; font-weight:700 !important; margin-bottom:.2rem !important; }
      h2 { font-size:1.25rem !important; font-weight:650 !important; }
      p, label { color:#344054; }
      [data-testid="stMetric"] {
        background:#fff; border:1px solid var(--line); border-radius:12px;
        padding:14px 18px; box-shadow:0 1px 2px rgba(16,24,40,.03);
      }
      [data-testid="stMetricLabel"] { color:var(--muted); font-size:.82rem; }
      [data-testid="stMetricValue"] { color:var(--ink); font-weight:700; }
      [data-testid="stVerticalBlockBorderWrapper"] {
        background:#fff; border-color:var(--line); border-radius:12px;
      }
      div.stButton > button, div.stFormSubmitButton > button {
        background:#176b5b; color:#fff; border:0; border-radius:8px;
        min-height:2.7rem; font-weight:600; padding:0 1.1rem;
      }
      div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background:#105447; color:#fff; border:0;
      }
      .eyebrow { color:#176b5b; font-size:.74rem; font-weight:700; letter-spacing:.1em; }
      .subcopy { color:#667085; font-size:1rem; margin-top:0; }
      .demo-pill { display:inline-block; border:1px solid #d7e6e1; color:#176b5b;
        background:#edf6f2; border-radius:999px; padding:.34rem .7rem;
        font-size:.74rem; font-weight:700; letter-spacing:.04em; }
      .risk-callout { border-left:4px solid #d97706; background:#fff8eb;
        padding:.8rem 1rem; border-radius:0 8px 8px 0; color:#693f0b; }
      .quiet { color:#667085; font-size:.86rem; }
      hr { border-color:#e5eaf0; }
    </style>
    """,
    unsafe_allow_html=True,
)

shipments = read_csv("shipments.csv")
shipment_by_id = {row["shipment_id"]: row for row in shipments}

header, badge = st.columns([5, 1])
with header:
    st.markdown('<div class="eyebrow">OPERATIONS WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Shipment impact review")
    st.markdown(
        '<p class="subcopy">See which orders may be exposed when an inbound shipment is late.</p>',
        unsafe_allow_html=True,
    )
with badge:
    st.markdown('<div class="demo-pill">DEMO DATA</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.subheader("Choose a shipment")
    with st.form("shipment_review_form"):
        choose, arrival_col, action_col = st.columns([2.2, 1.2, 1])
        with choose:
            selected_id = st.selectbox("Delayed shipment", list(shipment_by_id))
        shipment = shipment_by_id[selected_id]
        with arrival_col:
            st.text_input("Expected arrival", shipment["expected_arrival_date"], disabled=True)
        with action_col:
            st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Review impact", type="primary", width="stretch")

if submitted:
    st.session_state["reviewed_shipment_id"] = selected_id

reviewed_id = st.session_state.get("reviewed_shipment_id")
if reviewed_id == selected_id:
    shipment = shipment_by_id[reviewed_id]
    impact = execute_tool("check_shipment_impact", {"shipment_id": reviewed_id})
    risks = impact["at_risk_orders"]

    st.markdown("### Impact summary")
    if risks:
        total_uncovered = sum(row["qty_uncovered"] for row in risks)
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Orders at risk", len(risks))
        metric2.metric("Units uncovered", total_uncovered)
        metric3.metric("Shipment arrival", shipment["expected_arrival_date"])

        st.markdown("#### At-risk orders")
        st.dataframe(risks, width="stretch", hide_index=True)

        with st.container(border=True):
            st.markdown("#### Recommended analyst review")
            for action in impact["allowed_next_steps"]:
                st.markdown(f"**{action['order_id']}** · {action['action']}")
                st.caption(action["basis"])
    else:
        st.success("No at-risk orders were found in the demo records for this shipment.")

    if not shipment.get("delay_reason", "").strip():
        st.markdown(
            '<div class="risk-callout"><strong>Cause not recorded.</strong> '
            'The demo data does not explain why this shipment is late.</div>',
            unsafe_allow_html=True,
        )

    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    with st.expander("Optional AI explanation" if has_api_key else "AI explanation unavailable"):
        if has_api_key:
            use_ai = st.checkbox("Generate explanation with OpenAI (uses API credits)", value=False)
            if use_ai:
                question = (
                    f"Shipment {reviewed_id} is delayed. Which orders are at risk, "
                    "and what should the analyst do next?"
                )
                try:
                    st.write(answer_with_openai(
                        question, model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    ))
                except Exception as exc:
                    st.warning(
                        f"OpenAI explanation unavailable ({type(exc).__name__}); "
                        "the deterministic impact result above is still available."
                    )
        else:
            st.caption("Set OPENAI_API_KEY in your environment to enable model-generated explanations.")

    with st.expander("Evidence, policy, and assumptions"):
        st.markdown("**Business records used for the calculation**")
        st.code("data/shipments.csv  ·  data/inventory.csv  ·  data/orders.csv", language=None)
        st.markdown("**Demo policy (synthetic—not a real company policy)**")
        st.caption("Local source: `docs/sources/brighthome_demo_playbook.md`")
        policy_passages = search_documents(
            "shortage above 10 units same-day analyst review", limit=1
        )
        if policy_passages:
            st.write(policy_passages[0]["text"])
        st.caption(impact["note"])
        st.markdown("**Public references (general import context; not shipment evidence)**")
        st.markdown(
            "[CBP: Basic Importing and Exporting](https://www.cbp.gov/trade/basic-import-export) · "
            "[Tips for New Importers](https://www.cbp.gov/trade/basic-import-export/importer-exporter-tips)"
        )
else:
    st.markdown(
        '<div class="quiet">Select a shipment and choose <strong>Review impact</strong> to see the evidence-backed order analysis.</div>',
        unsafe_allow_html=True,
    )

st.divider()
st.markdown(
    '<div class="quiet">Prototype only · synthetic company records · analyst makes the final decision</div>',
    unsafe_allow_html=True,
)
