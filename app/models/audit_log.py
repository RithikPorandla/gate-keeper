from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import uuid_pk


class AuditLog(db.Model):
    """Append-only audit trail.

    Every meaningful state change (submission, decision, human review) writes a row
    here. Rows are never updated or deleted. created_at is indexed so the table can
    be range-partitioned by time once it grows — see docs/ARCHITECTURE.md.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    entity: Mapped[str] = mapped_column(String(64))  # e.g. "application"
    entity_id: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128))  # "system", reviewer email, etc.
    action: Mapped[str] = mapped_column(String(64))  # "submitted", "decided", "reviewed"
    payload_json: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (Index("ix_audit_entity", "entity", "entity_id"),)
