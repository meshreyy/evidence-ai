import unittest

from src.openai_agent import (
    MAX_TOOL_CALLS,
    deterministic_preflight,
    execute_tool,
)


class OpenAIToolTest(unittest.TestCase):
    def test_impact_tool_returns_data_provenance(self):
        result = execute_tool("check_shipment_impact", {"shipment_id": "S-104"})
        self.assertEqual(result["at_risk_orders"][0]["qty_uncovered"], 15)
        self.assertIn("data/orders.csv", result["data_sources"])
        self.assertEqual(result["allowed_next_steps"][0]["order_id"], "O-202")
        self.assertIn("same-day", result["allowed_next_steps"][0]["action"])
        self.assertIn("synthetic://brighthome/operations-playbook", result["allowed_next_steps"][0]["source"])
        self.assertTrue(result["prohibited_or_unsupported"])

    def test_shipment_lookup_says_delay_cause_is_unrecorded(self):
        result = execute_tool("get_shipment_details", {"shipment_id": "S-104"})
        self.assertTrue(result["found"])
        self.assertIsNone(result["delay_reason"])
        self.assertEqual(result["reason_status"], "not recorded in the demo data")

    def test_shipment_lookup_distinguishes_unknown_id(self):
        result = execute_tool("get_shipment_details", {"shipment_id": "S-999"})
        self.assertFalse(result["found"])
        self.assertIn("not present", result["message"])

    def test_document_tool_returns_source_citations(self):
        result = execute_tool("search_reference_docs", {
            "query": "uncovered quantity high priority analyst review",
            "limit": 2,
        })
        self.assertTrue(result["passages"])
        self.assertTrue(result["passages"][0]["url"])

    def test_cause_question_gets_direct_missing_evidence_answer(self):
        answer = deterministic_preflight("Why was shipment S-104 delayed?")
        self.assertIn("do not say why", answer)
        self.assertIn("data/shipments.csv", answer)

    def test_unsupported_action_request_gets_policy_grounded_answer(self):
        answer = deterministic_preflight(
            "For shipment S-104, promise the customer June 20 and ask the supplier to expedite."
        )
        self.assertIn("15 units uncovered", answer)
        self.assertIn("same-day", answer)
        self.assertIn("not supported", answer)
        self.assertIn("synthetic://brighthome/operations-playbook", answer)

    def test_unknown_shipment_gets_direct_not_found_answer(self):
        answer = deterministic_preflight("Shipment S-999: which orders are affected?")
        self.assertIn("S-999 is not present", answer)
        self.assertIn("can't determine", answer)

    def test_tool_budget_is_bounded(self):
        self.assertEqual(MAX_TOOL_CALLS, 4)

    def test_rejects_unregistered_tool(self):
        with self.assertRaisesRegex(ValueError, "Tool not allowed"):
            execute_tool("delete_orders", {})


if __name__ == "__main__":
    unittest.main()
