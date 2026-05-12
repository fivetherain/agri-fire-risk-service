import argparse
import random
from typing import Literal

from geoalchemy2.elements import WKTElement
from shapely.geometry import Polygon
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.land_plot import LandPlot

RegionName = Literal["canada_sk", "australia_nsw"]

REGION_CONFIG = {
    "canada_sk": {
        "prefix": "CA_SK",
        "min_lon": -107.5,
        "max_lon": -105.5,
        "min_lat": 51.5,
        "max_lat": 52.8,
        "crop_types": ["wheat", "canola", "barley", "pasture", "fallow"],
    },
    "australia_nsw": {
        "prefix": "AU_NSW",
        "min_lon": 146.0,
        "max_lon": 148.0,
        "min_lat": -35.5,
        "max_lat": -34.0,
        "crop_types": ["wheat", "barley", "canola", "pasture", "fallow"],
    },
}

def create_square_polygon(lon:float, lat:float, size:float) -> Polygon:
    # generate a square polygon
    # coordinate of bottom-left corner(longtitude and latitude)
    #  Dimensions:
        # Side length of the small square blocks, in "degrees."
        # Note: This is intended for generating test data, not for precise area calculation.
    return Polygon(
        [
            (lon, lat),
            (lon + size, lat),
            (lon + size, lat + size),
            (lon, lat + size),
            (lon, lat),
        ]
    )

def generate_land_plots(
    n: int,
    region: RegionName,
    reset: bool = False,
    batch_size: int = 500,
) -> None:
    # generate n pieces of algricultural testing data,then import to PostGIS
    config = REGION_CONFIG[region]
    prefix = config["prefix"]

    db = SessionLocal()

    try:
        if reset:
            print(f"Deleting old test data with prefix: {prefix}_")
            db.query(LandPlot).filter(LandPlot.plot_id.like(f"{prefix}_%")).delete(
                synchronize_session=False
            )
            db.commit()

        print(f"Start generating {n} land plots for region :{region}")

        for i in range(1, n + 1):
            lon = random.uniform(config["min_lon"], config["max_lon"])
            lat = random.uniform(config["min_lat"], config["max_lat"])

            polygon = create_square_polygon(lon, lat, size=0.003)

            obj = LandPlot(
                plot_id=f"{prefix}_{i:06d}",
                crop_type=random.choice(config["crop_types"]),
                area_ha=round(random.uniform(5.0, 120.0), 2),
                geom=WKTElement(polygon.wkt, srid=4326),
            )

            db.add(obj)

            if i % batch_size == 0:
                db.commit()
                print(f"Inserted {i}/{n} rows")

        db.commit()
        print(f"Done. Inserted {n} land plots into PostGIS.")

    except SQLAlchemyError as exc:
        db.rollback()
        print("Database Error.transaction rolled back.")
        print(exc)
        raise

    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic agricultural land plot data."
    )

    parser.add_argument(
        "--n",
        type=int,
        default=10000,
        help="Number of land plots to generate.",
    )

    parser.add_argument(
        "--region",
        choices=["canada_sk", "australia_nsw"],
        default="canada_sk",
        help="Target region for synthetic data.",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete old generated test data for the selected region before inserting.",
    )

    args = parser.parse_args()

    generate_land_plots(
        n=args.n,
        region=args.region,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
