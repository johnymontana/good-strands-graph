"""Book recommendation and commerce agent powered by AWS Strands and Neo4j."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from typing import Any

import boto3
from neo4j import GraphDatabase
from neo4j_agent_memory.integrations.strands import StrandsConfig, context_graph_tools
from strands import Agent, tool
from strands.models import BedrockModel
from strands.types.tools import ToolContext

from ..config import get_settings
from .prompts import BOOK_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Neo4j driver singleton for tool queries
_driver = None

# Bedrock client singleton for embeddings
_bedrock_client = None


def _get_driver():
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        settings = get_settings()
        _bedrock_client = boto3.client(
            "bedrock-runtime", region_name=settings.aws_region
        )
    return _bedrock_client


def _query(cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a read query against Neo4j and return list of dicts."""
    settings = get_settings()
    driver = _get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]


def _compute_embedding(text: str) -> list[float] | None:
    """Compute a text embedding using Amazon Titan Embed Text v2."""
    try:
        settings = get_settings()
        client = _get_bedrock_client()
        response = client.invoke_model(
            modelId=settings.bedrock_embedding_model_id,
            body=json.dumps({
                "inputText": text[:8000],
                "dimensions": 1024,
            }),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    except Exception as e:
        logger.warning(f"Failed to compute embedding: {e}")
        return None


def _simulate_price(book: dict) -> float:
    """Generate a simulated price based on book properties."""
    # Use bookId as seed for consistent pricing
    seed = int(hashlib.md5(str(book.get("bookId", "")).encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    base = 9.99
    if book.get("format") == "Hardcover":
        base = 24.99
    elif book.get("format") == "Paperback":
        base = 14.99
    elif book.get("isEbook") or book.get("format") in ("ebook", "Kindle Edition"):
        base = 9.99

    # Add some variance
    return round(base + rng.uniform(-2.0, 5.0), 2)


# ---------------------------------------------------------------------------
# Book graph tools
# ---------------------------------------------------------------------------


@tool
def search_books(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search books by title, description, or semantic meaning.

    Combines vector similarity search on description embeddings with fulltext
    keyword search for best results. Use this when the user asks for books
    by name, topic, or keyword.

    Args:
        query: The search query (book title, keywords, topic, or description).
        limit: Maximum number of results to return (default: 10).

    Returns:
        A list of matching books with title, rating, description, and metadata.
    """
    # Try vector search first
    query_embedding = _compute_embedding(query)

    if query_embedding:
        records = _query(
            """
            CALL db.index.vector.queryNodes('bookEmbedding', $limit, $embedding)
            YIELD node AS b, score
            OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(pub:Publisher)
            RETURN b.bookId AS bookId, b.title AS title,
                   b.averageRating AS averageRating,
                   b.ratingsCount AS ratingsCount,
                   b.numPages AS numPages,
                   b.publicationYear AS publicationYear,
                   b.imageUrl AS imageUrl,
                   b.description AS description,
                   b.format AS format,
                   b.isbn AS isbn,
                   pub.name AS publisher,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """,
            {"embedding": query_embedding, "limit": limit},
        )
        if records:
            return records

    # Fallback to fulltext search
    records = _query(
        """
        CALL db.index.fulltext.queryNodes('bookSearch', $query)
        YIELD node AS b, score
        OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(pub:Publisher)
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               b.format AS format,
               b.isbn AS isbn,
               pub.name AS publisher,
               score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"query": query, "limit": limit},
    )
    return records


@tool
def get_book_details(book_id: str) -> dict[str, Any]:
    """Get full details for a specific book including publisher and review summary.

    Use this when you need complete information about a book, including
    its top reviews and review statistics.

    Args:
        book_id: The unique book identifier.

    Returns:
        A dictionary with the book's full details including review statistics.
    """
    records = _query(
        """
        MATCH (b:Book {bookId: $bookId})
        OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(pub:Publisher)
        OPTIONAL MATCH (rev:Review)-[:REVIEWS]->(b)
        WHERE rev.rating > 0
        WITH b, pub,
             count(rev) AS reviewCount,
             avg(rev.rating) AS avgUserRating
        RETURN b.bookId AS bookId, b.title AS title,
               b.titleWithoutSeries AS titleWithoutSeries,
               b.description AS description,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.textReviewsCount AS textReviewsCount,
               b.numPages AS numPages,
               b.format AS format,
               b.languageCode AS languageCode,
               b.isbn AS isbn, b.isbn13 AS isbn13,
               b.asin AS asin, b.kindleAsin AS kindleAsin,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.link AS link,
               b.isEbook AS isEbook,
               b.publisher AS publisherName,
               pub.name AS publisher,
               reviewCount,
               avgUserRating
        """,
        {"bookId": book_id},
    )
    if records:
        return records[0]
    return {"error": f"Book with id '{book_id}' not found"}


@tool
def get_book_reviews(
    book_id: str, limit: int = 5, sort_by: str = "helpful"
) -> list[dict[str, Any]]:
    """Get reviews for a specific book.

    Use this to show what readers think about a book, with their ratings
    and review text.

    Args:
        book_id: The book ID to get reviews for.
        limit: Maximum number of reviews (default: 5).
        sort_by: Sort order - "helpful" (by votes), "recent" (by date), or "rating" (by rating).

    Returns:
        A list of reviews with text, rating, votes, and dates.
    """
    order_clause = {
        "helpful": "r.nVotes DESC",
        "recent": "r.dateAdded DESC",
        "rating": "r.rating DESC",
    }.get(sort_by, "r.nVotes DESC")

    records = _query(
        f"""
        MATCH (u:User)-[:WROTE_REVIEW]->(r:Review)-[:REVIEWS]->(b:Book {{bookId: $bookId}})
        WHERE r.text IS NOT NULL AND r.text <> ''
        RETURN r.reviewId AS reviewId,
               r.rating AS rating,
               r.text AS text,
               r.dateAdded AS dateAdded,
               r.nVotes AS nVotes,
               r.nComments AS nComments,
               u.userId AS userId
        ORDER BY {order_clause}
        LIMIT $limit
        """,
        {"bookId": book_id, "limit": limit},
    )
    return records


@tool
def find_similar_books(book_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Find books similar to a given book using embedding-based similarity.

    Uses pre-computed SIMILAR_TO relationships derived from content embeddings.
    Use this to recommend books related to one the user already likes.

    Args:
        book_id: The book ID to find similar books for.
        limit: Maximum number of similar books (default: 5).

    Returns:
        A list of similar books with details and similarity scores.
    """
    records = _query(
        """
        MATCH (b:Book {bookId: $bookId})-[r:SIMILAR_TO]->(similar:Book)
        OPTIONAL MATCH (similar)-[:PUBLISHED_BY]->(pub:Publisher)
        RETURN similar.bookId AS bookId, similar.title AS title,
               similar.averageRating AS averageRating,
               similar.ratingsCount AS ratingsCount,
               similar.numPages AS numPages,
               similar.publicationYear AS publicationYear,
               similar.imageUrl AS imageUrl,
               similar.description AS description,
               similar.format AS format,
               pub.name AS publisher,
               r.score AS similarityScore
        ORDER BY r.score DESC
        LIMIT $limit
        """,
        {"bookId": book_id, "limit": limit},
    )
    return records


@tool
def get_popular_books(
    limit: int = 10, min_rating: float | None = None
) -> list[dict[str, Any]]:
    """Get the most popular books sorted by number of ratings.

    Use this for general "what's popular" or "best books" requests.

    Args:
        limit: Maximum books to return (default: 10).
        min_rating: Optional minimum average rating filter.

    Returns:
        A list of popular books sorted by ratings count.
    """
    if min_rating is not None:
        records = _query(
            """
            MATCH (b:Book)
            WHERE b.ratingsCount IS NOT NULL AND b.averageRating >= $minRating
            OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(pub:Publisher)
            RETURN b.bookId AS bookId, b.title AS title,
                   b.averageRating AS averageRating,
                   b.ratingsCount AS ratingsCount,
                   b.numPages AS numPages,
                   b.publicationYear AS publicationYear,
                   b.imageUrl AS imageUrl,
                   b.description AS description,
                   b.format AS format,
                   pub.name AS publisher
            ORDER BY b.ratingsCount DESC
            LIMIT $limit
            """,
            {"minRating": min_rating, "limit": limit},
        )
    else:
        records = _query(
            """
            MATCH (b:Book)
            WHERE b.ratingsCount IS NOT NULL
            OPTIONAL MATCH (b)-[:PUBLISHED_BY]->(pub:Publisher)
            RETURN b.bookId AS bookId, b.title AS title,
                   b.averageRating AS averageRating,
                   b.ratingsCount AS ratingsCount,
                   b.numPages AS numPages,
                   b.publicationYear AS publicationYear,
                   b.imageUrl AS imageUrl,
                   b.description AS description,
                   b.format AS format,
                   pub.name AS publisher
            ORDER BY b.ratingsCount DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )
    return records


@tool
def get_books_by_publisher(publisher: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get books by a specific publisher.

    Use this when the user asks about books from a particular publisher
    or publishing house.

    Args:
        publisher: The publisher name (partial match supported).
        limit: Maximum books to return (default: 10).

    Returns:
        A list of books from the publisher.
    """
    records = _query(
        """
        MATCH (b:Book)-[:PUBLISHED_BY]->(p:Publisher)
        WHERE toLower(p.name) CONTAINS toLower($publisher)
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               b.format AS format,
               p.name AS publisher
        ORDER BY b.ratingsCount DESC
        LIMIT $limit
        """,
        {"publisher": publisher, "limit": limit},
    )
    return records


@tool
def get_recommended_books(book_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Get book recommendations based on collaborative filtering.

    Finds books that were highly rated by users who also highly rated the
    given book. This uses the review graph to find "users who liked X also
    liked Y" patterns.

    Args:
        book_id: The book ID to base recommendations on.
        limit: Maximum recommendations (default: 5).

    Returns:
        A list of recommended books with a recommendation score.
    """
    records = _query(
        """
        MATCH (b:Book {bookId: $bookId})<-[:REVIEWS]-(r:Review)<-[:WROTE_REVIEW]-(u:User)
        WHERE r.rating >= 4
        MATCH (u)-[:WROTE_REVIEW]->(r2:Review)-[:REVIEWS]->(rec:Book)
        WHERE rec.bookId <> $bookId AND r2.rating >= 4
        WITH rec, count(DISTINCT u) AS sharedUsers
        WHERE sharedUsers >= 2
        OPTIONAL MATCH (rec)-[:PUBLISHED_BY]->(pub:Publisher)
        RETURN rec.bookId AS bookId, rec.title AS title,
               rec.averageRating AS averageRating,
               rec.ratingsCount AS ratingsCount,
               rec.numPages AS numPages,
               rec.publicationYear AS publicationYear,
               rec.imageUrl AS imageUrl,
               rec.description AS description,
               rec.format AS format,
               pub.name AS publisher,
               sharedUsers AS recommendationScore
        ORDER BY sharedUsers DESC, rec.averageRating DESC
        LIMIT $limit
        """,
        {"bookId": book_id, "limit": limit},
    )
    return records


# ---------------------------------------------------------------------------
# Commerce tools (simulated)
# ---------------------------------------------------------------------------


@tool
def add_to_cart(book_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Add a book to the shopping cart.

    Use this when the user wants to buy or add a book to their cart.

    Args:
        book_id: The book ID to add to cart.

    Returns:
        Confirmation with updated cart contents and total.
    """
    cart = tool_context.invocation_state.get("cart", {})

    # Get book info
    books = _query(
        """
        MATCH (b:Book {bookId: $bookId})
        RETURN b.bookId AS bookId, b.title AS title,
               b.imageUrl AS imageUrl, b.format AS format,
               b.isEbook AS isEbook, b.numPages AS numPages
        """,
        {"bookId": book_id},
    )

    if not books:
        return {"error": f"Book with id '{book_id}' not found"}

    book = books[0]
    price = _simulate_price(book)

    if book_id in cart:
        cart[book_id]["quantity"] += 1
    else:
        cart[book_id] = {
            "bookId": book_id,
            "title": book["title"],
            "price": price,
            "quantity": 1,
            "imageUrl": book.get("imageUrl"),
        }

    tool_context.invocation_state["cart"] = cart

    items = list(cart.values())
    total = sum(item["price"] * item["quantity"] for item in items)

    return {
        "message": f"Added '{book['title']}' to cart",
        "items": items,
        "total": round(total, 2),
        "item_count": sum(item["quantity"] for item in items),
    }


@tool
def get_cart(tool_context: ToolContext) -> dict[str, Any]:
    """View the current shopping cart.

    Use this when the user wants to see what's in their cart.

    Returns:
        Cart contents with items, quantities, and total.
    """
    cart = tool_context.invocation_state.get("cart", {})
    items = list(cart.values())
    total = sum(item["price"] * item["quantity"] for item in items)

    return {
        "items": items,
        "total": round(total, 2),
        "item_count": sum(item["quantity"] for item in items),
    }


@tool
def remove_from_cart(book_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Remove a book from the shopping cart.

    Use this when the user wants to remove a book from their cart.

    Args:
        book_id: The book ID to remove.

    Returns:
        Updated cart contents.
    """
    cart = tool_context.invocation_state.get("cart", {})

    if book_id not in cart:
        return {"error": f"Book '{book_id}' is not in the cart"}

    removed = cart.pop(book_id)
    tool_context.invocation_state["cart"] = cart

    items = list(cart.values())
    total = sum(item["price"] * item["quantity"] for item in items)

    return {
        "message": f"Removed '{removed['title']}' from cart",
        "items": items,
        "total": round(total, 2),
        "item_count": sum(item["quantity"] for item in items),
    }


@tool
def checkout(tool_context: ToolContext) -> dict[str, Any]:
    """Complete the purchase (simulated).

    Use this when the user wants to check out and complete their order.

    Returns:
        Order confirmation with order ID and summary.
    """
    cart = tool_context.invocation_state.get("cart", {})

    if not cart:
        return {"error": "Cart is empty. Add some books first!"}

    items = list(cart.values())
    total = sum(item["price"] * item["quantity"] for item in items)

    # Generate order ID
    order_id = f"ORD-{int(time.time())}-{random.randint(1000, 9999)}"

    # Clear cart
    tool_context.invocation_state["cart"] = {}

    return {
        "orderId": order_id,
        "items": items,
        "total": round(total, 2),
        "item_count": sum(item["quantity"] for item in items),
        "status": "confirmed",
        "message": "Order placed successfully! Your books will be delivered soon.",
    }


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

_book_agent: Agent | None = None


def create_book_agent() -> Agent:
    """Create the book recommendation and commerce Strands agent."""
    settings = get_settings()

    # Neo4j Agent Memory context graph tools
    config = StrandsConfig.from_env()
    memory_tools = context_graph_tools(**config.to_dict())

    book_tools = [
        search_books,
        get_book_details,
        get_book_reviews,
        find_similar_books,
        get_popular_books,
        get_books_by_publisher,
        get_recommended_books,
    ]

    commerce_tools = [
        add_to_cart,
        get_cart,
        remove_from_cart,
        checkout,
    ]

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
        ),
        tools=[*book_tools, *commerce_tools, *memory_tools],
        system_prompt=BOOK_AGENT_SYSTEM_PROMPT,
    )


def get_book_agent() -> Agent:
    """Get or create the global book agent instance."""
    global _book_agent
    if _book_agent is None:
        _book_agent = create_book_agent()
    return _book_agent
