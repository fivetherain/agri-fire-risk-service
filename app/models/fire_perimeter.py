from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from app.models.base import Base

class FirePerimeter(Base):
    __tablename__ = "fire_perimeters"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable = False) # data source
    event_id = Column(String, nullable = True, index = True)
    name = Column(String, nullable = True)
    geom = Column(Geometry('Polygon', srid = 4326, spatial_index = True), nullable = False)