-- THE EXTENSION: geohash vs GiST.
--
-- The tutorial does not cover geohashing; the assignment asks you to analyse it.
-- This file builds both index strategies over the SAME rows so the comparison is
-- apples to apples, then measures the three things that actually distinguish them:
-- over-fetching, the boundary problem, and K-NN.
--
-- It runs on a 50M-row subset, not the full 500M. That is deliberate and worth
-- saying out loud in the report: what is being compared here is plan shape,
-- selectivity and correctness, none of which change with scale, and a second
-- 500M table with two more indexes would need another ~90 GB for no new insight.

\timing on

-- --------------------------------------------------------------------------
-- Build the comparison table
-- --------------------------------------------------------------------------

DROP TABLE IF EXISTS locations_gh;

-- gh is declared COLLATE "C" on purpose. A geohash is only prefix-searchable if
-- string comparison follows byte order; under a locale-aware collation like
-- en_US.UTF-8 the ordering of the base32 alphabet is not guaranteed to agree
-- with prefix containment, and a plain B-tree cannot then be used for LIKE 'x%'
-- at all. This one keyword is the difference between an index scan and a seq scan.
--
-- The table is declared explicitly rather than with CREATE TABLE AS so the
-- collation is a property of the column, not something inferred from the
-- expression that happened to populate it.
CREATE UNLOGGED TABLE locations_gh (
    location_id  BIGINT,
    name         TEXT,
    geolocation  POINT,
    gh           TEXT COLLATE "C"       -- precision 7 ~= 153 m x 153 m cells
);

INSERT INTO locations_gh (location_id, name, geolocation, gh)
SELECT location_id,
       name,
       geolocation,
       ST_GeoHash(ST_SetSRID(ST_MakePoint(geolocation[0], geolocation[1]), 4326), 7)
FROM locations
WHERE location_id <= 50000000;

SELECT count(*) AS subset_rows FROM locations_gh;

SET maintenance_work_mem = '4GB';
CREATE INDEX idx_gh_btree ON locations_gh USING btree (gh);
CREATE INDEX idx_gh_gist  ON locations_gh USING gist  (geolocation);
ANALYZE locations_gh;

\echo ''
\echo '--- Index sizes: the B-tree over a 7-char string vs the GiST over points ---'
SELECT indexrelid::regclass AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_index WHERE indrelid = 'locations_gh'::regclass
ORDER BY pg_relation_size(indexrelid) DESC;


-- --------------------------------------------------------------------------
-- 1. A query box does not correspond to one geohash cell
-- --------------------------------------------------------------------------
\echo ''
\echo '======================================================================'
\echo ' 1. The NYC box in geohash terms'
\echo '======================================================================'
\echo 'Geohashes of the box corners at each precision. They agree on the first'
\echo 'few characters and then diverge -- that divergence point is the finest'
\echo 'single prefix that can cover the whole box.'

SELECT p AS precision,
       ST_GeoHash(ST_SetSRID(ST_MakePoint(-74.1, 40.6), 4326), p) AS sw_corner,
       ST_GeoHash(ST_SetSRID(ST_MakePoint(-73.7, 40.9), 4326), p) AS ne_corner
FROM generate_series(1, 7) AS p;

-- The longest common prefix of the two corners, turned into a LIKE pattern.
WITH c AS (
  SELECT ST_GeoHash(ST_SetSRID(ST_MakePoint(-74.1, 40.6), 4326), 7) AS a,
         ST_GeoHash(ST_SetSRID(ST_MakePoint(-73.7, 40.9), 4326), 7) AS b
)
SELECT coalesce(max(left(a, i)) FILTER (WHERE left(a, i) = left(b, i)), '') || '%' AS box_pat
FROM c, generate_series(1, 7) AS i \gset

\echo ''
\echo 'Covering prefix pattern for the box:'
\echo :'box_pat'


-- --------------------------------------------------------------------------
-- 2. Same question, three ways
-- --------------------------------------------------------------------------
\echo ''
\echo '======================================================================'
\echo ' 2. "How many points are in the NYC box?" -- geohash vs GiST'
\echo '======================================================================'

\echo ''
\echo '--- (a) Geohash B-tree prefix scan: candidates only ---'
\echo '    This is what a geohash lookup actually returns. It is a range scan'
\echo '    over one contiguous slice of the B-tree -- very cheap per row -- but'
\echo '    the rows are the cell, not the box.'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM locations_gh WHERE gh LIKE :'box_pat';

\echo ''
\echo '--- (b) Geohash prefix scan + the re-check the application must do ---'
\echo '    Real geohash systems filter the candidates afterwards. The gap between'
\echo '    (a) and (b) is wasted work: rows read from disk only to be discarded.'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM locations_gh
WHERE gh LIKE :'box_pat'
  AND geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

