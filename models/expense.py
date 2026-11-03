from datetime import datetime
from models import db


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    # Seeds, Fertilizer, Labour, Equipment, Irrigation, Transportation, Other
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(250))
    payment_method = db.Column(db.String(50))  # Cash, Card, UPI, Bank Transfer, Other
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Expense {self.category}: {self.amount}>'
