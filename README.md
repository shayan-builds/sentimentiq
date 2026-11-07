# SentimentIQ

SentimentIQ is an AI-powered sentiment and aspect analysis platform for product reviews and campus feedback. This repository contains the initial monorepo foundation; it does not yet include authentication, analysis models, database tables, dashboards, or business workflows.

## Technology stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Frontend:** React, TypeScript, Vite
- **Database:** PostgreSQL
- **Local database service:** Docker Compose

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/app/` | FastAPI application package and health endpoint |
| `backend/tests/` | Starting location for backend tests |
| `backend/requirements.txt` | Backend runtime and persistence dependencies |
| `frontend/src/` | React application entry point, starter screen, and styles |
| `frontend/package.json` | Frontend scripts and dependencies |
| `docs/architecture.md` | Short overview of the monorepo boundaries |
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

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health endpoint is available at <http://127.0.0.1:8000/health>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Run the frontend

In a separate terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually <http://localhost:5173>). The frontend runs independently from the backend and database.

## Run PostgreSQL

From the repository root, create a local environment file and start the database:

```powershell
Copy-Item .env.example .env
docker compose up -d db
```

The example values are placeholders intended for local development. Replace them in your untracked `.env` file as appropriate. PostgreSQL is published on port `5432` by default. To stop the service, run `docker compose down`; to also remove its stored data, run `docker compose down -v`.

SQLAlchemy and Alembic are included in the backend dependencies as the planned ORM and migration tooling. Database connection configuration, models, and migrations will be added in later work.
