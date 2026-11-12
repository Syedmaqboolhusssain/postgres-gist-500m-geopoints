-- Isolate a real geohash workflow from the comparison GiST index. Without the
-- MATERIALIZED boundary PostgreSQL can BitmapAnd both indexes, which measures a
-- hybrid plan rather than geohash candidate generation plus application-style
-- exact filtering.

\timing on

\echo '--- Geohash-only prefix candidates, then exact re-check ---'
EXPLAIN (ANALYZE, BUFFERS)
WITH candidates AS MATERIALIZED (
  SELECT location_id, geolocation
  FROM locations_gh
  WHERE gh LIKE 'dr%'
)
SELECT count(*)
FROM candidates
WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

\echo '--- Geohash quality metrics ---'
WITH counts AS (
  SELECT
    count(*) FILTER (WHERE gh LIKE 'dr%') AS candidates,
    count(*) FILTER (
      WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))'
    ) AS true_rows,
    count(*) FILTER (
      WHERE gh LIKE 'dr%'
        AND geolocation <@ box '((-74.1,40.6),(-73.7,40.9))'
    ) AS true_from_candidates
  FROM locations_gh
)
SELECT candidates,
       true_rows,
       candidates - true_from_candidates AS false_positives,
       round(100.0 * true_from_candidates / candidates, 3) AS precision_pct,
       round(100.0 * true_from_candidates / true_rows, 3) AS recall_pct,
       round(candidates::numeric / true_rows, 1) AS overfetch_factor
FROM counts;
