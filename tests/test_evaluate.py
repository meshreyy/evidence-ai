import unittest

from src.evaluate import run_evaluations


class EvaluationSuiteTest(unittest.TestCase):
    def test_all_golden_cases_pass(self):
        report = run_evaluations()
        self.assertEqual(report["passed"], report["total"])
        self.assertGreaterEqual(report["total"], 4)


if __name__ == "__main__":
    unittest.main()
