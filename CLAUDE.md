# Good Strands Graph

Agentic commerce book recommendation app powered by Neo4j context graphs, AWS Strands Agents SDK, and neo4j-agent-memory. Uses a knowledge graph of 219K Goodreads mystery/thriller/crime books.

## Project Structure

```
good-strands-graph/
├── data/
│   └── goodreads_books_mystery_thriller_crime.json   # 219K books, JSONL (1GB)
├── backend/                                          # Python FastAPI + Strands Agent
│   ├── pyproject.toml
│   ├── load_data.py                                  # Neo4j batch data loader (3-pass)
│   ├── book_ontology.json                            # Custom entity schema for agent memory
│   └── src/
│       ├── main.py                                   # FastAPI app entry point
│       ├── config.py                                 # Pydantic Settings (env vars)
│       ├── agents/
│       │   ├── book_agent.py                         # Strands Agent + 7 @tool functions
│       │   └── prompts.py                            # System prompt
│       ├── services/
│       │   └── memory_service.py                     # neo4j-agent-memory MemoryClient
│       └── api/routes/
│           └── chat.py                               # POST /api/chat, GET /api/chat/history
├── frontend/                                         # Next.js App Router + Chakra UI v3
│   ├── src/app/
│   │   ├── layout.tsx                                # Root layout with Chakra Provider
│   │   └── page.tsx                                  # Main chat page
│   ├── src/components/
│   │   ├── ChatInterface.tsx                         # Chat UI with session management
│   │   ├── MessageBubble.tsx                         # Message display
│   │   └── BookCard.tsx                              # Book card with rating, cover, badges
│   └── src/lib/
│       └── api.ts                                    # API client
├── Makefile                                          # Dev commands (install, dev, load-data, etc.)
└── CLAUDE.md
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, AWS Strands Agents SDK (`strands-agents`), `neo4j-agent-memory[aws]`, Neo4j Python driver
- **Frontend**: Next.js 16 (App Router), Chakra UI v3, TypeScript
- **Database**: Neo4j (book knowledge graph + agent memory)
- **LLM**: AWS Bedrock (Claude via Strands)
- **Embeddings**: Amazon Titan Embed Text v2 (via neo4j-agent-memory)

## Graph Data Model

```
(:Book)-[:WRITTEN_BY]->(:Author)
(:Book)-[:PART_OF_SERIES]->(:Series)
(:Book)-[:SIMILAR_TO]->(:Book)
(:Book)-[:ON_SHELF {count}]->(:Shelf)
(:Book)-[:PUBLISHED_BY]->(:Publisher)
```

Key properties on Book: bookId, title, description, averageRating, ratingsCount, numPages, imageUrl, publicationYear, isbn.

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
make load-data      # Load 219K books into Neo4j (run once)
make dev            # Start backend (port 8000) + frontend (port 3000)
```

### Individual targets

```bash
make install-backend    # uv sync in backend/
make install-frontend   # npm install in frontend/
make load-data          # Load Goodreads data into Neo4j (~5-10 min)
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

### Agent Tools (in `backend/src/agents/book_agent.py`)

Seven `@tool` decorated functions that query Neo4j via Cypher:
- `search_books` — fulltext search on title/description
- `get_book_details` — full book info with author, series, shelves
- `find_similar_books` — traverse SIMILAR_TO relationships
- `get_books_by_author` — books by author ID
- `search_by_genre` — books on a shelf with min rating filter
- `get_popular_books` — top books by ratings count
- `find_books_in_series` — all books in a series

Plus 4 memory tools from `context_graph_tools()` (neo4j-agent-memory Strands integration):
- `search_context` — semantic search over conversation history and entities
- `get_entity_graph` — relationship graph traversal
- `add_memory` — store content with entity extraction
- `get_user_preferences` — retrieve user preferences

### Custom Ontology (`backend/book_ontology.json`)

Defines book-domain entity types for agent memory entity extraction: BOOK, AUTHOR, GENRE, SERIES, PERSON. Loaded via `neo4j_agent_memory.schema.models.load_schema_from_file()`.

### API Endpoints

- `POST /api/chat` — send message to agent, returns response + session_id
- `GET /api/chat/history/{session_id}` — conversation history
- `POST /api/chat/search` — semantic search past conversations

## Frontend Architecture

- Chakra UI v3 with snippets (`components/ui/provider.tsx`, `color-mode.tsx`)
- `ChatInterface` manages session state, message list, input, loading states
- `BookCard` displays book with cover image, star rating (RatingGroup), badges for pages/year/genres
- `MessageBubble` renders user and assistant messages
- API client in `lib/api.ts` talks to FastAPI backend

## Development Notes

- **Fulltext index**: `bookSearch` index on Book.title and Book.description. Must exist before agent tools work. Created by `load_data.py`.
- **Author names**: The Goodreads dataset only has author_id, not author names. Author nodes have `authorId` only.
- **Shelf data**: Only top 10 shelves per book are loaded to keep graph manageable.
- **Memory vs book graph**: The agent uses two separate Neo4j graph layers — the book knowledge graph (queried by @tool functions) and the agent memory context graph (managed by neo4j-agent-memory). Both live in the same Neo4j database.

## Useful Cypher Queries (for verification)

```cypher
-- Node counts
MATCH (b:Book) RETURN count(b);
MATCH (a:Author) RETURN count(a);
MATCH (s:Shelf) RETURN count(s);

-- Sample search
CALL db.index.fulltext.queryNodes('bookSearch', 'detective noir') YIELD node, score
RETURN node.title, score LIMIT 5;

-- Top rated books in a genre
MATCH (b:Book)-[:ON_SHELF]->(s:Shelf {name: 'mystery'})
WHERE b.averageRating > 4.0
RETURN b.title, b.averageRating
ORDER BY b.ratingsCount DESC LIMIT 10;

-- Similar books chain
MATCH (b:Book {title: 'Gone Girl'})-[:SIMILAR_TO]->(s)
RETURN s.title, s.averageRating;

-- Schema visualization
CALL db.schema.visualization();
```
