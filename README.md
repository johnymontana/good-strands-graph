# Good Strands Graph

An agentic book recommendation application that demonstrates the power of **context graphs** for building AI agents with long-term memory. Built with a Neo4j knowledge graph of 219K Goodreads mystery/thriller/crime books, the AWS Strands Agents SDK, and `neo4j-agent-memory` for conversational memory with entity extraction.

The agent remembers your reading preferences, tracks books you've read or want to read, and uses graph relationships (similar books, series, genres) to deliver personalized recommendations that improve over time.

Use this as a **hackathon template** for building agentic applications powered by knowledge graphs and conversational memory.

## Architecture

```
┌──────────────────┐     ┌───────────────────────────────────┐     ┌─────────────────┐
│   Next.js +      │     │         FastAPI Backend            │     │                 │
│   Chakra UI v3   │────>│                                   │────>│     Neo4j       │
│   (Chat UI)      │<────│  Strands Agent                    │<────│                 │
│                  │     │  ┌─────────────┬────────────────┐ │     │  Book Graph     │
│  - ChatInterface │     │  │ 7 Book      │ 4 Memory       │ │     │  (219K books,   │
│  - BookCard      │     │  │ Graph Tools │ Context Tools  │ │     │   authors,      │
│  - MessageBubble │     │  └─────────────┴────────────────┘ │     │   series,       │
│                  │     │                                   │     │   shelves)       │
│                  │     │  neo4j-agent-memory               │     │                 │
│                  │     │  (entity extraction + embeddings) │     │  Agent Memory   │
│                  │     │                                   │     │  (conversations, │
└──────────────────┘     └───────────────────────────────────┘     │   entities,     │
                                        │                         │   preferences)  │
                                        v                         └─────────────────┘
                                  AWS Bedrock
                                  (Claude + Titan Embeddings)
```

### How It Works

1. **User sends a message** via the chat UI (e.g., "recommend a good noir mystery")
2. **The Strands agent** receives the message along with its system prompt and available tools
3. **The agent decides which tools to call** — it might:
   - `search_context` to recall your past preferences from memory
   - `search_by_genre("noir")` to query the Neo4j book graph
   - `find_similar_books(book_id)` to traverse SIMILAR_TO relationships
   - `add_memory` to remember what you told it about your reading tastes
4. **Neo4j provides the data** — both the book knowledge graph (219K books with relationships) and the agent memory context graph (your conversations, extracted entities, preferences)
5. **The agent synthesizes a response** with personalized recommendations, complete with titles, ratings, and descriptions from real data

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js (App Router), Chakra UI v3 | Chat interface with book recommendation cards |
| Backend | Python, FastAPI | API server with agent orchestration |
| Agent Framework | AWS Strands Agents SDK | Tool-calling agent with system prompt |
| Agent Memory | neo4j-agent-memory | Conversational memory, entity extraction, embeddings |
| Database | Neo4j | Book knowledge graph + agent memory store |
| LLM | AWS Bedrock (Claude) | Agent reasoning and response generation |
| Embeddings | Amazon Titan Embed Text v2 | Semantic search over conversations |

## Quickstart

