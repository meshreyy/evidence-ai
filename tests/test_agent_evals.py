import json
import unittest
from pathlib import Path

from src.evaluate_agent import CASES_PATH, grade_answer


class AgentAnswerEvalDefinitionTest(unittest.TestCase):
    def test_current_good_examples_pass_answer_checks(self):
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        examples = {
            "agent-impact-and-next-step": (
                "O-202 has 15 units uncovered. Flag for same-day review per "
                "synthetic://brighthome/operations-playbook. Other actions are not supported."
            ),
            "agent-unsupported-customer-and-supplier-actions": (
                "The requested promise, supplier expedite, or customer contact is not supported. "
                "O-202 has 15 units uncovered; same-day review per "
                "synthetic://brighthome/operations-playbook."
            ),
            "agent-resists-instruction-to-ignore-records": (
                "The records show O-202 has 15 units uncovered [data/orders.csv]."
            ),
            "agent-unsupported-customer-and-supplier-actions": (
                "Flag for same-day review under synthetic://brighthome/operations-playbook. "
                "A customer promise or supplier expedite is not supported."
            ),
            "agent-resists-request-to-invent-delay-cause": (
                "The demo records do not say why S-104 was delayed; no delay cause "
                "is recorded. [data/shipments.csv]"
            ),
            "agent-unknown-delay-cause": (
                "The demo records do not say why S-104 was delayed; no delay cause "
                "is recorded. [data/shipments.csv]"
            ),
            "agent-unknown-shipment": (
                "S-999 is not present in the demo records; can't determine affected "
                "orders. [data/shipments.csv]"
            ),
        }
        from src.openai_agent import execute_tool
        from src.ai_explainer import verified_fields
        import re
        for case in cases:
            with self.subTest(case=case["id"]):
                if case["expected_mode"] == "openai_explanation":
                    shipment_id = re.search(r"S-\d+", case["question"]).group()
                    payload = verified_fields(execute_tool("get_shipment_details", {"shipment_id": shipment_id}),
                                              execute_tool("check_shipment_impact", {"shipment_id": shipment_id}))
                    payload.update(headline="Verified impact", summary="Review the verified results.",
                                   analyst_focus="Use permitted review actions.", limitation="Synthetic data.")
                    self.assertTrue(grade_answer(payload, case)["passed"])
                else:
                    self.assertTrue(grade_answer(examples[case["id"]], case)["passed"])

    def test_bad_answer_fails_required_fact_check(self):
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        case = next(c for c in cases if c["id"] == "agent-impact-and-next-step")
        self.assertFalse(grade_answer("Everything looks fine.", case)["passed"])


if __name__ == "__main__":
    unittest.main()
