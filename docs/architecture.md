# Architecture overview

SentimentIQ is a small monorepo with independently runnable application parts:

- `backend/` contains the FastAPI service, SQLAlchemy models, and Alembic migrations.
- `frontend/` contains the React and TypeScript single-page application, built with Vite.
- PostgreSQL is provided as a local development service through Docker Compose.

The backend and frontend do not depend on Compose to start. The backend can serve its health endpoints without connecting to PostgreSQL; database operations use the configured PostgreSQL connection. Persistence definitions are versioned with Alembic. The agreed initial database contract is documented in `docs/database-design.md`.
