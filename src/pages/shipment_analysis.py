"""Focused visual investigation for one selected inbound shipment."""
from datetime import date
import os
import json

import pandas as pd
import streamlit as st

from src.ai_explainer import explain_impact_with_openai
from src.documents import search_documents
from src.openai_agent import execute_tool
from src.supplychain import read_csv
from src.ui import get_openai_api_key, page_heading

shipments = read_csv("shipments.csv")
shipment_by_id = {row["shipment_id"]: row for row in shipments}
inventory = read_csv("inventory.csv")
inventory_by_item = {row["item_id"]: int(row["available_qty"]) for row in inventory}
as_of = shipments[0]["as_of_date"] if shipments else None

page_heading(
    "SHIPMENT INVESTIGATION",
    "Impact analysis",
    "Identify what is short, when it is due, and why the analyst should care.",
    as_of,
)
if not shipments:
    st.info("No shipment data found. Seed the demo database to analyze shipments.")
    st.code("python scripts/build_database.py")
    st.stop()

requested = st.session_state.pop("requested_shipment", None)
if requested in shipment_by_id:
    st.session_state["selected_shipment"] = requested
selected_id = st.selectbox(
    "Select shipment",
    list(shipment_by_id),
    key="selected_shipment",
    format_func=lambda shipment_id: (
        f"{shipment_id}  ·  {shipment_by_id[shipment_id]['item_id']}  ·  "
        f"{shipment_by_id[shipment_id]['item_name']}"
    ),
)
shipment = shipment_by_id[selected_id]
impact = execute_tool("check_shipment_impact", {"shipment_id": selected_id})
risks = impact["at_risk_orders"]
units_uncovered = sum(row["qty_uncovered"] for row in risks)

if risks:
    first = risks[0]
    gap_days = (
        date.fromisoformat(shipment["expected_arrival_date"])
        - date.fromisoformat(first["due_date"])
    ).days
    severity = "HIGH PRIORITY" if any(action["action_id"] == "same_day_review" for action in impact["allowed_next_steps"]) else "ANALYST REVIEW"
    st.markdown(
        f"""<div class="impact-hero">
          <div class="impact-label">{severity} &nbsp;·&nbsp; {selected_id}</div>
          <div class="impact-value">{units_uncovered:,} units uncovered across {len(risks)} {"order" if len(risks) == 1 else "orders"}</div>
          <div class="impact-detail">First exposed order {first['order_id']}: {first['qty_uncovered']} units short · due {first['due_date']} · shipment arrives {shipment['expected_arrival_date']} · {gap_days} days later</div>
        </div>""",
        unsafe_allow_html=True,
    )
else:
    st.success("No at-risk customer orders before this shipment's arrival.")

with st.container(key="analysis_metrics"):
    m1, m2, m3 = st.columns(3)
    m1.metric("Orders at risk", len(risks))
    m2.metric("Available inventory", f"{inventory_by_item.get(shipment['item_id'], 0):,} units")
    m3.metric("Shipment quantity", f"{int(shipment['qty']):,} units")

left, right = st.columns([1.25, 1], gap="medium")
with left, st.container(border=True):
    st.markdown("### Order impact")
    st.caption("Allocation includes fully covered orders, in due-date / priority / order-ID sequence.")
    st.dataframe(pd.DataFrame([{
        "Order": row["order_id"], "Needed": row["qty_needed"],
        "Allocated": row["qty_covered"], "Short": row["qty_uncovered"],
        "Due": row["due_date"], "Customer": row.get("customer", ""),
    } for row in impact["allocation"]]), width="stretch", hide_index=True)
    if risks:
        st.caption("Available inventory is allocated by due date, then priority.")
        focus = risks[0]
        covered = int(focus.get("qty_covered", focus["qty_needed"] - focus["qty_uncovered"]))
        needed = int(focus["qty_needed"])
        covered_width = max(0, min(100, round(covered / needed * 100)))
        short_width = 100 - covered_width
        st.markdown(f"**{focus['order_id']}** · {focus['item']} · {needed} units needed")
        st.markdown(
            f'<div class="allocation-track"><div class="allocation-covered" style="width:{covered_width}%">'
            f'{covered} covered</div><div class="allocation-short" style="width:{short_width}%">'
            f'{focus["qty_uncovered"]} short</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="timeline"><strong>ORDER DUE&nbsp; {focus["due_date"]}</strong>'
            '<div class="timeline-line"></div>'
            f'<strong>ARRIVAL&nbsp; {shipment["expected_arrival_date"]}</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**Inventory covers all orders due before arrival.**")
        st.caption("The current scenario shows no uncovered quantity to escalate.")

api_key = get_openai_api_key()
policy_results = search_documents("shortage above 10 units same-day analyst review", limit=1)
policy_text = policy_results[0]["text"] if policy_results else "No policy passage was retrieved."
state_key = "ai_explanation"
snapshot = json.dumps({"shipment": shipment, "impact": impact, "policy": policy_text}, sort_keys=True)
if st.session_state.get("ai_input_snapshot") != snapshot:
    st.session_state.pop(state_key, None)
    st.session_state["ai_input_snapshot"] = snapshot
with right, st.container(border=True):
    st.markdown('<div class="eyebrow">AI EXPLANATION</div>', unsafe_allow_html=True)
    st.markdown("### Analyst brief")
    st.caption("Generated text is AI commentary. Verified quantities and actions are shown separately.")
    if risks:
        st.markdown(f"**Verified input:** {first['order_id']} · {first['qty_uncovered']} units short · due {first['due_date']}.")
    else:
        st.markdown("**Verified input:** no order shortfall before arrival.")
    if api_key:
        if st.button("Generate explanation", type="primary", key=f"generate_{selected_id}"):
            with st.spinner("Preparing a grounded explanation…"):
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
                st.error(f"Explanation unavailable ({brief['error']}); verified results remain unchanged.")
            else:
                st.markdown(f"**{brief['headline']}**")
                st.write(brief["summary"])
                st.info(brief["analyst_focus"])
                st.caption(f"Limit: {brief['limitation']} · Source: verified order data + synthetic playbook")
        else:
            st.caption("Generate a brief to explain the timing, shortage, and policy-supported focus.")
    else:
        st.caption("AI commentary is optional. Verified allocation and recommended actions are available without it.")

if risks:
    st.markdown("### Recommended analyst action")
    for action in impact["allowed_next_steps"]:
        st.markdown(
            f'<div class="action-card"><span class="status-risk">{action["order_id"]}</span>'
            f'<span>{action["action"]}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("No policy escalation is indicated by the available records.")

with st.expander("Sources & calculation"):
    st.caption("Firebase Firestore collections: shipments · inventory · orders · items · customers")
    st.caption("Policy: `docs/sources/brighthome_demo_playbook.md` (synthetic scenario policy)")
    if policy_results:
        st.write(policy_text)
    st.caption(impact["note"])
    st.caption("All company and operational records shown here are synthetic.")
