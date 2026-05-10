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
def exposure_for_plot(plot_id: int, db: Session = Depends(get_db)):
    """
    Analyze wildfire exposure for one land plot.

    Business meaning:
    - Input: one agricultural land plot ID
    - Output: wildfire perimeters that intersect with this land plot
    - Calculate:
      1. plot area in square meters
      2. intersection area in square meters
      3. exposure percentage
    """

    # 1. Check whether the land plot exists.
    plot = db.query(LandPlot).filter(LandPlot.id == plot_id).first()

    if not plot:
        raise HTTPException(status_code=404, detail="LandPlot not found")

    # 2. Calculate the land plot area in square meters.
    #
    # - LandPlot.geom is a SQLAlchemy column expression.
    # - plot.geom is a loaded Python-side WKBElement object.
    # - For PostGIS calculations, use LandPlot.geom instead of plot.geom.
    plot_area_m2 = (
        db.query(func.ST_Area(cast(LandPlot.geom, Geography)))
        .filter(LandPlot.id == plot_id)
        .scalar()
    )

    # 3. Query all wildfire perimeters that intersect with this land plot.
    intersecting_fires = (
        db.query(FirePerimeter)
        .join(
            LandPlot,
            func.ST_Intersects(LandPlot.geom, FirePerimeter.geom),
        )
        .filter(LandPlot.id == plot_id)
        .all()
    )

    results = []

    # 4. Calculate intersection area and exposure percentage for each fire perimeter.
    for fire in intersecting_fires:
        intersection_area_m2 = (
            db.query(
                func.ST_Area(
                    cast(
                        func.ST_Intersection(
                            LandPlot.geom,
                            FirePerimeter.geom,
                        ),
                        Geography,
                    )
                )
            )
            .filter(
                LandPlot.id == plot_id,
                FirePerimeter.id == fire.id,
            )
            .scalar()
        )

        # Convert the full wildfire perimeter geometry to GeoJSON.
        fire_geojson = (
            db.query(func.ST_AsGeoJSON(FirePerimeter.geom, 6))
            .filter(FirePerimeter.id == fire.id)
            .scalar()
        )

        # Convert the intersection geometry to GeoJSON.
        #
        # This represents the actual overlapping area between
        # the land plot and the wildfire perimeter.
        intersection_geojson = (
            db.query(
                func.ST_AsGeoJSON(
                    func.ST_Intersection(
                        LandPlot.geom,
                        FirePerimeter.geom,
                    ),
                    6,
                )
            )
            .filter(
                LandPlot.id == plot_id,
                FirePerimeter.id == fire.id,
            )
            .scalar()
        )

        exposure_pct = 0.0

        # Avoid division by zero when plot area is empty or invalid.
        if plot_area_m2 and plot_area_m2 > 0:
            exposure_pct = float((intersection_area_m2 or 0.0) / plot_area_m2 * 100)

        results.append(
            {
                "fire_id": fire.id,
                "source": fire.source,
                "event_id": fire.event_id,
                "name": fire.name,
                "intersection_area_m2": float(intersection_area_m2 or 0.0),
                "intersection_pct": exposure_pct,
                "fire_geom_geojson": json.loads(fire_geojson) if fire_geojson else None,
                "intersection_geom_geojson": (
                    json.loads(intersection_geojson) if intersection_geojson else None
                ),
            }
        )

    return {
        "plot_id": plot_id,
        "plot_area_m2": float(plot_area_m2 or 0.0),
        "fire_count": len(results),
        "items": results,
    }