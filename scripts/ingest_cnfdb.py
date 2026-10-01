import argparse
from pathlib import Path

import geopandas as gpd
from geoalchemy2 import Geometry

from app.db.session import engine
from app.models.fire_perimeter import FirePerimeter

SOURCE_NAME = 'CNFDB'

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest and inspect CNFDB wildfire sample"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--load",
        action="store_true",
    )

    return parser.parse_args()

# Data inspection
def inspect_dataset(gdf: gpd.GeoDataFrame) -> None:
    print(f"rows: (len(gdf))")
    print(f"column: {list(gdf.columns)}")
    print(f"source CRS: {gdf.crs}")
    print(f"geometry type:")
    print(f"gdf.geom_type.value_counts(dropna=False)")
    print(f"bounds: {gdf.total_bounds}")

    preview_columns = [
        column
        for column in [
            "SRC_AGENCY",
            "YEAR",
            "FIRE_ID",
            "FIRENAME",
            "SIZE_HA",
            "CALC_HA",
        ]
        if column in gdf.columns
    ]

    print(gdf[preview_columns].head())

def build_load_frame(
    gdf: gpd.GeoDataFrame,
    limit: int,
) -> gpd.GeoDataFrame:
    required = {"FIRE_ID", "FIRENAME"}
    missing = required - set(gdf.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")
     
    if gdf.crs is None:
        raise ValueError("Source dataset has no CRS")

    projected = gdf.to_crs(4326)

    compatible = projected.loc[
        projected.geometry.notna()
        & ~projected.geometry.is_empty
        & projected.geometry.eq("Polygon")
    ].head(limit).copy()

    noramlized = gpd.GeoDataFrame(
        {
            "source": [SOURCE_NAME] * len(compatible),
            "event_id": (
                compatible["Fire_ID"].astype("string").str.strip().to_numpy()
            ),
            "name": (
                compatible["FIRENAME"].astype("string").str.strip().to_numpy()
            ),
        },
        geometry=compatible.geometry.to_numpy(),
        crs=copmpatible.crs,
    )

    return normalized.rename_geometry("geom")

def load_to_postgis(
    frame: gpd.GeoDataFrame,
) -> None:
    with engine.begin() as connection:
        frame.to_postgis(
            name=FirePerimeter.__tablename__,
            con=connection,
            if_exists="append",
            index=False,
            dtype={
                "geom": Geometry(
                    "POLYGON",
                    srid=4326,
                )
            },
        )

def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file does not exist: {args.input}")
    
    gdf = gdp.read_file(args.input, engine="pyogrio")

    inspect_dataset(gdf)

    noramlized = build_load_frame(gdf, args.limit)

    print(f"rows prepared: {len(normalized)}")
    print(f"target CRS: {noramlized.crs}")

    print(
        normalized[
            ["source", "event_id", "name"]
        ].head()
    )

    if not args.load:
        print(
            "Dry run only."
            "Add --load to write to PostGIS"
        )
        return

    load_to_postgis(noramlized)
    print(f"rows loaded: {len(normalized)}")

if __name__ == "_main_":
    main()
