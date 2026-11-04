import unittest

import tests.support  # Installs the offline Firestore fake for this test process.
from src.database import database_counts, read_table, seed_firestore
from src.supplychain import read_csv
from tests.support import FakeFirestore


class FirestoreDatabaseTest(unittest.TestCase):
    def test_seeded_collections_have_expected_breadth(self):
        self.assertEqual(
            database_counts(),
            {"items": 50, "customers": 12, "shipments": 50, "inventory": 50, "orders": 248},
        )

    def test_order_view_enriches_account_and_item_details(self):
        orders = read_csv("orders.csv")
        order = next(row for row in orders if row["order_id"] == "O-202")
        self.assertEqual(order["customer_name"], "Demo Account 002")
        self.assertEqual(order["item_name"], "Control module")
        self.assertEqual(order["customer_segment"], "OEM")

    def test_seed_command_is_repeatable(self):
        client = FakeFirestore()
        first = seed_firestore(client=client)
        second = seed_firestore(client=client)
        self.assertEqual(first, second)
        self.assertEqual(first["orders"], 248)
        self.assertEqual(len(read_table("customers", client=client)), 12)


if __name__ == "__main__":
    unittest.main()
