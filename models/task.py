from datetime import datetime
from models import db


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.title}>'
