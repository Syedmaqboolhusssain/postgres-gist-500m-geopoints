-- AFTER GiST. Steps 6, 7, 8 and 9 of the tutorial, byte-for-byte the same
-- queries as 04_baseline.sql so the comparison is honest.
--
-- What to look for in each plan:
--   Q1/Q2/Q4  Bitmap Index Scan on idx_locations_gist, then a Bitmap Heap Scan
--             with a Recheck Cond. The recheck exists because GiST is a lossy
--             index -- it stores bounding boxes, so it returns candidates that
--             the heap must confirm. "Rows Removed by Index Recheck" is the cost
--             of that lossiness.
--   Q3        Index Scan (NOT bitmap) with an "Order By:" line. This is the K-NN
--             search: GiST walks the tree in distance order and stops after 100
--             rows. A bitmap scan cannot do this, because bitmaps have no order.

\timing on
\echo '======================================================================'
\echo ' AFTER GiST'
\echo '======================================================================'

\echo ''
\echo '--- Q1: bounding box (point <@ box), run 1 of 2 (cold) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM locations
WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

\echo '--- Q1: bounding box, run 2 of 2 (warm) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM locations
WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

\echo ''
\echo '--- Q2: radius / circle (point <@ circle), run 1 of 2 (cold) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM locations
WHERE geolocation <@ circle '((-73.9855,40.7580), 0.02)';

\echo '--- Q2: radius / circle, run 2 of 2 (warm) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM locations
WHERE geolocation <@ circle '((-73.9855,40.7580), 0.02)';

\echo ''
\echo '--- Q3: K-NN nearest neighbour (ORDER BY <-> LIMIT 100), run 1 of 2 ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, name, geolocation
FROM locations
ORDER BY geolocation <-> POINT(-73.9855, 40.7580)
LIMIT 100;

\echo '--- Q3: K-NN, run 2 of 2 (warm) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, name, geolocation
FROM locations
ORDER BY geolocation <-> POINT(-73.9855, 40.7580)
LIMIT 100;

\echo ''
\echo '--- Q4: polygon containment (point <@ polygon), run 1 of 2 (cold) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM locations
WHERE geolocation <@ polygon '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';

\echo '--- Q4: polygon containment, run 2 of 2 (warm) ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM locations
WHERE geolocation <@ polygon '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';

\echo ''
\echo '--- The actual answers, not just the plans ---'
SELECT count(*) AS rows_in_nyc_box
FROM locations WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

SELECT count(*) AS rows_in_circle
FROM locations WHERE geolocation <@ circle '((-73.9855,40.7580), 0.02)';

SELECT count(*) AS rows_in_polygon
FROM locations
WHERE geolocation <@ polygon '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';
