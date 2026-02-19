"""Book recommendation agent powered by AWS Strands and Neo4j."""

from __future__ import annotations

import logging
from typing import Any

from neo4j import GraphDatabase
from neo4j_agent_memory.integrations.strands import StrandsConfig, context_graph_tools
from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import BOOK_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Neo4j driver singleton for tool queries
_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def _query(cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a read query against Neo4j and return list of dicts."""
    settings = get_settings()
    driver = _get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]


# ---------------------------------------------------------------------------
# Book graph tools
# ---------------------------------------------------------------------------


@tool
def search_books(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search books by title, description, or keywords using fulltext search.

    Use this tool when the user asks for books by name, topic, or keyword.

    Args:
        query: The search query (book title, keywords, topic).
        limit: Maximum number of results to return (default: 10).

    Returns:
        A list of matching books with title, rating, description, and metadata.
    """
    records = _query(
        """
        CALL db.index.fulltext.queryNodes('bookSearch', $query)
        YIELD node, score
        WITH node AS b, score
        OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
        OPTIONAL MATCH (b)-[:ON_SHELF]->(s:Shelf)
        WITH b, score, collect(DISTINCT a.authorId) AS authorIds,
             collect(DISTINCT s.name)[..5] AS shelves
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               authorIds, shelves, score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"query": query, "limit": limit},
    )
    return records


@tool
def get_book_details(book_id: str) -> dict[str, Any]:
    """Get full details for a specific book including author, series, and shelves.

    Use this when you need complete information about a book.

    Args:
        book_id: The unique book identifier.

    Returns:
        A dictionary with the book's full details.
    """
    records = _query(
        """
        MATCH (b:Book {bookId: $bookId})
        OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
        OPTIONAL MATCH (b)-[:PART_OF_SERIES]->(s:Series)
        OPTIONAL MATCH (b)-[:ON_SHELF]->(shelf:Shelf)
        WITH b, collect(DISTINCT a.authorId) AS authorIds,
             collect(DISTINCT s.seriesId) AS seriesIds,
             collect(DISTINCT shelf.name)[..10] AS shelves
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
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.link AS link,
               b.isEbook AS isEbook,
               authorIds, seriesIds, shelves
        """,
        {"bookId": book_id},
    )
    if records:
        return records[0]
    return {"error": f"Book with id '{book_id}' not found"}


@tool
def find_similar_books(book_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Find books similar to a given book via SIMILAR_TO graph relationships.

    Use this to recommend books that are related to one the user already likes.

    Args:
        book_id: The book ID to find similar books for.
        limit: Maximum number of similar books (default: 5).

    Returns:
        A list of similar books with details.
    """
    records = _query(
        """
        MATCH (b:Book {bookId: $bookId})-[:SIMILAR_TO]->(similar:Book)
        OPTIONAL MATCH (similar)-[:WRITTEN_BY]->(a:Author)
        OPTIONAL MATCH (similar)-[:ON_SHELF]->(s:Shelf)
        WITH similar, collect(DISTINCT a.authorId) AS authorIds,
             collect(DISTINCT s.name)[..5] AS shelves
        RETURN similar.bookId AS bookId, similar.title AS title,
               similar.averageRating AS averageRating,
               similar.ratingsCount AS ratingsCount,
               similar.numPages AS numPages,
               similar.publicationYear AS publicationYear,
               similar.imageUrl AS imageUrl,
               similar.description AS description,
               authorIds, shelves
        ORDER BY similar.averageRating DESC
        LIMIT $limit
        """,
        {"bookId": book_id, "limit": limit},
    )
    return records


@tool
def get_books_by_author(author_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get all books by a specific author, sorted by rating.

    Args:
        author_id: The author's unique identifier.
        limit: Maximum books to return (default: 10).

    Returns:
        A list of books by the author.
    """
    records = _query(
        """
        MATCH (a:Author {authorId: $authorId})<-[:WRITTEN_BY]-(b:Book)
        OPTIONAL MATCH (b)-[:ON_SHELF]->(s:Shelf)
        WITH b, collect(DISTINCT s.name)[..5] AS shelves
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               shelves
        ORDER BY b.averageRating DESC
        LIMIT $limit
        """,
        {"authorId": author_id, "limit": limit},
    )
    return records


@tool
def search_by_genre(
    genre: str, min_rating: float = 3.5, limit: int = 10
) -> list[dict[str, Any]]:
    """Find highly-rated books in a specific genre or shelf category.

    Use this when the user wants recommendations for a genre like "mystery",
    "thriller", "crime", "noir", "detective", "cozy-mystery", etc.

    Args:
        genre: The genre/shelf name to search (e.g., "mystery", "thriller").
        min_rating: Minimum average rating filter (default: 3.5).
        limit: Maximum books to return (default: 10).

    Returns:
        A list of top-rated books in the genre.
    """
    records = _query(
        """
        MATCH (b:Book)-[:ON_SHELF]->(s:Shelf {name: $genre})
        WHERE b.averageRating >= $minRating
        OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
        WITH b, collect(DISTINCT a.authorId) AS authorIds
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               authorIds
        ORDER BY b.ratingsCount DESC
        LIMIT $limit
        """,
        {"genre": genre, "minRating": min_rating, "limit": limit},
    )
    return records


@tool
def get_popular_books(
    genre: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Get the most popular books sorted by number of ratings.

    Optionally filter by genre. Use this for general "what's popular" requests.

    Args:
        genre: Optional genre/shelf name to filter by.
        limit: Maximum books to return (default: 10).

    Returns:
        A list of popular books.
    """
    if genre:
        records = _query(
            """
            MATCH (b:Book)-[:ON_SHELF]->(s:Shelf {name: $genre})
            OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
            WITH b, collect(DISTINCT a.authorId) AS authorIds
            RETURN b.bookId AS bookId, b.title AS title,
                   b.averageRating AS averageRating,
                   b.ratingsCount AS ratingsCount,
                   b.numPages AS numPages,
                   b.publicationYear AS publicationYear,
                   b.imageUrl AS imageUrl,
                   b.description AS description,
                   authorIds
            ORDER BY b.ratingsCount DESC
            LIMIT $limit
            """,
            {"genre": genre, "limit": limit},
        )
    else:
        records = _query(
            """
            MATCH (b:Book)
            WHERE b.ratingsCount IS NOT NULL
            OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
            WITH b, collect(DISTINCT a.authorId) AS authorIds
            RETURN b.bookId AS bookId, b.title AS title,
                   b.averageRating AS averageRating,
                   b.ratingsCount AS ratingsCount,
                   b.numPages AS numPages,
                   b.publicationYear AS publicationYear,
                   b.imageUrl AS imageUrl,
                   b.description AS description,
                   authorIds
            ORDER BY b.ratingsCount DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )
    return records


@tool
def find_books_in_series(series_id: str) -> list[dict[str, Any]]:
    """Get all books in a series, sorted by publication year.

    Args:
        series_id: The series identifier.

    Returns:
        A list of books in the series.
    """
    records = _query(
        """
        MATCH (b:Book)-[:PART_OF_SERIES]->(s:Series {seriesId: $seriesId})
        OPTIONAL MATCH (b)-[:WRITTEN_BY]->(a:Author)
        WITH b, collect(DISTINCT a.authorId) AS authorIds
        RETURN b.bookId AS bookId, b.title AS title,
               b.averageRating AS averageRating,
               b.ratingsCount AS ratingsCount,
               b.numPages AS numPages,
               b.publicationYear AS publicationYear,
               b.imageUrl AS imageUrl,
               b.description AS description,
               authorIds
        ORDER BY b.publicationYear ASC
        """,
        {"seriesId": series_id},
    )
    return records


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

_book_agent: Agent | None = None


def create_book_agent() -> Agent:
    """Create the book recommendation Strands agent."""
    settings = get_settings()

    # Neo4j Agent Memory context graph tools (search_context, get_entity_graph, add_memory, get_user_preferences)
    config = StrandsConfig.from_env()
    memory_tools = context_graph_tools(**config.to_dict())

    book_tools = [
        search_books,
        get_book_details,
        find_similar_books,
        get_books_by_author,
        search_by_genre,
        get_popular_books,
        find_books_in_series,
    ]

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
        ),
        tools=[*book_tools, *memory_tools],
        system_prompt=BOOK_AGENT_SYSTEM_PROMPT,
    )


def get_book_agent() -> Agent:
    """Get or create the global book agent instance."""
    global _book_agent
    if _book_agent is None:
        _book_agent = create_book_agent()
    return _book_agent
