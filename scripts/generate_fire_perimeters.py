import argparse
import random
from typing import Literal

from geoalchemy2.elements import WKTElement
from shapely.geometry import Polygon
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.fire_perimeter import FirePerimeter

RegionName = Literal["canada_sk", "australia_nsw"]

REGION_CONFIG = {
    "canada_sk": {
        "prefix": "CA_SK",
        "min_lon": -107.5,
        "max_lon": -105.5,
        "min_lat": 51.5,
        "max_lat": 52.8,
        "source": "SYNTH_CANADA_FIRE",
    },
    "australia_nsw": {
        "prefix": "AU_NSW",
        "min_lon": 146.0,
        "max_lon": 148.0,
        "min_lat": -35.5,
        "max_lat": -34.0,
        "source": "SYNTH_AUSTRALIA_FIRE",
    },
}

def create_square_polygon(lon: float, lat:float, size: float) -> Polygon:
    # create a square polygon for synthetic wildfire perimeter data.
    # this is test data only.the size is measured in degrees,not meters.

    return Polygon(
        [
            (lon, lat),
            (lon + size, lat),
            (lon + size, lat + size),
            (lon, lat + size),
            (lon, lat),
        ]
    )

def generate_fire_perimeters(
    n: int,
    region: RegionName,
    reset: bool = False,
    batch_size: int = 100,
) -> None:
    # Generate synthetic wildfire perimeter polygons and insert them into PostGIS.

    # These polygons are intentionally larger than land plot polygons so that
    # each fire perimeter can intersect multiple land plots.

    config = REGION_CONFIG[region]
    prefix = config["prefix"]
    source = config["source"]

    db = SessionLocal()

    try:
        if reset:
            print(f"Deleting old synthetic fire perimeters with source {source}")
            db.query(FirePerimeter).filter(FirePerimeter.source == source).delete(
                synchronize_session=False
            )
            db.commit()

            print(f"Start generating {n} fire perimeters for region: {region}")

        for i in range(1,n + 1):
            lon = random.uniform(config["min_lon"], config["max_lon"])
            lat = random.uniform(config["min_lat"], config["max_lat"])

            polygon = create_square_polygon(lon, lat,size=0.08)

            obj = FirePerimeter(
                source=source,
                event_id=f"{prefix}_FIRE_{i:04d}",
                name=f"Synthetic wildfire perimeter {i}",
                geom=WKTElement(polygon.wkt, srid=4326),
            )

            db.add(obj)

            if i % batch_size == 0:
                db.commit()
                print(f"Inserted {i}/{n} fire perimeters")

        db.commit()
        print(f"Done. Inserted {n} fire perimeters into PostGIS.")

    except SQLAlchemyError as exc:
        db.rollback()
        print("Database error. Transaction rolled back.")
        print(exc)
        raise

    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic wildfire perimeter data."
    )

    parser.add_argument(
        "--n",
        type=int,
        default=30,
        help="Number of wildfire perimeters to generate.",
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
        help="Delete old generated synthetic fire perimeters before inserting.",
    )

    args = parser.parse_args()

    generate_fire_perimeters(
        n=args.n,
        region=args.region,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
        