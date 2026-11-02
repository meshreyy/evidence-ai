# SupplyChain Copilot architecture

```mermaid
flowchart TD
    U[Operations analyst] --> UI[Streamlit UI or CLI]
    UI --> W[Bounded assistant workflow]
    W -->|OpenAI function calling, max 4 calls| T[Read-only tool allowlist]
    T --> C[Deterministic impact calculator]
    C --> DB[(SQLite relational database\nseeded from synthetic CSV tables)]
    T --> R[BM25 document retrieval\nwith small query synonym map]
    R --> DOCS[(Saved CBP pages\nand synthetic demo playbook)]
    W --> G[Grounded answer with evidence]
    G --> U
    E[Golden eval cases] --> C
    E --> R
    E --> W
```

## Request flow

1. The analyst selects a shipment or asks a question.
2. Deterministic guards answer known missing facts (unknown shipment IDs, absent delay cause, or unsupported actions) without asking the model to guess.
3. For other questions, the OpenAI model can call only the read-only shipment-impact, shipment-lookup, and document-search tools. The tool budget is capped.
4. Python calculates order shortfalls from SQLite records. BM25 retrieves document passages and source identifiers; the model explains the returned evidence.
5. Golden evaluations check calculation results, retrieval sources, and selected answer requirements.

## Data boundaries

- SQLite is the runtime store, reproducibly seeded from versioned synthetic CSVs for shipments, inventory, orders, items, and demo accounts.
- The local synthetic playbook is the authority for demo escalation policy, not real-company policy.
- The language model is not trained or fine-tuned on the records; it reads selected facts at request time through tools. Python performs calculations.
- CBP pages provide general import guidance only. They do not establish a shipment's delay cause or business impact.
- BM25 is a lexical ranker with a small explicit synonym map; it is not embedding-based semantic search.
