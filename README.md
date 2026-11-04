# SupplyChain Copilot (prototype)

A working decision-support prototype for an operations analyst investigating delayed
inbound supply. It runs on a relational SQLite database seeded from a reproducible,
clearly labeled synthetic dataset: 50 shipments, 50 SKUs, 50 inventory balances,
248 customer order lines, and 12 demo accounts. No private or real-company data is used.

## Run

Requires Python 3.9+. Install the OpenAI SDK to enable the optional AI decision brief:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/generate_synthetic_data.py  # optional: regenerate labeled CSV seed records
python scripts/build_database.py          # rebuild the relational SQLite store
sqlite3 data/supplychain.sqlite3 < data/inspect.sql  # inspect counts and S-104 allocation in SQL
python -m unittest discover -s tests -v
python -m src.evaluate
python -m src.evaluate_agent  # live OpenAI answer checks; uses API credits
python -m src.cli             # terminal interface
streamlit run src/web_app.py  # visual interface
```

Set `OPENAI_API_KEY` in the server environment or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your own key. Never paste the key into source code, chat, or commit the real secrets file. The model only receives the selected shipment's deterministic result and relevant policy excerpt; it has no database tools and does not calculate or choose actions. Without a key, the overview and deterministic analysis still work, while the AI panel shows the verified context and explains how to enable model-generated commentary. Set `OPENAI_MODEL` to override `gpt-4o-mini`.

Example question: `Shipment S-104 is delayed. Which orders are at risk?`

## Architecture

- `data/schema.sql`: inspectable SQL schema; `data/inspect.sql`: runnable SQL count/join/allocation examples.
- `src/database.py`: creates a relational SQLite database with foreign keys and indexes from the versioned CSV seed tables.
- `src/supplychain.py`: validates database records and deterministically allocates stock.
- `src/documents.py`: extracts passages from saved CBP HTML pages and the
  synthetic playbook, then ranks them with BM25 plus a small explicit synonym map.
- `src/assistant.py`: bounded, read-only tool workflow; currently routes using
  a shipment-ID pattern, not an LLM planner.
- `src/cli.py`: simple interactive demo.
- `src/web_app.py` + `src/pages/`: dark-themed, three-page Streamlit workspace. Overview has portfolio-level risk metrics, an exposure chart, and shipment register; Shipment analysis drills into order-level evidence and analyst next steps; Data explorer provides read-only access to the synthetic SQLite tables.
- `tests/` and `evals/cases.json`: calculation, validation, retrieval, workflow,
  and deterministic golden-case evaluations. Run `python -m src.evaluate` to
  see tool/retrieval results. Run `python -m src.evaluate_agent` for live answer
  checks; it calls the model, uses API credits, and saves outputs under `evals/`.

The AI decision brief is an explanation layer: deterministic Python computes the result, then the model receives only that result and a relevant policy passage to summarize it. The model cannot call tools, query the database, change figures, or execute actions. Unknown shipments and missing delay causes are handled deterministically. The separate document retrieval uses BM25 and a small synonym map; it is lexical search, not embedding-based semantic retrieval. The AI brief requires an API key and network access.

See [`docs/architecture.md`](docs/architecture.md) for the system diagram,
[`docs/database_guide.md`](docs/database_guide.md) to inspect the SQL database,
and [`docs/demo_script.md`](docs/demo_script.md) for a short walkthrough.
Source-selection decisions and failed fetch checks are recorded in
[`docs/sources/README.md`](docs/sources/README.md).

## Assumptions and limitations

- All shipment, inventory, customer, product, and order records are synthetic scenario data; they do not describe an actual company.
- The 50-shipment database is large enough to exercise multiple scenarios in this portfolio prototype, but it is not historical or enterprise-operational data.
- Orders due on the shipment arrival date are treated conservatively as at risk.
- Allocate current inventory by earliest due date, then lower numeric priority,
  then order ID. Lower priority number means higher priority.
- Each demo SKU has one inbound shipment. The prototype analyzes one selected shipment at a time and does not aggregate multiple incoming shipments, reserved stock, partial shipment arrivals, or supplier substitutions.
- CBP reference pages are general import guidance, not proof of a shipment's
  delay, status, or business impact. The BrightHome playbook is synthetic demo
  policy, not a real company procedure. Keep those source types distinct.
- The language model is not trained or fine-tuned on the database. It receives the selected precomputed result only to explain it; deterministic Python code does the arithmetic and chooses permitted next steps. The separate document retrieval uses lexical BM25 with a small synonym map and can still miss paraphrases.
