"""Build/rebuild the SQLite database and print the synthetic dataset size."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import database_counts, initialize_database


if __name__ == "__main__":
    path = initialize_database(force=True)
    counts = database_counts()
    print(f"SQLite database: {path}")
    print("Record counts: " + ", ".join(f"{table}={count}" for table, count in counts.items()))
