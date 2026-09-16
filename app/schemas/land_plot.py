# Pydantic schemas
from pydantic import BaseModel, Field
from typing import Optional, Any
from app.schemas.common import PolygonWKT

class LandPlotCreate(BaseModel):
    plot_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["BC_PLOT_0001"]
        )
    crop_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Wheat"]
        )
    area_ha: Optional[float] = Field(None, gt=0, examples=[12.5])

    # output polygon in WKT format
    geom_wkt: PolygonWKT= Field(
        ...,
        examples=["POLYGON((120.123456 30.123456, 120.123457 30.123457, 120.123458 30.123458, 120.123456 30.123456))"]
    )

class LandPlotUpdate(BaseModel):
    crop_type: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
    )
    area_ha: Optional[float] = Field(None, gt=0)
    geom_wkt: Optional[PolygonWKT] = None
class LandPlotOut(BaseModel):
    id: int
    plot_id: str
    crop_type: Optional[str] = None
    area_ha: Optional[float] = None

    # output to frontend in GeoJSON format
    geom_geojson: Any

    class Config:
        from_attributes = True