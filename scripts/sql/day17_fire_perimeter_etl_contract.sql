BEGIN;

ALTER TABLE fire_perimeters
    ALTER COLUMN geom
    TYPE geometry(Geometry, 4326)
    USING geom::geometry(Geometry, 4326);

ALTER TABLE fire_perimeters
    ADD COLUMN IF NOT EXISTS year INTEGER;

ALTER TABLE fire_perimeters
    ADD COLUMN IF NOT EXISTS area_ha DOUBLE PRECISION;

ALTER TABLE fire_perimeters
    ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ
    NOT NULL DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 
            'uq_fire_perimeter_source_event_id'
            AND conrelid = 
                'fire_perimeters'::regclass
    ) THEN
        ALTER TABLE fire_perimeters
            ADD CONSTRAINT
                uq_fire_perimeters_source_event_id
            UNIQUE (source, event_id);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXIST (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 
            'ck_fire_perimeters_polygonal'
            AND conrelid = 
                'fire_perimeters'::regclass
    ) THEN
        ALTER TABLE fire_perimeters
            ADD CONSTRAINT
                ck_fire_perimeters_polygonal
            CHECK (
                ST_GeometryType(geom) IN (
                    'ST_Polygon',
                    'ST_MultiPolygon'
                )
            );
    END IF;
END
$$;

COMMIT;
