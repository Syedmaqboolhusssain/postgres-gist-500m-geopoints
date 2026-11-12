-- After the bulk load: restore the primary key, fix the sequence, collect stats.
-- Run this once run-load.sh reports all four workers finished.

\timing on

-- Proof of the row count for the report.
SELECT count(*) AS total_rows FROM locations;

-- Build the primary key in one pass now that the data is in place.
-- Expect roughly 10-20 minutes at 500M.
SET maintenance_work_mem = '4GB';
ALTER TABLE locations ADD CONSTRAINT locations_pkey PRIMARY KEY (location_id);

-- Recreate the sequence the tutorial's BIGSERIAL would have given us, so the
-- final schema is a genuine match rather than an approximation.
CREATE SEQUENCE IF NOT EXISTS locations_location_id_seq AS bigint OWNED BY locations.location_id;
ALTER TABLE locations ALTER COLUMN location_id SET DEFAULT nextval('locations_location_id_seq');
SELECT setval('locations_location_id_seq', (SELECT max(location_id) FROM locations));

-- Step 3 (tutorial) -- ANALYZE after bulk load.
-- Without this the planner still thinks the table is empty and every "before"
-- plan below would be measuring the wrong decision.
ANALYZE locations;

\echo ''
\echo '--- Table shape (screenshot this: it is the 500M proof) ---'
\d locations

SELECT
  pg_size_pretty(pg_relation_size('locations'))        AS table_only,
  pg_size_pretty(pg_indexes_size('locations'))         AS indexes_only,
  pg_size_pretty(pg_total_relation_size('locations'))  AS total_with_indexes;

SELECT reltuples::bigint AS planner_row_estimate,
       relpages          AS heap_pages
FROM pg_class WHERE relname = 'locations';

SELECT * FROM locations ORDER BY location_id LIMIT 5;
