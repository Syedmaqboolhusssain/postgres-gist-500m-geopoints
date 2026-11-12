-- Step 2 (tutorial) -- insert random points, one batch at a time.
--
-- The tutorial does the whole load in a single statement:
--
--     INSERT INTO locations (name, geolocation)
--     SELECT 'Location_' || g,
--            POINT(-180 + random()*360, -90 + random()*180)
--     FROM generate_series(1, 10000000) AS g;
--
-- That is fine at 10M. At 500M it is one transaction holding ~36 GB of dirty
-- pages, with no progress output and no way to stop it without losing everything.
-- Same statement, run 50 times over 10M-row windows, with :lo and :hi passed in
-- by scripts/run-load.sh.
--
-- Note that random() is PARALLEL RESTRICTED, so PostgreSQL will not parallelise
-- this INSERT internally no matter how many workers are configured. That is why
-- run-load.sh starts four separate client sessions on disjoint id ranges -- the
-- parallelism has to come from outside the server.

INSERT INTO locations (location_id, name, geolocation)
SELECT g,
       'Location_' || g,
       POINT( -180 + random()*360,      -- longitude
              -90  + random()*180 )     -- latitude
FROM generate_series(:lo, :hi) AS g;
