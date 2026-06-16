from __future__ import annotations

from pydantic import BaseModel, Field

from app.constants import ReviewAction


class ReviewCreate(BaseModel):
    """A reviewer's action on a needs_review application."""

    action: ReviewAction
    notes: str | None = Field(default=None, max_length=2000)
