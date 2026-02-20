# Good Strands Graph

An agentic commerce book recommendation app that demonstrates the power of **context graphs** for building AI agents with long-term memory and a complete shopping experience. Built with a Neo4j knowledge graph of 10K Goodreads books and 70K user reviews, vector embeddings for semantic search, the AWS Strands Agents SDK, and `neo4j-agent-memory` for conversational memory with entity extraction.

The agent remembers your reading preferences, finds books through semantic and collaborative filtering, shows real user reviews, and guides you through a simulated purchase flow — all within a rich chat interface with interactive product cards.

Use this as a **hackathon template** for building agentic commerce applications powered by knowledge graphs and conversational memory.

## Architecture

```
┌──────────────────────┐     ┌──────────────────────────────────────┐     ┌──────────────────┐
│   Next.js +          │     │          FastAPI Backend              │     │                  │
│   Chakra UI v3       │────>│                                      │────>│      Neo4j       │
│   (Chat + Commerce)  │<────│  Strands Agent                       │<────│                  │
│                      │     │  ┌──────────┬──────────┬───────────┐ │     │  Book Graph      │
│  - BookCard          │     │  │ 7 Book   │ 4 Cart   │ 4 Memory  │ │     │  (10K books,     │
│  - BookDetailCard    │     │  │ Discovery│ Commerce │ Context   │ │     │   70K reviews,   │
│  - ReviewList        │     │  │ Tools    │ Tools    │ Tools     │ │     │   publishers,    │
│  - CartDisplay       │     │  └──────────┴──────────┴───────────┘ │     │   SIMILAR_TO)    │
│  - OrderConfirmation │     │                                      │     │                  │
│  - ToolResultRenderer│     │  neo4j-agent-memory                  │     │  Vector Index    │
│                      │     │  (entity extraction + embeddings)    │     │  (1024-dim       │
│                      │     │                                      │     │   embeddings)    │
└──────────────────────┘     └──────────────────────────────────────┘     │                  │
                                         │                               │  Agent Memory    │
                                         v                               │  (conversations, │
                                   AWS Bedrock                           │   entities,      │
                                   (Claude + Titan Embeddings)           │   preferences)   │
                                                                         └──────────────────┘
```

### How It Works

1. **User sends a message** via the chat UI (e.g., "find me books about space exploration")
2. **The Strands agent** receives the message along with its system prompt and 15 available tools
3. **The agent decides which tools to call** — it might:
   - `search_context` to recall your past preferences from memory
   - `search_books("space exploration")` to run a hybrid vector + fulltext search on Neo4j
   - `get_book_reviews(book_id)` to fetch what real readers think
   - `get_recommended_books(book_id)` for collaborative filtering ("users who liked X also liked Y")
   - `add_to_cart(book_id)` when you want to buy
4. **Neo4j provides the data** — the book knowledge graph (10K books with reviews, embeddings, and SIMILAR_TO relationships) and the agent memory context graph (conversations, extracted entities, preferences)
5. **The frontend renders rich interactive cards** — book cards with covers, ratings, prices, and "Add to Cart" buttons; review lists; shopping cart; and order confirmation — all embedded inline in the chat

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16 (App Router), Chakra UI v3, react-markdown | Chat interface with rich product cards and purchase flow |
| Backend | Python 3.11+, FastAPI | API server with agent orchestration and tool result extraction |
| Agent Framework | AWS Strands Agents SDK | Tool-calling agent with 15 tools |
| Agent Memory | neo4j-agent-memory | Conversational memory, entity extraction, embeddings |
| Database | Neo4j | Book knowledge graph + vector index + agent memory store |
| LLM | AWS Bedrock (Claude Sonnet) | Agent reasoning and response generation |
| Embeddings | Amazon Titan Embed Text v2 (1024-dim) | Semantic search + SIMILAR_TO computation |

## Quickstart

