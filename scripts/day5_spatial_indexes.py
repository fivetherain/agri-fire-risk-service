import argparse

from sqlalchemy import text

from app.db.session import SessionLocal

CREATE_INDEX_SQL = [
    """
    CREATE INDEX IF NOT EXISTS idx_land_plots_geom_gist
    ON land_plots
    USING GIST(geom);
    """,
    """
    CREATE INDEX IF NOT EXISTS  idx_fire_perimeters_geom_gist
    ON fire_perimeters
    USING GIST(geom)
    """
]

DROP_INDEX_SQL = [
    "DROP INDEX IF EXISTS idx_land_plots_geom_gist;",
    "DROP INDEX IF EXISTS idx_fire_perimeters_geom_gist;",
    "DROP INDEX IF EXISTS idx_land_plots_geom;",
    "DROP INDEX IF EXISTS idx_fire_perimeters_geom;",
]

ANALYZE_SQL = [
    "ANALYZE land_plots;",
    "ANALYZE fire_perimeters;",
]

CHECK_INDEX_SQL = """
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('land_plots', 'fire_perimeters')
ORDER BY tablename, indexname;
"""

def execute_statements(statements: list[str]) -> None:
    db = SessionLocal()

    try:
        for sql in statements:
            print(sql.strip()) 
            db.execute(text(sql))

        db.commit()
        print("Done.")
    finally:
        db.close()

def show_indexes() -> None:
    db = SessionLocal()

    try:
        rows = db.execute(text(CHECK_INDEX_SQL)).fetchall()

        if not rows:
            print("No indexes found for land_plots or fire_perimeters.")
            return
        for row in rows:
            print("-" * 80)
            print(f"table: {row.tablename}")
            print(f"index: {row.indexname}")
            print(row.indexdef)

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create, drop, analyze, or inspect spatial indexes."
    )

    parser.add_argument(
        "action",
        choices=["create", "drop", "analyze", "show"],
        help="Index action to perform."
    )

    args = parser.parse_args()

    if args.action == "create":
        execute_statements(CREATE_INDEX_SQL)

    elif args.action == "drop":
        execute_statements(DROP_INDEX_SQL)

    elif args.action == "analyze":
        execute_statements(ANALYZE_SQL)

    elif args.action == "show":
        show_indexes()


if __name__ == "__main__":
    main()