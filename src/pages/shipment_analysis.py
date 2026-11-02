"""Order-level investigation for one selected inbound shipment."""
import os

import pandas as pd
import streamlit as st

from src.ai_explainer import explain_impact_with_openai
from src.documents import search_documents
from src.openai_agent import execute_tool
from src.supplychain import read_csv
from src.ui import get_openai_api_key, page_heading

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

api_key = get_openai_api_key()
policy_results = search_documents("shortage above 10 units same-day analyst review", limit=1)
policy_text = policy_results[0]["text"] if policy_results else "No policy passage retrieved."
state_key = f"ai_explanation_{selected_id}"

with st.container(border=True):
    ai_title, ai_badge = st.columns([5, 1])
    with ai_title:
        st.markdown('<div class="eyebrow">AI DECISION BRIEF</div>', unsafe_allow_html=True)
        st.markdown("### Explain the operational impact")
        st.caption("AI summarizes the verified calculation and policy. It does not calculate quantities or decide actions.")
    with ai_badge:
        st.markdown('<div class="pill">GROUNDED</div>', unsafe_allow_html=True)

    if api_key:
        if st.button("Generate AI explanation", type="primary", key=f"generate_{selected_id}"):
            with st.spinner("Explaining the verified result…"):
                try:
                    st.session_state[state_key] = explain_impact_with_openai(
                        shipment,
                        impact,
                        policy_text,
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        api_key=api_key,
                    )
                except Exception as exc:
                    st.session_state[state_key] = {"error": type(exc).__name__}
        brief = st.session_state.get(state_key)
        if brief:
            if "error" in brief:
                st.error(f"AI explanation unavailable ({brief['error']}). The verified calculations below are unchanged.")
            else:
                st.markdown(f"**{brief['headline']}**")
                st.write(brief["summary"])
                insight_col, action_col = st.columns([1.2, 1])
                with insight_col:
                    st.markdown("**Why it matters**")
                    for factor in brief["risk_factors"]:
                        st.markdown(f"- {factor}")
                with action_col:
                    st.markdown("**Analyst focus**")
                    st.info(brief["analyst_focus"])
                st.caption(f"Evidence limitation: {brief['limitation']} · Synthetic scenario records")
    else:
        if risks:
            focus = risks[0]
            st.markdown(
                f"**Verified context:** {focus['order_id']} · {focus['customer']} · "
                f"{focus['qty_uncovered']} units uncovered · due {focus['due_date']}."
            )
        else:
            st.markdown("**Verified context:** No order shortfall was found before this shipment arrives.")
        st.warning(
            "Connect a server-side OpenAI key to generate the AI decision brief. "
            "The calculation and policy-backed recommendation remain available below."
        )
        st.button("Generate AI explanation", type="primary", disabled=True, key=f"generate_disabled_{selected_id}")

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

with st.expander("Evidence & calculation method"):
    st.markdown("**Runtime store** · SQLite tables: `shipments`, `items`, `inventory`, `orders`, `customers`")
    st.markdown("**Records used** · `data/supplychain.sqlite3` seeded from the versioned CSV files")
    st.markdown("**Policy used** · synthetic playbook; shortages above 10 units receive same-day analyst review")
    if policy_results:
        st.caption(policy_results[0]["text"])
    st.caption(impact["note"])
    st.caption("Business records and playbook are synthetic scenario data—not evidence about a real company.")
