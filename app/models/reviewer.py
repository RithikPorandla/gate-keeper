from __future__ import annotations

import datetime as dt
import hashlib
import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.mixins import uuid_pk


class Reviewer(db.Model):
    """An ops user who can act on the review queue.

    Authentication is via an API key; only the SHA-256 hash is stored.
    """

    __tablename__ = "reviewers"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {"id": str(self.id), "name": self.name, "email": self.email}
