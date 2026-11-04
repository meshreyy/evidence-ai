import unittest

import tests.support  # Installs the offline Firestore fake for this test process.
from src.assistant import MAX_TOOL_CALLS, investigate


class AssistantWorkflowTest(unittest.TestCase):
    def test_shipment_question_uses_bounded_read_only_tools(self):
        result = investigate("Shipment S-104 is delayed. Which orders are at risk?")
        self.assertEqual(result["at_risk_orders"][0]["order_id"], "O-202")
        self.assertLessEqual(result["tool_calls"], MAX_TOOL_CALLS)
        # General CBP pages are not evidence for this company's shipment facts.
        self.assertEqual(result["references"], [])

    def test_import_question_retrieves_cbp_reference(self):
        result = investigate("What should a new importer know about customs brokers?")
        self.assertTrue(result["references"])
        self.assertIn("CBP", result["references"][0]["title"])

    def test_missing_shipment_id_is_reported_without_guessing(self):
        result = investigate("Which customer orders may be affected?")
        self.assertTrue(result["warnings"])
        self.assertEqual(result["at_risk_orders"], [])


if __name__ == "__main__":
    unittest.main()
