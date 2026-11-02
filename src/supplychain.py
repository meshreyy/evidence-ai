import csv
from datetime import date
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def read_csv(filename):
    with (DATA_DIR / filename).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def validate_records(shipments, inventory_rows, orders):
    """Fail early on missing IDs, duplicates, invalid dates, or bad quantities."""
    def require_unique(rows, key, label):
        values = [row.get(key, "").strip() for row in rows]
        if any(not value for value in values):
            raise ValueError(f"{label} must have a non-empty {key}")
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {label} {key}")

    require_unique(shipments, "shipment_id", "shipment")
    require_unique(inventory_rows, "item_id", "inventory item")
    require_unique(orders, "order_id", "order")

    for row in shipments:
        if not row.get("item_id", "").strip():
            raise ValueError("Shipment must have a non-empty item_id")
        date.fromisoformat(row["expected_arrival_date"])
        if int(row["qty"]) <= 0:
            raise ValueError("Shipment quantity must be positive")

    for row in inventory_rows:
        if int(row["available_qty"]) < 0:
            raise ValueError("Inventory quantity cannot be negative")

    for row in orders:
        if not row.get("item_id", "").strip():
            raise ValueError("Order must have a non-empty item_id")
        date.fromisoformat(row["due_date"])
        if int(row["qty_needed"]) <= 0:
            raise ValueError("Order quantity must be positive")
        if int(row.get("priority", 999)) < 1:
            raise ValueError("Order priority must be 1 or greater")


def calculate_at_risk_orders(shipment, inventory_rows, orders):
    """Calculate shortages using supplied records; no file or AI dependency.

    Orders due on the shipment's arrival date are included conservatively:
    dates have no time-of-day, so arrival-before-fulfillment cannot be assumed.
    """
    validate_records([shipment], inventory_rows, orders)
    item_id = shipment["item_id"]
    shipment_id = shipment["shipment_id"]
    arrival = date.fromisoformat(shipment["expected_arrival_date"])

    inventory = {
        row["item_id"]: int(row["available_qty"])
        for row in inventory_rows
    }
    available = inventory.get(item_id, 0)

    due_orders = [
        order for order in orders
        if order["item_id"] == item_id
        and date.fromisoformat(order["due_date"]) <= arrival
    ]
    due_orders.sort(key=lambda order: (
        order["due_date"],
        int(order.get("priority", 999)),
        order["order_id"],
    ))

    results = []
    for order in due_orders:
        needed = int(order["qty_needed"])
        covered = min(available, needed)
        shortfall = needed - covered
        available -= covered
        if shortfall:
            results.append({
                "order_id": order["order_id"],
                "qty_needed": needed,
                "qty_uncovered": shortfall,
                "due_date": order["due_date"],
                "shipment_id": shipment_id,
                "expected_arrival_date": arrival.isoformat(),
            })

    return results


def find_at_risk_orders(shipment_id):
    """Load CSV records and calculate shortages for one shipment."""
    shipments = {row["shipment_id"]: row for row in read_csv("shipments.csv")}
    if shipment_id not in shipments:
        raise ValueError(f"Unknown shipment: {shipment_id}")

    shipment = shipments[shipment_id]
    inventory_rows = read_csv("inventory.csv")
    orders = read_csv("orders.csv")
    validate_records(list(shipments.values()), inventory_rows, orders)
    return calculate_at_risk_orders(shipment, inventory_rows, orders)
