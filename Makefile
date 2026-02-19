.PHONY: install install-backend install-frontend load-data backend frontend dev clean

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

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
