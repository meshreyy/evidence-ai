import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.ai_explainer import explain_impact_with_openai
from src.openai_agent import execute_tool
from src.supplychain import read_csv


class AIExplainerTest(unittest.TestCase):
    @patch("openai.OpenAI")
    def test_model_receives_precomputed_result_without_tools(self, openai_client):
        brief_json = {
            "orders": [{"order_id": "O-202", "qty_uncovered": 15}],
            "actions": [{"order_id": "O-202", "action_id": "same_day_review"}],
            "delay_cause": "not recorded", "delivery_promise": None,
            "headline": "O-202 needs same-day review",
            "summary": "O-202 is short 15 units before the shipment arrives.",
            "analyst_focus": "Flag O-202 for same-day analyst review.",
            "limitation": "The demo records do not state why the shipment was delayed.",
        }
        client = openai_client.return_value
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(brief_json)))]
        )
        shipment = next(row for row in read_csv("shipments.csv") if row["shipment_id"] == "S-104")
        impact = execute_tool("check_shipment_impact", {"shipment_id": "S-104"})

        result = explain_impact_with_openai(
            shipment, impact, "Synthetic policy: shortages above 10 units receive same-day review.",
            api_key="test-key",
        )

        self.assertEqual(result["headline"], brief_json["headline"])
        call = client.chat.completions.create.call_args.kwargs
        self.assertNotIn("tools", call)
        supplied_context = json.loads(call["messages"][1]["content"])
        self.assertEqual(supplied_context["precomputed_at_risk_orders"][0]["qty_uncovered"], 15)
        self.assertIn("same-day", supplied_context["allowed_next_steps"][0]["action"])

    @patch("openai.OpenAI")
    def test_rejects_incomplete_structured_response(self, openai_client):
        client = openai_client.return_value
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"incomplete"}'))]
        )
        shipment = next(row for row in read_csv("shipments.csv") if row["shipment_id"] == "S-104")
        impact = execute_tool("check_shipment_impact", {"shipment_id": "S-104"})
        with self.assertRaisesRegex(ValueError, "missing required"):
            explain_impact_with_openai(shipment, impact, "Policy.", api_key="test-key")


if __name__ == "__main__":
    unittest.main()
