from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.models.base import Base

class FirePerimeter(Base):
    __tablename__ = "fire_perimeters"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "event_id",
            name="uq_fire_perimeters_source_event_id",
        ),
        CheckConstraint(
            "ST_GeometryType(geom) IN "
            "('ST_Polygon', 'ST_MultiPolygon')",
            name="ck_fire_perimeters_polygonal",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    event_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    area_ha = Column(Float, nullable=True)
    ingested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    geom = Column(
        Geometry(
            "GEOMETRY",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )