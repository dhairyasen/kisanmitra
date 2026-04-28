"""
MODULE — Database Schemas
SQLAlchemy ORM models for KisanMitra database.
"""

import sys
sys.path.insert(0, '.')

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text
from api.database import Base


def generate_uuid():
    return str(uuid.uuid4())[:8]


class Farmer(Base):
    """Farmer registration table."""
    __tablename__ = "farmers"

    farmer_id        = Column(String, primary_key=True, default=generate_uuid)
    name             = Column(String(100), nullable=False)
    phone            = Column(String(15), nullable=False, unique=True)
    whatsapp         = Column(Boolean, default=True)
    language         = Column(String(5), default="hi")
    lat              = Column(Float, nullable=False)
    lon              = Column(Float, nullable=False)
    district         = Column(String(100), nullable=False)
    state            = Column(String(100), nullable=False)
    crop             = Column(String(50), nullable=False)
    growth_stage     = Column(String(50), nullable=False)
    field_area_acres = Column(Float, default=1.0)
    soil_type        = Column(String(50), default="loamy")
    created_at       = Column(DateTime, default=datetime.utcnow)
    last_alert_at    = Column(DateTime, nullable=True)
    notes            = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "farmer_id":        self.farmer_id,
            "name":             self.name,
            "phone":            self.phone,
            "whatsapp":         self.whatsapp,
            "language":         self.language,
            "lat":              self.lat,
            "lon":              self.lon,
            "district":         self.district,
            "state":            self.state,
            "crop":             self.crop,
            "growth_stage":     self.growth_stage,
            "field_area_acres": self.field_area_acres,
            "soil_type":        self.soil_type,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "last_alert_at":    self.last_alert_at.isoformat() if self.last_alert_at else None,
        }