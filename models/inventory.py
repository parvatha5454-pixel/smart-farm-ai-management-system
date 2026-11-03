from datetime import datetime
from models import db


class InventoryItem(db.Model):
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50))  # Seeds, Fertilizers, Pesticides, Tools, Equipment
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20))  # kg, liters, units, etc.
    minimum_stock_level = db.Column(db.Float, default=0.0)
    purchase_date = db.Column(db.Date)
    supplier = db.Column(db.String(120))
    cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_low_stock(self):
        return self.quantity < self.minimum_stock_level

    def __repr__(self):
        return f'<InventoryItem {self.name}>'
