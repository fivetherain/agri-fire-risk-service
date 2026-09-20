
from typing import Annotated

from pydantic import AfterValidator
from shapely import from_wkt
from shapely.errors import GEOSException

def validate_polygon_wkt(value: str) -> str:
    candidate = value.strip()

    if not candidate:
        raise ValueError("geom_wkt must not be blank")

    try:
        geometry = from_wkt(candidate)
    except (GEOSException, TypeError) as exc:
        raise ValueError("geom_wkt must be valid WKT") from exc

    if geometry is None:
        raise ValueError("geom_wkt must be valid WKT,which cannot be None")
    
    if geometry.geom_type != "Polygon":
        raise ValueError("geom_wkt must be a Polygon")

    if geometry.is_empty:
        raise ValueError("geom_wkt cannot be empty")

    if not geometry.is_valid:
        raise ValueError("geom_wkt must contain a valid topologically polygon")

    min_x, min_y, max_x, max_y = geometry.bounds

    if min_x < -180 or max_x > 180:
        raise ValueError("geom_wkt longitude must be between -180 and 180")

    if min_y < -90 or max_y > 90:
        raise ValueError("geom_wkt must be between -90 and 90")

    return geometry.wkt

PolygonWKT = Annotated[str, AfterValidator(validate_polygon_wkt)]
