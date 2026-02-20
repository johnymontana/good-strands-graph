"""Load Goodreads books and reviews into Neo4j.

Reads JSONL data files and batch-loads into Neo4j using UNWIND + MERGE.
Runs in multiple passes:
  1. Books + Publishers
  2. Authors + AUTHORED (optional; if author data files exist)
  3. Users + Reviews (WROTE_REVIEW / REVIEWS relationships)
  4. Compute embeddings on Book descriptions (Amazon Titan Embed v2)
  5. Compute SIMILAR_TO relationships via vector KNN

Usage:
    python load_data.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
EMBEDDING_MODEL_ID = os.environ.get(
    "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)

DATA_DIR = Path(__file__).parent.parent / "data"
BOOKS_FILE = DATA_DIR / "10k-books-demo.json"
REVIEWS_FILE = DATA_DIR / "10k-book-reviews-demo.json"
BOOK_AUTHORS_FILE = DATA_DIR / "10k-book-authors.json"
AUTHORS_FILE = DATA_DIR / "10k-authors-demo.json"
BATCH_SIZE = 500
EMBEDDING_BATCH_SIZE = 10
EMBEDDING_DIMENSIONS = 1024
SIMILARITY_THRESHOLD = 0.7
SIMILAR_NEIGHBORS = 6  # query k=6 to get top 5 after excluding self


def read_jsonl(path: Path):
    """Yield parsed JSON objects from a JSONL file."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_int(val) -> int | None:
    """Convert string to int, returning None for empty/invalid values."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return int(val_str)
    except (ValueError, TypeError):
        return None


def safe_float(val) -> float | None:
    """Convert string to float, returning None for empty/invalid values."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Constraints, indexes
# ---------------------------------------------------------------------------


def create_constraints_and_indexes(driver):
    """Create uniqueness constraints and indexes before loading."""
    statements = [
        "CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.bookId IS UNIQUE",
        "CREATE CONSTRAINT publisher_name IF NOT EXISTS FOR (p:Publisher) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.authorId IS UNIQUE",
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE",
        "CREATE CONSTRAINT review_id IF NOT EXISTS FOR (r:Review) REQUIRE r.reviewId IS UNIQUE",
        "CREATE INDEX book_title IF NOT EXISTS FOR (b:Book) ON (b.title)",
        "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
        "CREATE INDEX book_rating IF NOT EXISTS FOR (b:Book) ON (b.averageRating)",
        "CREATE INDEX book_isbn IF NOT EXISTS FOR (b:Book) ON (b.isbn)",
        "CREATE INDEX book_pub_year IF NOT EXISTS FOR (b:Book) ON (b.publicationYear)",
        "CREATE INDEX review_rating IF NOT EXISTS FOR (r:Review) ON (r.rating)",
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


def create_vector_index(driver):
    """Create vector index on Book embedding for semantic search."""
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            f"""CREATE VECTOR INDEX bookEmbedding IF NOT EXISTS
            FOR (b:Book) ON (b.embedding)
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                `vector.similarity_function`: 'cosine'
            }}}}"""
        )
    print(f"Created vector index 'bookEmbedding' ({EMBEDDING_DIMENSIONS} dims, cosine)")


# ---------------------------------------------------------------------------
# Pass 1: Books + Publishers
# ---------------------------------------------------------------------------


