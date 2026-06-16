"""Reusable column helpers for models."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[dt.datetime]:
    # Server-side default so timestamps are consistent regardless of which
    # process inserts the row.
    return mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
