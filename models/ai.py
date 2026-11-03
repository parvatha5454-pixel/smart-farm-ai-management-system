from datetime import datetime
from models import db


class AuditLog(db.Model):
    """Append-only record of AI tool calls, proposals and user decisions."""
    __tablename__ = 'ai_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True)
    user_name = db.Column(db.String(120))
    # tool_call, ai_proposed, user_approved, user_rejected, executed, failed, denied
    event = db.Column(db.String(40), nullable=False)
    tool = db.Column(db.String(60))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class ChatMessage(db.Model):
    __tablename__ = 'ai_chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PendingAction(db.Model):
    """A change proposed by the AI/planner. Nothing is saved until the owner approves."""
    __tablename__ = 'ai_pending_actions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    tool = db.Column(db.String(60), nullable=False)
    args_json = db.Column(db.Text, nullable=False)
    preview = db.Column(db.String(500), nullable=False)
    reason = db.Column(db.String(500))
    source = db.Column(db.String(20), default='copilot')  # copilot / planner
    # pending, approved, rejected, failed, superseded
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
