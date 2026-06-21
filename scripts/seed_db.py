"""scripts/seed_db.py — one-time: ingest seed regulation text files into ChromaDB.

Run before the demo:
    python scripts/seed_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SEED_DIR, SUPPORTED_REGULATORS
from rag.ingestion import Ingestion
from rag.retriever import Retriever


def main():
    ingestion = Ingestion()
    total_chunks = 0

    for regulator in SUPPORTED_REGULATORS:
        reg_dir = SEED_DIR / regulator
        if not reg_dir.exists():
            print(f"[{regulator.upper()}] No seed directory found at {reg_dir}, skipping.")
            continue

        for path in sorted(reg_dir.glob("*.txt")):
            count = ingestion.ingest_file(path, regulator)
            total_chunks += count
            print(f"[{regulator.upper()}] Ingesting {path.name} ... {count} chunks added")

    stats = Retriever().get_collection_stats()
    n_collections = len(stats)
    print(f"\u2713 ChromaDB seeded. Total: {total_chunks} chunks across {n_collections} collections.")
    print(f"  Per-regulator counts: {stats}")


if __name__ == "__main__":
    main()
