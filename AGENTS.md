# SentimentIQ agent instructions

## Architecture

- This repository is a monorepo with independent `backend/` and `frontend/` applications.
- The backend uses Python 3.11+, FastAPI, SQLAlchemy, and Alembic. PostgreSQL is the planned database and is available for local development through the root Docker Compose file.
- The frontend uses React, TypeScript, and Vite.
- Keep the backend and frontend independently runnable. Do not require Docker Compose to start either application.
- Keep application configuration in environment variables. Never commit secrets or real credentials; `.env.example` must contain placeholders only.

## Coding conventions

- Prefer small, readable modules and explicit names over clever abstractions.
- Add Python type annotations to public functions and keep frontend code strictly typed.
- Keep API routes and UI components focused. Add dependencies only when they support an agreed requirement.
- Keep persistence definitions and Alembic migrations in the backend as they are introduced.
- Document new setup steps and configuration variables in `README.md`.

## Working instructions

- Read the relevant files and existing instructions before editing.
- Preserve the existing Git repository and history; never initialize a nested repository.
- Do not add authentication, ML models, database tables, dashboards, or business features unless requested.
- Do not add or run tests unless the user asks for testing or verification.
- After edits, summarize changed files and report verification only when it was requested or required for a deliverable.
