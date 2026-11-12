-- Rubric extension: the tutorial's COUNT(*) polygon query is index-only on
-- PostgreSQL 17. Returning full rows requires heap access and naturally shows
-- the Bitmap Index Scan + Bitmap Heap Scan plan requested by the assignment.

\timing on

\echo '--- Polygon row retrieval: cold run ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, name, geolocation
FROM locations
WHERE geolocation <@ polygon
  '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';

\echo '--- Polygon row retrieval: warm run ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, name, geolocation
FROM locations
WHERE geolocation <@ polygon
  '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';

SELECT count(*) AS polygon_rows
FROM locations
WHERE geolocation <@ polygon
  '((-74.02,40.70),(-73.94,40.70),(-73.94,40.80),(-74.02,40.80))';
