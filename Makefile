.PHONY: install install-backend install-frontend load-data fetch-author-data dump-embeddings load-embeddings backend frontend dev clean

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && uv sync
	@if [ ! -f backend/.env ]; then \
		if [ -f .env ]; then \
			cp .env backend/.env && echo "Copied .env to backend/.env (backend/.env was missing)."; \
		else \
			echo "Warning: backend/.env not found. Backend and scripts (e.g. load-data, dump-embeddings) need it for Neo4j/AWS. Copy backend/.env.example to backend/.env and configure."; \
		fi; \
	fi

install-frontend:
	cd frontend && npm install

# Fetch author data (book-author links + author details) into data/
fetch-author-data:
	python backend/scripts/fetch_author_data.py

# Dump Book embeddings to data/book-embeddings.json (JSONL by bookId)
dump-embeddings:
	cd backend && uv run python scripts/book_embeddings.py dump

# Load Book embeddings from data/book-embeddings.json into Neo4j
load-embeddings:
	cd backend && uv run python scripts/book_embeddings.py load

# Load Goodreads data into Neo4j (run once)
load-data:
	cd backend && uv run python load_data.py

# Start backend (FastAPI on port 8000)
backend:
	cd backend && uv run uvicorn src.main:app --reload --port 8000

# Start frontend (Next.js on port 3000)
frontend:
	cd frontend && npm run dev

# Start both backend and frontend
dev:
	@echo "Starting backend and frontend..."
	$(MAKE) backend & $(MAKE) frontend

# Build frontend for production
build-frontend:
	cd frontend && npm run build

# Lint frontend
lint:
	cd frontend && npm run lint

# Remove generated files
clean:
	rm -rf backend/.venv backend/uv.lock
	rm -rf frontend/.next frontend/node_modules
