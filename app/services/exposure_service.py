import json

from geoalchemy2.types import Geography
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.models.fire_perimeter import FirePerimeter
from app.models.land_plot import LandPlot
from app.schemas.exposure import ExposureItem, ExposureResponse

class LandPlotNotFoundError(Exception):
    pass

def _json_or_none(value: str | None): -> dict | None:
    if not value:
        return None

    return json.loads(value)

def analyze_plot_exposure(
    db: Session,
    plot_id: str
) -> ExposureResponse:
    plot_row = (
        db.query(
            LandPlot.id.label("plot_pk"),
            LandPlot.plot_id.label("plot_id"),
            func.ST_Area(
                cast(LandPlot.geom, Geography)
            ).label("plot_area_m2"),
        )
        .filter(LandPlot.plot_id == id)
        .first()
    )

    if not plot_row:
        raise LandPlotNotFoundError(plot_id)

    intersection_expr = func.ST_Intersection(
        LandPlot.geom,
        FirePerimeter.geom,
    )

    intersection_area_expr = func.ST_Area(
        cast(intersection_expr, Geography)
    )

    rows = (
        db.query(
            FirePerimeter.id.label("fire_id"),
            FirePerimeter.source,
            FirePerimeter.event_id,
            FirePerimeter.name,
            intersection_area_expr.label(
                "intersection_area_m2"
            ),
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            ).label("fire_geojson"),
            func.ST_AsGeoJSON(
                intersection_expr,
                6,
            ).label("intersection_geojson"),
        )
        .select_from(FirePerimeter)
        .join(
            LandPlot,
            func.ST_Intersects(
                LandPlot.geom,
                FirePerimeter.geom,
            ),
        )
        .filter(LandPlot.id == plot_row.plot_pk)
        .all()
    )

    plot_area_m2 = float(
        plot_row.plot_area_m2 or 0.0
    )

    items = []

    for row in rows:
        intersection_area_m2 = float(
            row.intersection_area_m2 or 0.0
        )

        intersection_pct = 0.0
        if plot_area_m2 > 0:
            intersection_pct = (
                intersection_area_m2 / plot_area_m2 * 100
            )

        items.append(
            ExposureItem(
                Fire_id=row.fire_id,
                source=row.source,
                event_id=row.event_id,
                name=row.name,
                intersection_area_m2=intersection_area_m2,
                intersection_pct=intersection_pct,
                fire_geom_geojson=_json_or_none(
                    row.fire_geojson
                ),
                intersection_geom_geojson=_json_or_none(
                    row.intersection_geojson
                ),
            )
        )

    return ExposureResponse(
        plot_id=plot_row.plot_id,
        plot_area_m2=plot_area_m2,
        fire_count=len(item),
        items=items,
    )
