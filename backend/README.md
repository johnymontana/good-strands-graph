# Good Strands Graph — Backend

Python FastAPI backend with an AWS Strands agent that has 15 tools for book discovery, commerce, and conversational memory. Queries a Neo4j knowledge graph of 10K books with 70K reviews, vector embeddings for semantic search, and embedding-based SIMILAR_TO relationships.

## Getting Started

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your Neo4j and AWS credentials

# Load data into Neo4j (run once)
uv run python load_data.py

# Start the server
uv run uvicorn src.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

## Architecture

```
src/
├── main.py                     # FastAPI app with lifespan (memory init/shutdown)
├── config.py                   # Pydantic Settings from environment variables
├── agents/
│   ├── book_agent.py           # Strands Agent creation + 15 tool definitions
│   └── prompts.py              # System prompt
├── services/
│   └── memory_service.py       # neo4j-agent-memory MemoryClient wrapper
└── api/routes/
    └── chat.py                 # Chat endpoints + tool result extraction + cart state
```

## Data Loading (`load_data.py`)

The data loader runs 4 sequential passes:

### Pass 1: Books + Publishers
- Source: `data/10k-books-demo.json` (JSONL, 10K records)
- Creates `:Book` nodes with 20 properties (title, description, averageRating, ratingsCount, numPages, format, isbn, imageUrl, publicationYear, etc.)
- Creates `:Publisher` nodes and `[:PUBLISHED_BY]` relationships
- Handles dirty data: string-to-int/float conversion, boolean parsing, empty field handling
- Batch size: 500

### Pass 2: Users + Reviews
- Source: `data/10k-book-reviews-demo.json` (JSONL, 70K records)
- Creates `:User` nodes (45K unique users, anonymized MD5 IDs)
- Creates `:Review` nodes with rating (0-5), text, dates, votes, comments
- Creates `[:WROTE_REVIEW]` (User→Review) and `[:REVIEWS]` (Review→Book) relationships
- Batch size: 500

### Pass 3: Embeddings
- Queries all Book nodes with non-empty descriptions (~8,200 books)
- Calls Amazon Titan Embed Text v2 via `boto3` to compute 1024-dim embeddings
- Stores embeddings as `Book.embedding` (LIST<FLOAT>)
- Rate-limited with 0.1s delay between batches of 10
- Idempotent: skips books that already have embeddings

### Pass 4: SIMILAR_TO Relationships
- Uses the Neo4j vector index (`bookEmbedding`) to find k-nearest neighbors
- For each book with an embedding, queries top 6 neighbors (k=6 to exclude self)
- Creates `[:SIMILAR_TO {score}]` relationships for neighbors with cosine similarity >= 0.7
- Typically creates ~5 relationships per book

### Constraints and Indexes

```cypher
-- Uniqueness constraints
CREATE CONSTRAINT book_id FOR (b:Book) REQUIRE b.bookId IS UNIQUE;
CREATE CONSTRAINT publisher_name FOR (p:Publisher) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT user_id FOR (u:User) REQUIRE u.userId IS UNIQUE;
CREATE CONSTRAINT review_id FOR (r:Review) REQUIRE r.reviewId IS UNIQUE;

-- Property indexes
CREATE INDEX book_title FOR (b:Book) ON (b.title);
CREATE INDEX book_rating FOR (b:Book) ON (b.averageRating);
CREATE INDEX book_isbn FOR (b:Book) ON (b.isbn);
CREATE INDEX book_pub_year FOR (b:Book) ON (b.publicationYear);
CREATE INDEX review_rating FOR (r:Review) ON (r.rating);

-- Fulltext index (keyword search)
CREATE FULLTEXT INDEX bookSearch FOR (b:Book) ON EACH [b.title, b.description];

-- Vector index (semantic search)
CREATE VECTOR INDEX bookEmbedding FOR (b:Book) ON (b.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}};
```

## Agent Tools

### Book Discovery Tools (7)

**`search_books(query, limit=10)`** — Hybrid search. First attempts vector similarity search by computing a query embedding via Titan Embed v2 and querying the `bookEmbedding` vector index. Falls back to fulltext search on the `bookSearch` index if embedding computation fails.

