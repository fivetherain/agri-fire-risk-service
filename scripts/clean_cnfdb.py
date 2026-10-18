import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Polygon,
)

def parse_args():
    parser =argparse.ArgumentParser(
        description="Clean CNFDB wildfire perimeter data."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/processed/cnfdb_clean.gpkg"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "doc/data/cnfdb_cleaning_report.json"
        ),
    )

    return parser.parse_args()

def polygon_parts(geometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]

    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)

    if isinstance(geometry, GeometryCollection):
        parts = []

        for child in geometry.geoms:
            parts.extend(polygon_parts(child))

        return parts

    return []

def to_multipolygon(geometry):
    if geometry is None or geometry.is_empty:
        return None

    parts = polygon_parts(geometry)

    if not parts:
        return None

    return MultiPolygon(parts)

def clean_text(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.strip()
    )

    return cleaned.mask(cleaned == "")

def clean_cnfdb(
    source: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    required_columns = {
        "CFS_REF_ID",
        "FIRENAME",
        "YEAR",
        "CALC_HA",
        "geometry",
    }

    missing = required_columns - set(source.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if source.crs is None:
        raise ValueError("Source dataset has no CRS")

    rows_read = len(source)
    working = source.copy()

    null_geometry = int(
        working.geometry.isna().sum()
    )

    working = working.loc[
        working.geometry.notna()
    ].copy()

    empty_geometry = int(
        working.geometry.is_empty.sum()
    )

    working = working.loc[
        ~working.geometry.is_empty
    ].copy()

    invalid_mask = ~working.geometry.is_valid
    invalid_geometry_found = int(
        invalid_mask.sum()
    )

    working.loc[
        invalid_mask,
        "geometry",
    ] = working.loc[
        invalid_mask,
        "geometry",
    ]
        
    working["geometry"] = (
        working.geometry.map(to_multipolygon)
    )

    working = gpd.GeoDataFrame(
        working,
        geometry="geometry",
        crs=source.crs,
    )

    unsupported_mask = working.geometry.isna()
    unsupported_geometry = int(
        unsupported_mask.sum()
    )

    working = working.loc[
        ~unsupported_mask
    ].copy()

    working = working.reset_index(drop=True)

    normalized = gpd.GeoDataFrame(
        {
            "source": ["CNFDB"] * len(working),
            "event_id": clean_text(
                working["CFS_REF_ID"]
            ),
            "name": clean_text(
                working["FIRENAME"]
            ),
            "year": (
                pd.to_numeric(
                    working["YEAR"],
                    errors="coerce",
                )
                .replace(-9999, pd.NA)
                .astype("Int64")
            ),
            "area_ha": pd.to_numeric(
                working["CALC_HA"],
                errors="coerce",
            ),
        },
        geometry=working.geometry,
        crs=working.crs,
    )

    missing_event_mask = (
        normalized["event_id"].isna()
    )

    missing_event_id = int(
        missing_event_mask.sum()
    )

    invalid_area_mask = (
        normalized["area_ha"].isna()
        | normalized["area_ha"].le(0)
    )

    invalid_area = int(
        invalid_area_mask.sum()
    )

    reject_mask = (
        missing_event_mask | invalid_area_mask
    )

    normalized = normalized.loc[
        ~reject_mask
    ].copy()

    duplicate_mask = normalized.duplicated(
        subset=["source", "event_id"],
        keep=False,
    )

    duplicate_key_rows = int(
        duplicate_mask.sum()
    )

    duplicate_groups = int(
        normalized.loc[duplicate_mask]
        .groupby(["source", "event_id"])
        .ngroups
    )

    row_before_dissolve = len(normalized)

    cleaned = normalized.dissolve(
        by=["source", "event_id"],
        aggfunc={
            "name": "first",
            "year": "first",
            "area_ha": "sum",
        },
        as_index=False,
        sort=False,
        method="unary",
    )

    cleaned["geometry"] = (
        cleaned.geometry.map(to_multipolygon)
    )

    cleaned = gpd.GeoDataFrame(
        cleaned,
        geometry="geometry",
        crs=normalized.crs,
    )

    rows_merged_duplicated = (
        row_before_dissolve - len(cleaned)
    )

    cleaned = cleaned.to_crs(epsg=4326)
    cleaned = cleaned.rename_geometry("geom")

    rows_rejected = (
        null_geometry
        + empty_geometry
        + unsupported_geometry
        + missing_event_id
        + invalid_area
    )

    report = {
        "rows_read": rows_read,
        "rows_valid": len(cleaned),
        "rows_rejected": rows_rejected,
        "null_geometry": null_geometry,
        "empty_geometry": empty_geometry,
        "invalid_geometry_repaired": (
            invalid_geometry_found
        ),
        "unsupported_geometry": (
            unsupported_geometry
        ),
        "missing_event_id": missing_event_id,
        "invalid_area": invalid_area,
        "unknown_year": int(
            cleaned["year"].isna().sum()
        ),
        "missing_name": int(
            cleaned["name"].isna().sum()
        ),
        "duplicate_key_rows": (
            duplicate_key_rows
        ),
        "duplicate_groups": duplicate_groups,
        "rows_merged_duplicated": (
            rows_merged_duplicated
        ),
        "source_crs": str(source.crs),
        "target_crs": str(cleaned.crs),
    }

    return cleaned, report

def validate_cleaned(
     cleaned: gpd.GeoDataFrame,
) -> None:
    if cleaned.crs is None:
        raise ValueError("Cleaned dataset has no CRS")

    if cleaned.crs.to_epsg() != 4326:
        raise ValueError("cleaned dataset must use EPSG: 4326")

    if cleaned.geometry.isna().any():
        raise ValueError("cleaned dataset has null geometry")

    if cleaned.geometry.is_empty.any():
        raise ValueError("cleaned data contains empty geometry")

    if not cleaned.geometry.is_valid.all():
        raise ValueError("cleaned data contains invalid geometry")

    if not cleaned.geom_type.eq("MultiPolygon").all():
        raise ValueError("Cleaned geometry must be MultiPolygon")

    if cleaned.duplicated(["source", "event_id"]).any():
        raise ValueError("cleaned data contains duplicate event keys")

def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    source = gpd.read_file(
        args.input,
        engine="pyogrio",
    )

    cleaned, report = clean_cnfdb(source)
    validate_cleaned(cleaned)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cleaned.to_file(
        args.output,
        layer="fire_perimeters",
        driver="GPKG",
        engine="pyogrio",
        index=False,
    )

    args.report.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"cleaned data: {args.output}")
    print(f"quality report: {args.report}")

if __name__ == "__main__":
    main()