### Prerequisites

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/) (Python package manager)
- **Node.js 18+** and npm
- **Neo4j** — either:
  - [Neo4j Desktop](https://neo4j.com/download/) (local)
  - [Neo4j Aura](https://neo4j.com/cloud/aura/) (cloud, free tier available)
  - Docker: `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5`
- **AWS account** with Bedrock access (Claude Sonnet + Titan Embeddings enabled in your region)
- **AWS credentials** configured (`aws configure` or environment variables)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd good-strands-graph
make install
```

This installs both backend (Python via uv) and frontend (Node.js via npm) dependencies.

### 2. Configure environment

```bash
cp .env.example backend/.env
```

Edit `backend/.env` with your settings:

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-neo4j-password>
NEO4J_DATABASE=neo4j
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
CORS_ORIGINS=http://localhost:3000
```

### 3. Load the book data

```bash
make load-data
```

This loads 219K books into Neo4j in 3 passes (books/authors/publishers, similar-to relationships, shelves). Takes ~5-10 minutes. Progress is logged every 5,000 records.

### 4. Run the application

```bash
make dev
```

This starts both the backend (FastAPI on port 8000) and frontend (Next.js on port 3000).

Open **http://localhost:3000** and start chatting with the book recommendation agent.

### Quick Commands Reference

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make load-data` | Load books into Neo4j (run once) |
| `make dev` | Start backend + frontend |
| `make backend` | Start only the backend (port 8000) |
| `make frontend` | Start only the frontend (port 3000) |
| `make build-frontend` | Production build |
| `make clean` | Remove generated files |

## Graph Data Model

The book knowledge graph uses this schema:

```
(:Book)-[:WRITTEN_BY]->(:Author)
(:Book)-[:PART_OF_SERIES]->(:Series)
(:Book)-[:SIMILAR_TO]->(:Book)
(:Book)-[:ON_SHELF {count}]->(:Shelf)
(:Book)-[:PUBLISHED_BY]->(:Publisher)
```

Key Book properties: `bookId`, `title`, `description`, `averageRating`, `ratingsCount`, `numPages`, `imageUrl`, `publicationYear`, `isbn`.

The agent memory layer (managed by `neo4j-agent-memory`) adds a separate context graph in the same database for storing conversations, extracted entities, and user preferences.

## Agent Tools

The agent has 11 tools available — 7 for querying the book graph and 4 for conversational memory:

### Book Graph Tools
| Tool | Description |
|------|-------------|
| `search_books` | Fulltext search on title and description |
| `get_book_details` | Complete book info with author, series, shelves |
| `find_similar_books` | Traverse SIMILAR_TO relationships |
| `get_books_by_author` | All books by an author |
| `search_by_genre` | Books on a shelf with minimum rating filter |
| `get_popular_books` | Top books by ratings count, optional genre filter |
| `find_books_in_series` | All books in a series |

### Memory Context Tools (from neo4j-agent-memory)
| Tool | Description |
|------|-------------|
| `search_context` | Semantic search over past conversations and entities |
| `get_entity_graph` | Traverse the entity relationship graph |
| `add_memory` | Store content with automatic entity extraction |
| `get_user_preferences` | Retrieve stored user preferences |

## Custom Ontology

The agent memory uses a custom ontology (`backend/book_ontology.json`) tailored to the book domain instead of the default POLE+O model. This teaches the entity extraction system to recognize:

**Entity types**: BOOK, AUTHOR, GENRE (with subtypes: MYSTERY, THRILLER, CRIME, NOIR, COZY_MYSTERY, SUSPENSE, DETECTIVE), SERIES, PERSON

**Relation types**: WRITTEN_BY, IN_GENRE, PART_OF_SERIES, SIMILAR_TO, PREFERS, HAS_READ, WANTS_TO_READ

When a user says "I love Agatha Christie's mysteries, especially the Poirot series", the agent extracts entities (AUTHOR: Agatha Christie, GENRE: mystery, SERIES: Poirot) and relations (PREFERS) into the memory graph, enabling personalized recommendations in future conversations.

## Project Structure

```
good-strands-graph/
├── data/
│   └── goodreads_books_mystery_thriller_crime.json   # 219K books (JSONL, ~1GB)
├── backend/
│   ├── pyproject.toml                                # Python deps (uv)
│   ├── load_data.py                                  # Neo4j batch data loader
│   ├── book_ontology.json                            # Custom entity schema
│   └── src/
│       ├── main.py                                   # FastAPI app
│       ├── config.py                                 # Settings (env vars)
│       ├── agents/
│       │   ├── book_agent.py                         # Strands Agent + 7 @tool functions
│       │   └── prompts.py                            # System prompt
│       ├── services/
│       │   └── memory_service.py                     # neo4j-agent-memory MemoryClient
│       └── api/routes/
│           └── chat.py                               # Chat API endpoints
├── frontend/
│   ├── src/app/                                      # Next.js App Router pages
│   ├── src/components/                               # Chat UI + BookCard components
│   └── src/lib/api.ts                                # API client
├── Makefile                                          # Dev commands
├── CLAUDE.md                                         # Claude Code project context
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Send a message to the agent |
| `GET` | `/api/chat/history/{session_id}` | Get conversation history |
| `POST` | `/api/chat/search` | Semantic search past conversations |

Interactive API docs available at **http://localhost:8000/docs** when the backend is running.

## Adapting This Template for a Hackathon

This project is designed to be forked and adapted for any domain that benefits from a knowledge graph + conversational AI agent. Here's how to make it your own:

### 1. Replace the data

Swap the Goodreads dataset with your own domain data. Edit `backend/load_data.py` to match your schema:

- Update the Cypher `MERGE` statements for your node types and relationships
- Adjust the `BATCH_SIZE` based on your data volume
- Modify the fulltext index to cover your searchable properties

### 2. Update the graph data model

Redesign the node labels and relationships for your domain. Common patterns:

- **E-commerce**: `(:Product)-[:IN_CATEGORY]->(:Category)`, `(:Product)-[:REVIEWED_BY]->(:User)`
- **Music**: `(:Song)-[:PERFORMED_BY]->(:Artist)`, `(:Song)-[:ON_ALBUM]->(:Album)`
- **Movies**: `(:Movie)-[:DIRECTED_BY]->(:Director)`, `(:Movie)-[:HAS_GENRE]->(:Genre)`
- **Recipes**: `(:Recipe)-[:USES]->(:Ingredient)`, `(:Recipe)-[:IN_CUISINE]->(:Cuisine)`

### 3. Customize the agent tools

Edit `backend/src/agents/book_agent.py`:

- Replace the 7 `@tool` functions with Cypher queries for your domain
- Each tool is a simple function: write a Cypher query, call `_query()`, return results
- The `@tool` decorator + docstring is all Strands needs to make it available to the agent

### 4. Update the ontology

Edit `backend/book_ontology.json` to define entity types for your domain. This controls how `neo4j-agent-memory` extracts and categorizes entities from conversations.

### 5. Update the system prompt

Edit `backend/src/agents/prompts.py` to describe your agent's personality, available tools, and domain expertise.

### 6. Customize the frontend

- Update `BookCard.tsx` to display your domain objects (products, movies, recipes, etc.)
- Adjust the chat interface styling and branding in `ChatInterface.tsx`
- Modify `page.tsx` for your app's title and description

### Key Extension Ideas

- **Add user authentication** to persist preferences per user across sessions
- **Implement streaming responses** with FastAPI StreamingResponse + SSE on the frontend
- **Add a "purchase" or "save" action** to book cards for commerce functionality
- **Build an admin panel** to visualize the knowledge graph and agent memory
- **Add vector search** on book embeddings for semantic similarity beyond SIMILAR_TO
- **Multi-agent architecture** — add a separate agent for order management, reviews, etc.

## Useful Cypher Queries

For exploring the loaded data in Neo4j Browser (http://localhost:7474):

```cypher
-- Node counts
MATCH (b:Book) RETURN count(b);
MATCH (a:Author) RETURN count(a);
MATCH (s:Shelf) RETURN count(s);

-- Top rated mysteries
MATCH (b:Book)-[:ON_SHELF]->(s:Shelf {name: 'mystery'})
WHERE b.averageRating > 4.0
RETURN b.title, b.averageRating
ORDER BY b.ratingsCount DESC LIMIT 10;

-- Fulltext search
CALL db.index.fulltext.queryNodes('bookSearch', 'detective noir')
YIELD node, score
RETURN node.title, score LIMIT 5;

-- Similar books traversal
MATCH (b:Book)-[:SIMILAR_TO]->(s:Book)
WHERE b.title CONTAINS 'Gone Girl'
RETURN s.title, s.averageRating;

-- Schema visualization
CALL db.schema.visualization();

-- Agent memory entities (after chatting)
MATCH (e:Entity)
WHERE e.type IN ['BOOK', 'AUTHOR', 'GENRE']
RETURN e LIMIT 20;
```

## Resources

- [AWS Strands Agents SDK](https://github.com/strands-agents/sdk-python)
- [neo4j-agent-memory](https://github.com/neo4j-labs/agent-memory)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Chakra UI v3](https://www.chakra-ui.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UCSD Book Graph Dataset](https://mengtingwan.github.io/data/goodreads.html)