**`get_book_details(book_id)`** — Returns full book properties plus publisher name, review count, and average user rating (computed from actual Review nodes, separate from Goodreads' `averageRating`).

**`get_book_reviews(book_id, limit=5, sort_by="helpful")`** — Fetches review text, rating, votes, and dates. Sort options: `helpful` (by nVotes), `recent` (by dateAdded), `rating` (by rating). Filters out empty reviews.

**`find_similar_books(book_id, limit=5)`** — Traverses pre-computed `[:SIMILAR_TO]` relationships with similarity scores. Returns similar books ordered by score.

**`get_popular_books(limit=10, min_rating=None)`** — Books ordered by `ratingsCount` DESC. Optional `min_rating` filter on `averageRating`.

**`get_books_by_publisher(publisher, limit=10)`** — Case-insensitive partial match on Publisher name via `toLower(p.name) CONTAINS toLower($publisher)`.

**`get_recommended_books(book_id, limit=5)`** — Collaborative filtering via the review graph. Pattern: find users who rated the given book >= 4 stars, then find other books those users also rated >= 4 stars, ranked by number of shared users. Requires at least 2 shared users to surface a recommendation.

### Commerce Tools (4)

Cart state is stored in-memory per session and passed to the agent via `ToolContext.invocation_state`. Tools access it via `tool_context.invocation_state["cart"]`.

**`add_to_cart(book_id, tool_context)`** — Looks up book details from Neo4j, generates a deterministic simulated price (based on bookId hash + format), adds to cart. Returns cart summary.

**`get_cart(tool_context)`** — Returns current cart items, quantities, and total.

**`remove_from_cart(book_id, tool_context)`** — Removes item from cart. Returns updated cart.

**`checkout(tool_context)`** — Generates an order ID (`ORD-{timestamp}-{random}`), returns order summary, clears the cart.

### Memory Tools (4, from neo4j-agent-memory)

Loaded via `context_graph_tools()` from `neo4j-agent-memory`:
- `search_context` — semantic search over conversation history
- `get_entity_graph` — traverse entity relationships
- `add_memory` — store content with entity extraction
- `get_user_preferences` — retrieve preferences by category

## API

### `POST /api/chat`

Send a message to the agent.

**Request:**
```json
{
  "message": "find me books about space",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "Here are some books about space exploration...",
  "session_id": "abc-123",
  "tool_results": [
    {
      "tool_name": "search_books",
      "tool_use_id": "tooluse_abc",
      "data": [
        {
          "bookId": "12345",
          "title": "The Martian",
          "averageRating": 4.4,
          "ratingsCount": 500000,
          "numPages": 369,
          "publicationYear": 2014,
          "imageUrl": "https://...",
          "description": "...",
          "format": "Paperback",
          "publisher": "Crown Publishing",
          "score": 0.89
        }
      ]
    }
  ]
}
```

The `tool_results` array contains structured data from each tool call the agent made during its reasoning loop. The frontend uses these to render rich interactive cards.

**Tool result extraction** works by walking `agent.messages` after invocation:
1. Collect `toolUse` blocks from assistant messages → map `toolUseId` to `tool_name`
2. Collect `toolResult` blocks from user messages → extract JSON data
3. Filter to exposed tool names (book discovery + commerce tools only, not memory tools)

### `GET /api/chat/history/{session_id}`

Returns conversation history as `[{role, content, timestamp}]`.

### `POST /api/chat/search`

Semantic search over past conversations.

**Request:** `{"query": "books about space", "limit": 10}`

### `GET /health`

Health check. Returns `{"status": "healthy"}`.

## Custom Ontology (`book_ontology.json`)

Defines entity types for the neo4j-agent-memory entity extraction system:

**Entity types:**
- `BOOK` (subtypes: NOVEL, SHORT_STORY, ANTHOLOGY, GRAPHIC_NOVEL, NONFICTION, AUDIOBOOK)
- `PUBLISHER`
- `REVIEWER`
- `PERSON`
- `ORDER`

**Relation types:** PUBLISHED_BY, REVIEWED, SIMILAR_TO, PURCHASED, ADDED_TO_CART, PREFERS, HAS_READ, WANTS_TO_READ

Settings: `default_entity_type: "BOOK"`, `enable_subtypes: true`, `strict_types: false`.

## Configuration (`src/config.py`)

Pydantic Settings loaded from `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `neo4j://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `AWS_REGION` | `us-west-2` | AWS region for Bedrock |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | LLM model for the agent |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `DEBUG` | `false` | Debug mode |

## Dependencies

```
strands-agents          # AWS Strands Agent SDK
strands-agents-tools    # Strands tool utilities
neo4j-agent-memory[aws] # Neo4j agent memory with AWS (Bedrock) extras
neo4j                   # Neo4j Python driver
fastapi                 # Web framework
uvicorn[standard]       # ASGI server
pydantic                # Data validation
pydantic-settings       # Settings from environment
python-dotenv           # .env file loading
boto3                   # AWS SDK (Bedrock embeddings)
```

## Development

```bash
# Run with auto-reload
uv run uvicorn src.main:app --reload --port 8000

# Run data loader
uv run python load_data.py
```

The FastAPI app uses a lifespan handler that initializes the `BookMemoryService` on startup and closes it on shutdown. If Neo4j is unreachable on startup, the memory service degrades gracefully and the agent still works (without memory tools).
