# Three-minute walkthrough

[Watch the animated offline walkthrough](images/offline-walkthrough.gif). This
26-second GIF holds six screenshots captured from real local app interactions;
it has no audio and does not demonstrate a generated AI response.

1. **0:00–0:30** Open the live demo or run `python scripts/run_offline_demo.py`.
   Explain: 50 synthetic shipments, 50 SKUs, 248 order lines, 12 demo accounts.
   The offline launcher uses an ephemeral fake; the deployed app uses Firestore.
2. **0:30–1:15** On Overview, choose S-104 and click Open shipment analysis.
   Show the allocation table: O-201 consumes 20 of 30 units, leaving 10 for O-202.
   O-202 is short 15 before November 20; Python chooses same-day analyst review.
3. **1:15–1:45** Select S-105: no exposed orders. Select S-106: 53 units across
   three orders, with O-209 short 13. Explain why totals and order quantities differ.
4. **1:45–2:15** Expand Sources & calculation. The playbook is synthetic policy;
   CBP pages give general guidance and do not explain an individual delay cause.
   A fabricated customs delay or delivery promise must not be treated as evidence.
5. **2:15–3:00** Run the offline suite and `python -m src.evaluate --offline`.
   Structured AI facts/actions are validated; prose checks still have limits.
   AI commentary does not own the calculations or execute actions.

## Public AI and real recording checklist

Leave the public OpenAI key unset and `ENABLE_LIVE_AI=false`. Anonymous visitors
cannot trigger paid UI generation in this mode. There is no shared public request
budget, so do not enable public live generation. Confirm the actual deployment
settings before release. For private use, set `ENABLE_LIVE_AI=true` and a server key.

A real AI recording remains a release task: privately generate S-104 (single order),
S-106 (multiple orders), and S-105 (no shortage); inspect both commentary and facts,
then record a short clip labeled “Real AI commentary — private run” with date/model.
Do not label an offline walkthrough or mocked response as a real AI run. No paid
calls, cloud changes, or credential reads are needed for the offline checks.

## Shortlist variation

The default selector contains only S-104, S-105, S-150, S-106, and S-108.
Use S-150 for a small eight-unit shortage with standard review, and S-108 for
zero inventory and three exposed orders (58 units). S-104 is selected first.
Labels and overview metrics follow the selected records; Show full dataset
restores the original 50-shipment portfolio without changing any records.
