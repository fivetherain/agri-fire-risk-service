from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from app.models.base import Base

class LandPlot(Base):
    __tablename__ = 'land_plots'
    id = Column(Integer, primary_key = True, index = True)
    plot_id = Column(String, unique = True, nullable = False, index = True)
    crop_type = Column(String, nullable = True)
    area_ha = Column(Float, nullable = True)
    geom = Column(Geometry("Polygon", srid=4326, spatial_index=True), nullable=False) # generate the polygon type and store it in the database;its geographic coordinate system is wsg84