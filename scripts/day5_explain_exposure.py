import argparse
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal

REPORT_DIR = Path("docs/performance")

FIND_INTERSECTING_PLOT_SQL = """
SELECT lp.id
FROM land_plots lp
JOIN fire_perimeters fp
ON ST_Intersects(lp.geom, fp.geom)
ORDER BY lp.id
LIMIT 1;
"""

FIND_FIRE_SQL = """
SELECT id
FROM fire_perimeters
ORDER BY id
LIMIT 1;
"""

PLOT_EXPOSURE_SQL = """
SELECT
    fp.id AS fire_id,
    fp.source,
    fp.event_id,
    fp.name,
    ST_Area(
        CAST(
            ST_Intersection(lp.geom, fp.geom)
            AS geography
        )
    ) AS intersection_area_m2
FROM land_plots lp
JOIN fire_perimeters fp
ON ST_Intersects(lp.geom, fp.geom)
WHERE lp.id = :plot_id;
"""

FIRE_TO_PLOTS_SQL = """
SELECT
    lp.id AS plot_id,
    lp.plot_id AS business_plot_id,
    lp.crop_type,
    fp.id AS fire_id
FROM fire_perimeters fp
JOIN land_plots lp
ON ST_Intersects(lp.geom, fp.geom)
WHERE fp.id = :fire_id;
"""

COUNT_INTERSECTIONS_SQL = """
SELECT COUNT(*) AS intersection_count
FROM land_plots lp
JOIN fire_perimeters fp
ON ST_Intersects(lp.geom, fp.geom);
"""

def run_explain(sql: str, params: dict) -> str:
    db = SessionLocal()

    try:
        explain_sql = f"""
        EXPLAIN (ANALYZE, BUFFERS)
        {sql}
        """

        rows = db.execute(text(explain_sql), params).fetchall()

        return "\n".join(row[0] for row in rows)

    finally:
        db.close()

def fetch_scalar(sql: str):
    db = SessionLocal()

    try:
        return db.execute(text(sql)).scalar()

    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run EXPLAIN ANALYZE for wildfire expose queries."
    )

    parser.add_argument(
        "--label",
        required=True,
        help="Report label, for example: no_index or with_gist.",
    )

    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    plot_id = fetch_scalar(FIND_INTERSECTING_PLOT_SQL)
    fire_id = fetch_scalar(FIND_FIRE_SQL)
    intersection_count = fetch_scalar(COUNT_INTERSECTIONS_SQL)

    if plot_id is None:
        raise RuntimeError(
            "No intersecting plot found.Generate overlapping fire perimeters."
        )

    if fire_id is None:
        raise RuntimeError(
            "No fire perimeters found. Generate fire perimeters first."
        )

    print(f"Using plot_id={plot_id}")
    print(f"Using fire_id={fire_id}")    
    print(f"Total land_plot/fire_perimeter intersections: {intersection_count}")

    plot_explain = run_explain(
        PLOT_EXPOSURE_SQL,
        {"plot_id": plot_id},
    )

    fire_explain = run_explain(
        FIRE_TO_PLOTS_SQL,
        {"fire_id": fire_id},
    )

    report_path = REPORT_DIR / f"day5_explain_{args.label}.md"

    report = f"""# Day5 EXPLAIN ANALYZE Report - {args.label}

## Test Context

- Selected plot_id: `{plot_id}`
- Selected fire_id: `{fire_id}`
- Total land_plot / fire_perimeter intersections: `{intersection_count}`

## Query 1: Plot Exposure Query

This query simulates the API behavior of checking which wildfire perimeters intersect one land plot.

```sql
{PLOT_EXPOSURE_SQL.strip()}

{plot_explain}

{FIRE_TO_PLOTS_SQL.strip()}

{fire_explain}
"""
    report_path.write_text(report, encoding="utf-8")

    print(f"Report written to: {report_path}")

if __name__ == "__main__":
    main()