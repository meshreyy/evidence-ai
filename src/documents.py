"""Ingest saved CBP pages plus the synthetic playbook; lexical retrieval baseline.

This transparent baseline is not semantic embedding search.
"""
import json
import math
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "docs" / "sources"
CORPUS_PATH = ROOT / "docs" / "corpus.jsonl"
SOURCES = [
    {
        "file": "cbp_basic_importing_exporting.html",
        "title": "CBP: Basic Importing and Exporting",
        "url": "https://www.cbp.gov/trade/basic-import-export",
    },
    {
        "file": "cbp_importer_exporter_tips.html",
        "title": "CBP: Tips for New Importers and Exporters",
        "url": "https://www.cbp.gov/trade/basic-import-export/importer-exporter-tips",
    },
]
SYNTHETIC_SOURCES = [{
    "file": "brighthome_demo_playbook.md",
    "title": "BrightHome Demo Operations Playbook (Synthetic)",
    "url": "synthetic://brighthome/operations-playbook",
}]


class ParagraphParser(HTMLParser):
    BLOCKS = {"h1", "h2", "h3", "p", "li"}

    def __init__(self):
        super().__init__()
        self.blocks = []
        self.active = False
        self.parts = []
        self.tag = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self._finish()
            self.active, self.tag = True, tag

    def handle_endtag(self, tag):
        if self.active and tag == self.tag:
            self._finish()

    def handle_data(self, data):
        if self.active:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def _finish(self):
        text = " ".join(self.parts).strip()
        if len(text) >= 45:
            self.blocks.append({"section": self.tag, "text": text})
        self.parts = []
        self.active = False
        self.tag = ""


def ingest_sources():
    """Extract HTML and synthetic playbook passages with source metadata."""
    records = []
    for source in SOURCES:
        path = SOURCE_DIR / source["file"]
        if not path.exists():
            raise FileNotFoundError(f"Missing downloaded source: {path}")
        parser = ParagraphParser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        if not parser.blocks:
            raise ValueError(f"No readable content extracted from {path.name}")
        for index, block in enumerate(parser.blocks):
            records.append({
                **source,
                "section": block["section"],
                "chunk_id": f"{source['file']}:{index + 1}",
                "text": block["text"],
            })

    for source in SYNTHETIC_SOURCES:
        path = SOURCE_DIR / source["file"]
        paragraphs = [
            " ".join(part.split())
            for part in re.split(r"\n\s*\n", path.read_text(encoding="utf-8"))
            if len(part.strip()) >= 45 and not part.lstrip().startswith("#")
        ]
        for index, text in enumerate(paragraphs):
            records.append({
                **source,
                "section": "synthetic procedure",
                "chunk_id": f"{source['file']}:{index + 1}",
                "text": text,
            })

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
    "from", "how", "i", "in", "is", "it", "of", "on", "or", "our", "the",
    "this", "to", "was", "what", "when", "which", "who", "why", "with",
}


def _tokens(text):
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOP_WORDS]


QUERY_SYNONYMS = {
    "missing": ["uncovered", "shortage", "shortfall"],
    "short": ["uncovered", "shortage", "shortfall"],
    "parts": ["units", "items"],
    "urgent": ["high", "priority", "same", "day"],
    "urgently": ["high", "priority", "same", "day"],
    "escalation": ["review", "priority"],
    "escalate": ["review", "priority"],
}


def search_documents(query, limit=3):
    """Rank source passages with BM25 and return source-aware citations.

    BM25 improves on raw term overlap by weighting rarer terms and accounting
    for passage length. It is still lexical retrieval, not semantic embeddings.
    """
    if not CORPUS_PATH.exists():
        ingest_sources()
    query_terms = _tokens(query)
    if not query_terms:
        return []
    expanded = list(query_terms)
    for term in query_terms:
        expanded.extend(QUERY_SYNONYMS.get(term, []))
    query_terms = list(dict.fromkeys(expanded))

    records = []
    with CORPUS_PATH.open(encoding="utf-8") as file:
        records = [json.loads(line) for line in file]
    tokenized = [_tokens(record["text"]) for record in records]
    if not tokenized:
        return []

    document_frequency = Counter(
        token for document in tokenized for token in set(document)
    )
    average_length = sum(map(len, tokenized)) / len(tokenized) or 1
    k1, b = 1.5, 0.75
    scored = []
    for record, document in zip(records, tokenized):
        frequencies = Counter(document)
        score = 0.0
        matched_terms = set()
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            matched_terms.add(term)
            df = document_frequency[term]
            idf = math.log(1 + (len(records) - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(document) / average_length)
            score += idf * frequency * (k1 + 1) / denominator
        # Ignore one-word accidental matches; allow a single highly distinctive term.
        if score > 0 and (len(matched_terms) >= 2 or score >= 1.5):
            scored.append((score, record))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["chunk_id"]))
    return [
        {**record, "score": round(score, 3)}
        for score, record in scored[:limit]
    ]
