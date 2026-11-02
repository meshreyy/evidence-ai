"""Regenerate the clearly synthetic, deterministic SupplyChain Copilot dataset."""
import csv
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AS_OF = date(2026, 11, 2)

ITEMS = [
    ("CTRL-01", "Control module", "Electronics", 42.50),
    ("PUMP-02", "Compact fluid pump", "Fluid systems", 86.00),
    ("SENSOR-03", "Pressure sensor", "Sensors", 18.75),
    ("VALVE-04", "Flow control valve", "Fluid systems", 31.20),
    ("MOTOR-05", "Drive motor", "Motion", 124.00),
    ("SEAL-06", "Seal kit", "Service parts", 7.80),
    ("PCB-07", "Interface board", "Electronics", 55.00),
    ("FAN-08", "Cooling fan assembly", "Thermal", 23.40),
    ("CABLE-09", "Harness assembly", "Electrical", 12.60),
    ("BRKT-10", "Mounting bracket", "Mechanical", 9.25),
]
CUSTOMERS = [
    (f"CUST-{i:03}", f"Demo Account {i:03}", ["Retail", "Wholesale", "OEM"][i % 3],
     ["Northeast", "Midwest", "South", "West"][i % 4])
    for i in range(1, 13)
]
SHIPMENT_SPECS = [
    ("S-104", "CTRL-01", 100, 18, ""),
    ("S-105", "PUMP-02", 60, 10, "Carrier schedule change"),
    ("S-106", "SENSOR-03", 80, 25, "Port congestion"),
    ("S-107", "VALVE-04", 50, 14, "Documentation review"),
    ("S-108", "MOTOR-05", 40, 32, ""),
    ("S-109", "SEAL-06", 200, 7, "Carrier schedule change"),
    ("S-110", "PCB-07", 100, 38, "Port congestion"),
    ("S-111", "FAN-08", 75, 21, ""),
    ("S-112", "CABLE-09", 120, 12, "Weather disruption"),
    ("S-113", "BRKT-10", 90, 28, "Documentation review"),
]
INVENTORY = {
    "CTRL-01": 30, "PUMP-02": 65, "SENSOR-03": 5, "VALVE-04": 22,
    "MOTOR-05": 0, "SEAL-06": 100, "PCB-07": 14, "FAN-08": 36,
    "CABLE-09": 75, "BRKT-10": 8,
}


def write_csv(filename, columns, rows):
    with (DATA_DIR / filename).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    write_csv("items.csv", ["item_id", "item_name", "category", "unit_cost_usd"], [
        dict(zip(["item_id", "item_name", "category", "unit_cost_usd"], row)) for row in ITEMS
    ])
    write_csv("customers.csv", ["customer_id", "customer_name", "segment", "region"], [
        dict(zip(["customer_id", "customer_name", "segment", "region"], row)) for row in CUSTOMERS
    ])

    shipments = []
    inventory = []
    for shipment_id, item_id, qty, days_out, reason in SHIPMENT_SPECS:
        shipments.append({
            "shipment_id": shipment_id,
            "item_id": item_id,
            "qty": qty,
            "expected_arrival_date": (AS_OF + timedelta(days=days_out)).isoformat(),
            "delay_reason": reason,
            "status": "Delayed",
            "as_of_date": AS_OF.isoformat(),
        })
        inventory.append({
            "item_id": item_id,
            "available_qty": INVENTORY[item_id],
            "as_of_date": AS_OF.isoformat(),
        })
    write_csv("shipments.csv", list(shipments[0]), shipments)
    write_csv("inventory.csv", list(inventory[0]), inventory)

    orders = [
        {"order_id": "O-201", "item_id": "CTRL-01", "customer_id": "CUST-001",
         "qty_needed": 20, "due_date": "2026-11-12", "priority": 2, "order_status": "Open"},
        {"order_id": "O-202", "item_id": "CTRL-01", "customer_id": "CUST-002",
         "qty_needed": 25, "due_date": "2026-11-15", "priority": 1, "order_status": "Open"},
        {"order_id": "O-203", "item_id": "CTRL-01", "customer_id": "CUST-003",
         "qty_needed": 15, "due_date": "2026-11-27", "priority": 3, "order_status": "Open"},
    ]
    for index, (shipment_id, item_id, _qty, days_out, _reason) in enumerate(SHIPMENT_SPECS[1:], start=1):
        arrival = AS_OF + timedelta(days=days_out)
        for n, (offset, quantity, priority) in enumerate(
            [(-12, 18, 1), (-7, 24, 2), (-2, 16, 1), (5, 12, 3), (12, 20, 2)],
            start=1,
        ):
            order_number = 203 + (index - 1) * 5 + n
            orders.append({
                "order_id": f"O-{order_number}",
                "item_id": item_id,
                "customer_id": f"CUST-{((index * 2 + n - 1) % len(CUSTOMERS)) + 1:03}",
                "qty_needed": quantity,
                "due_date": (arrival + timedelta(days=offset)).isoformat(),
                "priority": priority,
                "order_status": "Open",
            })
    write_csv("orders.csv", list(orders[0]), orders)
    print(
        f"Wrote deterministic synthetic seed data: {len(shipments)} shipments, "
        f"{len(ITEMS)} items, {len(CUSTOMERS)} demo accounts, "
        f"{len(inventory)} inventory balances, {len(orders)} orders."
    )


if __name__ == "__main__":
    main()
