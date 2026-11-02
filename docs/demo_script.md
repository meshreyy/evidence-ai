# Three-minute demo script

## 1. Set up the problem (30 seconds)

“BrightHome is fictional. Its operations analyst has a delayed controller shipment and needs to know which customer orders are exposed. The data is synthetic so we can test exact expected results.”

## 2. Show the business logic (45 seconds)

Select shipment `S-104` and analyze it. Explain that the tool joins records using `item_id`, allocates current stock by due date and priority, and finds O-202 is short 15 units. The model does not do the arithmetic.

## 3. Show evidence and bounded recommendation (45 seconds)

Expand evidence. Point out that order impact comes from the CSV files and same-day analyst review comes from a clearly labeled synthetic playbook. CBP references are general import context, not evidence of this shipment's cause.

## 4. Show the agent and limits (30 seconds)

If API credits are available, enable the optional OpenAI explanation. Explain that it can call only allowlisted read-only tools, with a maximum tool-call budget. It cannot change orders or contact customers.

## 5. Show evaluation (30 seconds)

Run `python -m src.evaluate` for deterministic calculation/retrieval cases and `python -m src.evaluate_agent` for answer-level checks. Mention that the answer checks are phrase-based and only a few cases exercise model-generated answers; passing is evidence of tested behavior, not a reliability guarantee.
