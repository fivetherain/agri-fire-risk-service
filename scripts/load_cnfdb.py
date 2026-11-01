import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from geoalchemy2.shape import from_shape
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.fire_perimeter import FirePerimeter


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Load cleaned CNFDB wildfire perimeters"
            "into PostGIS."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "data/processed/cnfdb_clean.gpkg"
        ),
        help="Path to the cleaned CNFDB GeoPackage."
    )

    parser.add_argument(
        "--replace-source",
        action="store_true",
        help=(
            "Delete existing rows for the input source"
            "before loading."
        ),
    )

    return parser.parse_args()

def required_text(
    value: Any,
    field_name: str,
) -> str:
    if pd.isna(value):
        raise ValueError(
            f"{field_name} is requied"
        )

    text = str(value).strip()

    if not text:
        raise ValueError(
            f"{field_name} is required"
        )

    return text

def optional_text(value: Any) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()

    return text or None

def optional_year(value: Any) -> int | None:
    if pd.isna(value):
        return None

    number = float(value)

    if not math.isfinite(number):
        raise ValueError("year is not finite")

    if not number.is_integer():
        raise ValueError("year is not integer")

    return int(number)

def required_area(value: Any) -> float:
    if pd.isna(value):
        raise ValueError("area_ha is required")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError("area_ha is not finite")

    if number <= 0:
        raise ValueError(
            "area_ha must be greater than zero"
        )

    return number

def read_input(
    input_path: Path,
) -> gpd.GeoDataFrame:
    if not input_path.exists():
        raise FireNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    frame = gpd.read_file(
        input_path,
        layer="fire_perimeters",
        engine="pyogrio",
    )

    required_columns = {
        "source",
        "event_id",
        "name",
        "year",
        "area_ha",
    }

    missing = required_columns - set(frame.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if frame.crs is None:
        raise ValueError(
            "Input dataset has no CRS"
        )

    if frame.crs.to_epsg() != 4326:
        raise ValueError(
            "Input dataset must use EPSG: 4326"
        )

    if frame.empty:
        raise ValueError(
            "Input dataset contains no rows"
        )

    return frame

def prepare_values(
    row: pd.Series,
    geometry_column: str,
) -> dict[str, Any]:
    geometry = row[geometry_column]

    if geometry is None:
        raise ValueError("geometry is null")

    if geometry.is_empty:
        raise ValueError("geometry is empty")

    if not geometry.is_valid:
        raise ValueError("geometry is invalid")

    if geometry.geom_type not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError(
            "geometry must be Polygon or MultiPolygon"
        )

    return {
        "source": required_text(
            row["source"],
            "source",
        ),
        "event_id": required_text(
            row["event_id"],
            "event_id",
        ),
         "name": optional_text(row["name"]),
        "year": optional_year(row["year"]),
        "area_ha": required_area(
            row["area_ha"]
        ),
        "geom": from_shape(
            geometry,
            srid=4326,
            extended=True,
        ),
    }

def find_existing(
    db: Session,
    source: str,
    event_id: str,
    geom_value,
):
    statement = select(
        FirePerimeter.name,
        FirePerimeter.year,
        FirePerimeter.area_ha,
        func.ST_Equals(
            FirePerimeter.geom,
            geom_value,
        ).label("same_geom"),
    ).where(
        FirePerimeter.source == source,
        FirePerimeter.event_id == event_id,
    )

    return db.execute(statement).one_or_none()

def same_float(
    existing: float | None,
    incoming: float | None,
) -> bool:
    if existing is None or incoming is None:
        return existing is incoming

    return math.isclose(
        float(existing),
        float(incoming),
        rel_tol=le-9,
        abs_tol=le-6,
    )

def is_unchanged(
    existing,
    values: dict[str, Any],
) -> bool:
    return (
        existing["name"] == value["name"]
        and existing["year"] == values["year"]
        and same_float(
            existing["area_ha"],
            values["area_ha"],
        )
        and bool(existing["same_geom"])
    )

def upsert_fire(db: Session, values: dict) -> None:
    base_statement = (
        insert(FirePerimeter)
        .values(**values)
    )

    statement = (
        base_statement.on_conflict_do_update(
            constraint=(
                "uq_fire_perimeters_"
                "source_event_id"
            ),
            set_={
                "name": (
                    base_statement.excluded.name
                ),
                "year": (
                    base_statement.excluded.year
                ),
                "area_ha": (
                    base_statement.excluded.area_ha
                ),
                "geom": (
                    base_statement.excluded.geom
                ),
                "ingested_at": func.now(),
            },
        )
    )

    db.execute(statement)

def load_frame(
    db: Session,
    frame: gpd.GeoDataFrame,
    replace_source: bool,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    prepared_rows = []
    seen_keys = set()
    rejected = 0
    rejection_reasons: dict[str, int] = {}

    geometry_column = frame.geometry.name

    for _, row in frame.iterrows():
        try:
            values = prepare_values(
                row,
                geometry_column,
            )

        except ValueError as exc:
            rejected += 1

            reason = str(exc)

            rejection_reasons[reason] = (
                rejection_reasons.get(reason, 0)
                + 1
            )

            continue

        business_key = (
            values["source"],
            values["event_id"],
        )

        if business_key in seen_keys:
            raise ValueError(
                "Input contains duplicatye business key:"
                f"{business_key}"
            )

        seen_keys.add(business_key)
        prepared_rows.append(values)

    if not prepared_rows:
        raise ValueError(
            "No valid rows are available for loading"
        )
        
    sources = {
        values["source"]
        for values in prepared_rows
    }

    if replace_source and rejected > 0:
        raise ValueError(
            "--replace-source refused because"
            f"{rejected} rows were rejected"
        )

    inserted = 0
    updated = 0
    skipped = 0
    deleted = 0

    try:
        if replace_source:
            source_name = next(iter(sources))

            result = db.execute(
                delete(FirePerimeter).where(
                    FirePerimeter.source
                    == source_name
                )
            )

            deleted = max(
                result.rowcount or 0,
                0,
            )

        for values in prepared_rows:
            existing = find_existing(
                db=db,
                source=values["source"],
                event_id=values["event_id"],
                geom_value=values["geom"],
            )

            if existing is None:
                upsert_fire(db, values)
                inserted += 1
                continue

            if is_unchanged(existing, values):
                skipped += 1
                continue

            upsert_fire(db, values)
            updated += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    duration_seconds = (
        time.perf_counter() - started_at 
    )

    return {
        "rows_read": len(frame),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "delected_before_reload": deleted,
        "duration_seconds": round(
            duration_seconds,
            3,
        ),
        "rejection_reasons": (
            rejection_reasons
        ),
    }

def main() -> None:
    args = parse_args()

    frame = read_input(args.input)

    with SessionLocal() as db:
        report = load_frame(
            db=db,
            frame=frame,
            replace_source=(
                args.replace_source
            ),
        )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()