### Prerequisites

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/) (Python package manager)
- **Node.js 18+** and npm
- **Neo4j** — a [Neo4j Aura Free](https://neo4j.com/cloud/aura-free/) instance (see step 2 below), or a local Neo4j via Docker/Desktop
- **AWS account** with Bedrock access (Claude Sonnet + Titan Embeddings enabled in your region)
- **AWS credentials** configured (`aws configure` or environment variables)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd good-strands-graph
make install
```

This installs both backend (Python via uv) and frontend (Node.js via npm) dependencies.

### 2. Create a Neo4j database

The easiest option is a free Neo4j Aura instance:

1. Go to [console.neo4j.io](https://console.neo4j.io/) and sign up (or log in)
2. Click **New Instance** and select the **Free** tier
3. Choose a region and click **Create**
4. **Save the generated password** — it is only shown once. Also note the **Connection URI** (e.g. `neo4j+s://xxxxxxxx.databases.neo4j.io`)

> Alternatively, you can run Neo4j locally with [Neo4j Desktop](https://neo4j.com/download/) or Docker:
> ```bash
> docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
> ```

### 3. Configure environment

```bash
cp .env.example backend/.env
```

Edit `backend/.env` with your Neo4j Aura credentials and AWS settings:

```env
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password-from-aura>
NEO4J_DATABASE=neo4j
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
CORS_ORIGINS=http://localhost:3000
```

> If running Neo4j locally, use `NEO4J_URI=neo4j://localhost:7687` instead.

### 4. Load the book data

```bash
make load-data
```

This runs the 4-pass data loader:

1. **Books + Publishers** — 10K books from `data/10k-books-demo.json` (~30 seconds)
2. **Users + Reviews** — 70K reviews from `data/10k-book-reviews-demo.json` (~2 minutes)
3. **Embeddings** — computes 1024-dim vectors via Amazon Titan Embed v2 for ~8K books with descriptions (~15-20 minutes)
4. **SIMILAR_TO** — KNN via vector index, creates similarity relationships between books (~5-10 minutes)

Progress is logged throughout. Passes 1-2 are fast; passes 3-4 require AWS Bedrock access and take longer.

### 5. Run the application

```bash
make dev
```

This starts both the backend (FastAPI on port 8000) and frontend (Next.js on port 3000).

Open **http://localhost:3000** and start chatting with the book recommendation agent.

### Quick Commands Reference

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make load-data` | Load books, reviews, embeddings into Neo4j |
| `make dev` | Start backend + frontend |
| `make backend` | Start only the backend (port 8000) |
| `make frontend` | Start only the frontend (port 3000) |
| `make build-frontend` | Production build |
| `make clean` | Remove generated files |

## Graph Data Model

```
(:Book {bookId, title, description, averageRating, ratingsCount, numPages,
        format, isbn, imageUrl, publicationYear, publisher, embedding})

(:Publisher {name})
(:User {userId})
(:Review {reviewId, rating, text, dateAdded, nVotes, nComments})

(:Book)-[:PUBLISHED_BY]->(:Publisher)
(:User)-[:WROTE_REVIEW]->(:Review)-[:REVIEWS]->(:Book)
(:Book)-[:SIMILAR_TO {score}]->(:Book)
```

**Indexes**: fulltext `bookSearch` on Book.title + description, vector `bookEmbedding` (1024-dim cosine) on Book.embedding, plus property indexes on Book.title, Book.averageRating, Book.isbn, Book.publicationYear, Review.rating.

The agent memory layer (managed by `neo4j-agent-memory`) adds a separate context graph in the same database for storing conversations, extracted entities, and user preferences.

## Agent Tools

The agent has 15 tools — 7 for book discovery, 4 for commerce, and 4 for conversational memory:

### Book Discovery Tools
| Tool | Description |
|------|-------------|
| `search_books` | Hybrid vector + fulltext search on title and description |
| `get_book_details` | Full book info with publisher, review statistics |
| `get_book_reviews` | User reviews sorted by helpfulness, recency, or rating |
| `find_similar_books` | Traverse embedding-based SIMILAR_TO relationships |
| `get_popular_books` | Top books by ratings count, optional min rating filter |
| `get_books_by_publisher` | Books from a specific publisher |
| `get_recommended_books` | Collaborative filtering — "users who liked X also liked Y" |

### Commerce Tools
| Tool | Description |
|------|-------------|
| `add_to_cart` | Add a book to the shopping cart |
| `get_cart` | View current cart contents and total |
| `remove_from_cart` | Remove a book from the cart |
| `checkout` | Complete the purchase (simulated) |

### Memory Context Tools (from neo4j-agent-memory)
| Tool | Description |
|------|-------------|
| `search_context` | Semantic search over past conversations and entities |
| `get_entity_graph` | Traverse the entity relationship graph |
| `add_memory` | Store content with automatic entity extraction |
| `get_user_preferences` | Retrieve stored user preferences |

## Frontend: Rich Tool Result Cards

The chat interface renders structured data from tool calls as interactive cards:

| Tool Result | Card Component | Features |
|-------------|---------------|----------|
| Book search / popular / similar / recommended | `BookCardList` | Cover image, rating, price, format badge, "Add to Cart" |
| Single book details | `BookDetailCard` | Full description, review stats, publisher, all metadata, purchase button |
| Book reviews | `ReviewList` | Star ratings, review text, helpful votes, dates |
| Cart operations | `CartDisplay` | Item list with thumbnails, prices, remove buttons, checkout |
| Order confirmation | `OrderConfirmation` | Order ID, item summary, total charged |

The `ToolResultRenderer` component dispatches each tool result to the appropriate card type based on `tool_name`.

## Agent Transparency

The frontend includes built-in agent transparency features:

- **Agent Config Panel** — collapsible accordion at the top of the chat showing the model ID, AWS region, full system prompt, and all 15 tools grouped by category (book discovery, commerce, memory). Fetches from `GET /api/chat/config`.
- **Tool Call Inspector** — each assistant message shows a collapsible "N tool calls" section. Expanding it reveals each tool call with its name, status (ok/error), input arguments, and raw result JSON. The `tool_context` parameter is filtered out for readability.

## Custom Ontology

The agent memory uses a custom ontology (`backend/book_ontology.json`) tailored to the book commerce domain. This teaches the entity extraction system to recognize:

**Entity types**: BOOK (with subtypes: NOVEL, SHORT_STORY, ANTHOLOGY, GRAPHIC_NOVEL, NONFICTION, AUDIOBOOK), PUBLISHER, REVIEWER, PERSON, ORDER

**Relation types**: PUBLISHED_BY, REVIEWED, SIMILAR_TO, PURCHASED, ADDED_TO_CART, PREFERS, HAS_READ, WANTS_TO_READ

When a user says "I really enjoyed that sci-fi novel, add it to my cart", the agent extracts entities and relations into the memory graph, enabling personalized recommendations in future conversations.

## Project Structure

```
good-strands-graph/
├── data/
│   ├── 10k-books-demo.json                              # 10K books (JSONL, 13.5MB)
│   └── 10k-book-reviews-demo.json                       # 70K reviews (JSONL, 73MB)
├── backend/
│   ├── pyproject.toml                                    # Python deps (uv)
│   ├── load_data.py                                      # Neo4j 4-pass data loader
│   ├── book_ontology.json                                # Custom entity schema
│   └── src/
│       ├── main.py                                       # FastAPI app
│       ├── config.py                                     # Settings (env vars)
│       ├── agents/
│       │   ├── book_agent.py                             # Strands Agent + 15 tools
│       │   └── prompts.py                                # System prompt
│       ├── services/
│       │   └── memory_service.py                         # neo4j-agent-memory client
│       └── api/routes/
│           └── chat.py                                   # Chat API with tool result extraction
├── frontend/
│   ├── src/app/                                          # Next.js App Router pages
│   ├── src/components/                                   # Chat UI + product/commerce cards
│   └── src/lib/api.ts                                    # API client + TypeScript types
├── Makefile                                              # Dev commands
├── CLAUDE.md                                             # Claude Code project context
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Send message to agent; returns `{response, session_id, tool_results[], tool_calls[]}` |
| `GET` | `/api/chat/config` | Agent configuration (model ID, system prompt, tool list with categories) |
| `GET` | `/api/chat/history/{session_id}` | Get conversation history |
| `POST` | `/api/chat/search` | Semantic search past conversations |

The `tool_results` array contains structured data for rich card rendering. The `tool_calls` array contains all tool calls with inputs and raw results for the transparency UI. See `backend/README.md` for full API documentation.

Interactive API docs available at **http://localhost:8000/docs** when the backend is running.

## Adapting This Template

This project is designed to be forked and adapted for any domain that benefits from a knowledge graph + conversational AI agent + commerce. Here's how:

### 1. Replace the data

Swap the Goodreads dataset with your own domain data. Edit `backend/load_data.py`:

- Update the Cypher `MERGE` statements for your node types and relationships
- Adjust embedding computation for your content fields
- Modify fulltext and vector indexes for your searchable properties

### 2. Update the graph data model

Redesign the node labels and relationships for your domain:

- **E-commerce**: `(:Product)-[:IN_CATEGORY]->(:Category)`, `(:User)-[:WROTE_REVIEW]->(:Review)-[:REVIEWS]->(:Product)`
- **Music**: `(:Song)-[:PERFORMED_BY]->(:Artist)`, `(:Song)-[:ON_ALBUM]->(:Album)`
- **Movies**: `(:Movie)-[:DIRECTED_BY]->(:Director)`, `(:Movie)-[:HAS_GENRE]->(:Genre)`
- **Recipes**: `(:Recipe)-[:USES]->(:Ingredient)`, `(:Recipe)-[:IN_CUISINE]->(:Cuisine)`

### 3. Customize the agent tools

Edit `backend/src/agents/book_agent.py`:

- Replace the `@tool` functions with Cypher queries for your domain
- Each tool is a simple function: write a Cypher query, call `_query()`, return results
- Commerce tools use `ToolContext.invocation_state` for cart/session state
- The `@tool` decorator + docstring is all Strands needs to make it available to the agent

### 4. Customize the frontend cards

- Update `BookCard.tsx` → `ProductCard.tsx` for your domain objects
- Add domain-specific card components (e.g., `RecipeCard`, `MovieCard`)
- Update `ToolResultRenderer.tsx` to map your tool names to your card components

### 5. Update the ontology and system prompt

- Edit `backend/book_ontology.json` for your domain's entity types
- Edit `backend/src/agents/prompts.py` for your agent's personality and tools

## Useful Cypher Queries

For exploring the loaded data in Neo4j Browser (http://localhost:7474):

```cypher
-- Node counts
MATCH (b:Book) RETURN count(b);
MATCH (u:User) RETURN count(u);
MATCH (r:Review) RETURN count(r);
MATCH (p:Publisher) RETURN count(p);

-- Books with embeddings
MATCH (b:Book) WHERE b.embedding IS NOT NULL RETURN count(b);

-- Fulltext search
CALL db.index.fulltext.queryNodes('bookSearch', 'fantasy adventure')
YIELD node, score
RETURN node.title, score LIMIT 5;

-- Top rated books
MATCH (b:Book) WHERE b.averageRating > 4.0
RETURN b.title, b.averageRating
ORDER BY b.ratingsCount DESC LIMIT 10;

-- Most helpful reviews
MATCH (u:User)-[:WROTE_REVIEW]->(r:Review)-[:REVIEWS]->(b:Book)
RETURN b.title, r.text, r.rating, r.nVotes
ORDER BY r.nVotes DESC LIMIT 5;

-- Collaborative filtering
MATCH (b:Book)<-[:REVIEWS]-(r:Review)<-[:WROTE_REVIEW]-(u:User)
WHERE b.title CONTAINS 'Hobbit' AND r.rating >= 4
MATCH (u)-[:WROTE_REVIEW]->(r2:Review)-[:REVIEWS]->(rec:Book)
WHERE rec <> b AND r2.rating >= 4
RETURN rec.title, count(DISTINCT u) AS sharedUsers
ORDER BY sharedUsers DESC LIMIT 10;

-- Similar books (embedding-based)
MATCH (b:Book)-[r:SIMILAR_TO]->(s:Book)
WHERE b.title CONTAINS 'Harry Potter'
RETURN s.title, s.averageRating, r.score
ORDER BY r.score DESC LIMIT 5;

-- Schema visualization
CALL db.schema.visualization();

-- Agent memory entities (after chatting)
MATCH (e:Entity)
RETURN e.type, e.name LIMIT 20;
```

## Resources

- [AWS Strands Agents SDK](https://github.com/strands-agents/sdk-python)
- [neo4j-agent-memory](https://github.com/neo4j-labs/agent-memory)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Chakra UI v3](https://www.chakra-ui.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UCSD Book Graph Dataset](https://mengtingwan.github.io/data/goodreads.html)
