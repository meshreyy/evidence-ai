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

    if os.getenv("ENABLE_LIVE_AI", "false").lower() != "true":
        return None
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
          :root { --ink:#EEF2FF; --muted:#9BA8C1; --line:#29344A;
                  --surface:#171E2E; --accent:#8290FF; --cyan:#46D7CF; }
          .stApp { background:#0D1220; color:var(--ink); }
          [data-testid="stHeader"] { background:rgba(13,18,32,.96); }
          [data-testid="stAppViewContainer"] .main .block-container {
            max-width:1380px; padding-top:1.35rem; padding-bottom:2.2rem;
          }
          [data-testid="stSidebar"] { background:#111827; border-right:1px solid var(--line); }
          h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
          h1 { font-size:1.9rem !important; font-weight:720 !important; margin:.15rem 0 .25rem !important; }
          h2 { font-size:1.18rem !important; font-weight:680 !important; }
          h3 { font-size:1rem !important; font-weight:680 !important; }
          p,label { color:#C4CDE0; }
          [data-testid="stMetric"] {
            background:linear-gradient(145deg,#1A2337,#151C2C); border:1px solid #303D58;
            border-radius:12px; padding:13px 17px; min-height:100px;
            box-shadow:0 5px 18px rgba(0,0,0,.18);
          }
          [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) [data-testid="stMetric"] { border-top:3px solid #8290FF; }
          [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) [data-testid="stMetric"] { border-top:3px solid #46D7CF; }
          [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) [data-testid="stMetric"] { border-top:3px solid #F4B84A; }
          [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) [data-testid="stMetric"] { border-top:3px solid #F27691; }
          [data-testid="stMetricLabel"] { color:var(--muted); font-size:.78rem; }
          [data-testid="stMetricValue"] { color:#F5F7FF; font-weight:760; }
          [data-testid="stVerticalBlockBorderWrapper"] {
            background:#151C2B; border-color:var(--line); border-radius:12px;
            box-shadow:0 5px 18px rgba(0,0,0,.16);
          }
          [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; }
          div.stButton > button, div.stFormSubmitButton > button {
            background:#6675EA; color:#fff; border:1px solid #7885F2;
            border-radius:8px; min-height:2.45rem; font-weight:680;
          }
          div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background:#7885F2; color:#fff; border-color:#8D98FF;
          }
          .eyebrow { color:#9AA6FF; font-size:.7rem; font-weight:750; letter-spacing:.12em; }
          .subcopy { color:var(--muted); font-size:.92rem; margin:.1rem 0 0; }
          .brand { color:#F1F4FF; font-size:1.02rem; font-weight:750; letter-spacing:-.02em; }
          .brand-mark { color:#8290FF; }
          .pill { display:inline-block; border:1px solid #394574; color:#B7C0FF;
            background:#202943; border-radius:999px; padding:.3rem .64rem;
            font-size:.68rem; font-weight:750; letter-spacing:.05em; }
          .status-risk { color:#FFD27A; background:#352B1A; border:1px solid #70582C;
            border-radius:999px; padding:.24rem .55rem; font-size:.7rem; font-weight:750; }
          .quiet { color:var(--muted); font-size:.8rem; }
          .impact-hero { background:linear-gradient(120deg,#2C271D,#202235); border:1px solid #6B572F;
            border-left:5px solid #F4B84A; border-radius:12px; padding:1rem 1.15rem; }
          .impact-value { color:#FFD166; font-size:2rem; line-height:1.05; font-weight:850; letter-spacing:-.04em; }
          .impact-label { color:#F5C96F; font-size:.72rem; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }
          .ai-card { background:#1A2036; border:1px solid #3A426A; border-radius:12px; padding:.9rem 1rem; }
          .allocation-track { display:flex; height:38px; overflow:hidden; border-radius:8px; background:#252D40; margin:.65rem 0; }
          .allocation-covered { background:#586CE0; color:#fff; display:flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:750; white-space:nowrap; }
          .allocation-short { background:#F4B84A; color:#382507; display:flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:800; white-space:nowrap; }
          .timeline { display:flex; align-items:center; gap:.75rem; color:#C1CBE0; font-size:.76rem; }
          .timeline-line { flex:1; height:4px; background:linear-gradient(90deg,#F4B84A 0 50%,#586CE0 50% 100%); border-radius:4px; }
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
