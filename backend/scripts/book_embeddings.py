"""Dump and load Book embedding properties by bookId.

Subcommands:
  dump  - Export (bookId, embedding) for all Books with non-null embedding to JSONL.
  load  - Read JSONL and set Book.embedding in Neo4j for each bookId.

Usage:
  python backend/scripts/book_embeddings.py dump [--file PATH]
  python backend/scripts/book_embeddings.py load [--file PATH]

Default file: data/book-embeddings.json (JSONL, one line per book).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_FILE = DATA_DIR / "book-embeddings.json"
BATCH_SIZE = 500

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


def dump(file_path: Path) -> None:
    """Query Books with non-null embedding and write JSONL."""
    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}", file=sys.stderr)
        sys.exit(1)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (n:Book)
            WHERE n.embedding IS NOT NULL
            RETURN n.bookId AS bookId, n.embedding AS embedding
            """
        )
        with open(file_path, "w", encoding="utf-8") as f:
            for record in result:
                row = {
                    "bookId": record["bookId"],
                    "embedding": record["embedding"],
                }
                f.write(json.dumps(row) + "\n")
                count += 1

    driver.close()
    print(f"Wrote {count:,} embeddings to {file_path}")


def load(file_path: Path) -> None:
    """Read JSONL and set Book.embedding in Neo4j by bookId."""
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}", file=sys.stderr)
        sys.exit(1)

    query = """
    UNWIND $batch AS row
    MATCH (b:Book {bookId: row.bookId})
    SET b.embedding = row.embedding
    """
    batch = []
    total = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            batch.append(json.loads(line))
            total += 1
            if len(batch) >= BATCH_SIZE:
                with driver.session(database=NEO4J_DATABASE) as session:
                    session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []

    if batch:
        with driver.session(database=NEO4J_DATABASE) as session:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    driver.close()
    print(f"Set embeddings for {total:,} books from {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dump or load Book embeddings (JSONL keyed by bookId)."
    )
    parser.add_argument(
        "subcommand",
        choices=["dump", "load"],
        help="dump: export to file; load: set from file",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=DEFAULT_FILE,
        help=f"Input/output file path (default: {DEFAULT_FILE})",
    )
    args = parser.parse_args()

    if args.subcommand == "dump":
        dump(args.file)
    else:
        load(args.file)


if __name__ == "__main__":
    main()
