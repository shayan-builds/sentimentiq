"""SQLAlchemy models for the initial SentimentIQ schema."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_email_lower", text("lower(email)"), unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (CheckConstraint("domain IN ('product', 'campus')", name="ck_projects_domain"), UniqueConstraint("id", "domain", name="uq_projects_id_domain"), Index("ix_projects_owner_created", "owner_user_id", "created_at"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("id", "project_id", name="uq_datasets_id_project"), Index("ix_datasets_project_created", "project_id", "created_at"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class DatasetRow(Base):
    __tablename__ = "dataset_rows"
    __table_args__ = (UniqueConstraint("dataset_id", "row_number", name="uq_dataset_rows_dataset_row_number"), UniqueConstraint("id", "dataset_id", name="uq_dataset_rows_id_dataset"), CheckConstraint("row_number > 0", name="ck_dataset_rows_row_number_positive"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB().with_variant(JSON(), "sqlite"))

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (CheckConstraint("domain IN ('product', 'campus')", name="ck_analysis_jobs_domain"), ForeignKeyConstraint(["project_id", "domain"], ["projects.id", "projects.domain"], ondelete="CASCADE", name="fk_analysis_jobs_project_domain"), ForeignKeyConstraint(["dataset_id", "project_id"], ["datasets.id", "datasets.project_id"], ondelete="CASCADE", name="fk_analysis_jobs_dataset_project"), UniqueConstraint("id", "dataset_id", name="uq_analysis_jobs_id_dataset"), UniqueConstraint("id", "project_id", name="uq_analysis_jobs_id_project"), Index("ix_analysis_jobs_project_created", "project_id", "created_at"), Index("ix_analysis_jobs_status_created", "status", "created_at"), Index("ix_analysis_jobs_dataset", "dataset_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    model_revision: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))

class AnalysisJobAttempt(Base):
    __tablename__ = "analysis_job_attempts"
    __table_args__ = (UniqueConstraint("analysis_job_id", "attempt_number", name="uq_analysis_job_attempts_job_number"), CheckConstraint("attempt_number > 0", name="ck_analysis_job_attempts_number_positive"), Index("ix_analysis_job_attempts_job_created", "analysis_job_id", "created_at"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running", server_default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))

class AnalysisJobItem(Base):
    __tablename__ = "analysis_job_items"
    __table_args__ = (ForeignKeyConstraint(["analysis_job_id", "dataset_id"], ["analysis_jobs.id", "analysis_jobs.dataset_id"], ondelete="CASCADE", name="fk_analysis_job_items_job_dataset"), ForeignKeyConstraint(["dataset_row_id", "dataset_id"], ["dataset_rows.id", "dataset_rows.dataset_id"], ondelete="CASCADE", name="fk_analysis_job_items_row_dataset"), UniqueConstraint("analysis_job_id", "input_index", name="uq_analysis_job_items_job_input_index"), UniqueConstraint("analysis_job_id", "dataset_row_id", name="uq_analysis_job_items_job_row"), UniqueConstraint("id", "analysis_job_id", name="uq_analysis_job_items_id_job"), CheckConstraint("input_index >= 0", name="ck_analysis_job_items_input_index"), CheckConstraint("outcome_status IN ('pending', 'succeeded', 'failed')", name="ck_analysis_job_items_status"), CheckConstraint("(outcome_status = 'failed' AND error_code IS NOT NULL) OR (outcome_status IN ('pending', 'succeeded') AND error_code IS NULL)", name="ck_analysis_job_items_error_outcome"), Index("ix_analysis_job_items_job_status", "analysis_job_id", "outcome_status"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dataset_row_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    input_index: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    error_code: Mapped[str | None] = mapped_column(String(128))

class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (ForeignKeyConstraint(["analysis_job_item_id", "analysis_job_id"], ["analysis_job_items.id", "analysis_job_items.analysis_job_id"], ondelete="CASCADE", name="fk_predictions_job_item"), CheckConstraint("sentiment_label IN ('positive', 'negative', 'neutral', 'mixed')", name="ck_predictions_label"), CheckConstraint("sentiment_score >= -1 AND sentiment_score <= 1", name="ck_predictions_score_range"), CheckConstraint("confidence_value >= 0 AND confidence_value <= 1", name="ck_predictions_confidence_range"), CheckConstraint("confidence_kind IN ('raw_score', 'calibrated_probability')", name="ck_predictions_confidence_kind"), UniqueConstraint("analysis_job_item_id", name="uq_predictions_job_item"), Index("ix_predictions_analysis_job", "analysis_job_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_job_item_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    confidence_value: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    confidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class AspectResult(Base):
    __tablename__ = "aspect_results"
    __table_args__ = (CheckConstraint("sentiment_label IN ('positive', 'negative', 'neutral', 'mixed')", name="ck_aspect_results_label"), CheckConstraint("sentiment_score >= -1 AND sentiment_score <= 1", name="ck_aspect_results_score_range"), CheckConstraint("confidence_value >= 0 AND confidence_value <= 1", name="ck_aspect_results_confidence_range"), CheckConstraint("confidence_kind IN ('raw_score', 'calibrated_probability')", name="ck_aspect_results_confidence_kind"), CheckConstraint("aspect_index >= 0", name="ck_aspect_results_index"), CheckConstraint("(start_offset IS NULL AND end_offset IS NULL) OR (start_offset IS NOT NULL AND end_offset IS NOT NULL AND start_offset >= 0 AND end_offset > start_offset)", name="ck_aspect_results_offsets"), UniqueConstraint("prediction_id", "aspect_index", name="uq_aspect_results_prediction_index"), Index("ix_aspect_results_prediction_category", "prediction_id", "aspect_category"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    aspect_index: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_text: Mapped[str] = mapped_column(Text, nullable=False)
    aspect_category: Mapped[str | None] = mapped_column(Text)
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    confidence_value: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    confidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (CheckConstraint("expires_at > created_at", name="ck_reports_expiry"), ForeignKeyConstraint(["analysis_job_id", "project_id"], ["analysis_jobs.id", "analysis_jobs.project_id"], ondelete="CASCADE", name="fk_reports_job_project"), Index("ix_reports_project_created", "project_id", "created_at"), Index("ix_reports_job", "analysis_job_id"), Index("ix_reports_expiry", "expires_at"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    analysis_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    storage_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128))
