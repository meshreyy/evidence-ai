"""Read-only browser view of the local SQLite database."""
import pandas as pd
import streamlit as st

from src.database import SCHEMA_PATH, database_counts, read_table
from src.ui import page_heading

counts = database_counts()
page_heading(
    "DATA / SQLITE",
    "Database explorer",
    "Browse the records behind the shipment analysis. Read-only; all rows are synthetic.",
)

m1, m2, m3 = st.columns(3)
m1.metric("Linked tables", len(counts))
m2.metric("Total records", f"{sum(counts.values()):,}")
m3.metric("Database engine", "SQLite")

labels = {
    "shipments": "Shipments",
    "orders": "Customer orders",
    "items": "Items / SKUs",
    "inventory": "Inventory balances",
    "customers": "Customer accounts",
}
columns = st.columns([1, 2])
with columns[0]:
    selected_table = st.selectbox(
        "Choose a table",
        list(labels),
        format_func=lambda table: f"{labels[table]} · {counts[table]} rows",
    )
with columns[1]:
    search = st.text_input("Filter rows", placeholder="Search IDs, names, items, dates…")

rows = read_table(selected_table)
if search.strip():
    query = search.strip().lower()
    rows = [
        row for row in rows
        if any(query in str(value).lower() for value in row.values())
    ]
st.markdown(f"### {labels[selected_table]}")
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=460)
st.caption(
    f"Showing {len(rows):,} matching rows · generated database: `data/supplychain.sqlite3` · "
    "CSV seed files are versioned; the SQLite file is rebuilt locally."
)

with st.expander("View relational schema"):
    st.code(SCHEMA_PATH.read_text(encoding="utf-8"), language="sql")
    st.caption(
        "Orders link to customer accounts and SKUs. Inventory and inbound shipments link to SKUs. "
        "The AI does not query this page or database; it only explains the result prepared by the app."
    )
