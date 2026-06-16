"""Server-rendered ops UI: the review queue and the metrics dashboard.

This is the trusted internal ops console. Review actions submitted here are
attributed to the seeded demo reviewer (resolved server-side from config), so the
demo works out of the box without the operator pasting an API key into the browser.
In a real deployment this would sit behind SSO.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from app.config import get_settings
from app.constants import ReviewAction
from app.extensions import db
from app.models import Reviewer
from app.repository.applications import get_application, get_queue
from app.repository.metrics import metrics_summary, outcome_breakdown, recent_decisions
from app.services.review_service import ReviewError, perform_review

bp = Blueprint("ui", __name__)


def _demo_reviewer() -> Reviewer | None:
    settings = get_settings()
    key_hash = Reviewer.hash_key(settings.demo_reviewer_api_key)
    return db.session.scalar(select(Reviewer).where(Reviewer.api_key_hash == key_hash))


@bp.get("/")
def index():
    return redirect(url_for("ui.dashboard"))


@bp.get("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        metrics=metrics_summary(),
        breakdown=outcome_breakdown(),
        recent=recent_decisions(8),
    )


@bp.get("/queue")
def queue():
    sort = request.args.get("sort", "risk")
    items = get_queue(limit=100, sort=sort)
    return render_template("queue.html", items=items, sort=sort, now=datetime.now(timezone.utc))


@bp.get("/applications/<application_id>")
def application_detail(application_id: str):
    application = get_application(application_id)
    if application is None:
        abort(404)
    return render_template("application.html", app_row=application)


@bp.post("/applications/<application_id>/review")
def ui_review(application_id: str):
    application = get_application(application_id)
    if application is None:
        abort(404)
    reviewer = _demo_reviewer()
    if reviewer is None:
        flash("No demo reviewer seeded — run scripts/seed.py first.", "error")
        return redirect(url_for("ui.queue"))

    action = ReviewAction.APPROVE if request.form.get("action") == "approve" else ReviewAction.DECLINE
    notes = request.form.get("notes") or None
    try:
        perform_review(application, reviewer, action, notes)
        flash(f"Application {action.value}d.", "success")
    except ReviewError as exc:
        flash(exc.message, "error")
    return redirect(url_for("ui.queue"))
