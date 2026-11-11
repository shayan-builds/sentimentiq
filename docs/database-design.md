# SentimentIQ database design

> **Status: Initial schema agreed and implemented.** The first migration records the platform-owned policies approved by Person 2 and the ML result contract confirmed by Person 1. It does not implement authentication, API authorization, report generation, cleanup scheduling, or ML computation.

## Agreed policies and contracts

- Primary keys are UUIDs generated in Python with `uuid.uuid4`. Timestamps are timezone-aware.
- A project domain is `product` or `campus`. Analysis jobs must match both the project's domain and its dataset's project.
- Deleting a user cascades to their projects and all dependent records. Analysis content is not retained after account deletion.
- A report row stores project/job/requester references, format and status, timestamps, and an external file storage key. It does not store report files or duplicate predictions. Report records/files expire after 30 days and are removed immediately when their owning project or user is deleted. Expiry metadata is stored here; a separate cleanup task must enforce the retention period.
- Password and refresh-session fields are deferred until an authentication method is selected. Emotion results are deferred.
- Each input in a job has an ordered item row with one pending/succeeded/failed outcome. Failed inputs store a safe `error_code`; successful items have a prediction. Job attempts are recorded separately. Application transaction logic must ensure exactly one result or error for each completed item.
- Analysis jobs snapshot one `model_id` and immutable `model_revision`. The product model revision is its artifact SHA-256; the current campus model revision is `vaderSentiment-3.3.2`.
- Overall and aspect labels are `positive`, `negative`, `neutral`, or `mixed`. The product classifier predicts the first three; the engine may produce `mixed`.
- `sentiment_score` is a model-specific polarity score in [-1, 1]. Product uses positive probability minus negative probability; campus uses VADER compound polarity.
- `confidence_value` is in [0, 1] and is not necessarily a calibrated probability. Use `raw_score` for current outputs; reserve `calibrated_probability` for a calibrated and evaluated model.
- Aspect results are per mention. Repeated text is allowed. `aspect_index` preserves result order; offsets are nullable zero-based, end-exclusive Unicode code-point positions in the original input text.
- Batch analysis returns one ordered outcome per input. Retry and attempt history belongs to the platform.
- Analytics consumes successful stored results with overall sentiment, confidence and kind, aspects, timestamp, and domain. Filter by domain before computing; confidence aggregates remain separated by kind and include counts.

## Initial tables

| Table | Purpose |
| --- | --- |
| `users` | Minimal account identity and active state; case-insensitive unique email. Password fields are deferred. |
| `projects` | User ownership boundary, name, and supported domain. |
| `datasets` | Project-scoped imported dataset metadata. |
| `dataset_rows` | Source text, row order, optional external reference and JSONB metadata. |
| `analysis_jobs` | Project/dataset run, domain, lifecycle state, model ID and revision. |
| `analysis_job_attempts` | Ordered job retry/attempt history with safe error codes. |
| `analysis_job_items` | One ordered outcome per dataset row in a job. |
| `predictions` | Overall sentiment result for a successful job item. |
| `aspect_results` | Per-mention sentiment and optional source-text offsets. |
| `reports` | Report metadata and external storage key with a 30-day expiry. |

Optional emotion results, authentication password/session fields, and project sharing are outside this first migration.

## Constraints and ownership

- Email is unique case-insensitively. Project and analysis domains are constrained to `product` and `campus`.
- Composite foreign keys ensure an analysis job's domain matches its project, its dataset belongs to that project, and each job item points to a row in the job's dataset.
- Input indexes are zero-based and unique within a job; dataset row numbers are positive and unique within a dataset. Job and report lifecycle vocabularies, as well as report formats, remain application-level values and are not constrained by this migration.
- Sentiment scores are constrained to [-1, 1], confidence values to [0, 1], and offset pairs to both-null or valid increasing ranges.
- Foreign keys cascade through the owned-data graph. These database constraints do not replace project-scoped authorization in API endpoints.
- Prediction/item result-or-error exclusivity is coordinated in the application transaction; relational constraints ensure at most one prediction per item and only one item per job input.

## Migration and operations

Alembic configuration is in `backend/alembic.ini`; the initial revision is in `backend/migrations/versions/`. Run `python -m alembic upgrade head` from `backend/` after configuring the PostgreSQL environment. The schema migration has not been applied to a development database as part of this change.
