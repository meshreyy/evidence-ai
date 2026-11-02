import unittest

from src.documents import ingest_sources, search_documents


class DocumentRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = ingest_sources()

    def test_ingestion_extracts_useful_passages_with_source_metadata(self):
        self.assertGreater(len(self.records), 10)
        self.assertTrue(all(
            record["url"].startswith(("https://", "synthetic://"))
            for record in self.records
        ))
        self.assertTrue(all(record["text"].strip() for record in self.records))

    def test_shortage_query_retrieves_labeled_synthetic_playbook(self):
        results = search_documents("uncovered quantity high priority same day analyst review", limit=3)
        self.assertTrue(results)
        self.assertIn("Synthetic", results[0]["title"])
        self.assertTrue(results[0]["url"].startswith("synthetic://"))

    def test_paraphrased_policy_query_retrieves_playbook(self):
        results = search_documents("missing parts need urgent escalation", limit=1)
        self.assertTrue(results)
        self.assertIn("Synthetic", results[0]["title"])
        self.assertTrue(results[0]["url"].startswith("synthetic://"))

    def test_importer_query_returns_cited_cbp_passage(self):
        results = search_documents("importer customs broker merchandise", limit=3)
        self.assertTrue(results)
        self.assertIn("CBP", results[0]["title"])
        self.assertIn("cbp.gov", results[0]["url"])
        self.assertTrue(results[0]["chunk_id"])


if __name__ == "__main__":
    unittest.main()
