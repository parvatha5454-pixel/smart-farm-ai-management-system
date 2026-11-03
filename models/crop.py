from datetime import datetime
from models import db


class Crop(db.Model):
    __tablename__ = 'crops'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
    planting_date = db.Column(db.Date, nullable=False)
    expected_harvest_date = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default='Planned')
    # Planned, Growing, Ready for Harvest, Harvested
    quantity = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Crop {self.name}>'
