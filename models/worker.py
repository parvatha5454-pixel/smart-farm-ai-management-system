from datetime import datetime
from models import db


class Worker(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    role = db.Column(db.String(50))  # job role e.g. "Field Laborer", "Irrigation Specialist"
    joining_date = db.Column(db.Date)
    # Optional link to a login account if the worker also has system access
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_account = db.relationship('User', backref='worker_profile', lazy=True)
    tasks = db.relationship('Task', backref='worker', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Worker {self.name}>'
