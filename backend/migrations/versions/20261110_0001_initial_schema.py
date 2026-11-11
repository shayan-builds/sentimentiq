"""Create the approved initial persistence schema.

Revision ID: 20261110_0001
Revises:
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("domain IN ('product', 'campus')", name="ck_projects_domain"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE", name="fk_projects_owner_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("id", "domain", name="uq_projects_id_domain"),
    )
    op.create_index("ix_projects_owner_created", "projects", ["owner_user_id", "created_at"])

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_datasets_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_datasets"),
        sa.UniqueConstraint("id", "project_id", name="uq_datasets_id_project"),
    )
    op.create_index("ix_datasets_project_created", "datasets", ["project_id", "created_at"])

    op.create_table(
        "dataset_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("row_number > 0", name="ck_dataset_rows_row_number_positive"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE", name="fk_dataset_rows_dataset_id_datasets"),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_rows"),
        sa.UniqueConstraint("dataset_id", "row_number", name="uq_dataset_rows_dataset_row_number"),
        sa.UniqueConstraint("id", "dataset_id", name="uq_dataset_rows_id_dataset"),
    )
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("model_revision", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("domain IN ('product', 'campus')", name="ck_analysis_jobs_domain"),
        sa.ForeignKeyConstraint(["project_id", "domain"], ["projects.id", "projects.domain"], ondelete="CASCADE", name="fk_analysis_jobs_project_domain"),
        sa.ForeignKeyConstraint(["dataset_id", "project_id"], ["datasets.id", "datasets.project_id"], ondelete="CASCADE", name="fk_analysis_jobs_dataset_project"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_jobs"),
        sa.UniqueConstraint("id", "dataset_id", name="uq_analysis_jobs_id_dataset"),
        sa.UniqueConstraint("id", "project_id", name="uq_analysis_jobs_id_project"),
    )
    op.create_index("ix_analysis_jobs_project_created", "analysis_jobs", ["project_id", "created_at"])
    op.create_index("ix_analysis_jobs_status_created", "analysis_jobs", ["status", "created_at"])
    op.create_index("ix_analysis_jobs_dataset", "analysis_jobs", ["dataset_id"])

    op.create_table(
        "analysis_job_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="running", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_analysis_job_attempts_number_positive"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="CASCADE", name="fk_analysis_job_attempts_analysis_job_id_analysis_jobs"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_job_attempts"),
        sa.UniqueConstraint("analysis_job_id", "attempt_number", name="uq_analysis_job_attempts_job_number"),
    )
    op.create_index("ix_analysis_job_attempts_job_created", "analysis_job_attempts", ["analysis_job_id", "created_at"])

    op.create_table(
        "analysis_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_index", sa.Integer(), nullable=False),
        sa.Column("outcome_status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("input_index >= 0", name="ck_analysis_job_items_input_index"),
        sa.CheckConstraint("outcome_status IN ('pending', 'succeeded', 'failed')", name="ck_analysis_job_items_status"),
        sa.CheckConstraint("(outcome_status = 'failed' AND error_code IS NOT NULL) OR (outcome_status IN ('pending', 'succeeded') AND error_code IS NULL)", name="ck_analysis_job_items_error_outcome"),
        sa.ForeignKeyConstraint(["analysis_job_id", "dataset_id"], ["analysis_jobs.id", "analysis_jobs.dataset_id"], ondelete="CASCADE", name="fk_analysis_job_items_job_dataset"),
        sa.ForeignKeyConstraint(["dataset_row_id", "dataset_id"], ["dataset_rows.id", "dataset_rows.dataset_id"], ondelete="CASCADE", name="fk_analysis_job_items_row_dataset"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_job_items"),
        sa.UniqueConstraint("analysis_job_id", "input_index", name="uq_analysis_job_items_job_input_index"),
        sa.UniqueConstraint("analysis_job_id", "dataset_row_id", name="uq_analysis_job_items_job_row"),
        sa.UniqueConstraint("id", "analysis_job_id", name="uq_analysis_job_items_id_job"),
    )
    op.create_index("ix_analysis_job_items_job_status", "analysis_job_items", ["analysis_job_id", "outcome_status"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_job_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sentiment_label", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("confidence_value", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("confidence_kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sentiment_label IN ('positive', 'negative', 'neutral', 'mixed')", name="ck_predictions_label"),
        sa.CheckConstraint("sentiment_score >= -1 AND sentiment_score <= 1", name="ck_predictions_score_range"),
        sa.CheckConstraint("confidence_value >= 0 AND confidence_value <= 1", name="ck_predictions_confidence_range"),
        sa.CheckConstraint("confidence_kind IN ('raw_score', 'calibrated_probability')", name="ck_predictions_confidence_kind"),
        sa.ForeignKeyConstraint(["analysis_job_item_id", "analysis_job_id"], ["analysis_job_items.id", "analysis_job_items.analysis_job_id"], ondelete="CASCADE", name="fk_predictions_job_item"),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
        sa.UniqueConstraint("analysis_job_item_id", name="uq_predictions_job_item"),
    )
    op.create_index("ix_predictions_analysis_job", "predictions", ["analysis_job_id"])

    op.create_table(
        "aspect_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aspect_index", sa.Integer(), nullable=False),
        sa.Column("aspect_text", sa.Text(), nullable=False),
        sa.Column("aspect_category", sa.Text(), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("confidence_value", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("confidence_kind", sa.String(length=32), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.CheckConstraint("sentiment_label IN ('positive', 'negative', 'neutral', 'mixed')", name="ck_aspect_results_label"),
        sa.CheckConstraint("sentiment_score >= -1 AND sentiment_score <= 1", name="ck_aspect_results_score_range"),
        sa.CheckConstraint("confidence_value >= 0 AND confidence_value <= 1", name="ck_aspect_results_confidence_range"),
        sa.CheckConstraint("confidence_kind IN ('raw_score', 'calibrated_probability')", name="ck_aspect_results_confidence_kind"),
        sa.CheckConstraint("aspect_index >= 0", name="ck_aspect_results_index"),
        sa.CheckConstraint("(start_offset IS NULL AND end_offset IS NULL) OR (start_offset IS NOT NULL AND end_offset IS NOT NULL AND start_offset >= 0 AND end_offset > start_offset)", name="ck_aspect_results_offsets"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE", name="fk_aspect_results_prediction_id_predictions"),
        sa.PrimaryKeyConstraint("id", name="pk_aspect_results"),
        sa.UniqueConstraint("prediction_id", "aspect_index", name="uq_aspect_results_prediction_index"),
    )
    op.create_index("ix_aspect_results_prediction_category", "aspect_results", ["prediction_id", "aspect_category"])

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="ck_reports_expiry"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_reports_project_id_projects"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE", name="fk_reports_requested_by_user_id_users"),
        sa.ForeignKeyConstraint(["analysis_job_id", "project_id"], ["analysis_jobs.id", "analysis_jobs.project_id"], ondelete="CASCADE", name="fk_reports_job_project"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
    )
    op.create_index("ix_reports_project_created", "reports", ["project_id", "created_at"])
    op.create_index("ix_reports_job", "reports", ["analysis_job_id"])
    op.create_index("ix_reports_expiry", "reports", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_expiry", table_name="reports")
    op.drop_index("ix_reports_job", table_name="reports")
    op.drop_index("ix_reports_project_created", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_aspect_results_prediction_category", table_name="aspect_results")
    op.drop_table("aspect_results")
    op.drop_index("ix_predictions_analysis_job", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_analysis_job_items_job_status", table_name="analysis_job_items")
    op.drop_table("analysis_job_items")
    op.drop_index("ix_analysis_job_attempts_job_created", table_name="analysis_job_attempts")
    op.drop_table("analysis_job_attempts")
    op.drop_index("ix_analysis_jobs_dataset", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status_created", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_project_created", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_table("dataset_rows")
    op.drop_index("ix_datasets_project_created", table_name="datasets")
    op.drop_table("datasets")
    op.drop_index("ix_projects_owner_created", table_name="projects")
    op.drop_table("projects")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
