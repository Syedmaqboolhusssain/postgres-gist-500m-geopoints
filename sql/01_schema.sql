-- Step 1 (tutorial) -- create the locations table.
--
-- The tutorial's DDL is:
--
--     CREATE TABLE locations (
--         location_id  BIGSERIAL PRIMARY KEY,
--         name         TEXT,
--         geolocation  POINT
--     );
--
-- Three deviations are needed at 500M rows. Each one belongs in the report,
-- because each is a real bulk-loading decision, not a shortcut:
--
--   1. UNLOGGED. A logged load of 500M rows writes every row to the WAL as well
--      as the heap, roughly doubling the I/O for data we can regenerate in an
--      hour. UNLOGGED skips the WAL entirely. The trade-off is that the table is
--      truncated if the server crashes -- acceptable for a benchmark fixture.
--
--   2. No PRIMARY KEY during the load. A B-tree maintained row-by-row across
--      500M inserts is far slower, and more bloated, than one built in a single
--      pass afterwards. The key is added in 03_finalize_load.sql, so the final
--      schema matches the tutorial exactly.
--
--   3. location_id supplied explicitly instead of via BIGSERIAL. Four concurrent
--      loader sessions all drawing from one sequence is pointless contention when
--      each session already knows its own id range. The sequence is created and
--      set to the right value afterwards so the table is still a drop-in match.

\timing on

CREATE EXTENSION IF NOT EXISTS postgis;      -- for ST_GeoHash in 08_geohash.sql
CREATE EXTENSION IF NOT EXISTS pg_prewarm;   -- for warming the cache between runs

DROP TABLE IF EXISTS locations;

CREATE UNLOGGED TABLE locations (
    location_id  BIGINT NOT NULL,
    name         TEXT,
    geolocation  POINT        -- (x, y) = (longitude, latitude), per the tutorial
);

\echo 'Schema created. Next: scripts/run-load.sh'
