"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

_now = sa.text("now()")


def upgrade():
    op.create_table(
        "reviewers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now),
    )
    op.create_index("ix_reviewers_api_key_hash", "reviewers", ["api_key_hash"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(64), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("industry_code", sa.String(16), nullable=False),
        sa.Column("requested_spend_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("applicant_name", sa.String(255), nullable=False),
        sa.Column("applicant_email", sa.String(255), nullable=False),
        sa.Column("applicant_dob", sa.String(10), nullable=True),
        sa.Column("mock_credit_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=_now),
        sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True),
    )
    op.create_index("ix_applications_registration_number", "applications", ["registration_number"])
    op.create_index("ix_applications_applicant_email", "applications", ["applicant_email"])
    op.create_index("ix_applications_status_submitted", "applications", ["status", "submitted_at"])

    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stage", sa.String(32), server_default="automated"),
        sa.Column("combined_risk_score", sa.Float(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("llm_recommendation", sa.String(16), nullable=True),
        sa.Column("llm_risk_score", sa.Float(), nullable=True),
        sa.Column("llm_rationale", sa.Text(), nullable=True),
        sa.Column("llm_top_concerns", sa.JSON(), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now),
    )
    op.create_index("ix_decisions_application_id", "decisions", ["application_id"])
    op.create_index("ix_decisions_outcome_created", "decisions", ["outcome", "created_at"])

    op.create_table(
        "rule_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_name", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
    )
    op.create_index("ix_rule_results_application_id", "rule_results", ["application_id"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            sa.Uuid(),
            sa.ForeignKey("reviewers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=_now),
        sa.Column("time_to_decision_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("ix_reviews_application_id", "reviews", ["application_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_entity", "audit_log", ["entity", "entity_id"])


def downgrade():
    op.drop_table("audit_log")
    op.drop_table("reviews")
    op.drop_table("rule_results")
    op.drop_table("decisions")
    op.drop_table("applications")
    op.drop_table("reviewers")
