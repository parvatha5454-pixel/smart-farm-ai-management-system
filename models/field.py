from datetime import datetime
from models import db


class Field(db.Model):
    __tablename__ = 'fields'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200))
    area = db.Column(db.Float, nullable=False, default=0.0)  # in acres
    soil_type = db.Column(db.String(50))
    irrigation_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    crops = db.relationship('Crop', backref='field', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Field {self.name}>'
