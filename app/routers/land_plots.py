# app/routers/land_plots.py
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DBAPIError

from geoalchemy2.elements import WKTElement

from app.db.deps import get_db
from app.models.land_plot import LandPlot
from app.schemas.land_plot import LandPlotCreate, LandPlotOut, LandPlotUpdate

router = APIRouter(tags=["land_plots"])


def _geojson_or_none(geojson_text: str | None) -> Any:
    """ST_AsGeoJSON returns a JSON string; convert to dict (or None)."""
    if not geojson_text:
        return None
    return json.loads(geojson_text)


def _to_out(obj: LandPlot, geojson_text: str | None) -> dict:
    return {
        "id": obj.id,
        "plot_id": obj.plot_id,
        "crop_type": obj.crop_type,
        "area_ha": obj.area_ha,
        "geom_geojson": _geojson_or_none(geojson_text),
    }


@router.post("", response_model=LandPlotOut, status_code=status.HTTP_201_CREATED)
def create_land_plot(payload: LandPlotCreate, db: Session = Depends(get_db)):
    # WKT -> geometry(SRID=4326)
    geom = WKTElement(payload.geom_wkt, srid=4326)

    obj = LandPlot(
        plot_id=payload.plot_id,
        crop_type=payload.crop_type,
        area_ha=payload.area_ha,
        geom=geom,
    )

    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="plot_id already exists")
    except DBAPIError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"DB error / invalid geometry: {str(e.orig)}")

    geojson_text = db.query(func.ST_AsGeoJSON(obj.geom, 6)).scalar()
    return _to_out(obj, geojson_text)


@router.get("", response_model=list[LandPlotOut])
def list_land_plots(db: Session = Depends(get_db)):
    # avoid N+1: fetch LandPlot + GeoJSON in one query
    rows = (
        db.query(
            LandPlot,
            func.ST_AsGeoJSON(LandPlot.geom, 6).label("geom_geojson"),
        )
        .order_by(LandPlot.id.desc())
        .all()
    )
    return [_to_out(obj, geojson_text) for (obj, geojson_text) in rows]


@router.get("/geojson")
def list_land_plots_geojson(db: Session = Depends(get_db)):
    rows = (
        db.query(
            LandPlot,
            func.ST_AsGeoJSON(LandPlot.geom, 6).label("geom_geojson"),
        )
        .order_by(LandPlot.id.desc())
        .all()
    )

    features = []
    for obj,geom_geojson in rows:
        features.append({
            "type": "Feature",
            "id": obj.id,
            "geometry": json.loads(geom_geojson) if geom_geojson else None,
            "properties": {
                "id": obj.id,
                "plot_id": obj.plot_id,
                "crop_type": obj.crop_type,
                "area_ha": obj.area_ha,
            },
        })
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }

@router.get("/{land_plot_id}", response_model=LandPlotOut)
def get_land_plot(land_plot_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(
            LandPlot,
            func.ST_AsGeoJSON(LandPlot.geom, 6).label("geom_geojson"),
        )
        .filter(LandPlot.id == land_plot_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="LandPlot not found")

    obj, geojson_text = row
    return _to_out(obj, geojson_text)


@router.patch("/{land_plot_id}", response_model=LandPlotOut)
def update_land_plot(land_plot_id: int, payload: LandPlotUpdate, db: Session = Depends(get_db)):
    obj = db.query(LandPlot).filter(LandPlot.id == land_plot_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="LandPlot not found")

    if payload.crop_type is not None:
        obj.crop_type = payload.crop_type
    if payload.area_ha is not None:
        obj.area_ha = payload.area_ha
    if payload.geom_wkt is not None:
        obj.geom = WKTElement(payload.geom_wkt, srid=4326)

    try:
        db.commit()
        db.refresh(obj)
    except DBAPIError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"DB error / invalid geometry: {str(e.orig)}")

    geojson_text = db.query(func.ST_AsGeoJSON(obj.geom, 6)).scalar()
    return _to_out(obj, geojson_text)


@router.delete("/{land_plot_id}")
def delete_land_plot(land_plot_id: int, db: Session = Depends(get_db)):
    obj = db.query(LandPlot).filter(LandPlot.id == land_plot_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="LandPlot not found")

    db.delete(obj)
    db.commit()
    return {"deleted": True, "id": land_plot_id}