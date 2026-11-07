"""Portfolio-scale operations overview."""
import pandas as pd
import streamlit as st

from src.ui import load_workspace, page_heading

counts, shipments, exposed_orders, as_of = load_workspace()
page_heading(
    "CONTROL TOWER / OVERVIEW",
    "Inbound supply overview",
    "A live view of shipment exposure, order risk, and where to focus first.",
    as_of,
)

at_risk_shipments = [row for row in shipments if row["units_uncovered"] > 0]
units_uncovered = sum(row["units_uncovered"] for row in at_risk_shipments)
orders_at_risk = sum(row["at_risk_orders"] for row in at_risk_shipments)

with st.container(key="overview_metrics"):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inbound shipments", counts["shipments"], help="Synthetic delayed-shipment scenarios")
    m2.metric("Shipments with exposure", len(at_risk_shipments))
    m3.metric("Orders at risk", orders_at_risk)
    m4.metric("Units uncovered", f"{units_uncovered:,}")

left, right = st.columns([1.35, 1], gap="large")
with left, st.container(border=True):
    st.markdown("### Exposure by shipment")
    st.caption("Uncovered units before the selected inbound shipment arrives")
    if at_risk_shipments:
        chart_rows = sorted(
            at_risk_shipments,
            key=lambda row: (-row["units_uncovered"], row["arrival"]),
        )[:10]
        chart = pd.DataFrame([
            {"Shipment · SKU": f"{row['shipment_id']} · {row['item_id']}",
             "Units uncovered": row["units_uncovered"]}
            for row in chart_rows
        ]).set_index("Shipment · SKU")
        st.bar_chart(chart, color="#62BBA6", horizontal=True, height=340, x_label="Uncovered units", y_label="", sort=False)
        st.caption("The 10 highest-exposure shipments · current stock allocated before arrival.")
    else:
        st.success("No order exposure in the current scenario records.")

with right, st.container(border=True):
    st.markdown("### Needs attention")
    st.caption("Highest uncovered quantities, prioritized for analyst review")
    if exposed_orders:
        focus_rows = [{
            "Shipment": row["shipment_id"],
            "Order": row["order_id"],
            "Customer": row.get("customer", ""),
            "Short": row["qty_uncovered"],
            "Due": row["due_date"],
        } for row in exposed_orders[:7]]
        st.dataframe(pd.DataFrame(focus_rows), width="stretch", hide_index=True)

    else:
        st.success("No customer orders currently show a shortfall.")

    if shipments:
        chosen = st.selectbox("Open shipment", [row["shipment_id"] for row in shipments])
        if st.button("Open shipment analysis", width="stretch", type="primary"):
            st.session_state["requested_shipment"] = chosen
            st.switch_page("pages/shipment_analysis.py")

st.markdown("### Shipment register")
st.caption(f"Arrival windows and calculated exposure across all {counts['shipments']} inbound scenarios")
register_rows = [{
    "Shipment": row["shipment_id"],
    "Item": row["item_id"],
    "Description": row["item_name"],
    "Arrival": row["arrival"],
    "On hand": row["on_hand"],
    "Orders at risk": row["at_risk_orders"],
    "Units uncovered": row["units_uncovered"],
} for row in shipments]
st.dataframe(pd.DataFrame(register_rows), width="stretch", hide_index=True, height=360)
st.caption(
    "Synthetic demo records · deterministic allocation by due date, priority, and order ID · read-only decision support."
)
