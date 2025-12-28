# InSite Survey Backend (FastAPI + MongoDB)

This repository bootstraps a FastAPI service plus MongoDB data model tailored to the Functional Requirements Document (FRD) for the InSite Survey Management Portal. It focuses on the schema and configuration so you can layer business logic, routers, and services on top.

## Prerequisites
- Python 3.11+
- MongoDB instance (local or Atlas)

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit values
uvicorn app.main:app --reload
```

The service exposes a health endpoint at `GET /health` and will connect to the MongoDB URI defined in `.env` when the application starts.

## Project Structure

```
app/
  core/config.py        # Environment-driven settings (MONGODB_URI, etc.)
  db/mongo.py           # Motor client wrapper + lifespan hook
  main.py               # FastAPI entrypoint
  models/               # Pydantic models describing Mongo collections
requirements.txt        # API + Mongo client dependencies
docs/data-model.md      # Narrative description of each collection
```

## Data Model

Detailed collection definitions, relationships, and suggested indexes live in `docs/data-model.md`. Pydantic representations of the same structures are available in `app/models/domain.py` and can be reused for validation.

## Next Steps
1. **Routers/Services** – create feature modules (auth, templates, surveys, analytics, subscriptions) that import the models and interact with MongoDB.
2. **Repositories** – add CRUD helpers per collection that also stamp `created_at`/`updated_at` timestamps and enforce business rules (e.g., single published template/survey).
3. **Auth + Sessions** – wire JWT/session management plus dependency injection to respect the role-based permissions described in the FRD.
4. **Testing** – use `httpx.AsyncClient` + `pytest` to validate repositories and routers against a MongoDB fixture (e.g., `mongomock` or a test container).
