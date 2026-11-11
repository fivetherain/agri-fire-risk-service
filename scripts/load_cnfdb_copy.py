import argparse
import csv
import json
import time
from io import StringIO
from pathlib import Path
from typing import Any

import geopandas as gpd
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.fire_perimeter import FirePerimeter
from scripts.load_cnfdb import (
    prepare_values,
    read_input,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Load cleaned CNFDB data with "
            "PostgreSQL COPY and a staging table."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            data/processed/cnfdb_clean.pgkg
        ),
    )

    parser.add_argument(
        "--replace_source",
        action="store_true",
    )

     parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "docs/performance/"
            "day18_copy_report.json"
        ),
    )

    return parser.parse_args()

def prepare_copy_rows(
    frame: gpd.GeoDataFrame,
) -> tuple[
    list[tuple[Any, ...]],
    int,
    dict[str, int],
]:
    rows = []
    seen_keys = set()
    rejected = 0
    rejection_reasons = dict[str, int] = {}

    geometry_column = frame.geometry.name

    for _, row in frame.iterrows():
        try:
            values = prepared_values(
                row,
                geometry_column,
            )
        except ValueError as exc:
            rejected += 1
            reason = str[exc]

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
                "Input contains duplicate business key: "
                f"{business_key}"
            )

        seen_keys.add(business_key)

        geometry = row[geometry_column]

        rows.append(
            (
                values["source"],
                values["event_id"],
                values["name"],
                values["year"],
                values["area_ha"],
                (
                    "SRID=4326;"
                    f"{geometry.wkt}"
                ),
            )
        )
    
    return (
        rows,
        rejected,
        rejection_reasons,
    )

def create_staging_table(
    db: Session,
) -> None:
    db.execute(
        text(
            """
            CREATE TEMP TABLE
                staging_fire_perimeter (
                    source TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    name TEXT,
                    year INTEGER,
                    area_ha DOUBLE PRECISION NOT NULL,
                    geom_ewkt TEXT NOT NULL,
                    PRIMARY KEY (
                        source,
                        event_id
                    )
                )
            ON COMMIT DROP
            """
        )
    )

def copy_to_staging(
    db: Session,
    rows: list[tuple[Any, ...]],
) -> None:
    buffer = StringIO()

    writer = csv.writer(
        buffer,
        lineterminator="\n",
    )

    write.writerows(rows)
    buffer.seek(0)

    driver_connection = (
        db.connection()
        .connection
        .driver_connection
    )

    with driver_connection.cursor() as cursor:
        cursor.copy_expert(
            """
                COPY staging_fire_perimeters (
                    source,
                    event_id,
                    name,
                    year,
                    area_ha,
                    geom_ewkt
                )
                FROM STDIN
                WITH (
                    FORMAT CSV,
                    NULL ''
                )
            """,
            buffer,
        )

def classify_staging(
    db: Session,
):
    statement= text(
        """
            WITH typed_staging AS (
                SELECT
                    source,
                    event_id,
                    name,
                    year,
                    area_ha,
                    ST_GeomFromEWKT(
                        geom_ewkt
                    ) AS geom
                FROM staging_fire_perimeters
            )
            SELECT
                COUNT(*) FILTER (
                    WHERE target.id IS NULL
                ) AS inserted,
                COUNT(*) FILTER (
                    WHERE target.id IS NOT NULL
                    AND (
                        target.name
                            IS DISTINCT FROM
                            staging.name
                        OR target.year
                            IS DICTINCT FROM
                            staging.year
                        OR target.area_ha
                            IS DISTINCT FROM
                            staging.area_ha
                        OR NOT ST_Equals(
                            target.geom,
                            staging.geom
                        )
                    )
                ) AS updated,
                COUNT(*) FILTER (
                    WHERE target.id IS NOT NULL
                    AND NOT (
                        target.name
                        IS DISTINCT FROM
                        staging.name
                    OR target.year
                        IS DISTINCT FROM
                        staging.year
                    OR target.area_ha
                        IS DISTINCT FROM
                        staging.area_ha
                    OR NOT ST_Equals(
                        target.geom.
                        staging.geom
                    )
                )
            ) AS skipped
        FROM typed_staging AS staging
        LEFT JOIN fire_perimeters AS target
            ON target.source = staging.source
            AND target.event_id =
                staging.event_id
        """
    )

    return (
        db.execute(statement)
        .mappings()
        .one()
    )

