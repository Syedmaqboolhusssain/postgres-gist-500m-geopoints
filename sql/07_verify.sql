-- Step 10 (tutorial) -- verify index usage and size, plus a correctness check
-- the tutorial does not do.

\timing on

\echo '--- Is the index actually being used? ---'
SELECT indexrelid::regclass AS index_name,
       idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relid = 'locations'::regclass
ORDER BY idx_scan DESC;

\echo ''
\echo '--- Table vs. indexes size ---'
SELECT
  pg_size_pretty(pg_relation_size('locations'))        AS table_only,
  pg_size_pretty(pg_indexes_size('locations'))         AS indexes_only,
  pg_size_pretty(pg_total_relation_size('locations'))  AS total_with_indexes;

\echo ''
\echo '--- Individual index size ---'
SELECT
  indexrelid::regclass AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_index
WHERE indrelid = 'locations'::regclass
ORDER BY pg_relation_size(indexrelid) DESC;


\echo ''
\echo '======================================================================'
\echo ' Are the answers even right? (a check the tutorial skips)'
\echo '======================================================================'
\echo 'The points are uniform over the whole globe: 360 deg of longitude by 180'
\echo 'of latitude = 64800 square degrees. So the expected number of hits for any'
\echo 'shape is simply  N * area / 64800.  If the measured counts land near these'
\echo 'numbers, the data really is uniform and the index really is returning'
\echo 'everything it should -- a fast query that quietly returns too few rows is'
\echo 'not a win. This also explains why the tutorial''s circle and polygon queries'
\echo 'return zero rows at 10M: the expected counts there are 0.2 and 1.2.'
\echo ''

WITH n AS (SELECT count(*)::numeric AS rows FROM locations),
shapes(shape, area_deg2) AS (
    VALUES ('box   (0.4 x 0.3 deg)',      0.4 * 0.3),
           ('circle (r = 0.02 deg)',      pi() * 0.02 * 0.02),
           ('polygon (0.08 x 0.10 deg)',  0.08 * 0.10)
)
SELECT shape,
       round(area_deg2::numeric, 6)                      AS area_deg2,
       round(n.rows * area_deg2::numeric / 64800, 1)     AS expected_rows
FROM shapes, n;

\echo ''
\echo 'Measured counts (compare against expected_rows above):'
SELECT
  (SELECT count(*) FROM locations
     WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))')            AS actual_box,
  (SELECT count(*) FROM locations
     WHERE geolocation <@ circle '((-73.9855,40.7580), 0.02)')          AS actual_circle,
  (SELECT count(*) FROM locations
     WHERE geolocation <@ polygon
       '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))') AS actual_polygon;

\echo ''
\echo '--- Server settings that shaped these numbers (put in the report) ---'
SELECT name, setting, unit
FROM pg_settings
WHERE name IN ('shared_buffers','work_mem','maintenance_work_mem',
               'effective_cache_size','max_parallel_workers_per_gather',
               'random_page_cost','jit','track_io_timing')
ORDER BY name;

SELECT version();
