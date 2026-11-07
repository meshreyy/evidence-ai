# Local verification and remaining release work

Local checks: fresh Python 3.12.14, pinned direct dependencies, full offline
unittest suite, seven deterministic golden cases, mocked structured AI responses.
The existing Python 3.9.6 environment also passed the initial expanded suite.
A local Streamlit server used the seeded fake only. Desktop and 390px-wide
checks covered totals, navigation, sources, S-104/S-105/S-106; mobile data tables
scroll horizontally. No cloud seed/replacement or paid generation was performed.

Before calling the public release complete:

- Deploy the reviewed changes and verify Render has live generation disabled and
  no public OpenAI key. Then repeat desktop/phone checks on the deployed app.
- Run private paid checks for S-104, S-106, S-105 and record a real response;
  link the labeled recording near the README top. No real recording exists yet.
- Update GitHub description/topics after reauthenticating: the local `gh` login
  token was invalid, so no repository metadata was changed.

Suggested description: “Supply-chain decision support with deterministic stock
allocation, Firestore data, BM25 references, and validated AI commentary.”
Suggested topics: python, streamlit, firestore, supply-chain, decision-support,
bm25, openai, portfolio.

The repository is prepared locally only; no push, production deployment,
credential change, or live database mutation is implied by these checks.
