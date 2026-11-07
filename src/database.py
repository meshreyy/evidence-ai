"""Firebase Firestore access and reproducible synthetic-data seeding."""
import csv
import os
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEED_FILES = {
    "items": ("items.csv", "item_id"),
    "customers": ("customers.csv", "customer_id"),
    "shipments": ("shipments.csv", "shipment_id"),
    "inventory": ("inventory.csv", "item_id"),
    "orders": ("orders.csv", "order_id"),
}
INTEGER_FIELDS = {"qty", "available_qty", "qty_needed", "priority"}
FLOAT_FIELDS = {"unit_cost_usd"}
_firestore_client = None


class FirebaseConfigurationError(RuntimeError):
    """Raised when Firestore credentials or its SDK are not configured."""


def set_firestore_client_for_testing(client):
    """Inject a Firestore-compatible client in unit tests."""
    global _firestore_client
    _firestore_client = client


def get_firestore_client():
    """Return the Firebase Admin Firestore client using server-side credentials."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not project_id:
        raise FirebaseConfigurationError(
            "Set FIREBASE_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS to connect to Firebase. "
            "Keep the service-account JSON outside the repository."
        )
    if credentials_path and not Path(credentials_path).is_file():
        raise FirebaseConfigurationError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to your local Firebase service-account JSON file."
        )
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        try:
            app = firebase_admin.get_app()
        except ValueError:
            credential = (
                credentials.Certificate(credentials_path)
                if credentials_path
                else credentials.ApplicationDefault()
            )
            app = firebase_admin.initialize_app(credential, {"projectId": project_id})
        _firestore_client = firestore.client(app=app)
        return _firestore_client
    except ImportError as exc:
        raise FirebaseConfigurationError(
            "Firebase Admin SDK is missing. Install project dependencies with `pip install -r requirements.txt`."
        ) from exc
    except Exception as exc:
        raise FirebaseConfigurationError(
            f"Could not connect to Firebase project {project_id!r}: {type(exc).__name__}. "
            "Check the project ID, service-account permissions, and network connection."
        ) from exc


def _convert_csv_row(row):
    converted = dict(row)
    for key in INTEGER_FIELDS & converted.keys():
        converted[key] = int(converted[key])
    for key in FLOAT_FIELDS & converted.keys():
        converted[key] = float(converted[key])
    return converted


def load_validated_seed():
    """Read the entire seed and reject invalid data before any cloud mutation."""
    from src.supplychain import validate_records

    fields = {
        "items": {"item_id", "item_name", "category", "unit_cost_usd"},
        "customers": {"customer_id", "customer_name", "segment", "region"},
        "shipments": {"shipment_id", "item_id", "qty", "expected_arrival_date", "status", "as_of_date"},
        "inventory": {"item_id", "available_qty", "as_of_date"},
        "orders": {"order_id", "item_id", "customer_id", "qty_needed", "due_date", "priority", "order_status"},
    }
    tables = {}
    for name, (filename, id_field) in SEED_FILES.items():
        with (DATA_DIR / filename).open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if not fields[name].issubset(reader.fieldnames or []):
                raise ValueError(f"Missing required fields in {filename}")
            rows = []
            for raw in reader:
                if None in raw or any(not isinstance(raw.get(k), str) or not raw[k].strip() for k in fields[name]):
                    raise ValueError(f"Missing required values in {filename}")
                row = _convert_csv_row({k: v.strip() if isinstance(v, str) else v for k, v in raw.items()})
                if "/" in row[id_field]:
                    raise ValueError(f"Invalid document ID in {filename}")
                for key in ("as_of_date", "due_date", "expected_arrival_date"):
                    if key in row:
                        date.fromisoformat(row[key])
                rows.append(row)
        if not rows:
            raise ValueError(f"Synthetic seed file is empty: {filename}")
        ids = [row[id_field] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {filename}")
        tables[name] = rows
    validate_records(tables["shipments"], tables["inventory"], tables["orders"])
    for row in tables["items"]:
        if not math.isfinite(row["unit_cost_usd"]) or row["unit_cost_usd"] < 0:
            raise ValueError("Item cost must be finite and non-negative")
    item_ids = {row["item_id"] for row in tables["items"]}
    customer_ids = {row["customer_id"] for row in tables["customers"]}
    for table in ("shipments", "inventory", "orders"):
        if any(row["item_id"] not in item_ids for row in tables[table]):
            raise ValueError(f"Unknown item reference in {table}")
    if any(row["customer_id"] not in customer_ids for row in tables["orders"]):
        raise ValueError("Unknown customer reference in orders")
    return tables


def seed_firestore(client=None, replace=False):
    """Upload versioned CSV seed records to Firestore using stable document IDs.

    Re-running without --replace is idempotent: records with the same IDs are
    updated, while other records are left untouched. --replace deletes the
    five demo collections first and should only be used for this demo project.
    """
    tables = load_validated_seed()
    client = client or get_firestore_client()
    if replace:
        for collection_name in SEED_FILES:
            docs = list(client.collection(collection_name).stream())
            for start in range(0, len(docs), 400):
                batch = client.batch()
                for doc in docs[start:start + 400]:
                    batch.delete(doc.reference)
                batch.commit()

    for collection_name, (filename, id_field) in SEED_FILES.items():
        rows = tables[collection_name]
        for start in range(0, len(rows), 400):
            batch = client.batch()
            for row in rows[start:start + 400]:
                batch.set(
                    client.collection(collection_name).document(row[id_field]),
                    row,
                )
            batch.commit()
    return database_counts(client)


def _collection_rows(client, name):
    return [doc.to_dict() for doc in client.collection(name).stream()]


def read_table(table, client=None):
    """Read a Firestore collection and enrich order rows with related labels."""
    if table not in SEED_FILES:
        raise ValueError(f"Unknown Firestore collection: {table}")
    client = client or get_firestore_client()
    rows = _collection_rows(client, table)
    if table == "items" or table == "customers":
        rows.sort(key=lambda row: row[SEED_FILES[table][1]])
        return rows

    items = {row["item_id"]: row for row in _collection_rows(client, "items")}
    if table == "shipments" or table == "inventory":
        for row in rows:
            item = items.get(row.get("item_id"), {})
            row["item_name"] = item.get("item_name", row.get("item_id", ""))
        rows.sort(key=lambda row: row[SEED_FILES[table][1]])
        return rows

    customers = {row["customer_id"]: row for row in _collection_rows(client, "customers")}
    for row in rows:
        item = items.get(row.get("item_id"), {})
        customer = customers.get(row.get("customer_id"), {})
        row["item_name"] = item.get("item_name", row.get("item_id", ""))
        row["customer_name"] = customer.get("customer_name", row.get("customer_id", ""))
        row["customer_segment"] = customer.get("segment", "")
        row["customer_region"] = customer.get("region", "")
    rows.sort(key=lambda row: row["order_id"])
    return rows


def database_counts(client=None):
    """Return record counts for each seeded Firestore collection."""
    client = client or get_firestore_client()
    counts = {}
    try:
        for collection_name in SEED_FILES:
            collection = client.collection(collection_name)
            try:
                counts[collection_name] = int(collection.count().get()[0][0].value)
            except (AttributeError, IndexError, TypeError):
                counts[collection_name] = len(list(collection.stream()))
    except Exception as exc:
        raise FirebaseConfigurationError(
            "Could not read Firestore collections. Confirm Cloud Firestore is enabled, "
            "the demo collections are seeded, and the service account has Firestore access."
        ) from exc
    return counts
