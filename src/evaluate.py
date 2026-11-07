"""Run a small, deterministic evaluation set without calling an LLM/API."""
import json
from pathlib import Path

from src.documents import search_documents
from src.supplychain import find_at_risk_orders

CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "cases.json"


def run_evaluations():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        passed = False
        detail = ""
        if case["type"] == "impact":
            actual = find_at_risk_orders(case["shipment_id"])
            expected = case["expected_orders"]
            passed = [
                {"order_id": row["order_id"], "qty_uncovered": row["qty_uncovered"]}
                for row in actual
            ] == expected
            detail = f"expected={expected}; actual={actual}"
        elif case["type"] == "impact-error":
            try:
                find_at_risk_orders(case["shipment_id"])
            except ValueError as exc:
                passed = case["expected_error_contains"] in str(exc)
                detail = str(exc)
            else:
                detail = "Expected an unknown-shipment error, got a result"
        elif case["type"] == "retrieval":
            passages = search_documents(case["query"], limit=3)
            passed = bool(passages)
            if passed:
                first = passages[0]
                passed = first["url"].startswith(case["expected_source_prefix"])
                if case.get("expected_title_contains"):
                    passed = passed and case["expected_title_contains"] in first["title"]
                detail = f"top_source={first['title']} [{first['url']}]"
            else:
                detail = "No relevant passage retrieved"
        results.append({"id": case["id"], "passed": passed, "detail": detail})

    passed_count = sum(row["passed"] for row in results)
    return {
        "passed": passed_count,
        "total": len(results),
        "pass_rate": passed_count / len(results) if results else 0.0,
        "results": results,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only the seeded in-memory demo database")
    if parser.parse_args().offline:
        from tests.support import seeded_fake_firestore
        from src.database import set_firestore_client_for_testing
        set_firestore_client_for_testing(seeded_fake_firestore())
    report = run_evaluations()
    print(f"Deterministic evals: {report['passed']}/{report['total']} passed ({report['pass_rate']:.0%})")
    for row in report["results"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['id']}: {row['detail']}")
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
