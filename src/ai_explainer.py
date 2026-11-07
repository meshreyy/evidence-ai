"""LLM explanation layer: explain precomputed evidence without doing analysis."""
import json
import re

SYSTEM_PROMPT = """You are the explanation layer for a supply-chain decision-support prototype.
All business facts, shortage quantities, priorities, and permitted next steps are already
calculated by deterministic application code. Do not recalculate, revise, or contradict them.
Use only the supplied JSON context. Do not infer a delay cause or invent actions. If no orders
are exposed, explain that clearly. The company, records, and playbook are synthetic scenario
data, not real company evidence. Never claim the language model was trained on these records.

Return a JSON object with these required structured fields:
- orders: copy every precomputed at-risk order as {"order_id": string, "qty_uncovered": integer}
- actions: copy every allowed next step as {"order_id": string, "action_id": string}
- delay_cause: copy shipment.delay_cause exactly
- delivery_promise: null (there is no supported delivery promise)
Also include these string fields:
- headline: concise, decision-oriented, max 8 words
- summary: one sentence, max 28 words, explaining the result and its timing
- analyst_focus: max 16 words; repeat only an action present in allowed_next_steps; if there is
  no supported action, say that the records do not establish one
- limitation: max 12 words, stating the most important evidence limitation
"""


def explain_impact_with_openai(shipment, impact, policy_text, model="gpt-4o-mini", api_key=None):
    """Generate a grounded explanation of already-computed shipment results.

    This function gives the model no tools and no database access. Deterministic
    code remains the source of quantities and operational recommendations.
    """
    from openai import OpenAI

    context = {
        "shipment": {
            "shipment_id": shipment["shipment_id"],
            "item_id": shipment["item_id"],
            "item_name": shipment.get("item_name"),
            "expected_arrival_date": shipment["expected_arrival_date"],
            "delay_cause": shipment.get("delay_reason") or "not recorded",
            "status": shipment.get("status"),
        },
        "precomputed_at_risk_orders": impact["at_risk_orders"],
        "allowed_next_steps": impact["allowed_next_steps"],
        "policy_excerpt": policy_text,
        "calculation_note": impact["note"],
        "provenance": impact["data_sources"],
    }
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=900,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty explanation.")
    brief = json.loads(content)
    validate_brief(brief, shipment, impact)
    return brief


def verified_fields(shipment, impact):
    """The exact facts and permitted action identifiers a response must preserve."""
    return {
        "orders": [{"order_id": row["order_id"], "qty_uncovered": row["qty_uncovered"]}
                   for row in impact["at_risk_orders"]],
        "actions": [{"order_id": row["order_id"], "action_id": row["action_id"]}
                    for row in impact["allowed_next_steps"]],
        "delay_cause": shipment.get("delay_reason") or "not recorded",
        "delivery_promise": None,
    }


def validate_brief(brief, shipment, impact):
    """Check structured facts exactly; apply conservative, limited prose checks."""
    required = {"headline", "summary", "analyst_focus", "limitation"}
    facts = verified_fields(shipment, impact)
    if not isinstance(brief, dict) or not (required | facts.keys()).issubset(brief):
        raise ValueError("The model response is missing required explanation fields.")
    for field in required:
        if not isinstance(brief[field], str) or not brief[field].strip():
            raise ValueError(f"The model returned an invalid {field} field.")
    # JSON equality alone would allow True == 1 or 15.0 == 15.
    if json.dumps({k: brief[k] for k in facts}, sort_keys=True) != json.dumps(facts, sort_keys=True):
        raise ValueError("The model response contradicts verified facts or permitted actions.")
    text = " ".join(brief[k] for k in required)
    expected_ids = {row["order_id"] for row in impact["at_risk_orders"]}
    if set(re.findall(r"\bO-\d+\b", text)) - expected_ids:
        raise ValueError("AI commentary contains an unsupported order ID.")
    quantities = {row["qty_uncovered"] for row in impact["at_risk_orders"]}
    quantities.add(sum(row["qty_uncovered"] for row in impact["at_risk_orders"]))
    for value in re.findall(r"\b(\d+)\s+units?\b", text, re.I):
        if int(value) not in quantities:
            raise ValueError("AI commentary contains a contradictory quantity.")
    if re.search(r"\b(zero|no)\s+(shortage|shortfall|exposure|uncovered|orders? (?:are )?at risk)", text, re.I) and impact["at_risk_orders"]:
        raise ValueError("AI commentary contradicts the recorded shortage.")
    # Reject action/cause claims, including ambiguous language, rather than guessing intent.
    if re.search(r"\b(promise[sd]?|guarantee[sd]?|expedit\w*|contact(?:ing)?|reallocat\w*)\b", text, re.I):
        raise ValueError("AI commentary mentions an unsupported operational action.")
    if not shipment.get("delay_reason") and re.search(
        r"\b(customs|weather|congestion|supplier|port|because|caused by|due to)\b", text, re.I
    ):
        raise ValueError("AI commentary suggests an unrecorded delay cause.")
    return brief
