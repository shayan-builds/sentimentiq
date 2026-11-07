# Architecture overview

SentimentIQ is a small monorepo with independently runnable application parts:

- `backend/` contains the FastAPI service and its Python dependencies.
- `frontend/` contains the React and TypeScript single-page application, built with Vite.
- PostgreSQL is provided as a local development service through Docker Compose.

The backend and frontend do not depend on Compose to run. SQLAlchemy and Alembic
are included as the planned persistence and migration tools; database models,
migrations, and application features will be introduced in later work.
