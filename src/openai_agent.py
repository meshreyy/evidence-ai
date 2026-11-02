"""Optional OpenAI tool-calling agent; the underlying business tools stay deterministic."""
import json
import re

from src.documents import search_documents
from src.supplychain import find_at_risk_orders, read_csv

MAX_TOOL_CALLS = 4
MODEL = "gpt-4o-mini"
SHIPMENT_ID_RE = re.compile(r"\b(S-\d+)\b", re.IGNORECASE)
CAUSE_QUESTION_RE = re.compile(r"\b(why|cause|reason|what caused)\b", re.IGNORECASE)
UNSUPPORTED_ACTION_RE = re.compile(
    r"\b(promise|promising|expedite|expediting|contact|contacting|change allocation|reallocate)\b",
    re.IGNORECASE,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_shipment_impact",
            "description": "Calculate which orders are short before a known shipment arrives.",
            "parameters": {
                "type": "object",
                "properties": {"shipment_id": {"type": "string"}},
                "required": ["shipment_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_details",
            "description": "Look up shipment facts and whether a delay cause is recorded. Use for status/cause questions.",
            "parameters": {
                "type": "object",
                "properties": {"shipment_id": {"type": "string"}},
                "required": ["shipment_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_reference_docs",
            "description": "Find cited passages in saved CBP guidance and the clearly synthetic BrightHome demo playbook.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "enum": [1, 2, 3]},
                },
                "required": ["query", "limit"],
                "additionalProperties": False,
            },
        },
    },
]

SYSTEM_PROMPT = """You are SupplyChain Copilot, a decision-support assistant for a fictional demo company.
For an order-impact question, call check_shipment_impact. For shipment status or delay-cause
questions, call get_shipment_details. For a question about procedure, call search_reference_docs.
If get_shipment_details says the cause is not recorded, state plainly: "The demo records do not
say why this shipment was delayed." If a shipment is not found, say that its ID is not in the
demo records; do not say there are no affected orders. Never invent inventory, dates, causes, supplier options, or actions.
You may recommend ONLY actions explicitly returned by a tool. If no tool provides an action,
say that the records do not establish a next step. The BrightHome playbook is synthetic demo
policy, not a real company's policy. CBP pages are general import guidance, not evidence of
a particular shipment's status or cause. Cite business facts as [data: ...] and policy claims
as [source: title, URL or synthetic URI, chunk_id]. Do not contact customers, change records,
or make commitments. Keep the answer concise and leave decisions to the human analyst."""


def execute_tool(name, arguments):
    """Allowlist tool execution. No model-supplied code or arbitrary queries run."""
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
    """Answer known-missing facts directly instead of trusting optional tool use."""
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
        return f"The recorded delay reason for {shipment_id} is: {reason}. [data: data/shipments.csv]"

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
            f"The requested promise, supplier expedite, or customer contact is not supported "
            f"by the demo records or policy. " + " ".join(findings) +
            " [source: synthetic://brighthome/operations-playbook; "
            "data: data/shipments.csv, data/inventory.csv, data/orders.csv]"
        )

    return None


def answer_with_openai(question, model=MODEL):
    """Use deterministic guards, then let OpenAI plan via bounded read-only tools."""
    preflight = deterministic_preflight(question)
    if preflight:
        return preflight

    from openai import OpenAI

    client = OpenAI()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    calls_used = 0
    evidence_checked = []

    for _round in range(MAX_TOOL_CALLS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto" if calls_used < MAX_TOOL_CALLS else "none",
            temperature=0,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            answer = message.content or "I couldn't produce an evidence-backed answer."
            if evidence_checked:
                unique_sources = list(dict.fromkeys(evidence_checked))
                answer += "\n\nEvidence checked: " + "; ".join(unique_sources)
            return answer

        messages.append(message.model_dump(exclude_none=True))
        for tool_call in message.tool_calls:
            if calls_used >= MAX_TOOL_CALLS:
                result = {"error": "Tool-call limit reached; no further tools were executed."}
            else:
                calls_used += 1
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_tool(tool_call.function.name, arguments)
                    if tool_call.function.name == "check_shipment_impact":
                        evidence_checked.extend(result["data_sources"])
                        if result["allowed_next_steps"]:
                            evidence_checked.append("synthetic://brighthome/operations-playbook")
                    elif tool_call.function.name == "get_shipment_details" and result.get("found"):
                        evidence_checked.append(result["data_source"])
                    elif tool_call.function.name == "search_reference_docs":
                        evidence_checked.extend(
                            f"{p['title']} — {p['url']} ({p['chunk_id']})"
                            for p in result["passages"]
                        )
                except Exception as exc:
                    result = {"error": str(exc)}
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
    return "I reached the tool-call limit before producing a final answer. Please narrow the question."
