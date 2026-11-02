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


def get_openai_api_key():
    """Read a key from the server environment or Streamlit secrets, never UI input."""
    import os

    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def apply_visual_theme():
    st.markdown(
        """
        <style>
          :root { --ink:#20283C; --muted:#778198; --line:#E5E8F0;
                  --surface:#FFFFFF; --accent:#5664D8; --accent-soft:#EEF0FF; }
          .stApp { background:#F4F6FB; color:var(--ink); }
          [data-testid="stHeader"] { background:rgba(244,246,251,.96); }
          [data-testid="stAppViewContainer"] .main .block-container {
            max-width:1380px; padding-top:1.45rem; padding-bottom:2.4rem;
          }
          [data-testid="stSidebar"] { background:#F8F9FD; border-right:1px solid var(--line); }
          h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
          h1 { font-size:1.9rem !important; font-weight:720 !important; margin:.15rem 0 .25rem !important; }
          h2 { font-size:1.18rem !important; font-weight:680 !important; }
          h3 { font-size:1rem !important; font-weight:680 !important; }
          p,label { color:#465168; }
          [data-testid="stMetric"] {
            background:var(--surface); border:1px solid var(--line); border-radius:12px;
            padding:13px 17px; min-height:100px; box-shadow:0 2px 8px rgba(31,44,78,.035);
          }
          [data-testid="stMetricLabel"] { color:var(--muted); font-size:.78rem; }
          [data-testid="stMetricValue"] { color:var(--ink); font-weight:720; }
          [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--surface); border-color:var(--line); border-radius:12px;
            box-shadow:0 2px 8px rgba(31,44,78,.035);
          }
          [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
          div.stButton > button, div.stFormSubmitButton > button {
            background:#5664D8; color:#fff; border:1px solid #5664D8;
            border-radius:8px; min-height:2.45rem; font-weight:650;
          }
          div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background:#4653C5; color:#fff; border-color:#4653C5;
          }
          .eyebrow { color:var(--accent); font-size:.7rem; font-weight:750; letter-spacing:.12em; }
          .subcopy { color:var(--muted); font-size:.92rem; margin:.1rem 0 0; }
          .brand { color:#20283C; font-size:1.02rem; font-weight:750; letter-spacing:-.02em; }
          .brand-mark { color:var(--accent); }
          .pill { display:inline-block; border:1px solid #D9DDFB; color:#4653C5;
            background:#EEF0FF; border-radius:999px; padding:.3rem .64rem;
            font-size:.68rem; font-weight:750; letter-spacing:.05em; }
          .status-risk { color:#9A5B08; background:#FFF5E5; border:1px solid #F4D7A7;
            border-radius:999px; padding:.24rem .55rem; font-size:.7rem; font-weight:750; }
          .quiet { color:var(--muted); font-size:.8rem; }
          .impact-hero { background:#FFF; border:1px solid #F0C878; border-left:5px solid #E5A323;
            border-radius:12px; padding:1rem 1.15rem; }
          .impact-value { color:#A86500; font-size:1.75rem; line-height:1.05; font-weight:800; }
          .impact-label { color:#7A5A2A; font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
          .ai-card { background:#F0F2FF; border:1px solid #DDE1FF; border-radius:12px; padding:.9rem 1rem; }
          .allocation-track { display:flex; height:34px; overflow:hidden; border-radius:7px; background:#EEF0F5; margin:.5rem 0; }
          .allocation-covered { background:#5664D8; color:#fff; display:flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:700; white-space:nowrap; }
          .allocation-short { background:#F5B849; color:#49320B; display:flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:750; white-space:nowrap; }
          .timeline { display:flex; align-items:center; gap:.75rem; color:#576176; font-size:.78rem; }
          .timeline-line { flex:1; height:3px; background:linear-gradient(90deg,#E5A323 0 50%,#D9DDFB 50% 100%); border-radius:4px; }
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