def pass1_books_publishers(driver):
    """Pass 1: Create Book nodes with Publisher relationships."""
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
        b.publicationYear = row.publication_year,
        b.publisher = row.publisher
    FOREACH (_ IN CASE WHEN row.publisher IS NOT NULL AND row.publisher <> '' THEN [1] ELSE [] END |
        MERGE (pub:Publisher {name: row.publisher})
        MERGE (b)-[:PUBLISHED_BY]->(pub)
    )
    """

    print("\n=== Pass 1: Books + Publishers ===")
    batch = []
    count = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(BOOKS_FILE):
            row = {
                "book_id": record["book_id"],
                "title": record.get("title", ""),
                "title_without_series": record.get("title_without_series", ""),
                "description": record.get("description", ""),
                "average_rating": safe_float(record.get("average_rating")),
                "ratings_count": safe_int(record.get("ratings_count")),
                "text_reviews_count": safe_int(record.get("text_reviews_count")),
                "num_pages": safe_int(record.get("num_pages")),
                "format": record.get("format", ""),
                "language_code": record.get("language_code", ""),
                "isbn": record.get("isbn", ""),
                "isbn13": record.get("isbn13", ""),
                "asin": record.get("asin", ""),
                "kindle_asin": record.get("kindle_asin", ""),
                "is_ebook": record.get("is_ebook", "") == "true",
                "image_url": record.get("image_url", ""),
                "link": record.get("link", ""),
                "publication_year": safe_int(record.get("publication_year")),
                "publisher": record.get("publisher", ""),
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


def iter_book_author_pairs(path: Path):
    """Yield (book_id, author_id) pairs from book-authors file.

    Supports JSONL with either:
      {"book_id": "x", "author_ids": ["a", "b"]}
      {"book_id": "x", "authors": [{"author_id": "a", "role": ""}]}
    """
    for record in read_jsonl(path):
        book_id = record.get("book_id")
        if not book_id:
            continue
        author_ids = record.get("author_ids")
        if author_ids is None:
            authors = record.get("authors") or []
            author_ids = [
                a.get("author_id") for a in authors if a.get("author_id")
            ]
        for aid in author_ids:
            if aid:
                yield str(book_id), str(aid)


# ---------------------------------------------------------------------------
# Pass 2a: Authors merge + AUTHORED
# ---------------------------------------------------------------------------


def pass2a_authors_and_authored(driver):
    """Merge Author nodes and create (Author)-[:AUTHORED]->(Book) from book-author links."""
    print("\n=== Pass 2a: Authors + AUTHORED ===")

    pairs = list(iter_book_author_pairs(BOOK_AUTHORS_FILE))
    if not pairs:
        print("  No book-author pairs found")
        return

    unique_author_ids = sorted({aid for _, aid in pairs})

    # Merge Author nodes (batch by unique author_id)
    merge_query = """
    UNWIND $batch AS row
    MERGE (a:Author {authorId: row.author_id})
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        for i in range(0, len(unique_author_ids), BATCH_SIZE):
            batch = [
                {"author_id": aid}
                for aid in unique_author_ids[i : i + BATCH_SIZE]
            ]
            session.execute_write(lambda tx: tx.run(merge_query, batch=batch))
    print(f"  Merged {len(unique_author_ids):,} Author nodes")

    # Create AUTHORED relationships
    authored_query = """
    UNWIND $batch AS row
    MATCH (b:Book {bookId: row.book_id})
    MATCH (a:Author {authorId: row.author_id})
    MERGE (a)-[:AUTHORED]->(b)
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        for i in range(0, len(pairs), BATCH_SIZE):
            batch = [
                {"book_id": bid, "author_id": aid}
                for bid, aid in pairs[i : i + BATCH_SIZE]
            ]
            session.execute_write(lambda tx: tx.run(authored_query, batch=batch))

    print(f"  Created AUTHORED from {len(pairs):,} book-author pairs")
    return len(unique_author_ids), len(pairs)


# ---------------------------------------------------------------------------
# Pass 2b: Hydrate Author properties
# ---------------------------------------------------------------------------


def pass2b_hydrate_authors(driver):
    """Set Author name and stats from authors JSONL."""
    if not AUTHORS_FILE.exists():
        print("\n=== Pass 2b: Hydrate Authors (skipped, no authors file) ===")
        return

    print("\n=== Pass 2b: Hydrate Authors ===")
    query = """
    UNWIND $batch AS row
    MATCH (a:Author {authorId: row.author_id})
    SET a.name = row.name,
        a.averageRating = row.average_rating,
        a.textReviewsCount = row.text_reviews_count,
        a.ratingsCount = row.ratings_count
    """
    batch = []
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(AUTHORS_FILE):
            author_id = record.get("author_id")
            if not author_id:
                continue
            name = record.get("name") or ""
            ar = record.get("average_rating")
            trc = record.get("text_reviews_count")
            rc = record.get("ratings_count")
            batch.append({
                "author_id": str(author_id),
                "name": name,
                "average_rating": safe_float(ar),
                "text_reviews_count": safe_int(trc),
                "ratings_count": safe_int(rc),
            })
            count += 1
            if len(batch) >= BATCH_SIZE:
                session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []
        if batch:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    print(f"  Pass 2b complete: hydrated {count:,} authors")


# ---------------------------------------------------------------------------
# Pass 3: Users + Reviews
# ---------------------------------------------------------------------------


def pass2_reviews(driver):
    """Pass 2: Create User and Review nodes with WROTE_REVIEW and REVIEWS relationships."""
    query = """
    UNWIND $batch AS row
    MERGE (u:User {userId: row.user_id})
    CREATE (r:Review {reviewId: row.review_id})
    SET r.rating = row.rating,
        r.text = row.text,
        r.dateAdded = row.date_added,
        r.dateUpdated = row.date_updated,
        r.readAt = row.read_at,
        r.startedAt = row.started_at,
        r.nVotes = row.n_votes,
        r.nComments = row.n_comments
    CREATE (u)-[:WROTE_REVIEW]->(r)
    WITH r, row
    MATCH (b:Book {bookId: row.book_id})
    CREATE (r)-[:REVIEWS]->(b)
    """

    print("\n=== Pass 2: Users + Reviews ===")
    batch = []
    count = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for record in read_jsonl(REVIEWS_FILE):
            row = {
                "review_id": record["review_id"],
                "book_id": record["book_id"],
                "user_id": record["user_id"],
                "rating": record.get("rating", 0),
                "text": record.get("text", ""),
                "date_added": record.get("date_added"),
                "date_updated": record.get("date_updated"),
                "read_at": record.get("read_at"),
                "started_at": record.get("started_at"),
                "n_votes": record.get("n_votes", 0),
                "n_comments": record.get("n_comments", 0),
            }
            batch.append(row)
            count += 1

            if len(batch) >= BATCH_SIZE:
                session.execute_write(lambda tx: tx.run(query, batch=batch))
                batch = []

            if count % 10000 == 0:
                print(f"  Processed {count:,} reviews...")

        if batch:
            session.execute_write(lambda tx: tx.run(query, batch=batch))

    print(f"  Pass 2 complete: {count:,} reviews loaded")
    return count


# ---------------------------------------------------------------------------
# Pass 3: Compute embeddings
# ---------------------------------------------------------------------------


def compute_embedding(bedrock_client, text: str) -> list[float]:
    """Compute a text embedding using Amazon Titan Embed Text v2."""
    # Titan v2 max input is ~8192 tokens; truncate long texts
    truncated = text[:8000]
    response = bedrock_client.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({
            "inputText": truncated,
            "dimensions": EMBEDDING_DIMENSIONS,
        }),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def pass3_embeddings(driver):
    """Pass 3: Compute and store embeddings for books with descriptions.

    Only books with b.embedding IS NULL are considered, so existing embeddings
    (e.g. restored via load-embeddings) are never overwritten.
    """
    print("\n=== Pass 3: Computing embeddings ===")

    bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    # Get all books with descriptions that don't have embeddings yet
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (b:Book)
            WHERE b.description IS NOT NULL
              AND b.description <> ''
              AND b.embedding IS NULL
            RETURN b.bookId AS bookId, b.description AS description
            """
        )
        books = [dict(r) for r in result]

    total = len(books)
    print(f"  Found {total:,} books needing embeddings")

    if total == 0:
        print("  No embeddings to compute")
        return

    count = 0
    errors = 0

    for i in range(0, total, EMBEDDING_BATCH_SIZE):
        batch = books[i : i + EMBEDDING_BATCH_SIZE]

        for book in batch:
            try:
                embedding = compute_embedding(bedrock, book["description"])
                with driver.session(database=NEO4J_DATABASE) as session:
                    session.execute_write(
                        lambda tx: tx.run(
                            "MATCH (b:Book {bookId: $bookId}) SET b.embedding = $embedding",
                            bookId=book["bookId"],
                            embedding=embedding,
                        )
                    )
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  Error embedding book {book['bookId']}: {e}")

        if count % 100 == 0 and count > 0:
            print(f"  Embedded {count:,}/{total:,} books ({errors} errors)...")

        # Small delay to respect rate limits
        time.sleep(0.1)

    print(f"  Pass 3 complete: {count:,} embeddings computed ({errors} errors)")


