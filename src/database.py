"""Local SQLite store seeded reproducibly from the labeled synthetic CSV files."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "supplychain.sqlite3"
SCHEMA_PATH = DATA_DIR / "schema.sql"
SEED_FILES = {
    "items": "items.csv",
    "customers": "customers.csv",
    "shipments": "shipments.csv",
    "inventory": "inventory.csv",
    "orders": "orders.csv",
}

def _seed_is_current():
    if not DB_PATH.exists() or DB_PATH.stat().st_mtime < SCHEMA_PATH.stat().st_mtime:
        return False
    return all(
        DB_PATH.stat().st_mtime >= (DATA_DIR / filename).stat().st_mtime
        for filename in SEED_FILES.values()
    )


def initialize_database(force=False):
    """Create/rebuild the local relational database from source CSV seed files."""
    DATA_DIR.mkdir(exist_ok=True)
    if not force and _seed_is_current():
        return DB_PATH

    temporary_path = DB_PATH.with_suffix(".tmp")
    temporary_path.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary_path)
    try:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        for table, filename in SEED_FILES.items():
            with (DATA_DIR / filename).open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            if not rows:
                raise ValueError(f"Synthetic seed file is empty: {filename}")
            columns = list(rows[0])
            placeholders = ",".join("?" for _ in columns)
            quoted_columns = ",".join(f'"{column}"' for column in columns)
            values = [tuple(row[column] for column in columns) for row in rows]
            connection.executemany(
                f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({placeholders})',
                values,
            )
        connection.commit()
    except Exception:
        connection.close()
        temporary_path.unlink(missing_ok=True)
        raise
    else:
        connection.close()
    temporary_path.replace(DB_PATH)
    return DB_PATH


def read_table(table):
    """Read a table-shaped view, joining descriptive item/customer fields."""
    initialize_database()
    queries = {
        "items": "SELECT * FROM items ORDER BY item_id",
        "customers": "SELECT * FROM customers ORDER BY customer_id",
        "shipments": "SELECT s.*, i.item_name FROM shipments s JOIN items i USING(item_id) ORDER BY shipment_id",
        "inventory": "SELECT v.*, i.item_name FROM inventory v JOIN items i USING(item_id) ORDER BY item_id",
        "orders": """SELECT o.*, i.item_name, c.customer_name, c.segment AS customer_segment,
                          c.region AS customer_region
                   FROM orders o JOIN items i USING(item_id)
                   JOIN customers c USING(customer_id) ORDER BY order_id""",
    }
    if table not in queries:
        raise ValueError(f"Unknown database table: {table}")
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(queries[table])]


def database_counts():
    initialize_database()
    with sqlite3.connect(DB_PATH) as connection:
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in SEED_FILES
        }
