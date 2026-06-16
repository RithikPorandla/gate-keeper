from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models import AuditLog


def write_audit(
    entity: str,
    entity_id: str,
    actor: str,
    action: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a row to the immutable audit log. Caller commits."""
    db.session.add(
        AuditLog(
            entity=entity,
            entity_id=str(entity_id),
            actor=actor,
            action=action,
            payload_json=payload or {},
        )
    )
