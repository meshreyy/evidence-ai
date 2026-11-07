# Local verification and remaining release work

Local checks: fresh Python 3.12.14, pinned direct dependencies, full offline
unittest suite (46 passing tests), seven deterministic golden cases (7/7), and
mocked structured AI responses. Rechecked on November 7, 2026.
The existing Python 3.9.6 environment also passed the initial expanded suite.
A local Streamlit server used the seeded fake only. Desktop and 390px-wide
checks covered totals, navigation, sources, S-104/S-105/S-106; mobile data tables
scroll horizontally. No cloud seed/replacement or paid generation was performed.

## Review report audit

All listed application fixes are implemented and covered by offline regressions:

| Report finding | Verified behavior |
| --- | --- |
| Relative UI test paths | All three original AppTest entry points resolve from `Path(__file__)`; the suite also passed from outside the repository. |
| Stale AI explanations | Shipment, impact, and policy snapshots invalidate saved commentary when inputs change. |
| Empty Firestore | Both app startup and direct analysis entry show the seed command before rendering a selector. |
| Keyword-only AI grading | Generated structured order IDs, shortages, action IDs, delay cause and delivery promise are checked against ground truth; negative quantity/cause/promise fixtures fail. Free-text checks remain limited. |
| Destructive seed replacement | All five seed files are validated before writes or deletes; malformed files leave the fake database untouched, with and without replacement. |
| Inconsistent priority banner | The banner uses deterministic per-order action IDs; 6+6 does not escalate, 10 does not, 11 does. |
| Misleading S-106 summary | Shipment total is 53 across three orders; O-209 is separately shown as short 13. |
| Hidden S-104 allocation | The allocation table includes O-201 consuming 20 units and O-202 receiving the remaining 10. |
| Disconnected overview | Open shipment analysis transfers the selected shipment through session state. |

A README screenshot, animated offline walkthrough, credential-free demo launcher,
and minimal offline CI workflow are included. The walkthrough holds five actual
app screenshots; it is not a real AI generation recording. The stack and scope
remain Streamlit, Firestore, BM25, and deterministic Python calculations.

## Remaining public release checks

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

The application fixes were pushed to `main` in commit `2e3473b`. This audit and
walkthrough are a follow-up documentation change. Production deployment state,
credential changes, and live database contents have not been verified by these
local checks.
