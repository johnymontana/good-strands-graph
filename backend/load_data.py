"""Load Goodreads mystery/thriller/crime books into Neo4j.

Reads the JSONL data file line-by-line and batch-loads into Neo4j using
UNWIND + MERGE for efficiency. Runs in 3 passes:
  1. Books + Authors + Publishers + Series
  2. SIMILAR_TO relationships
  3. Shelf nodes + ON_SHELF relationships (top 10 per book)

Usage:
    python load_data.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

DATA_FILE = Path(__file__).parent.parent / "data" / "goodreads_books_mystery_thriller_crime.json"
BATCH_SIZE = 500


def create_constraints_and_indexes(driver):
    """Create uniqueness constraints and indexes before loading."""
    statements = [
        "CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.bookId IS UNIQUE",
        "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.authorId IS UNIQUE",
        "CREATE CONSTRAINT series_id IF NOT EXISTS FOR (s:Series) REQUIRE s.seriesId IS UNIQUE",
        "CREATE CONSTRAINT shelf_name IF NOT EXISTS FOR (s:Shelf) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT publisher_name IF NOT EXISTS FOR (p:Publisher) REQUIRE p.name IS UNIQUE",
        "CREATE INDEX book_title IF NOT EXISTS FOR (b:Book) ON (b.title)",
        "CREATE INDEX book_rating IF NOT EXISTS FOR (b:Book) ON (b.averageRating)",
        "CREATE INDEX book_isbn IF NOT EXISTS FOR (b:Book) ON (b.isbn)",
    ]
    with driver.session(database=NEO4J_DATABASE) as session:
        for stmt in statements:
            session.run(stmt)
    print(f"Created {len(statements)} constraints/indexes")


def create_fulltext_index(driver):
    """Create fulltext index on Book title and description for search."""
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            "CREATE FULLTEXT INDEX bookSearch IF NOT EXISTS "
            "FOR (b:Book) ON EACH [b.title, b.description]"
        )
    print("Created fulltext index 'bookSearch'")


def read_jsonl(path: Path):
    """Yield parsed JSON objects from a JSONL file."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_int(val: str) -> int | None:
    """Convert string to int, returning None for empty/invalid values."""
    if not val or val.strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def safe_float(val: str) -> float | None:
    """Convert string to float, returning None for empty/invalid values."""
    if not val or val.strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def pass1_books_authors_publishers_series(driver):
    """Pass 1: Create Book nodes with Author, Publisher, and Series relationships."""
    query = """
    UNWIND $batch AS row
    MERGE (b:Book {bookId: row.book_id})
    SET b.title = row.title,
        b.titleWithoutSeries = row.title_without_series,
        b.description = row.description,
        b.averageRating = row.average_rating,
        b.ratingsCount = row.ratings_count,
        b.textReviewsCount = row.text_reviews_count,
        b.numPages = row.num_pages,
        b.format = row.format,
        b.languageCode = row.language_code,
        b.isbn = row.isbn,
        b.isbn13 = row.isbn13,
        b.asin = row.asin,
        b.kindleAsin = row.kindle_asin,
        b.isEbook = row.is_ebook,
        b.imageUrl = row.image_url,
        b.link = row.link,
        b.publicationYear = row.publication_year
    FOREACH (a IN row.authors |
        MERGE (author:Author {authorId: a.author_id})
        MERGE (b)-[:WRITTEN_BY]->(author)
    )
    FOREACH (_ IN CASE WHEN row.publisher <> '' THEN [1] ELSE [] END |
        MERGE (pub:Publisher {name: row.publisher})
        MERGE (b)-[:PUBLISHED_BY]->(pub)
    )
    FOREACH (s IN row.series |
        MERGE (series:Series {seriesId: s})
        MERGE (b)-[:PART_OF_SERIES]->(series)
    )
    """

    print("\n=== Pass 1: Books + Authors + Publishers + Series ===")
    batch = []
    count = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(DATA_FILE):
            row = {
                "book_id": record["book_id"],
                "title": record.get("title", ""),
                "title_without_series": record.get("title_without_series", ""),
                "description": record.get("description", ""),
                "average_rating": safe_float(record.get("average_rating", "")),
                "ratings_count": safe_int(record.get("ratings_count", "")),
                "text_reviews_count": safe_int(record.get("text_reviews_count", "")),
                "num_pages": safe_int(record.get("num_pages", "")),
                "format": record.get("format", ""),
                "language_code": record.get("language_code", ""),
                "isbn": record.get("isbn", ""),
                "isbn13": record.get("isbn13", ""),
                "asin": record.get("asin", ""),
                "kindle_asin": record.get("kindle_asin", ""),
                "is_ebook": record.get("is_ebook", "") == "true",
                "image_url": record.get("image_url", ""),
                "link": record.get("link", ""),
                "publication_year": safe_int(record.get("publication_year", "")),
                "publisher": record.get("publisher", ""),
                "authors": record.get("authors", []),
                "series": record.get("series", []),
            }
            batch.append(row)
            count += 1

            if len(batch) >= BATCH_SIZE:
                session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []

            if count % 5000 == 0:
                print(f"  Processed {count:,} books...")

        if batch:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    print(f"  Pass 1 complete: {count:,} books loaded")
    return count


