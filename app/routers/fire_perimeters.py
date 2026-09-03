import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.elements import WKTElement

from app.db.deps import get_db
from app.models.fire_perimeter import FirePerimeter
from app.schemas.fire_perimeter import FirePerimeterCreate, FirePerimeterOut, FirePerimeterUpdate

router = APIRouter(tags=["fire_perimeters"])

@router.post("", response_model=FirePerimeterOut)
def create_fire_perimeter(payload: FirePerimeterCreate, db: Session = Depends(get_db)):
    geom = WKTElement(payload.geom_wkt, srid=4326)

    obj = FirePerimeter(
        source=payload.source,
        event_id=payload.event_id,
        name=payload.name,
        geom=geom,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    geom_geojson = db.query(func.ST_AsGeoJSON(obj.geom, 6)).scalar()
    return {
        "id": obj.id,
        "source": obj.source,
        "event_id": obj.event_id,
        "name": obj.name,
        "geom_geojson": json.loads(geom_geojson) if geom_geojson else None,
    }

@router.get("", response_model=list[FirePerimeterOut])
def list_fire_perimeters(db: Session = Depends(get_db)):
    rows = db.query(FirePerimeter).order_by(FirePerimeter.id.desc()).all()
    out = []
    for r in rows:
        geom_geojson = db.query(func.ST_AsGeoJSON(r.geom, 6)).scalar()
        out.append({
            "id": r.id,
            "source": r.source,
            "event_id": r.event_id,
            "name": r.name,
            "geom_geojson": json.loads(geom_geojson) if geom_geojson else None,
        })
    return out

@router.get("/geojson")
def list_fire_perimeters_geojson(db: Session = Depends(get_db)):
    rows = (
        db.query(
            FirePerimeter,
            func.ST_AsGeoJSON(FirePerimeter.geom, 6).label("geom_geojson"),
        )
        .order_by(FirePerimeter.id.desc())
        .all()
    )

    features = []
    for obj, geom_geojson in rows:
        features.append({
            "type": "Feature",
            "id": obj.id,
            "geometry": json.loads(geom_geojson) if geom_geojson else None,
            "properties": {
                "id": obj.id,
                "source": obj.source,
                "event_id": obj.event_id,
                "name": obj.name,
            },
        })
    return {
        "type": "FeatureCollection",
        "features": features,
    }

@router.get("/{fire_perimeter_id}", response_model=FirePerimeterOut)
def get_fire_perimeter(fire_perimeter_id: int, db: Session = Depends(get_db)):
    obj = db.query(FirePerimeter).filter(FirePerimeter.id == fire_perimeter_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail = "FirePerimeter not found")

    geom_geojson = db.query(func.ST_AsGeoJSON(obj.geom, 6)).scalar()
    return {
        "id": obj.id,
        "source": obj.source,
        "event_id": obj.event_id,
        "name": obj.name,
        "geom_geojson": json.loads(geom_geojson) if geom_geojson else None,
    }

@router.patch("/{fire_perimeter_id}", response_model=FirePerimeterOut)
def update_fire_perimeter(fire_perimeter_id: int, payload: FirePerimeterUpdate, db: Session = Depends(get_db)):
    obj = db.query(FirePerimeter).filter(FirePerimeter.id == fire_perimeter_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail = "FirePerimetr not found")

    if payload.source is not None:
        obj.source = payload.source
    if payload.event_id is not None:
        obj.event_id = payload.event_id
    if payload.name is not None:
        obj.name = payload.name
    if payload.geom_wkt is not None:
        obj.geom = WKTElement(payload.geom_wkt, srid=4326)
    
    db.commit()
    db.refresh(obj)

    geom_geojson = db.query(func.ST_AsGeoJSON(obj.geom, 6)).scalar()
    return {
        "id": obj.id,
        "source": obj.source,
        "event_id": obj.event_id,
        "name": obj.name,
        "geom_geojson": json.loads(geom_geojson) if geom_geojson else None,
    }

@router.delete("/{perimeter_id}")
def delete_fire_perimeter(fire_perimeter_id: int, db: Session = Depends(get_db)):
    obj = db.query(FirePerimeter).filter(FirePerimeter.id == fire_perimeter_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail = "FirePerimeter not found")
    db.delete(obj)
    db.commit()
    return {"deleted": True, "id": perimeter_id}
