"""Order-level investigation for one selected inbound shipment."""
import os

import pandas as pd
import streamlit as st

from src.documents import search_documents
from src.openai_agent import answer_with_openai, execute_tool
from src.supplychain import read_csv
from src.ui import page_heading

shipments = read_csv("shipments.csv")
shipment_by_id = {row["shipment_id"]: row for row in shipments}
orders = read_csv("orders.csv")
inventory = read_csv("inventory.csv")
inventory_by_item = {row["item_id"]: int(row["available_qty"]) for row in inventory}
as_of = shipments[0]["as_of_date"] if shipments else None

page_heading(
    "INVESTIGATION / SHIPMENT DETAIL",
    "Shipment analysis",
    "Trace a delayed inbound item to the customer orders it may leave short.",
    as_of,
)
selected_id = st.selectbox(
    "Select shipment",
    list(shipment_by_id),
    format_func=lambda shipment_id: (
        f"{shipment_id}  ·  {shipment_by_id[shipment_id]['item_id']}  ·  "
        f"{shipment_by_id[shipment_id]['item_name']}"
    ),
    label_visibility="collapsed",
)
shipment = shipment_by_id[selected_id]
impact = execute_tool("check_shipment_impact", {"shipment_id": selected_id})
risks = impact["at_risk_orders"]
units_uncovered = sum(row["qty_uncovered"] for row in risks)

label_col, status_col = st.columns([4, 1])
with label_col:
    st.markdown(f"### {shipment['item_name']} <span class='quiet'>/ {shipment['item_id']}</span>", unsafe_allow_html=True)
with status_col:
    st.markdown(f"<div class='status-risk'>{shipment['status'].upper()}</div>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Expected arrival", shipment["expected_arrival_date"])
m2.metric("Shipment quantity", f"{int(shipment['qty']):,} units")
m3.metric("Available inventory", f"{inventory_by_item.get(shipment['item_id'], 0):,} units")
m4.metric("Orders exposed", len(risks))

left, right = st.columns([1.4, 1], gap="large")
with left, st.container(border=True):
    st.markdown("### Customer order exposure")
    if risks:
        st.caption(f"{units_uncovered:,} units are not covered by available inventory before arrival")
        rows = [{
            "Order": row["order_id"],
            "Customer": row.get("customer", ""),
            "Segment": row.get("customer_segment", ""),
            "Qty needed": row["qty_needed"],
            "Qty uncovered": row["qty_uncovered"],
            "Due date": row["due_date"],
        } for row in risks]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        chart = pd.DataFrame({
            "Units uncovered": [row["qty_uncovered"] for row in risks]
        }, index=[row["order_id"] for row in risks])
        st.bar_chart(chart, color="#E8A94B", height=220)
    else:
        st.success("Covered · no orders are short before this shipment arrives.")
        st.caption("Orders due after the arrival date are not counted as exposed to this delay.")

with right, st.container(border=True):
    st.markdown("### Analyst action")
    if risks:
        for action in impact["allowed_next_steps"]:
            st.markdown(f"**{action['order_id']}**")
            st.markdown(f"<span class='status-risk'>{action['action']}</span>", unsafe_allow_html=True)
            st.caption(f"Policy basis: {action['basis'].split(':', 1)[0]}")
    else:
        st.markdown("No escalation is indicated by the current inventory and order records.")
    reason = shipment.get("delay_reason", "").strip()
    if reason:
        st.markdown("**Recorded scenario reason**")
        st.caption(reason)
    else:
        st.markdown("**Delay cause**")
        st.caption("Not recorded in this scenario. Do not infer or invent a cause.")

has_api_key = bool(os.getenv("OPENAI_API_KEY"))
with st.expander("Ask the AI to explain this result" if has_api_key else "AI explanation (optional)"):
    if has_api_key:
        st.caption("The model reads tool results at request time; it is not trained on these records. API usage may incur cost.")
        with st.form("ai_explanation_form"):
            ask_ai = st.form_submit_button("Generate explanation", type="primary")
        if ask_ai:
            question = (
                f"Shipment {selected_id} is delayed. Which orders are at risk, "
                "and what should the analyst do next?"
            )
            try:
                st.write(answer_with_openai(
                    question, model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                ))
            except Exception as exc:
                st.warning(f"AI explanation unavailable ({type(exc).__name__}); deterministic results remain available above.")
    else:
        st.caption("Set OPENAI_API_KEY in your environment to enable a model-generated explanation. Deterministic analysis works without it.")

with st.expander("Evidence & calculation method"):
    st.markdown("**Runtime store** · SQLite tables: `shipments`, `items`, `inventory`, `orders`, `customers`")
    st.markdown("**Records used** · `data/supplychain.sqlite3` seeded from the versioned CSV files")
    st.markdown("**Policy used** · synthetic playbook; shortages above 10 units receive same-day analyst review")
    policy = search_documents("shortage above 10 units same-day analyst review", limit=1)
    if policy:
        st.caption(policy[0]["text"])
    st.caption(impact["note"])
    st.caption("Business records and playbook are synthetic scenario data—not evidence about a real company.")
