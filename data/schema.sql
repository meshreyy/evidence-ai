-- SupplyChain Copilot relational schema (SQLite).
-- All seeded company, order, inventory, and shipment records are synthetic.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_cost_usd REAL NOT NULL CHECK (unit_cost_usd >= 0)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(item_id),
    qty INTEGER NOT NULL CHECK (qty > 0),
    expected_arrival_date TEXT NOT NULL,
    delay_reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    as_of_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    item_id TEXT PRIMARY KEY REFERENCES items(item_id),
    available_qty INTEGER NOT NULL CHECK (available_qty >= 0),
    as_of_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(item_id),
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    qty_needed INTEGER NOT NULL CHECK (qty_needed > 0),
    due_date TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority >= 1),
    order_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_item_due
    ON orders(item_id, due_date, priority);
CREATE INDEX IF NOT EXISTS idx_shipments_arrival
    ON shipments(expected_arrival_date);