\echo ''
\echo '--- (c) GiST: exact, in one operator ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM locations_gh
WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))';

\echo ''
\echo '--- Precision and recall of the geohash approach ---'
SELECT
  (SELECT count(*) FROM locations_gh WHERE gh LIKE :'box_pat')            AS candidates_returned,
  (SELECT count(*) FROM locations_gh
     WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))')              AS true_answer,
  (SELECT count(*) FROM locations_gh
     WHERE geolocation <@ box '((-74.1,40.6),(-73.7,40.9))'
       AND gh NOT LIKE :'box_pat')                                       AS missed_by_geohash;


-- --------------------------------------------------------------------------
-- 3. The boundary problem, measured
-- --------------------------------------------------------------------------
\echo ''
\echo '======================================================================'
\echo ' 3. Two points 100 m apart can have nothing in common'
\echo '======================================================================'
\echo 'A geohash cell is a grid square, so proximity in space does not imply a'
\echo 'shared prefix -- a point just west of a cell edge and one just east of it'
\echo 'may diverge at the very first character. 1000 random pairs, each exactly'
\echo 'one pair 100 m apart, sampled over the NYC area:'

WITH a AS (
  SELECT ST_SetSRID(ST_MakePoint(-74.0 + random()*0.5, 40.6 + random()*0.4), 4326) AS p
  FROM generate_series(1, 1000)
), pairs AS (
  SELECT p,
         ST_SetSRID(ST_MakePoint(ST_X(p) + 0.0012, ST_Y(p)), 4326) AS q  -- ~100 m east
  FROM a
), gh AS (
  -- The geography cast is what makes "100 m" a real number. In the built-in
  -- point type 0.0012 degrees of longitude is not a distance at all; it is
  -- ~101 m at New York's latitude and ~133 m at the equator.
  SELECT ST_Distance(p::geography, q::geography) AS metres,
         ST_GeoHash(p, 7) AS gp, ST_GeoHash(q, 7) AS gq
  FROM pairs
)
SELECT count(*)                                                   AS pairs_tested,
       round(avg(metres)::numeric, 1)                             AS avg_metres_apart,
       count(*) FILTER (WHERE gp <> gq)                           AS in_different_cells,
       count(*) FILTER (WHERE left(gp,5) <> left(gq,5))           AS differ_by_char_5,
       count(*) FILTER (WHERE left(gp,3) <> left(gq,3))           AS differ_by_char_3
FROM gh;

\echo ''
\echo 'This is why a correct geohash "nearby" search must query the cell PLUS its'
\echo 'eight neighbours and then re-check distances -- nine range scans and a'
\echo 'post-filter to answer what GiST answers with one operator. GiST''s bounding'
\echo 'boxes overlap and adapt to the data, so it has no equivalent of an edge.'


-- --------------------------------------------------------------------------
-- 4. K-NN: the thing geohash cannot do
-- --------------------------------------------------------------------------
\echo ''
\echo '======================================================================'
\echo ' 4. "100 nearest points to Times Square"'
\echo '======================================================================'

\echo ''
\echo '--- (a) GiST: one ordered index scan, stops after 100 rows ---'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, geolocation
FROM locations_gh
ORDER BY geolocation <-> POINT(-73.9855, 40.7580)
LIMIT 100;

-- The precision-5 cell (~4.9 km) containing Times Square.
SELECT ST_GeoHash(ST_SetSRID(ST_MakePoint(-73.9855, 40.7580), 4326), 5) || '%' AS knn_pat \gset
\echo ''
\echo 'Times Square precision-5 cell pattern:'
\echo :'knn_pat'

\echo ''
\echo '--- (b) Geohash: scan a cell, then sort what you found ---'
\echo '    The sort is a real Sort node over every row in the cell. And the'
\echo '    result is only correct if the 100th nearest point is inside this cell;'
\echo '    otherwise the query silently returns neighbours that are not the'
\echo '    nearest. There is no "stop when you have K" -- geohash has no ordering'
\echo '    by distance, only by cell.'
EXPLAIN (ANALYZE, BUFFERS)
SELECT location_id, geolocation
FROM locations_gh
WHERE gh LIKE :'knn_pat'
ORDER BY geolocation <-> POINT(-73.9855, 40.7580)
LIMIT 100;

\echo ''
\echo '--- How many rows are even in that cell? ---'
\echo '    If this is below 100, the query above is wrong and the application'
\echo '    has to widen the prefix and try again -- the retry loop that every'
\echo '    geohash-based nearby-search implementation ends up carrying.'
SELECT count(*) AS rows_in_precision5_cell
FROM locations_gh WHERE gh LIKE :'knn_pat';
