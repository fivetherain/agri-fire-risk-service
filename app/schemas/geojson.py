from typing import Any, Literal

from pydantic import BaseModel

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any

class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int | None = None
    geometry: GeoJSONGeometry | None
    properties: dict[str, Any]

class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]