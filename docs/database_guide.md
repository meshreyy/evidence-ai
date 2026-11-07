# Firebase Firestore setup

The app stores the synthetic demo records in Firebase Cloud Firestore. Firestore is a document database, so the five CSV seed files become collections of documents with stable IDs:

- `customers` — demo customer accounts
- `orders` — customer order lines
- `items` — SKU descriptions
- `inventory` — on-hand balances
- `shipments` — inbound shipment scenarios

Orders keep `customer_id` and `item_id` references. The app resolves those references when it prepares an order view; Firestore itself does not enforce SQL foreign keys. The calculation and allocation logic remains deterministic in Python.

## Connect a Firebase project

1. Create a Firebase project in the Firebase console and create a **Cloud Firestore** database in Native mode.
2. Create a service account with the minimum IAM permissions needed to read and write Firestore documents. Download its JSON key and store it outside this repository. Never commit or paste this key into chat.
3. Install dependencies and configure the server environment:

   ```bash
   python -m pip install -r requirements.txt
   export FIREBASE_PROJECT_ID="your-firebase-project-id"
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/supplychain-copilot/firebase-service-account.json"
   ```

4. Upload the reproducible synthetic records:

   ```bash
   python scripts/build_database.py
   ```

   The command uses stable document IDs and is safe to rerun. To delete and recreate only the five demo collections first, use `python scripts/build_database.py --replace`.
5. Start the app in the same terminal so it inherits the Firebase environment:

   ```bash
   streamlit run src/web_app.py
   ```

The Firebase Admin SDK authenticates on the server; no service-account credentials are sent to the browser. Firestore security rules do not replace server-side IAM for this Admin SDK access.

## Synthetic records and local tests

The versioned `data/*.csv` files are the reproducible source records: 12 demo accounts, 248 orders, 50 items, 50 inventory balances, and 50 shipments. Regenerate them with `python scripts/generate_synthetic_data.py`, then rerun the Firestore seed command if you want the cloud records updated. `python -m unittest discover -s tests -v` uses an in-memory Firestore-compatible test double and does not contact Firebase or require credentials.

All account and operational records are synthetic. Never use this prototype's generated records as real-company facts.

## Seed validation and replacement safety

All five seed CSVs are loaded and checked before any cloud deletion or write:
required values, document IDs, duplicate IDs, numeric conversions, valid dates,
non-negative inventory/cost, positive quantities/priorities, and item/customer
references. Invalid input leaves existing collections untouched in both modes.
Repeated seeding upserts stable IDs. `python scripts/build_database.py --replace`
is explicitly destructive and deletes only `items`, `customers`, `shipments`,
`inventory`, and `orders`. Other collections are not part of replacement.
Prevalidation is not a transaction: multi-batch cloud replacement is not atomic;
network/permission failures after validation can still leave partial data.