def pass2_similar_books(driver):
    """Pass 2: Create SIMILAR_TO relationships between books."""
    query = """
    UNWIND $batch AS row
    MATCH (b:Book {bookId: row.book_id})
    UNWIND row.similar_books AS similar_id
    MATCH (similar:Book {bookId: similar_id})
    MERGE (b)-[:SIMILAR_TO]->(similar)
    """

    print("\n=== Pass 2: SIMILAR_TO relationships ===")
    batch = []
    count = 0
    skipped = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(DATA_FILE):
            similar = record.get("similar_books", [])
            if not similar:
                skipped += 1
                count += 1
                continue

            batch.append({
                "book_id": record["book_id"],
                "similar_books": similar,
            })
            count += 1

            if len(batch) >= BATCH_SIZE:
                session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []

            if count % 5000 == 0:
                print(f"  Processed {count:,} books ({skipped:,} with no similar books)...")

        if batch:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    print(f"  Pass 2 complete: {count:,} books processed, {skipped:,} had no similar books")


def pass3_shelves(driver):
    """Pass 3: Create Shelf nodes and ON_SHELF relationships (top 10 per book)."""
    query = """
    UNWIND $batch AS row
    MATCH (b:Book {bookId: row.book_id})
    UNWIND row.shelves AS shelf
    MERGE (s:Shelf {name: shelf.name})
    MERGE (b)-[r:ON_SHELF]->(s)
    SET r.count = shelf.count
    """

    print("\n=== Pass 3: Shelves + ON_SHELF relationships ===")
    batch = []
    count = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(DATA_FILE):
            shelves = record.get("popular_shelves", [])
            # Take top 10 shelves to avoid explosion
            top_shelves = [
                {"name": s["name"], "count": safe_int(s.get("count", "0")) or 0}
                for s in shelves[:10]
            ]

            if top_shelves:
                batch.append({
                    "book_id": record["book_id"],
                    "shelves": top_shelves,
                })

            count += 1

            if len(batch) >= BATCH_SIZE:
                session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []

            if count % 5000 == 0:
                print(f"  Processed {count:,} books...")

        if batch:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    print(f"  Pass 3 complete: {count:,} books processed")


def print_stats(driver):
    """Print summary statistics after loading."""
    queries = [
        ("Books", "MATCH (b:Book) RETURN count(b) AS count"),
        ("Authors", "MATCH (a:Author) RETURN count(a) AS count"),
        ("Series", "MATCH (s:Series) RETURN count(s) AS count"),
        ("Publishers", "MATCH (p:Publisher) RETURN count(p) AS count"),
        ("Shelves", "MATCH (s:Shelf) RETURN count(s) AS count"),
        ("WRITTEN_BY", "MATCH ()-[r:WRITTEN_BY]->() RETURN count(r) AS count"),
        ("SIMILAR_TO", "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS count"),
        ("ON_SHELF", "MATCH ()-[r:ON_SHELF]->() RETURN count(r) AS count"),
        ("PART_OF_SERIES", "MATCH ()-[r:PART_OF_SERIES]->() RETURN count(r) AS count"),
        ("PUBLISHED_BY", "MATCH ()-[r:PUBLISHED_BY]->() RETURN count(r) AS count"),
    ]

    print("\n=== Graph Statistics ===")
    with driver.session(database=NEO4J_DATABASE) as session:
        for label, query in queries:
            result = session.run(query).single()
            print(f"  {label}: {result['count']:,}")


def main():
    if not DATA_FILE.exists():
        print(f"Error: Data file not found at {DATA_FILE}")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully")

        start = time.time()

        create_constraints_and_indexes(driver)
        pass1_books_authors_publishers_series(driver)
        pass2_similar_books(driver)
        pass3_shelves(driver)
        create_fulltext_index(driver)
        print_stats(driver)

        elapsed = time.time() - start
        print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
