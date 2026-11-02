import unittest

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


if __name__ == "__main__":
    unittest.main()