# ---------------------------------------------------------------------------
# Pass 4: SIMILAR_TO from vector KNN
# ---------------------------------------------------------------------------


def pass4_similar_books(driver):
    """Pass 4: Compute SIMILAR_TO relationships via vector index KNN."""
    print("\n=== Pass 4: Computing SIMILAR_TO relationships ===")

    # Get all books with embeddings
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (b:Book)
            WHERE b.embedding IS NOT NULL
            RETURN b.bookId AS bookId
            """
        )
        book_ids = [r["bookId"] for r in result]

    total = len(book_ids)
    print(f"  Found {total:,} books with embeddings")

    if total == 0:
        print("  No SIMILAR_TO relationships to compute")
        return

    count = 0
    rels_created = 0

    for book_id in book_ids:
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    """
                    MATCH (b:Book {bookId: $bookId})
                    WHERE b.embedding IS NOT NULL
                    CALL db.index.vector.queryNodes('bookEmbedding', $k, b.embedding)
                    YIELD node AS similar, score
                    WHERE similar.bookId <> b.bookId AND score >= $threshold
                    MERGE (b)-[r:SIMILAR_TO]->(similar)
                    SET r.score = score
                    RETURN count(r) AS created
                    """,
                    bookId=book_id,
                    k=SIMILAR_NEIGHBORS,
                    threshold=SIMILARITY_THRESHOLD,
                ).single()
            )
            if result:
                rels_created += result["created"]

        count += 1
        if count % 500 == 0:
            print(f"  Processed {count:,}/{total:,} books...")

    print(f"  Pass 4 complete: {rels_created:,} SIMILAR_TO relationships created")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def print_stats(driver):
    """Print summary statistics after loading."""
    queries = [
        ("Books", "MATCH (b:Book) RETURN count(b) AS count"),
        ("Publishers", "MATCH (p:Publisher) RETURN count(p) AS count"),
        ("Authors", "MATCH (a:Author) RETURN count(a) AS count"),
        ("Users", "MATCH (u:User) RETURN count(u) AS count"),
        ("Reviews", "MATCH (r:Review) RETURN count(r) AS count"),
        ("PUBLISHED_BY", "MATCH ()-[r:PUBLISHED_BY]->() RETURN count(r) AS count"),
        ("AUTHORED", "MATCH ()-[r:AUTHORED]->() RETURN count(r) AS count"),
        ("WROTE_REVIEW", "MATCH ()-[r:WROTE_REVIEW]->() RETURN count(r) AS count"),
        ("REVIEWS", "MATCH ()-[r:REVIEWS]->() RETURN count(r) AS count"),
        ("SIMILAR_TO", "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS count"),
        (
            "Books with embeddings",
            "MATCH (b:Book) WHERE b.embedding IS NOT NULL RETURN count(b) AS count",
        ),
    ]

    print("\n=== Graph Statistics ===")
    with driver.session(database=NEO4J_DATABASE) as session:
        for label, query in queries:
            result = session.run(query).single()
            print(f"  {label}: {result['count']:,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not BOOKS_FILE.exists():
        print(f"Error: Books file not found at {BOOKS_FILE}")
        sys.exit(1)
    if not REVIEWS_FILE.exists():
        print(f"Error: Reviews file not found at {REVIEWS_FILE}")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully")

        start = time.time()

        create_constraints_and_indexes(driver)
        pass1_books_publishers(driver)
        if BOOK_AUTHORS_FILE.exists():
            pass2a_authors_and_authored(driver)
            pass2b_hydrate_authors(driver)
        else:
            print("\nAuthor data not found, skipping Author/AUTHORED (optional)")
        pass2_reviews(driver)
        create_fulltext_index(driver)
        create_vector_index(driver)
        pass3_embeddings(driver)
        pass4_similar_books(driver)
        print_stats(driver)

        elapsed = time.time() - start
        print(f"\nTotal time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
