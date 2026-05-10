from pydantic import BaseModel, Field
from typing import Optional, Any

class FirePerimeterCreate(BaseModel):
    source: str = Field(..., examples=["CNFDB", "CWFIS", "GA"])
    event_id: Optional[str] = Field(None, examples=["NFDB_2023_001"])
    name: Optional[str] = Field(None, examples=["kelowa Wildfire"])
    geom_wkt: str = Field(
        ...,
        examples=["POLYGON((120.123456 30.123456, 120.123457 30.123457, 120.123458 30.123458, 120.123456 30.123456))"]
    )

class FirePerimeterUpdate(BaseModel):
    source: Optional[str] = None
    event_id: Optional[str] = None
    name: Optional[str] = None
    geom_wkt: Optional[str] = None

class FirePerimeterOut(BaseModel):
    id: int
    source: str
    event_id: Optional[str] = None
    name: Optional[str] = None
    geom_geojson: Any
