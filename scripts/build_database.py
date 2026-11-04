"""Seed the Firebase Firestore demo collections from synthetic CSV records."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import seed_firestore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing documents in the five demo collections before seeding.",
    )
    args = parser.parse_args()
    counts = seed_firestore(replace=args.replace)
    print("Seeded Firebase Firestore collections:")
    for collection, count in counts.items():
        print(f"  {collection}: {count} documents")


if __name__ == "__main__":
    main()
