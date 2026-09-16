from pydantic import BaseModel, Field
from typing import Optional, Any
from app.schemas.common import PolygonWKT

class FirePerimeterCreate(BaseModel):
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["CNFDB", "CWFIS", "GA"]
        )
    event_id: Optional[str] = Field(
        None,
        examples=["NFDB_2023_001"],
        min_length=1,
        max_length=100,
        )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        examples=["kelowa Wildfire"]
        )
    geom_wkt: PolygonWKT = Field(
        ...,
        examples=["POLYGON((120.123456 30.123456, 120.123457 30.123457, 120.123458 30.123458, 120.123456 30.123456))"]
    )

class FirePerimeterUpdate(BaseModel):
    source: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
    )
    event_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
    )
    geom_wkt: Optional[PolygonWKT] = None

class FirePerimeterOut(BaseModel):
    id: int
    source: str
    event_id: Optional[str] = None
    name: Optional[str] = None
    geom_geojson: Any
