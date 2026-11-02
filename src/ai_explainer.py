"""LLM explanation layer: explain precomputed evidence without doing analysis."""
import json

SYSTEM_PROMPT = """You are the explanation layer for a supply-chain decision-support prototype.
All business facts, shortage quantities, priorities, and permitted next steps are already
calculated by deterministic application code. Do not recalculate, revise, or contradict them.
Use only the supplied JSON context. Do not infer a delay cause or invent actions. If no orders
are exposed, explain that clearly. The company, records, and playbook are synthetic scenario
data, not real company evidence. Never claim the language model was trained on these records.

Return only a JSON object with these string/list fields:
- headline: concise, decision-oriented, max 10 words
- summary: one or two short sentences explaining the result
- risk_factors: list of at most 3 short, directly supported observations
- analyst_focus: repeat or summarize only an action present in allowed_next_steps; if there is
  no supported action, say that the records do not establish one
- limitation: one short evidence limitation from the context
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
        max_tokens=350,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty explanation.")
    brief = json.loads(content)
    required = {"headline", "summary", "risk_factors", "analyst_focus", "limitation"}
    if not required.issubset(brief):
        raise ValueError("The model response is missing required explanation fields.")
    if not isinstance(brief["risk_factors"], list):
        raise ValueError("The model returned risk factors in an unexpected format.")
    for field in required - {"risk_factors"}:
        if not isinstance(brief[field], str):
            raise ValueError(f"The model returned an invalid {field} field.")
    brief["risk_factors"] = [str(item) for item in brief["risk_factors"][:3]]
    return brief
