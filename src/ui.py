"""Shared layout, theme, and portfolio-scale overview calculations for Streamlit."""
from datetime import date

import pandas as pd
import streamlit as st

from src.database import database_counts
from src.supplychain import calculate_at_risk_orders, read_csv


# A small tour of distinct existing scenarios; the underlying seed remains intact.
DEMO_SHIPMENT_IDS = ("S-104", "S-105", "S-150", "S-106", "S-108")


def demo_shipments(rows, show_all=False):
    """Select the demo tour without modifying operational records."""
    if show_all:
        return rows
    by_id = {row["shipment_id"]: row for row in rows}
    selected = [by_id[sid] for sid in DEMO_SHIPMENT_IDS if sid in by_id]
    # Custom databases may not contain any of the bundled demo IDs.
    return selected or rows


def shipment_option_label(shipment, risk_count, short_units, on_hand):
    if not risk_count:
        scenario = "Covered"
    elif on_hand == 0:
        scenario = "No stock"
    elif risk_count > 1:
        scenario = "Multiple orders"
    elif short_units > 10:
        scenario = "Same-day review"
    else:
        scenario = "Small shortage"
    return (f"{shipment['shipment_id']} · {scenario} · "
            f"{risk_count} at risk / {short_units} short")


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
          :root {
            --ink:#E8EDF5; --muted:#94A3B8; --line:#293446;
            --surface:#151E2C; --accent:#82A7FF; --cyan:#62D6BC;
          }
          .stApp { background:#0E1520; color:var(--ink); }
          [data-testid="stHeader"] { background:rgba(14,21,32,.95); }
          [data-testid="stAppDeployButton"] { display:none; }
          [data-testid="stMainBlockContainer"] {
            max-width:1320px; padding:2.25rem 2.75rem 3rem;
          }
          [data-testid="stVerticalBlock"] { gap:1.1rem; }
          [data-testid="stSidebar"] { background:#111A27; border-right:1px solid var(--line); }
          [data-testid="stSidebarUserContent"] { padding-top:1.2rem; }
          [data-testid="stSidebar"] [data-testid="stAlert"] { padding:.65rem; background:#19283A; }
          [data-testid="stSidebar"] [data-testid="stAlert"] p { font-size:.76rem; line-height:1.5; }
          [data-testid="stSidebarNavLink"] { border-radius:8px; }
          h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
          h1 { font-size:2rem !important; font-weight:650 !important; margin:0 !important; padding:.2rem 0 .25rem !important; }
          h2 { font-size:1.2rem !important; font-weight:650 !important; }
          h3 { font-size:1.05rem !important; font-weight:620 !important; padding:.1rem 0 !important; }
          p,label { color:#C6D0DF; }
          [data-testid="stCaptionContainer"] p { color:var(--muted); line-height:1.55; }
          [data-testid="stMetric"] {
            background:var(--surface); border:1px solid var(--line);
            border-radius:10px; padding:1rem 1.15rem; min-height:105px;
          }
          [data-testid="stMetricLabel"] { color:var(--muted); font-size:.78rem; }
          [data-testid="stMetricValue"] { color:var(--ink); font-size:1.9rem; font-weight:650; letter-spacing:-.04em; }
          [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:12px; }
          [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] { padding:.25rem; }
          [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
          [data-testid="stSelectbox"] [data-baseweb="select"] > div { border-radius:8px; background:#182231; border-color:#334155; }
          [data-testid="stWidgetLabel"] p { font-size:.8rem; font-weight:550; color:#B6C3D5; }
          div.stButton > button, div.stFormSubmitButton > button {
            background:#21324C; color:#E8EDF5; border:1px solid #3A506F;
            border-radius:8px; min-height:2.55rem; font-weight:600;
          }
          div.stButton > button p { color:inherit; font-size:.85rem; }
          div.stButton > button:hover { background:#2A4060; color:#fff; border-color:#82A7FF; }
          div.stButton > button[kind="primary"] { background:#88B1FF; color:#101B2C; border-color:#88B1FF; }
          div.stButton > button:focus-visible { outline:2px solid #88B1FF; outline-offset:3px; }
          .page-meta { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
          .eyebrow { color:#8FA8C7; font-size:.68rem; font-weight:650; letter-spacing:.13em; }
          .subcopy { color:var(--muted); font-size:.92rem; line-height:1.6; margin:0; }
          .brand { color:#F0F4FA; font-size:1.02rem; font-weight:650; letter-spacing:-.025em; }
          .brand-mark { color:var(--cyan); }
          .pill { display:inline-block; border:1px solid #34475B; color:#AABCD2;
            background:#172334; border-radius:999px; padding:.25rem .6rem;
            font-size:.62rem; font-weight:600; letter-spacing:.06em; white-space:nowrap; }
          .status-risk { color:#E3BC76; background:#302A21; border:1px solid #57472E;
            border-radius:5px; padding:.25rem .5rem; font-size:.74rem; font-weight:650; white-space:nowrap; }
          .impact-hero { background:#24231F; border:1px solid #514735;
            border-left:3px solid #D8AE65; border-radius:10px; padding:1.1rem 1.25rem; margin-bottom:.65rem; }
          .impact-value { color:#F0D7A6; font-size:1.85rem; line-height:1.25; font-weight:650; letter-spacing:-.035em; margin:.3rem 0 .5rem; }
          .impact-label { color:#D7B77E; font-size:.66rem; font-weight:650; text-transform:uppercase; letter-spacing:.1em; }
          .impact-detail { color:#C7BFAF; font-size:.83rem; line-height:1.65; }
          .action-card { display:flex; align-items:flex-start; gap:.8rem; background:#14241F;
            border:1px solid #29463D; border-radius:8px; padding:.85rem 1rem; color:#C0D9D0; font-size:.88rem; line-height:1.65; margin-bottom:.35rem; }
          .action-card .status-risk { color:#A5DDCC; background:#203930; border-color:#355346; }
          .allocation-track { display:flex; height:34px; overflow:hidden; border-radius:6px; background:#253143; margin:.45rem 0; }
          .allocation-covered { background:#547DA7; color:#fff; display:flex; align-items:center; justify-content:center; font-size:.73rem; font-weight:600; white-space:nowrap; }
          .allocation-short { background:#D4AF6F; color:#282218; display:flex; align-items:center; justify-content:center; font-size:.73rem; font-weight:650; white-space:nowrap; }
          .timeline { display:flex; align-items:center; gap:.65rem; color:#9BAFC7; font-size:.69rem; flex-wrap:wrap; }
          .timeline-line { flex:1; min-width:20px; height:2px; background:#42526A; }
          hr { border-color:var(--line); margin:1rem 0; }
          @media (max-width:640px) {
            [data-testid="stMainBlockContainer"] { padding:3.5rem 1rem 2rem; }
            h1 { font-size:1.65rem !important; }
            .page-meta { flex-wrap:wrap; gap:.5rem; }
            .eyebrow { font-size:.61rem; }
            .subcopy { font-size:.85rem; }
            .st-key-overview_metrics [data-testid="stHorizontalBlock"],
            .st-key-analysis_metrics [data-testid="stHorizontalBlock"] {
              display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem;
            }
            .st-key-overview_metrics [data-testid="stColumn"],
            .st-key-analysis_metrics [data-testid="stColumn"] { width:100% !important; min-width:0 !important; }
            [data-testid="stMetric"] { min-height:90px; padding:.8rem; }
            [data-testid="stMetricValue"] { font-size:1.55rem; }
            [data-testid="stMetricLabel"] p { font-size:.72rem; white-space:normal; overflow:visible; text-overflow:clip; }
            .st-key-analysis_metrics [data-testid="stHorizontalBlock"] { grid-template-columns:repeat(3,minmax(0,1fr)); }
            .st-key-analysis_metrics [data-testid="stMetric"] { padding:.7rem .6rem; }
            .st-key-analysis_metrics [data-testid="stMetricValue"] { font-size:1.15rem; }
            .impact-hero { padding:.9rem 1rem; }
            .impact-value { font-size:1.55rem; }
            .impact-detail { font-size:.78rem; }
            .action-card { padding:.8rem; gap:.65rem; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_heading(eyebrow, title, subtitle, as_of=None):
    st.markdown(
        f'<div class="page-meta"><span class="eyebrow">{eyebrow}</span>'
        '<span class="pill">SYNTHETIC DATA</span></div>', unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(f'<div class="subcopy">{subtitle}</div>', unsafe_allow_html=True)
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
