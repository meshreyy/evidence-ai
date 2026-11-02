# SupplyChain Copilot (prototype)

A small decision-support demo for an operations analyst investigating a delayed
shipment. It uses synthetic shipment/inventory/order records for business facts,
a clearly labeled synthetic playbook, and saved CBP pages for general import guidance.

## Run

Requires Python 3.9+ for tests/offline mode. Install the OpenAI SDK to enable
model-based tool calling:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.evaluate
python -m src.evaluate_agent  # live OpenAI answer checks; uses API credits
python -m src.cli             # terminal interface
streamlit run src/web_app.py  # visual interface
```

Set `OPENAI_API_KEY` in your shell to enable the OpenAI agent. Never paste the
key into source code, chat, or commit it. For example, in your own terminal run
`export OPENAI_API_KEY='your-key'` (keep the value private), then launch the CLI.
Set `OPENAI_MODEL` to override the default `gpt-4o-mini`. Without a key, the CLI
runs the deterministic offline workflow. Use `SUPPLYCHAIN_OFFLINE=1` to force
offline mode.

Example question: `Shipment S-104 is delayed. Which orders are at risk?`

## Architecture

- `src/supplychain.py`: validates records and deterministically allocates stock.
- `src/documents.py`: extracts passages from saved CBP HTML pages and the
  synthetic playbook, then ranks them with BM25 plus a small explicit synonym map.
- `src/assistant.py`: bounded, read-only tool workflow; currently routes using
  a shipment-ID pattern, not an LLM planner.
- `src/cli.py`: simple interactive demo.
- `src/web_app.py`: Streamlit dashboard to select a shipment and review its impact, supported next steps, and evidence.
- `tests/` and `evals/cases.json`: calculation, validation, retrieval, workflow,
  and deterministic golden-case evaluations. Run `python -m src.evaluate` to
  see tool/retrieval results. Run `python -m src.evaluate_agent` for live answer
  checks; it calls the model, uses API credits, and saves outputs under `evals/`.

The optional OpenAI path uses function/tool calling with three read-only tools
(order impact, shipment lookup, and document search), an allowlist, and a four-call budget.
Deterministic preflight handles unknown shipment IDs and unrecorded delay causes so
answers to these cases do not depend on the model choosing a tool. Business calculations remain deterministic.
The local retrieval uses BM25 and a small explicit synonym map; it is still
lexical search, not embedding-based semantic retrieval. Do not claim
production-grade or fully semantic RAG. The model-based path requires an API key and network access.

See [`docs/architecture.md`](docs/architecture.md) for the system diagram and
[`docs/demo_script.md`](docs/demo_script.md) for a short walkthrough.
Source-selection decisions and failed fetch checks are recorded in
[`docs/sources/README.md`](docs/sources/README.md).

## Assumptions and limitations

- All company data is fictional and explicitly for demonstration.
- Orders due on the shipment arrival date are treated conservatively as at risk.
- Allocate current inventory by earliest due date, then lower numeric priority,
  then order ID. Lower priority number means higher priority.
- This prototype considers one replenishment shipment and does not model
  multiple incoming shipments, reserved stock, partial shipment arrivals, or
  supplier substitutions.
- CBP reference pages are general import guidance, not proof of a shipment's
  delay, status, or business impact. The BrightHome playbook is synthetic demo
  policy, not a real company procedure. Keep those source types distinct.
- Retrieval uses lexical BM25 with a small synonym map; it can still miss
  paraphrases. Model answers must not treat a weak match as evidence.
