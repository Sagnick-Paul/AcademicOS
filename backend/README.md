# AcademicOS — Backend

Production-grade FastAPI backend for the AcademicOS platform.

## Stack

- **API**: FastAPI + Uvicorn
- **DB**: PostgreSQL via SQLAlchemy 2.x (async) + Alembic
- **Vector store**: Qdrant
- **Agents**: LangGraph
- **RAG / embeddings / parsers / OCR**: dedicated modules under `app/`
- **Workers**: Arq + Redis
- **Auth**: JWT (python-jose) + bcrypt (passlib)

## Layout

```
app/
├── api/             # HTTP routers and dependencies (versioned)
├── core/            # config, security, logging
├── db/              # SQLAlchemy base/session, models, repositories
├── schemas/         # Pydantic DTOs
├── services/        # Business use-cases
├── agents/          # LangGraph agents
├── rag/             # RAG pipelines (retrievers, prompt builders)
├── embeddings/      # Embedding model wrappers
├── parsers/         # Document parsers (PDF, DOCX, …)
├── ocr/             # OCR pipelines
├── storage/         # Object storage abstraction
├── workers/         # Background tasks
├── middleware/      # Custom ASGI middleware
├── utils/           # Generic helpers
├── tests/           # Pytest suite
├── static/          # Static files served by the API
└── uploads/         # Local upload destination (dev only)

alembic/             # Database migrations
```

## Local development

```bash
# 1. Create a virtualenv and install deps
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure env
cp .env.example .env

# 3. Run the API
uvicorn app.main:app --reload --port 8000

# OpenAPI docs:    http://localhost:8000/docs
# ReDoc:           http://localhost:8000/redoc
# Health check:    http://localhost:8000/health
```

## Database migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

## Docker

```bash
docker build -t academicos-backend .
docker run --rm -p 8000:8000 --env-file .env academicos-backend
```

## Conventions

- Async-first: prefer `async def` end-to-end.
- No business logic in routers — delegate to `services/`.
- Pydantic schemas for I/O, ORM models for persistence.
- Keep modules small; one responsibility per file.
