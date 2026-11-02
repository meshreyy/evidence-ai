import unittest

from src.database import database_counts, initialize_database
from src.supplychain import read_csv


class SupplyChainDatabaseTest(unittest.TestCase):
    def test_seeded_relational_store_has_expected_breadth(self):
        database_path = initialize_database()
        self.assertTrue(database_path.exists())
        self.assertEqual(
            database_counts(),
            {"items": 10, "customers": 12, "shipments": 10, "inventory": 10, "orders": 48},
        )

    def test_order_view_joins_customer_and_item_descriptions(self):
        orders = read_csv("orders.csv")
        order = next(row for row in orders if row["order_id"] == "O-202")
        self.assertEqual(order["customer_name"], "Demo Account 002")
        self.assertEqual(order["item_name"], "Control module")
        self.assertEqual(order["customer_segment"], "OEM")


if __name__ == "__main__":
    unittest.main()
