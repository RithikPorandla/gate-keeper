"""Shared enumerations used across models, schemas, rules, and the decision policy."""
from __future__ import annotations

import enum


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    NEEDS_REVIEW = "needs_review"


class Outcome(str, enum.Enum):
    APPROVED = "approved"
    DECLINED = "declined"
    NEEDS_REVIEW = "needs_review"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(str, enum.Enum):
    APPROVE = "approve"
    DECLINE = "decline"
    REVIEW = "review"


class ReviewAction(str, enum.Enum):
    APPROVE = "approve"
    DECLINE = "decline"


# Numeric weight per severity, used by the decision policy to fold rule results
# into the combined risk score.
SEVERITY_WEIGHT: dict[str, int] = {
    Severity.LOW.value: 5,
    Severity.MEDIUM.value: 20,
    Severity.HIGH.value: 45,
    Severity.CRITICAL.value: 100,
}
