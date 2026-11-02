# Three-minute demo script

## 1. Set up the problem (30 seconds)

“This is a working prototype backed by a local SQLite database. Its 50 shipments, 50 SKUs, 248 order lines, inventory, and 12 demo accounts are reproducibly generated synthetic scenario data—not a real company's records—so results have known ground truth.”

## 2. Show the business logic (45 seconds)

Start on Overview: point out 50 shipment scenarios, the exposure-by-shipment chart, the most exposed orders, and the shipment register. Open Shipment analysis, select `S-104` (CTRL-01), and show O-202 is short 15 units before the November 20 arrival. The tool joins records by `item_id`, allocates stock by due date and priority, and Python does the arithmetic.

## 3. Show evidence and bounded recommendation (45 seconds)

Expand Evidence & calculation method. Point out that runtime business facts come from SQLite, while the reproducible CSV files are the seed data. Same-day analyst review comes from the synthetic playbook. CBP references are general import context, not evidence of this shipment's cause.

## 4. Show the agent and limits (30 seconds)

If API credits are available, enable the optional OpenAI explanation. Explain that the model is not fine-tuned on the records: it can retrieve selected SQLite facts through allowlisted read-only tools, with a maximum tool-call budget. It cannot change orders or contact customers.

## 5. Show evaluation (30 seconds)

Run `python -m src.evaluate` for deterministic calculation/retrieval cases and `python -m src.evaluate_agent` for answer-level checks. Mention that the answer checks are phrase-based and only a few cases exercise model-generated answers; passing is evidence of tested behavior, not a reliability guarantee.
