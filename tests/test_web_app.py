import unittest

from streamlit.testing.v1 import AppTest


class SupplyChainDashboardTest(unittest.TestCase):
    def test_review_shipment_shows_impact_and_recommendation(self):
        app = AppTest.from_file("src/web_app.py").run(timeout=20)
        app.button[0].click().run(timeout=20)

        self.assertFalse(list(app.exception))
        self.assertEqual(
            [(metric.label, metric.value) for metric in app.metric],
            [
                ("Orders at risk", "1"),
                ("Units uncovered", "15"),
                ("Shipment arrival", "2026-11-20"),
            ],
        )
        self.assertTrue(any("O-202" in item.value and "same-day" in item.value for item in app.markdown))
        self.assertTrue(any("not a real company policy" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
