from datetime import datetime
from models import db


class IrrigationLog(db.Model):
    """A manual irrigation record or plan. No hardware is controlled; this is a logbook."""
    __tablename__ = 'irrigation_logs'

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False, index=True)
    scheduled_for = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer)
    water_liters = db.Column(db.Float)          # optional, entered by the user (not measured)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), nullable=False, default='Planned')  # Planned, Done, Skipped
    notes = db.Column(db.String(300))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    field = db.relationship('Field', backref=db.backref('irrigation_logs', lazy=True, cascade='all, delete-orphan'))


class CropObservation(db.Model):
    """A human-entered crop health observation. Not a diagnosis."""
    __tablename__ = 'crop_observations'

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False, index=True)
    observed_on = db.Column(db.Date, nullable=False)
    health_status = db.Column(db.String(30), nullable=False, default='Healthy')  # Healthy, Needs attention, Stressed
    growth_stage = db.Column(db.String(40))
    category = db.Column(db.String(30), default='General')  # General, Pest, Disease, Nutrient, Water
    notes = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    crop = db.relationship('Crop', backref=db.backref('observations', lazy=True, cascade='all, delete-orphan'))
