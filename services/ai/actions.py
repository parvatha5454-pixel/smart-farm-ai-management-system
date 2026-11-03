"""Pending-action lifecycle: propose -> (user) confirm/reject -> execute. Plus audit logging."""
import json
from datetime import datetime

from models import db
from models.ai import AuditLog, PendingAction
from services.ai.tools import prepare_call, run_tool
from services.ai.validation import ToolError

MAX_PENDING_PER_USER = 25


def log_audit(ctx, event, tool=None, details=None):
    text = details if isinstance(details, str) else json.dumps(details or {}, default=str)
    db.session.add(AuditLog(user_id=getattr(ctx, "id", None), user_name=getattr(ctx, "name", ""),
                            event=event, tool=tool, details=text[:1000]))


def serialize(a):
    return {"id": a.id, "tool": a.tool, "preview": a.preview, "reason": a.reason or "",
            "status": a.status, "source": a.source}


def propose_action(ctx, tool_name, args, reason="", source="copilot"):
    """Validate and store a proposal. Does NOT change farm data."""
    tool, cleaned = prepare_call(tool_name, args, ctx)
    if not tool.writes:
        raise ToolError("Only data-changing tools need a proposal.")
    pending_count = PendingAction.query.filter_by(user_id=ctx.id, status="pending").count()
    if pending_count >= MAX_PENDING_PER_USER:
        raise ToolError("Too many unreviewed proposals. Please approve or reject some first.")
    action = PendingAction(user_id=ctx.id, tool=tool.name, args_json=json.dumps(cleaned),
                           preview=tool.preview(cleaned)[:500], reason=(reason or "")[:500],
                           source=source, status="pending")
    db.session.add(action)
    log_audit(ctx, "ai_proposed", tool.name, cleaned)
    db.session.commit()
    return action


def _load_owned_pending(action_id, ctx):
    action = db.session.get(PendingAction, action_id)
    if action is None or action.user_id != ctx.id:
        raise ToolError("Proposal not found.", "not_found")
    if action.status != "pending":
        raise ToolError("This proposal was already %s." % action.status, "already_resolved")
    return action


def confirm_action(action_id, ctx):
    """Re-checks permission and re-validates inputs on the server before executing."""
    action = _load_owned_pending(action_id, ctx)
    try:
        args = json.loads(action.args_json)
        run_tool(action.tool, args, ctx, confirmed=True)  # permission + validation happen again here
        db.session.flush()
    except ToolError as e:
        db.session.rollback()
        action = db.session.get(PendingAction, action_id)
        action.status = "failed"
        action.result = e.message[:500]
        action.resolved_at = datetime.utcnow()
        log_audit(ctx, "denied" if e.code == "forbidden" else "failed", action.tool, e.message)
        db.session.commit()
        raise
    action.status = "approved"
    action.result = "Saved."
    action.resolved_at = datetime.utcnow()
    log_audit(ctx, "user_approved", action.tool, {"action_id": action.id})
    log_audit(ctx, "executed", action.tool, json.loads(action.args_json))
    db.session.commit()
    return serialize(action)


def reject_action(action_id, ctx):
    action = _load_owned_pending(action_id, ctx)
    action.status = "rejected"
    action.resolved_at = datetime.utcnow()
    log_audit(ctx, "user_rejected", action.tool, {"action_id": action.id})
    db.session.commit()
    return serialize(action)


def supersede_planner_actions(ctx):
    rows = PendingAction.query.filter_by(user_id=ctx.id, source="planner", status="pending").all()
    for a in rows:
        a.status = "superseded"
        a.resolved_at = datetime.utcnow()
    db.session.commit()
