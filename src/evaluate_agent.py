"""Run answer-level checks for the explanation-only OpenAI path and deterministic guards."""
import json
import os
from pathlib import Path

from src.openai_agent import answer_with_openai, deterministic_preflight

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "agent_cases.json"
RESULTS_PATH = ROOT / "evals" / "latest_agent_results.json"


def grade_answer(answer, case):
    normalized = answer.lower()
    checks = []
    for phrase in case.get("must_contain", []):
        checks.append({"check": f"contains: {phrase}", "passed": phrase.lower() in normalized})
    if case.get("must_contain_any"):
        options = case["must_contain_any"]
        checks.append({
            "check": "contains one of: " + " / ".join(options),
            "passed": any(phrase.lower() in normalized for phrase in options),
        })
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def run_live_evaluations():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your shell before running live agent evaluations.")

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        answer = answer_with_openai(
            case["question"], model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        )
        grade = grade_answer(answer, case)
        results.append({
            "id": case["id"],
            "mode": case["expected_mode"],
            "passed": grade["passed"],
            "checks": grade["checks"],
            "answer": answer,
        })

    report = {
        "passed": sum(row["passed"] for row in results),
        "total": len(results),
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    try:
        report = run_live_evaluations()
    except RuntimeError as exc:
        print(f"Cannot run live agent evals: {exc}")
        raise SystemExit(2)

    print(f"Agent answer evals: {report['passed']}/{report['total']} passed")
    for result in report["results"]:
        print(f"{'PASS' if result['passed'] else 'FAIL'} {result['id']} ({result['mode']})")
        for check in result["checks"]:
            print(f"  {'PASS' if check['passed'] else 'FAIL'} {check['check']}")
    print(f"Full answers saved to {RESULTS_PATH.relative_to(ROOT)}")
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
