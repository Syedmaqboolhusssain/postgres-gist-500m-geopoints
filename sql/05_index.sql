-- Step 5 (tutorial) -- create the GiST index.
--
-- Worth knowing before you watch the clock: since PostgreSQL 14, the point_ops
-- operator class provides "sort support" for GiST, so this is not the slow
-- one-row-at-a-time tree insertion it used to be. PostgreSQL sorts all 500M
-- points along a Z-order (Morton) space-filling curve and then packs the tree
-- bottom-up in one pass.
--
-- That detail matters for the geohash half of this assignment: a geohash string
-- IS a Z-order curve position, base32-encoded. So PostgreSQL is internally doing
-- the same spatial linearisation that geohashing does explicitly -- it just keeps
-- the result inside the index instead of in a user-visible column. Make this
-- point in the report.

\timing on

SET maintenance_work_mem = '4GB';   -- larger = fewer external sort merge passes

CREATE INDEX idx_locations_gist ON locations USING gist (geolocation);

-- Re-ANALYZE so the planner's selectivity estimates account for the new index.
ANALYZE locations;

\echo ''
\echo '--- Index built. Sizes: ---'
SELECT
  indexrelid::regclass AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_index
WHERE indrelid = 'locations'::regclass
ORDER BY pg_relation_size(indexrelid) DESC;

-- Step 11 (tutorial) notes, verified rather than quoted:
--   * CLUSTER is not supported on GiST -- there is no single physical order a
--     space-filling tree can be sorted into. Uncomment to show the error:
-- CLUSTER locations USING idx_locations_gist;
--
--   * For a live system you would build without blocking writes:
-- CREATE INDEX CONCURRENTLY idx_locations_gist ON locations USING gist (geolocation);
--     Do not use CONCURRENTLY here -- it is roughly twice as slow and you are not
--     serving traffic.
