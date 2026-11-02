"""Shared layout, theme, and portfolio-scale overview calculations for Streamlit."""
from datetime import date

import pandas as pd
import streamlit as st

from src.database import database_counts
from src.supplychain import calculate_at_risk_orders, read_csv


def load_workspace():
    shipments = read_csv("shipments.csv")
    inventory = read_csv("inventory.csv")
    orders = read_csv("orders.csv")
    counts = database_counts()
    inventory_by_item = {row["item_id"]: int(row["available_qty"]) for row in inventory}

    shipment_summaries = []
    exposed_orders = []
    for shipment in shipments:
        risks = calculate_at_risk_orders(shipment, inventory, orders)
        units = sum(row["qty_uncovered"] for row in risks)
        shipment_summaries.append({
            "shipment_id": shipment["shipment_id"],
            "item_id": shipment["item_id"],
            "item_name": shipment["item_name"],
            "arrival": shipment["expected_arrival_date"],
            "status": shipment["status"],
            "delay_reason": shipment["delay_reason"],
            "at_risk_orders": len(risks),
            "units_uncovered": units,
            "on_hand": inventory_by_item.get(shipment["item_id"], 0),
        })
        for row in risks:
            exposed_orders.append(row)

    shipment_summaries.sort(key=lambda row: (row["arrival"], row["shipment_id"]))
    exposed_orders.sort(key=lambda row: (-row["qty_uncovered"], row["due_date"], row["order_id"]))
    as_of = shipments[0]["as_of_date"] if shipments else date.today().isoformat()
    return counts, shipment_summaries, exposed_orders, as_of


def apply_visual_theme():
    st.markdown(
        """
        <style>
          :root { --ink:#E9F0F6; --muted:#91A1B3; --line:#263543;
                  --surface:#141E28; --surface2:#192633; --teal:#58D6B5; }
          .stApp { background:#0B1219; color:var(--ink); }
          [data-testid="stHeader"] { background:rgba(11,18,25,.94); }
          [data-testid="stAppViewContainer"] .main .block-container {
            max-width:1320px; padding-top:1.7rem; padding-bottom:3rem;
          }
          [data-testid="stSidebar"] { background:#101923; border-right:1px solid var(--line); }
          h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
          h1 { font-size:2rem !important; font-weight:700 !important; margin:.2rem 0 .35rem !important; }
          h2 { font-size:1.25rem !important; font-weight:650 !important; }
          h3 { font-size:1rem !important; font-weight:650 !important; }
          p,label { color:#C4D0DB; }
          [data-testid="stMetric"] {
            background:var(--surface); border:1px solid var(--line); border-radius:12px;
            padding:15px 18px; min-height:112px;
          }
          [data-testid="stMetricLabel"] { color:var(--muted); font-size:.8rem; }
          [data-testid="stMetricValue"] { color:var(--ink); font-weight:700; }
          [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--surface); border-color:var(--line); border-radius:12px;
          }
          [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
          div.stButton > button, div.stFormSubmitButton > button {
            background:#13745F; color:#F2FFFB; border:1px solid #18866E;
            border-radius:8px; min-height:2.55rem; font-weight:650;
          }
          div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background:#168B71; color:#fff; border-color:#168B71;
          }
          .eyebrow { color:var(--teal); font-size:.72rem; font-weight:750; letter-spacing:.12em; }
          .subcopy { color:var(--muted); font-size:.96rem; margin:.2rem 0 0; }
          .brand { color:#F0F5F9; font-size:1.05rem; font-weight:750; letter-spacing:-.02em; }
          .brand-mark { color:var(--teal); }
          .pill { display:inline-block; border:1px solid #285849; color:#79E2C5;
            background:#142A25; border-radius:999px; padding:.32rem .68rem;
            font-size:.7rem; font-weight:750; letter-spacing:.06em; }
          .status-risk { color:#FFCB79; background:#302719; border:1px solid #5E4828;
            border-radius:999px; padding:.25rem .55rem; font-size:.72rem; font-weight:700; }
          .quiet { color:var(--muted); font-size:.82rem; }
          .big-number { font-size:1.55rem; font-weight:750; color:var(--ink); }
          hr { border-color:var(--line); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_heading(eyebrow, title, subtitle, as_of=None):
    left, right = st.columns([5, 1])
    with left:
        st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
        st.title(title)
        st.markdown(f'<div class="subcopy">{subtitle}</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="pill">SYNTHETIC DATA</div>', unsafe_allow_html=True)
    if as_of:
        st.caption(f"Scenario snapshot · {as_of}")


def display_risk_table(rows, limit=None):
    shown = rows[:limit] if limit else rows
    if not shown:
        st.info("No customer orders are short before this shipment arrives.")
        return
    display_rows = [{
        "Order": row["order_id"],
        "Customer": row.get("customer", ""),
        "SKU": row.get("item", ""),
        "Short units": row["qty_uncovered"],
        "Due": row["due_date"],
        "Shipment": row["shipment_id"],
    } for row in shown]
    st.dataframe(pd.DataFrame(display_rows), width="stretch", hide_index=True)
