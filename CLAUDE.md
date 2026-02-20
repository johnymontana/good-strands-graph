# Good Strands Graph

Agentic commerce book recommendation app powered by Neo4j context graphs, AWS Strands Agents SDK, and neo4j-agent-memory. Uses a knowledge graph of 10K Goodreads books with 70K user reviews, vector embeddings for semantic search, and a simulated purchase flow.

## Project Structure

```
good-strands-graph/
├── data/
│   ├── 10k-books-demo.json                              # 10K books, JSONL (13.5MB)
│   ├── 10k-book-reviews-demo.json                       # 70K reviews, JSONL (73MB)
│   ├── 10k-book-authors.json                             # optional: book_id → author_ids (from make fetch-author-data)
│   ├── 10k-authors-demo.json                             # optional: author details JSONL (from make fetch-author-data)
│   └── book-embeddings.json                              # optional: Book.embedding dump by bookId (make dump-embeddings)
├── backend/                                              # Python FastAPI + Strands Agent
│   ├── pyproject.toml
│   ├── load_data.py                                      # Neo4j batch data loader (books, authors, reviews, embeddings, SIMILAR_TO)
│   ├── scripts/
│   │   ├── fetch_author_data.py                          # download author data into data/
│   │   └── book_embeddings.py                            # dump/load Book embeddings by bookId (make dump-embeddings, load-embeddings)
│   ├── book_ontology.json                                # Custom entity schema for agent memory
│   └── src/
│       ├── main.py                                       # FastAPI app entry point
│       ├── config.py                                     # Pydantic Settings (env vars)
│       ├── agents/
│       │   ├── book_agent.py                             # Strands Agent + 15 tools (11 @tool + 4 memory)
│       │   └── prompts.py                                # System prompt
│       ├── services/
│       │   └── memory_service.py                         # neo4j-agent-memory MemoryClient
│       └── api/routes/
│           └── chat.py                                   # POST /api/chat (with tool_results + tool_calls), GET /api/chat/history, GET /api/chat/config
├── frontend/                                             # Next.js App Router + Chakra UI v3
│   ├── src/app/
│   │   ├── layout.tsx                                    # Root layout with Chakra Provider
│   │   └── page.tsx                                      # Main chat page
│   ├── src/components/
│   │   ├── ChatInterface.tsx                             # Chat UI with session + cart management
│   │   ├── MessageBubble.tsx                             # Message display with markdown + tool calls + tool results
│   │   ├── ToolResultRenderer.tsx                        # Dispatches tool results to correct card type
│   │   ├── ToolCallDisplay.tsx                           # Collapsible tool call detail (input/output inspector)
│   │   ├── AgentConfigPanel.tsx                          # Collapsible panel showing model, system prompt, tools
│   │   ├── BookCard.tsx                                  # Book card with rating, cover, price, Add to Cart
│   │   ├── BookCardList.tsx                              # List of BookCards for search results
│   │   ├── BookDetailCard.tsx                            # Expanded single-book detail view
│   │   ├── ReviewCard.tsx                                # Single review display
│   │   ├── ReviewList.tsx                                # List of reviews
│   │   ├── CartDisplay.tsx                               # Shopping cart with items, totals, checkout
│   │   └── OrderConfirmation.tsx                         # Post-checkout confirmation
│   └── src/lib/
│       └── api.ts                                        # API client + TypeScript types
├── Makefile                                              # Dev commands (install, dev, load-data, etc.)
└── CLAUDE.md
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, AWS Strands Agents SDK (`strands-agents`), `neo4j-agent-memory[aws]`, Neo4j Python driver, boto3
- **Frontend**: Next.js 16 (App Router), Chakra UI v3, TypeScript, react-markdown
- **Database**: Neo4j (book knowledge graph + agent memory)
- **LLM**: AWS Bedrock (Claude via Strands)
- **Embeddings**: Amazon Titan Embed Text v2 (1024-dim, for vector search + SIMILAR_TO computation)

## Graph Data Model

```
(:Book {bookId, title, description, averageRating, ratingsCount, numPages, format,
        isbn, imageUrl, publicationYear, publisher, embedding})
(:Publisher {name})
(:Author {authorId, name, averageRating, textReviewsCount, ratingsCount})
(:User {userId})
(:Review {reviewId, rating, text, dateAdded, nVotes, nComments})

