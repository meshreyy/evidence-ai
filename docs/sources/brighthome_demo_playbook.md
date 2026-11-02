# BrightHome Demo Operations Playbook (Synthetic)

This document is fictional and was written only for the SupplyChain Copilot demo. It is not an actual company's policy.

## Shortage escalation

When an order has any uncovered quantity because a shipment arrives after its due date, flag the order for an operations analyst to review. If more than 10 units are uncovered, mark it high priority for same-day analyst review. The assistant must not promise a new delivery date or contact a customer.

## Allocation rule

For this demo, allocate available inventory to the earliest due order first. For orders with the same due date, a lower numeric priority value comes first. Use order ID as a final stable tie-break. This is a demo assumption, not a universal supply-chain practice.

## Evidence and uncertainty

Use the shipment, inventory, and order records to report quantities and dates. Treat orders due on the expected arrival date as potentially at risk because the records do not include delivery times. If a cause of delay, replacement shipment, or supplier alternative is not present in the records, state that it is unknown. Do not infer it from general industry reports.
