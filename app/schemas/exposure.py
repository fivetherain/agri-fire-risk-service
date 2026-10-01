from typing import Literal

from pydantic import BaseModel

from app.schemas.geojson import GeoJSONGeometry

class ExposureItem(BaseModel):
    fire_id: int
    source: str
    event_id: str | None
    name: str | None
    intersection_area_m2: float
    intersection_pct: float
    fire_geom_geojson: GeoJSONGeometry | None
    intersection_geom_geojson: GeoJSONGeometry | None

class ExposureResponse(BaseModel):
    plot_id: str
    plot_area_m2: float
    fire_count: int
    items: list[ExposureItem]

class ExposureFeatureProperties(BaseModel):
    plot_id: str
    fire_id: int
    source: str
    event_id: str | None
    name: str | None
    intersection_area_m2: float
    intersection_pct: float

class ExposureGeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: int
    geometry: GeoJSONGeometry | None
    properties: ExposureFeatureProperties

class ExposureGeoJSONResponse(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    plot_id: str
    plot_area_m2: float
    fire_count: int
    feature: list[ExposureGeoJSONFeature]
    