def merge_staging(
    db: Session,
) -> int:
    statement = text(
        """
        INSERT INTO fire_perimeters AS target (
            source,
            event_id,
            name,
            year,
            area_ha,
            geom
        )
        SELECT
            source,
            event_id,
            name,
            year,
            area_ha,
            ST_GeomFromEWKT(geom_ewkt)
        FROM staging_fire_perimeters
        WHERE TRUE
        ON CONFLICT ON CONSTRAINT
            uq_fire_perimeters_source_event_id
        DO UPDATE SET
            name = EXCLUDED.name,
            year = EXCLUDED.year,
            area_ha = EXCLUDED.area_ha,
            geom = EXCLUDED.geom,
            ingested_at = now()
        WHERE
            target.name
                IS DISTINCT FROM
                EXCLUDED.name
            target.year
                IS DISTINCT FROM
                EXCLUDED.year
            target.area_ha
                IS DISTINCT FROM
                EXCLUDED.area_ha
            OR NOT ST_Equals(
                target.geom,
                EXCLUDED.geom
            )
        """
    )

    result = db.execute(statement)
    return max(
        result.rowcount or 0,
        0,
    )

def load_with_copy(
    db: Session,
    frame: gpd.GeomDataFrame,
    replace_source: bool,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    (
        rows,
        rejected,
        rejection_reasons,
    ) = prepare_copy_rows(frame)

    if not rows:
        raise ValueError(
            "No valid rows are available for loading"
        )

    sources = {
        row[0]
        for row in rows
    }

    if replace_source and rejected > 0:
         raise ValueError(
            "--replace-source refused because "
            f"{rejected} rows were rejected"
        )

    if replace_source and len(sources) != 1:
        raise ValueError(
            "--replace-source requires exactly "
            "one source in the input"
        )

    database_started_at = time.perf_counter()

    deleted = 0
    copied = 0
    merged = 0
    copy_seconds 0.0
    merge_seconds = 0.0

    try:
        create_staging_table(db)
        copy_started_at = time.perf_counter()
        copy_to_staging(db, rows)
        copied = len(rows)

        copy_seconds = (
            time.perf_counter()
            - copy_started_at
        )

        merge_started_at = time.perf_counter()

        if replace_source:
            source_name = next(iter(sources))

            delete_result = dbn.execute(
                delete(FirePerimeter).where(
                    FirePerimeter.source
                    == source_name
                )
            )

            deleted = max(
                elete_result.rowcount or 0,
                0,
            )

        classification = classify_staging(db)


        inserted = int(
            classification["inserted"]
        )

        updated = int(
            classification["updated"]
        )

        skipped = int(
            classification["skipped"]
        )

        if (
            inserted
            + updated
            + skipped
            != len(rows)
        ):
            raise RuntimeError(
                "Classification counts do not "
                "match prepared row count"
            )

        merged = merge_staging(db)

         if merged != inserted + updated:
            raise RuntimeError(
                "Merged row count does not match "
                "inserted plus updated"
            )

        db.commit()

        merge_seconds = (
            time.perf_counter()
            - merge_started_at
        )

    except Exception:
        db.rollback()
        raise

    database_seconds = (
        time.perf_counter()
        - database_started_at
    )

    duration_seconds = (
        time.perf_counter()
        - started_at
    )

    return {
        "method": "copy_staging_upsert",
        "rows_read": len(frame),
        "copied_to_staging": copied,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "merged": merged,
        "deleted_before_reload": deleted,
        "copy_seconds": round(
            copy_seconds,
            3,
        ),
        "merge_seconds": round(
            merge_seconds,
            3,
        ),
        "database_seconds": round(
            database_seconds,
            3,
        ),
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
        report = load_with_copy(
            db=db,
            frame=frame,
            replace_source=(
                args.replace_source
            ),
        )

    output = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )


    print(output)

    args.report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.report.write_text(
        output,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
