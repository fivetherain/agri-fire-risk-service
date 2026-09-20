import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, cast
from sqlalchemy.orm import Session
from geoalchemy2.types import Geography

from app.db.deps import get_db
from app.models.land_plot import LandPlot
from app.models.fire_perimeter import FirePerimeter


router = APIRouter(tags=["exposure"])


@router.get("/plots/{plot_id}")
def exposure_for_plot(plot_id: str, db: Session = Depends(get_db)):
    """
    Analyze wildfire exposure for one land plot.

    This endpoint returns every intersecting fire perimeter,
    its intersection area, and its exposure percentage.
    """

    # Look up by business plot_id (string), not DB primary key.
    plot = db.query(LandPlot).filter(LandPlot.plot_id == plot_id).first()

    if not plot:
        raise HTTPException(status_code=404, detail="LandPlot not found")

    # Calculate the land plot area in square meters.
    #
    # - LandPlot.geom is a SQLAlchemy column expression.
    # - plot.geom is a loaded Python-side WKBElement object.
    # - For PostGIS calculations, use LandPlot.geom instead of plot.geom.
    plot_area_m2 = (
        db.query(func.ST_Area(cast(LandPlot.geom, Geography)))
        .filter(LandPlot.id == plot.id)
        .scalar()
    )

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
            FirePerimeter.source.label("source"),
            FirePerimeter.event_id.label("event_id"),
            FirePerimeter.name.label("name"),
            intersection_area_expr.label(
                "intersection_area_m2"
            ),
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
        .filter(LandPlot.id == plot.id)
        .all()
    )

    results = []

    for row in rows:
        intersection_area_m2 = float(
            row.intersection_area_m2 or 0.0
        )

        exposure_pct = 0.0

        if plot_area_m2 and plot_area_m2 > 0:
            exposure_pct = (
                intersection_area_m2
                / float(plot_area_m2)
                * 100
            )

        results.append(
            {
                "fire_id": row.fire_id,
                "source": row.source,
                "event_id": row.event_id,
                "name": row.name,
                "intersection_area_m2": (
                    intersection_area_m2
                ),
                "intersection_pct": exposure_pct,
                "fire_geom_geojson": (
                    json.loads(row.fire_geojson)
                    if row.fire_geojson
                    else None
                ),
                "intersection_geom_geojson": (
                    json.loads(
                        row.intersection_geojson
                    )
                    if row.intersection_geojson
                    else None
                ),
            }
        )
    return {
        "plot_id": plot.plot_id,
        "plot_area_m2": float(
            plot_area_m2 or 0.0
        ),
        "fire_count": len(results),
        "items": results,
    }


@router.get("/plots/{plot_id}/geojson")
def exposure_for_plot_geojson(
    plot_id: str,
    db: Session = Depends(get_db),
):
    # 1. Look up by business plot_id (string), not DB primary key.
    plot = (
        db.query(LandPlot).filter(LandPlot.plot_id == plot_id)
        .first()
    )

    if not plot:
        raise HTTPException(
            status_code=404,
            detail="LandPlot not found",
        )

    # 2. Calculate the complete land plot area in square meters.
    plot_area_m2 = (
        db.query(
            func.ST_Area(
                cast(LandPlot.geom, Geography)
            )
        )
        .filter(LandPlot.id == plot.id)
        .scalar()
    )

    # 3. Fetch every intersecting fire and its overlap geometry.
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
            FirePerimeter.source.label("source"),
            FirePerimeter.event_id.label("event_id"),
            FirePerimeter.name.label("name"),
            intersection_area_expr.label(
                "intersection_area_m2"
            ),
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
        .filter(LandPlot.id == plot.id)
        .all()
    )

    # 4. Convert the SQL rows into GeoJSON Features.
    features = []

    for row in rows:
        intersection_area_m2 = float(
            row.intersection_area_m2 or 0.0
        )

        exposure_pct = 0.0

        if plot_area_m2 and plot_area_m2 > 0:
            exposure_pct = (
                intersection_area_m2 / float(plot_area_m2) * 100
            )

        features.append(
            {
                "type": "Feature",
                "id": row.fire_id,
                "geometry": (
                    json.loads(row.intersection_geojson)
                    if row.intersection_geojson
                    else None
                ),
                "properties": {
                    "plot_id": plot.plot_id,
                    "fire_id": row.fire_id,
                    "source": row.source,
                    "event_id": row.event_id,
                    "name": row.name,
                    "intersection_area_m2": (
                        intersection_area_m2
                    ),
                    "intersection_pct": exposure_pct,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "plot_id": plot.plot_id,
        "plot_area_m2": float(plot_area_m2 or 0.0),
        "fire_count": len(features),
        "features": features,
    }