(:Book)-[:PUBLISHED_BY]->(:Publisher)
(:Author)-[:AUTHORED]->(:Book)
(:User)-[:WROTE_REVIEW]->(:Review)-[:REVIEWS]->(:Book)
(:Book)-[:SIMILAR_TO {score}]->(:Book)   -- computed from description embeddings
```

**Indexes**: fulltext `bookSearch` on Book.title+description, vector `bookEmbedding` (1024-dim cosine) on Book.embedding, plus property indexes on Book.title, Book.averageRating, Book.isbn, Book.publicationYear, Author.authorId, Author.name, Review.rating.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

```
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
CORS_ORIGINS=http://localhost:3000
```

## Package Management

- **Backend**: [uv](https://docs.astral.sh/uv/) for Python dependency management
- **Frontend**: npm

## Setup & Run

### Quick start

```bash
make install        # Install all dependencies (backend + frontend)
make load-data      # Load 10K books + 70K reviews + embeddings into Neo4j
make dev            # Start backend (port 8000) + frontend (port 3000)
```

### Individual targets

```bash
make install-backend    # uv sync in backend/
make install-frontend   # npm install in frontend/
make fetch-author-data # Download author data into data/ (optional; for Author nodes and AUTHORED)
make dump-embeddings   # Export Book embeddings to data/book-embeddings.json (by bookId)
make load-embeddings   # Load Book embeddings from data/book-embeddings.json into Neo4j
make load-data          # Load data into Neo4j (books, optional authors+AUTHORED, reviews, embeddings, SIMILAR_TO)
make backend            # Start FastAPI on port 8000
make frontend           # Start Next.js on port 3000
make dev                # Start both backend and frontend
make build-frontend     # Production build of frontend
make lint               # Lint frontend
make clean              # Remove .venv, node_modules, .next
```

### Manual commands (equivalent)

```bash
# Load data
cd backend && uv sync && uv run python load_data.py

# Start backend
cd backend && uv run uvicorn src.main:app --reload --port 8000

# Start frontend
cd frontend && npm install && npm run dev
```

API docs at http://localhost:8000/docs, frontend at http://localhost:3000

## Backend Architecture

### Data Loader (`backend/load_data.py`)

Batch loader (author passes run only if `data/10k-book-authors.json` exists; run `make fetch-author-data` to create it):
1. **Books + Publishers**: MERGE Book nodes with all properties, MERGE Publisher nodes with PUBLISHED_BY relationships
2. **Authors + AUTHORED** (optional): From `data/10k-book-authors.json`, MERGE Author nodes by authorId, then MERGE (Author)-[:AUTHORED]->(Book). If `data/10k-authors-demo.json` exists, hydrate Author nodes with name, averageRating, textReviewsCount, ratingsCount
3. **Users + Reviews**: MERGE User nodes, CREATE Review nodes with WROTE_REVIEW and REVIEWS relationships
4. **Embeddings**: Compute description embeddings via Amazon Titan Embed Text v2, store as `Book.embedding`
5. **SIMILAR_TO**: KNN via vector index, top 5 neighbors with cosine similarity >= 0.7

### Agent Tools (in `backend/src/agents/book_agent.py`)

11 `@tool` decorated functions (plus 4 memory tools = 15 total):

**Book discovery** (query Neo4j via Cypher):
- `search_books` — hybrid vector + fulltext search on title/description
- `get_book_details` — full book info with publisher and review statistics
- `get_book_reviews` — user reviews sorted by helpfulness, recency, or rating
- `find_similar_books` — traverse embedding-based SIMILAR_TO relationships
- `get_popular_books` — top books by ratings count with optional min rating filter
- `get_books_by_publisher` — books by publisher name (partial match)
- `get_recommended_books` — collaborative filtering ("users who liked X also liked Y")

**Commerce** (simulated, in-memory cart via `ToolContext.invocation_state`):
- `add_to_cart` — add a book to the shopping cart
- `get_cart` — view current cart contents
- `remove_from_cart` — remove a book from cart
- `checkout` — complete purchase, return order confirmation

Plus 4 memory tools from `context_graph_tools()` (neo4j-agent-memory Strands integration):
- `search_context` — semantic search over conversation history and entities
- `get_entity_graph` — relationship graph traversal
- `add_memory` — store content with entity extraction
- `get_user_preferences` — retrieve user preferences

### Custom Ontology (`backend/book_ontology.json`)

Defines book commerce entity types for agent memory: BOOK, PUBLISHER, REVIEWER, PERSON, ORDER. Relations: PUBLISHED_BY, REVIEWED, SIMILAR_TO, PURCHASED, ADDED_TO_CART, PREFERS, HAS_READ, WANTS_TO_READ.

### API Endpoints

- `POST /api/chat` — send message to agent, returns `{response, session_id, tool_results[], tool_calls[]}`
- `GET /api/chat/config` — agent configuration (model ID, system prompt, tool list with categories)
- `GET /api/chat/history/{session_id}` — conversation history
- `POST /api/chat/search` — semantic search past conversations

The `tool_results` array contains structured data from each tool call (book lists, reviews, cart state, order confirmations) which the frontend renders as rich interactive cards. The `tool_calls` array contains all tool calls with their inputs and raw results, used by the frontend's tool call transparency UI.

## Frontend Architecture

- **Chakra UI v3** with snippets (`components/ui/provider.tsx`, `color-mode.tsx`); `ColorModeProvider` loaded via `next/dynamic` with `ssr: false` to avoid hydration mismatch with `next-themes`
- **react-markdown** for rendering agent text responses
- **ChatInterface** manages session state, message list, input, loading states, and cart action callbacks
- **AgentConfigPanel** collapsible accordion showing model ID, system prompt, and all tools grouped by category (book_discovery, commerce, memory); fetches from `GET /api/chat/config`
- **MessageBubble** renders user (plain text) and assistant (markdown + collapsible tool calls + tool result cards) messages
- **ToolCallDisplay** collapsible per-tool-call inspector showing tool name, status badge (ok/error), input args, and raw result JSON; filters out `tool_context` from display
- **ToolResultRenderer** dispatches tool results to the correct card component based on `tool_name`
- **BookCard** displays book with cover image, star rating, price, format/publisher badges, and "Add to Cart" button
- **BookCardList** renders a vertical list of BookCards for search/popular/similar results
- **BookDetailCard** expanded single-book view with full description, review stats, and purchase button
- **ReviewCard** / **ReviewList** renders user reviews with ratings, helpful votes, and dates
- **CartDisplay** shows cart items with totals and checkout button
- **OrderConfirmation** shows post-checkout success with order ID and summary
- API client in `lib/api.ts` with full TypeScript types for all tool result shapes, tool call data, and agent config

### Tool → Component Mapping

| Tool Name | Component |
|-----------|-----------|
| `search_books`, `get_popular_books`, `find_similar_books`, `get_books_by_publisher`, `get_recommended_books` | BookCardList |
| `get_book_details` | BookDetailCard |
| `get_book_reviews` | ReviewList |
| `add_to_cart`, `get_cart`, `remove_from_cart` | CartDisplay |
| `checkout` | OrderConfirmation |

## Development Notes

- **Author data**: To load Author nodes and AUTHORED relationships, run `make fetch-author-data` once to download `data/10k-book-authors.json` and `data/10k-authors-demo.json` from Neo4j and the Gist. Then `make load-data` will run the author passes. If those files are missing, the loader skips Author/AUTHORED and continues.
- **Book embeddings dump/load**: Embeddings are addressed by `bookId`. Use `make dump-embeddings` to export to `data/book-embeddings.json` (JSONL) and `make load-embeddings` to set them back. Pass 3 in `load_data.py` only computes embeddings for books where `embedding IS NULL`, so restored embeddings are not overwritten.
- **Fulltext index**: `bookSearch` index on Book.title and Book.description. Created by `load_data.py`.
- **Vector index**: `bookEmbedding` on Book.embedding (1024-dim, cosine). Created by `load_data.py`.
- **Embeddings**: ~82% of books have descriptions and get embeddings. Books without descriptions are findable via fulltext but not vector search.
- **SIMILAR_TO**: Computed from embedding cosine similarity with threshold 0.7, top 5 neighbors per book.
- **Cart state**: Stored in-memory per session_id in `chat.py`. Cart is passed to agent via `invocation_state` and updated by commerce tools via `ToolContext`.
- **Simulated prices**: Deterministic based on bookId hash. Format affects base price (Hardcover ~$25, Paperback ~$15, ebook ~$10).
- **Memory vs book graph**: The agent uses two separate Neo4j graph layers — the book knowledge graph (queried by @tool functions) and the agent memory context graph (managed by neo4j-agent-memory). Both live in the same Neo4j database.

## Useful Cypher Queries (for verification)

```cypher
-- Node counts
MATCH (b:Book) RETURN count(b);
MATCH (p:Publisher) RETURN count(p);
MATCH (a:Author) RETURN count(a);
MATCH (u:User) RETURN count(u);
MATCH (r:Review) RETURN count(r);

