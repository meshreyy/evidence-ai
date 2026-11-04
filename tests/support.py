"""Small Firestore-compatible fake used by offline unit and UI tests."""
import csv

from src.database import DATA_DIR, SEED_FILES, _convert_csv_row, set_firestore_client_for_testing


class FakeDocument:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.id = document_id
        self.reference = self

    def to_dict(self):
        return dict(self.collection.documents[self.id])


class FakeCollection:
    def __init__(self, name, documents=None):
        self.name = name
        self.documents = documents if documents is not None else {}

    def document(self, document_id):
        return FakeDocument(self, document_id)

    def stream(self):
        return [FakeDocument(self, document_id) for document_id in sorted(self.documents)]


class FakeBatch:
    def __init__(self):
        self.operations = []

    def set(self, reference, value):
        self.operations.append(("set", reference, dict(value)))

    def delete(self, reference):
        self.operations.append(("delete", reference, None))

    def commit(self):
        for operation, reference, value in self.operations:
            if operation == "set":
                reference.collection.documents[reference.id] = value
            else:
                reference.collection.documents.pop(reference.id, None)
        self.operations.clear()


class FakeFirestore:
    def __init__(self, collections=None):
        self.collections = collections or {}

    def collection(self, name):
        return self.collections.setdefault(name, FakeCollection(name))

    def batch(self):
        return FakeBatch()


def seeded_fake_firestore():
    client = FakeFirestore()
    for collection_name, (filename, id_field) in SEED_FILES.items():
        with (DATA_DIR / filename).open(newline="", encoding="utf-8") as source:
            rows = [_convert_csv_row(row) for row in csv.DictReader(source)]
        collection = client.collection(collection_name)
        collection.documents.update({row[id_field]: row for row in rows})
    return client


set_firestore_client_for_testing(seeded_fake_firestore())
