# Inspecting the dataset and SQL database

This repository includes the synthetic source tables as CSV files and a SQL schema. The application builds a local SQLite database from those versioned inputs; the generated `.sqlite3` file is ignored by Git and is recreated when you run the app or the build script.

## Rebuild and inspect

From the project root:

```bash
python scripts/generate_synthetic_data.py  # optional; regenerates deterministic CSV seed data
python scripts/build_database.py          # creates data/supplychain.sqlite3
sqlite3 data/supplychain.sqlite3 < data/inspect.sql
```

The schema is visible in [`data/schema.sql`](../data/schema.sql), the SQL inspection queries are in [`data/inspect.sql`](../data/inspect.sql), and the reproducible source records are in `data/*.csv`. Open `data/supplychain.sqlite3` in DB Browser for SQLite or another SQLite viewer to browse tables and run queries.

The database contains 50 shipment records, 50 SKUs, 50 inventory balances, 248 order lines, and 12 demo accounts. Foreign keys link orders, items, customers, inventory, and inbound shipments. Dates are part of a fixed synthetic scenario snapshot (as of 2026-11-02), not live operational data.

## What to tell a reviewer

“The app uses a local relational SQLite database seeded from reproducible synthetic CSV records. The LLM is not trained on this data; it queries selected records through read-only tools, while deterministic Python code computes inventory allocation. I can inspect the schema, tables, joins, and a SQL reproduction of the S-104 shortfall.”

This is a portfolio-scale working prototype—not a real company database or production-grade supply-chain system. Each demo SKU has one inbound shipment; multi-shipment aggregation is not implemented.

## Firebase or hosted data

Firebase Firestore is a document/NoSQL database, not SQL. It could store this data, but would add cloud configuration, credentials, access-control rules, network dependencies, and a mismatch with the relational order/inventory joins. It would not make synthetic data more real or improve model quality by itself.

For this portfolio prototype, SQLite is the simplest inspectable and reproducible choice. If a hosted relational database is specifically needed later, a PostgreSQL service such as Supabase is a closer fit. Never put administrator/service-role credentials in a public repository; use narrowly scoped read-only access and keep secrets in deployment settings.
