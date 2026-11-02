import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class SupplyChainDashboardTest(unittest.TestCase):
    def test_overview_shows_operational_metrics_and_risk_data(self):
        app = AppTest.from_file("src/web_app.py").run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertEqual([title.value for title in app.title], ["Inbound supply overview"])
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Inbound shipments"], "50")
        self.assertEqual(metrics["Shipments with exposure"], "31")
        self.assertEqual(metrics["Units uncovered"], "1,046")
        self.assertTrue(app.dataframe)

    @patch("openai.OpenAI")
    def test_shipment_page_generates_visible_ai_brief(self, openai_client):
        client = openai_client.return_value
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=(
                '{"headline":"O-202 needs review",'
                '"summary":"O-202 is short 15 units before arrival.",'
                '"risk_factors":["Due date is before arrival."],'
                '"analyst_focus":"Flag O-202 for same-day review.",'
                '"limitation":"The delay cause is not recorded."}'
            )))]
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            app = AppTest.from_file("src/web_app.py").run(timeout=30)
            app.switch_page("pages/shipment_analysis.py").run(timeout=30)
            generate = next(button for button in app.button if button.label == "Generate AI explanation")
            self.assertFalse(generate.disabled)
            generate.click().run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertTrue(any("O-202 needs review" in item.value for item in app.markdown))
        self.assertTrue(any("Due date is before arrival" in item.value for item in app.markdown))
        self.assertNotIn("tools", client.chat.completions.create.call_args.kwargs)

    def test_shipment_page_shows_order_level_evidence_and_next_step(self):
        app = AppTest.from_file("src/web_app.py").run(timeout=30)
        app.switch_page("pages/shipment_analysis.py").run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertEqual([title.value for title in app.title], ["Shipment analysis"])
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Orders exposed"], "1")
        self.assertEqual(metrics["Expected arrival"], "2026-11-20")
        self.assertTrue(any("O-202" in str(item.value) for item in app.dataframe))
        self.assertTrue(any("same-day operations analyst review" in item.value for item in app.markdown))
        self.assertTrue(any("AI DECISION BRIEF" in item.value for item in app.markdown))
        self.assertTrue(any("Connect a server-side OpenAI key" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
