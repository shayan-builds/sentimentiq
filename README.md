# SentimentIQ

SentimentIQ is an AI-powered sentiment and aspect analysis platform for product reviews and campus feedback. This repository contains the initial monorepo foundation, the backend persistence schema, and the health endpoints.

## Technology stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Frontend:** React, TypeScript, Vite
- **Database:** PostgreSQL
- **Local database service:** Docker Compose

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/app/` | FastAPI application and SQLAlchemy persistence models |
| `backend/migrations/` | Alembic migration environment and versioned schema |
| `backend/tests/` | Starting location for backend tests |
| `backend/requirements.txt` | Backend runtime and persistence dependencies |
| `frontend/src/` | React application entry point, starter screen, and styles |
| `frontend/package.json` | Frontend scripts and dependencies |
| `docs/architecture.md` | Short overview of the monorepo boundaries |
| `docs/database-design.md` | Agreed initial database contract and schema |
| `docker-compose.yml` | Local PostgreSQL service and persistent volume |
| `.env.example` | Placeholder settings for local Compose use |
| `.gitignore` | Ignores generated files, local configuration, and IDE files |
| `AGENTS.md` | Architecture, conventions, and guidance for coding agents |

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Docker with the Compose plugin (only needed for PostgreSQL)

## Run the backend

From the repository root:

    cd backend
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    uvicorn app.main:app --reload

The health endpoint is available at <http://127.0.0.1:8000/health>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Run the frontend

In a separate terminal from the repository root:

    cd frontend
    npm install
    npm run dev

Open the local URL printed by Vite (usually <http://localhost:5173>). The frontend runs independently from the backend and database.

## Run PostgreSQL and apply migrations

From the repository root, create a local environment file and start the database:

    Copy-Item .env.example .env
    docker compose up -d db

The example values are placeholders intended for local development. Replace them in your untracked `.env` file as appropriate. PostgreSQL is published on port `5432` by default.

From the backend directory, apply the versioned schema:

    cd backend
    python -m alembic upgrade head

To render the migration SQL without applying it to the database:

    python -m alembic upgrade head --sql

Migration commands use the same PostgreSQL environment variables as the application. The initial migration creates the tables described in `docs/database-design.md`. Report rows carry a 30-day expiry timestamp; an application cleanup task must remove expired report metadata and files. That scheduled cleanup is not part of this schema migration.
