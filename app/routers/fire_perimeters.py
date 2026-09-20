import json
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.fire_perimeter import FirePerimeter
from app.schemas.fire_perimeter import (
    FirePerimeterCreate,
    FirePerimeterOut,
    FirePerimeterUpdate,
)

router = APIRouter(tags=["fire_perimeters"])

def _geojson_or_none(
    geojson_text: str | None,
) -> Any:
    if not geojson_text:
        return None

    return json.loads(geojson_text)

def _to_out(
    obj: FirePerimeter,
    geojson_text: str | None,
) -> dict:
    return {
        "id": obj.id,
        "source": obj.source,
        "event_id": obj.event_id,
        "name": obj.name,
        "geom_geojson": _geojson_or_none(
            geojson_text
        ),
    }

def _commit_or_500(db:Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Database operation failed",
        ) from exc

@router.post(
    "",
    response_model=FirePerimeterOut,
    status_code=status.HTTP_201_CREATED,
)

def create_fire_perimeter(
    payload: FirePerimeterCreate,
    db: Session = Depends(get_db),
):
    obj = FirePerimeter(
        source=payload.source,
        event_id=payload.event_id,
        name=payload.name,
        geom=geomWKTElement(
            payload.geom_wkt,
            srid=4326,
        ),
    )

    db.add(obj)
    _commit_or_500(db)
    db.refresh(obj)

    geom_geojson = (
        db.query(
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            )
        )
        .filter(FirePerimeter.id == obj.id)
        .scalar()
    )

    return _to_out(obj, geom_geojson)

@router.get(
    "",
    response_model=list[FirePerimeterOut],
)
def list_fire_perimeters(
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            FirePerimeter,
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            ).label("geom_geojson"),
        )
        .order_by(FirePerimeter.id.desc())
        .all()
    )

    return [
        _to_out(obj, geojson_text)
        for obj, geojson_text in rows
    ]

@router.get("/geojson")
def list_fire_perimeters_geojson(
    db: Session = Depends(get_db),
):
    rows=(
        db.query(
            FirePerimeter,
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            ).label("geom_geojson"),
        )
        .order_by(FirePerimeter.id.desc())
        .all()
    )

    feature = []

    for obj, geom_geojson in rows:
        features.append(
            {
                "type": "Feature",
                "id": obj.id,
                "geometry": _geojson_or_none(
                    geom_geojson
                ),
                "properties": {
                    "id": obj.id,
                    "source": obj.source,
                    "event_id": obj.event_id,
                    "name": obj.name,
                },
            }
        )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

@router.get(
    "/{fire_perimeter_id}",
    response_model=FirePerimeterOut,
)

def get_fire_perimeter(
    fire_perimeter_id: int,
    db: Session = Depends(get_db),
):
    row = (
        db.query(
            FirePerimeter,
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            ).label("geom_geojson"),
        )
        .filter(
            FirePerimeter.id == fire_perimeter_id
        )
        .first()
    )

    if not row:
        raise HTTPElement(
            status_code=404,
            detail="FirePerimeter not found",
        )

    obj, geojson_text = row
    return _to_out(obj, geojson_text)

@router.patch(
    "/{fire_perimeter_id}",
    response_model=FirePerimeterOut,
)

def update_fire_perimeter(
    fire_perimeter_id: int,
    payload: FirePerimeterUpdate,
    db: Session = Depends(get_db),
):
    obj = (
        db.query(FirePerimeter)
        .filter(
            FirePerimeter.id == fire_perimeter_id
        )
        .first()
    )

    if not obj:
        raise HTTPException(
            status_code=404,
            detail="FirePerimeter not found",
        )

    if payload.source is not None:
        obj.source = payload.source
    
    if payload.event_id is not None:
        obj.name = payload.name
    
    if payload.geom_wkt is not None:
        obj.geom = WKTElement(
            payload.geom_wkt,
            srid=4326,
        )

    _commit_or_500(db)
    db.refresh(obj)

    geom_geojson = (
        db.query(
            func.ST_AsGeoJSON(
                FirePerimeter.geom,
                6,
            )
        )
        .filter(FirePerimeter.id == obj.id)
        .scalar()
    )

    return _to_out(obj, geom_geojson)

@router.delete("/{fire_perimeter_id}")
def delete_fire_perimeter(
    fire_perimeter_id: int,
    db: Session = Depends(get_db),
):
    obj = (
        db.query(FirePerimeter)
        .filter(
            FirePerimeter.id == fire_perimeter_id
        )
        .first()
    )

    if not obj:
        raise HTTPException(
            status_code=404,
            detail="Fireperimeter not found",
        )

        db.delete(obj)
        _commit_or_500(db)

        return  {
            "deleted": True,
            "id": fire_perimeter_id,
        }