-- AUTHORED relationships
MATCH ()-[r:AUTHORED]->() RETURN count(r);

-- Books by author name
MATCH (a:Author)-[:AUTHORED]->(b:Book)
WHERE a.name CONTAINS 'Rowling'
RETURN b.title, a.name;

-- Books with embeddings
MATCH (b:Book) WHERE b.embedding IS NOT NULL RETURN count(b);

-- SIMILAR_TO relationships
MATCH ()-[r:SIMILAR_TO]->() RETURN count(r);

-- Sample fulltext search
CALL db.index.fulltext.queryNodes('bookSearch', 'fantasy adventure') YIELD node, score
RETURN node.title, score LIMIT 5;

-- Top rated books
MATCH (b:Book)
WHERE b.averageRating > 4.0
RETURN b.title, b.averageRating
ORDER BY b.ratingsCount DESC LIMIT 10;

-- Most helpful reviews for a book
MATCH (u:User)-[:WROTE_REVIEW]->(r:Review)-[:REVIEWS]->(b:Book)
WHERE b.title CONTAINS 'Harry Potter'
RETURN r.text, r.rating, r.nVotes
ORDER BY r.nVotes DESC LIMIT 5;

-- Collaborative filtering: users who liked book X also liked...
MATCH (b:Book {title: 'The Hobbit'})<-[:REVIEWS]-(r:Review)<-[:WROTE_REVIEW]-(u:User)
WHERE r.rating >= 4
MATCH (u)-[:WROTE_REVIEW]->(r2:Review)-[:REVIEWS]->(rec:Book)
WHERE rec <> b AND r2.rating >= 4
RETURN rec.title, count(DISTINCT u) AS sharedUsers
ORDER BY sharedUsers DESC LIMIT 10;

-- Schema visualization
CALL db.schema.visualization();
```
