"""Deterministic tools and an explanation-only OpenAI integration."""
import re

from src.ai_explainer import explain_impact_with_openai
from src.documents import search_documents
from src.supplychain import find_at_risk_orders, read_csv

MODEL = "gpt-4o-mini"
SHIPMENT_ID_RE = re.compile(r"\b(S-\d+)\b", re.IGNORECASE)
CAUSE_QUESTION_RE = re.compile(r"\b(why|cause|reason|what caused)\b", re.IGNORECASE)
UNSUPPORTED_ACTION_RE = re.compile(
    r"\b(promise|promising|expedite|expediting|contact|contacting|change allocation|reallocate)\b",
    re.IGNORECASE,
)


def execute_tool(name, arguments):
    """Allowlist read-only calculations and lookups; no model-supplied code runs."""
    if name == "check_shipment_impact":
        rows = find_at_risk_orders(arguments["shipment_id"])
        actions = []
        for row in rows:
            action = (
                "Flag as high priority for same-day operations analyst review."
                if row["qty_uncovered"] > 10
                else "Flag for operations analyst review."
            )
            actions.append({
                "order_id": row["order_id"],
                "action": action,
                "basis": "Synthetic BrightHome Demo Operations Playbook: shortages above 10 units receive same-day review; all uncovered orders are reviewed.",
                "source": "synthetic://brighthome/operations-playbook",
            })
        return {
            "at_risk_orders": rows,
            "allowed_next_steps": actions,
            "prohibited_or_unsupported": [
                "Do not recommend contacting customers or suppliers, expediting freight, or changing allocations: this demo has no records or policy supporting those actions."
            ],
            "data_sources": [
                "data/supplychain.sqlite3 (shipments, inventory, orders)",
                "data/shipments.csv", "data/inventory.csv", "data/orders.csv",
            ],
            "note": "The calculation allocates current stock by due date, then numeric priority. Same-day arrival is treated conservatively.",
        }
    if name == "get_shipment_details":
        shipment = next(
            (row for row in read_csv("shipments.csv") if row["shipment_id"] == arguments["shipment_id"]),
            None,
        )
        if shipment is None:
            return {
                "found": False,
                "shipment_id": arguments["shipment_id"],
                "message": "This shipment ID is not present in the demo records. Do not infer that it has no affected orders.",
            }
        reason = shipment.get("delay_reason", "").strip()
        return {
            "found": True,
            "shipment_id": shipment["shipment_id"],
            "item_id": shipment["item_id"],
            "item_name": shipment.get("item_name"),
            "quantity": int(shipment["qty"]),
            "status": shipment.get("status"),
            "as_of_date": shipment.get("as_of_date"),
            "expected_arrival_date": shipment["expected_arrival_date"],
            "delay_reason": reason or None,
            "reason_status": "recorded" if reason else "not recorded in the demo data",
            "data_source": "data/shipments.csv",
        }
    if name == "search_reference_docs":
        results = search_documents(arguments["query"], limit=arguments["limit"])
        return {"passages": results, "note": "A public source provides context; the synthetic playbook is demo policy, not a real company policy."}
    raise ValueError(f"Tool not allowed: {name}")


def deterministic_preflight(question):
    """Handle missing/unsupported facts deterministically, without an LLM call."""
    match = SHIPMENT_ID_RE.search(question)
    if not match:
        return None

    shipment_id = match.group(1).upper()
    shipment = next(
        (row for row in read_csv("shipments.csv") if row["shipment_id"] == shipment_id),
        None,
    )
    if shipment is None:
        return (
            f"Shipment {shipment_id} is not present in the demo records, so I can't "
            f"determine which orders are affected. [data: data/shipments.csv]"
        )

    if CAUSE_QUESTION_RE.search(question):
        reason = shipment.get("delay_reason", "").strip()
        if not reason:
            return (
                f"The demo records do not say why shipment {shipment_id} was delayed; "
                f"no delay cause is recorded. [data: data/shipments.csv]"
            )
        return f"The recorded scenario reason for {shipment_id} is: {reason}. [data: data/shipments.csv]"

    if UNSUPPORTED_ACTION_RE.search(question):
        impact = execute_tool("check_shipment_impact", {"shipment_id": shipment_id})
        risks = impact["at_risk_orders"]
        if not risks:
            return (
                f"The requested actions are not supported by the demo records or policy. "
                f"No at-risk orders were identified for {shipment_id}. "
                f"[data: data/shipments.csv, data/inventory.csv, data/orders.csv]"
            )
        findings = []
        for row in risks:
            action = next(
                item["action"] for item in impact["allowed_next_steps"]
                if item["order_id"] == row["order_id"]
            )
            findings.append(
                f"{row['order_id']} has {row['qty_uncovered']} units uncovered; {action}"
            )
        return (
            "The requested promise, supplier expedite, or customer contact is not supported "
            "by the demo records or policy. " + " ".join(findings) +
            " [source: synthetic://brighthome/operations-playbook; "
            "data: data/shipments.csv, data/inventory.csv, data/orders.csv]"
        )

    return None


def answer_with_openai(question, model=MODEL):
    """Explain deterministic shipment findings; the model receives no tools."""
    preflight = deterministic_preflight(question)
    if preflight:
        return preflight

    match = SHIPMENT_ID_RE.search(question)
    if not match:
        return "Please include a shipment ID so I can explain its verified impact."

    shipment_id = match.group(1).upper()
    shipment_result = execute_tool("get_shipment_details", {"shipment_id": shipment_id})
    if not shipment_result["found"]:
        return shipment_result["message"]
    impact = execute_tool("check_shipment_impact", {"shipment_id": shipment_id})
    policy = search_documents("uncovered shortage high priority same-day analyst review", limit=1)
    policy_text = policy[0]["text"] if policy else "No policy passage was retrieved."
    brief = explain_impact_with_openai(
        shipment_result, impact, policy_text, model=model
    )

    lines = [brief["headline"], brief["summary"]]
    lines.extend(f"- {factor}" for factor in brief["risk_factors"])
    lines.append(f"Analyst focus: {brief['analyst_focus']}")
    lines.append(f"Limitation: {brief['limitation']}")
    sources = ", ".join(impact["data_sources"])
    lines.append(f"Evidence: {sources}; synthetic://brighthome/operations-playbook")
    lines.append("Unsupported actions: customer contact, supplier expediting, and delivery promises are not supported by this scenario.")
    return "\n".join(lines)
