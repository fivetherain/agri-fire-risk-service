# Day5 EXPLAIN ANALYZE Report - with_gist

## Test Context

- Selected plot_id: `1`
- Selected fire_id: `1`
- Total land_plot / fire_perimeter intersections: `764`

## Query 1: Plot Exposure Query

This query simulates the API behavior of checking which wildfire perimeters intersect one land plot.

```sql
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

Nested Loop  (cost=0.42..53.97 rows=1 width=75) (actual time=7.568..7.577 rows=1 loops=1)
  Buffers: shared hit=81
  ->  Index Scan using ix_land_plots_id on land_plots lp  (cost=0.29..8.30 rows=1 width=120) (actual time=0.006..0.008 rows=1 loops=1)
        Index Cond: (id = 1)
        Buffers: shared hit=3
  ->  Index Scan using idx_fire_perimeters_geom_gist on fire_perimeters fp  (cost=0.14..20.65 rows=1 width=187) (actual time=0.031..0.036 rows=1 loops=1)
        Index Cond: (geom && lp.geom)
        Filter: st_intersects(lp.geom, geom)
        Buffers: shared hit=2
Planning:
  Buffers: shared hit=12
Planning Time: 0.688 ms
Execution Time: 7.633 ms

SELECT
    lp.id AS plot_id,
    lp.plot_id AS business_plot_id,
    lp.crop_type,
    fp.id AS fire_id
FROM fire_perimeters fp
JOIN land_plots lp
ON ST_Intersects(lp.geom, fp.geom)
WHERE fp.id = :fire_id;

Nested Loop  (cost=0.15..22.06 rows=23 width=27) (actual time=0.048..0.051 rows=1 loops=1)
  Buffers: shared hit=4
  ->  Seq Scan on fire_perimeters fp  (cost=0.00..1.39 rows=1 width=124) (actual time=0.007..0.008 rows=1 loops=1)
        Filter: (id = 1)
        Rows Removed by Filter: 30
        Buffers: shared hit=1
  ->  Index Scan using idx_land_plots_geom_gist on land_plots lp  (cost=0.15..20.67 rows=1 width=143) (actual time=0.039..0.039 rows=1 loops=1)
        Index Cond: (geom && fp.geom)
        Filter: st_intersects(geom, fp.geom)
        Buffers: shared hit=3
Planning:
  Buffers: shared hit=6
Planning Time: 0.678 ms
Execution Time: 0.068 ms
