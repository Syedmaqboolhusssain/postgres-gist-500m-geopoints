-- BEFORE GiST. Steps 4, 7, 8 and 9 of the tutorial, run with no spatial index.
--
-- Run this BEFORE 05_index.sql. You get one clean shot at these numbers; once
-- the GiST index exists you would have to drop it to measure them again.
--
-- Every query runs twice. The first run is cold (or as cold as the OS page cache
-- allows), the second is warm. The tutorial compares a cold 5997 ms sequential
-- scan against a warm 10 ms bitmap scan, which overstates the win -- part of that
-- gap is caching, not indexing. Reporting both runs is what separates a real
-- measurement from a copied one. EXPLAIN's "I/O Timings" line, enabled by
-- track_io_timing in compose.yaml, shows exactly how much was disk.

\timing on
\echo '======================================================================'
\echo ' BASELINE -- no spatial index'
\echo '======================================================================'

SELECT indexrelid::regclass AS existing_indexes
FROM pg_index WHERE indrelid = 'locations'::regclass;

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
\echo '    Without an index this is a full scan plus a Top-N heapsort over 500M'
\echo '    rows. Expect minutes, not seconds. This is the most dramatic before/'
\echo '    after pair in the whole assignment.'
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
