# Three-minute demo script

## 1. Set up the problem (30 seconds)

“This is a working prototype backed by a local SQLite database. Its 10 shipments, 10 SKUs, 48 order lines, inventory, and demo accounts are reproducibly generated synthetic scenario data—not a real company's records—so results have known ground truth.”

## 2. Show the business logic (45 seconds)

Select shipment `S-104` (CTRL-01) and review its impact. Explain that the tool joins order/inventory records by `item_id`, allocates current stock by due date and priority, and finds O-202 is short 15 units before the November 20 arrival. Python does the arithmetic; the model does not.

## 3. Show evidence and bounded recommendation (45 seconds)

Expand evidence. Point out that order impact comes from the CSV files and same-day analyst review comes from a clearly labeled synthetic playbook. CBP references are general import context, not evidence of this shipment's cause.

## 4. Show the agent and limits (30 seconds)

If API credits are available, enable the optional OpenAI explanation. Explain that the model is not fine-tuned on the records: it can retrieve selected SQLite facts through allowlisted read-only tools, with a maximum tool-call budget. It cannot change orders or contact customers.

## 5. Show evaluation (30 seconds)

Run `python -m src.evaluate` for deterministic calculation/retrieval cases and `python -m src.evaluate_agent` for answer-level checks. Mention that the answer checks are phrase-based and only a few cases exercise model-generated answers; passing is evidence of tested behavior, not a reliability guarantee.
