"""Bounded tool workflow for the supply-chain investigation demo.

This version uses deterministic routing (no external LLM/API key). It is the
safe, testable tool layer that a model-based planner can call later.
"""
import re

from src.documents import search_documents
from src.supplychain import find_at_risk_orders

MAX_TOOL_CALLS = 2
SHIPMENT_PATTERN = re.compile(r"\b(S-\d+)\b", re.IGNORECASE)
REFERENCE_TERMS = {"import", "importer", "export", "customs", "broker", "regulation", "documentation", "cbp"}


def investigate(question):
    """Run at most two read-only tools and return findings plus citations."""
    result = {"question": question, "at_risk_orders": [], "references": [], "warnings": []}
    calls = 0

    match = SHIPMENT_PATTERN.search(question)
    if match:
        calls += 1
        shipment_id = match.group(1).upper()
        try:
            result["at_risk_orders"] = find_at_risk_orders(shipment_id)
        except ValueError as exc:
            result["warnings"].append(str(exc))
    else:
        result["warnings"].append("Include a shipment ID such as S-104 to check affected orders.")

    # Only search the CBP corpus when the question is about import guidance.
    # Shipment/order questions should not receive irrelevant regulatory snippets.
    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    if calls < MAX_TOOL_CALLS and question_terms & REFERENCE_TERMS:
        calls += 1
        result["references"] = search_documents(question, limit=3)

    result["tool_calls"] = calls
    return result
