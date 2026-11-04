import unittest

import tests.support  # Installs the offline Firestore fake for this test process.
from src.supplychain import calculate_at_risk_orders, find_at_risk_orders


def shipment(shipment_id="S-200", item_id="CTRL-01", arrival="2026-06-20"):
    return {
        "shipment_id": shipment_id,
        "item_id": item_id,
        "qty": "100",
        "expected_arrival_date": arrival,
    }


class SupplyChainImpactTest(unittest.TestCase):
    def test_finds_order_shortfall_before_delayed_shipment_arrives(self):
        self.assertEqual(find_at_risk_orders("S-104"), [{
            "order_id": "O-202",
            "customer": "Demo Account 002",
            "item": "Control module",
            "qty_needed": 25,
            "qty_covered": 10,
            "customer_segment": "OEM",
            "qty_uncovered": 15,
            "due_date": "2026-11-15",
            "shipment_id": "S-104",
            "expected_arrival_date": "2026-11-20",
        }])

    def test_rejects_unknown_shipment(self):
        with self.assertRaisesRegex(ValueError, "Unknown shipment"):
            find_at_risk_orders("S-999")

    def test_zero_inventory_marks_order_at_risk(self):
        result = calculate_at_risk_orders(
            shipment=shipment(), inventory_rows=[],
            orders=[{
                "order_id": "O-300", "item_id": "CTRL-01",
                "qty_needed": "5", "due_date": "2026-06-19", "priority": "1",
            }],
        )
        self.assertEqual(result[0]["qty_uncovered"], 5)

    def test_order_due_on_arrival_date_is_conservatively_at_risk(self):
        result = calculate_at_risk_orders(
            shipment=shipment("S-201"),
            inventory_rows=[{"item_id": "CTRL-01", "available_qty": "0"}],
            orders=[{
                "order_id": "O-301", "item_id": "CTRL-01",
                "qty_needed": "3", "due_date": "2026-06-20", "priority": "1",
            }],
        )
        self.assertEqual(result[0]["qty_uncovered"], 3)

    def test_same_date_orders_use_explicit_priority(self):
        result = calculate_at_risk_orders(
            shipment=shipment("S-202"),
            inventory_rows=[{"item_id": "CTRL-01", "available_qty": "5"}],
            orders=[
                {"order_id": "O-402", "item_id": "CTRL-01", "qty_needed": "4",
                 "due_date": "2026-06-20", "priority": "2"},
                {"order_id": "O-401", "item_id": "CTRL-01", "qty_needed": "4",
                 "due_date": "2026-06-20", "priority": "1"},
            ],
        )
        self.assertEqual(result[0]["order_id"], "O-402")
        self.assertEqual(result[0]["qty_uncovered"], 3)

    def test_ignores_orders_for_other_items(self):
        result = calculate_at_risk_orders(
            shipment=shipment(),
            inventory_rows=[{"item_id": "CTRL-01", "available_qty": "0"}],
            orders=[{
                "order_id": "O-OTHER", "item_id": "LAMP-99",
                "qty_needed": "10", "due_date": "2026-06-19", "priority": "1",
            }],
        )
        self.assertEqual(result, [])

    def test_rejects_negative_inventory(self):
        with self.assertRaisesRegex(ValueError, "Inventory quantity cannot be negative"):
            calculate_at_risk_orders(
                shipment=shipment(),
                inventory_rows=[{"item_id": "CTRL-01", "available_qty": "-1"}],
                orders=[],
            )


if __name__ == "__main__":
    unittest.main()
