from sqlalchemy import func, cast
from geoalchemy2.types import Geography

from app.db.deps import get_db
from app.models.land_plot import LandPlot
from app.models.fire_perimeter import FirePerimeter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.exposure import (
    ExposureFeatureProperties,
    ExposureGeoJSONFeature,
    ExposureGeoJSONResponse,
    ExposureResponse,
)
from app.services.exposure_service import (
    LandPlotNotFoundError,
    analyze_plot_exposure,
)


router = APIRouter(tags=["exposure"])

def _analyze_or_404(
    db: Session,
    plot_id: str,
) -> ExposureResponse:
    try:
        return analyze_plot_exposure(db, plot_id)
    except LandPlotNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="LandPlot not found",
        ) from exc


@router.get("/plots/{plot_id}")
def exposure_for_plot(plot_id: str, db: Session = Depends(get_db)):
    """
    Analyze wildfire exposure for one land plot.

    This endpoint returns every intersecting fire perimeter,
    its intersection area, and its exposure percentage.
    """
    return _analyze_or_404(db, plot_id)


@router.get("/plots/{plot_id}/geojson")
def exposure_for_plot_geojson(
    plot_id: str,
    db: Session = Depends(get_db),
):
    analysis = _analyze_or_404(db, plot_id)

    feature = [
        ExposureGeoJSONFeature(
            id=item.fire_id,
            geometry=item.intersection_geom_geojson,
            properties=ExposureFeatureProperties(
                plot_id=analysis.plot_id,
                fire_id=item.fire_id,
                source=item.source,
                event_id=item.event_id,
                name=item.name,
                intersection_area_m2=(
                    item.intersection_area_m2
                ),
                intersection_pct=(
                    item.intersection_pct
                ),
            ),
        )
        for item in analysis.items
    ]

    return ExposureGeoJSONResponse(
        plot_id=analysis.plot_id,
        plot_area_m2=analysis.plot_area_m2,
        fire_count=len(features),
        features=features,
    )
