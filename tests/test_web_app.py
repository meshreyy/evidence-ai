import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

import tests.support  # Installs the offline Firestore fake for AppTest.


class SupplyChainDashboardTest(unittest.TestCase):
    def test_overview_shows_operational_metrics_and_risk_data(self):
        app = AppTest.from_file("src/web_app.py").run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertEqual(st.get_option("theme.base"), "dark")
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
                '"analyst_focus":"Flag O-202 for same-day review.",'
                '"limitation":"The delay cause is not recorded."}'
            )))]
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            app = AppTest.from_file("src/web_app.py").run(timeout=30)
            app.switch_page("pages/shipment_analysis.py").run(timeout=30)
            generate = next(button for button in app.button if button.label == "Generate explanation")
            self.assertFalse(generate.disabled)
            generate.click().run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertTrue(any("O-202 needs review" in item.value for item in app.markdown))
        self.assertNotIn("tools", client.chat.completions.create.call_args.kwargs)

    def test_shipment_page_shows_order_level_evidence_and_next_step(self):
        app = AppTest.from_file("src/web_app.py").run(timeout=30)
        app.switch_page("pages/shipment_analysis.py").run(timeout=30)

        self.assertFalse(list(app.exception))
        self.assertEqual([title.value for title in app.title], ["Impact analysis"])
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Orders at risk"], "1")
        self.assertEqual(metrics["Available inventory"], "30 units")
        self.assertTrue(any("15 units uncovered" in item.value for item in app.markdown))
        self.assertTrue(any("10 covered" in item.value and "15 short" in item.value for item in app.markdown))
        self.assertTrue(any("O-202" in str(item.value) for item in app.dataframe))
        self.assertTrue(any("same-day operations analyst review" in item.value for item in app.markdown))
        self.assertTrue(any("AI EXPLANATION" in item.value for item in app.markdown))
        self.assertTrue(any("Add a server-side OpenAI key" in item.value for item in app.caption))


if __name__ == "__main__":
    unittest.main()
