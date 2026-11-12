#!/usr/bin/env bash
# Load TOTAL random points using WORKERS concurrent sessions on disjoint id
# ranges, BATCH rows per transaction.
#
#   bash scripts/run-load.sh                  # 500M, 4 workers, 10M batches
#   TOTAL=50000000 bash scripts/run-load.sh   # 50M smoke test first -- do this
#
# Always run the smoke test before the real thing. It takes a few minutes and
# tells you the per-batch rate, which is what you multiply up to decide whether
# the full load fits in the evening you have.
set -euo pipefail

TOTAL=${TOTAL:-500000000}
BATCH=${BATCH:-10000000}
WORKERS=${WORKERS:-4}
CT=${CT:-week3-postgres}
RUNNER=${RUNNER:-docker}

per=$(( TOTAL / WORKERS ))
started=$(date +%s)

echo "Loading $TOTAL rows: $WORKERS workers x $(( per / BATCH )) batches of $BATCH"
echo "Started $(date +%T)"
echo

worker() {
  local w=$1 lo=$2 end=$3 hi t0
  while [ "$lo" -le "$end" ]; do
    hi=$(( lo + BATCH - 1 ))
    [ "$hi" -gt "$end" ] && hi=$end
    t0=$(date +%s)
    "$RUNNER" exec "$CT" psql -U postgres -d geo -q \
        -v ON_ERROR_STOP=1 -v lo="$lo" -v hi="$hi" \
        -f /sql/02_generate_batch.sql
    printf '[w%d] %s  rows %11d..%-11d  %4ds\n' \
        "$w" "$(date +%T)" "$lo" "$hi" "$(( $(date +%s) - t0 ))"
    lo=$(( hi + 1 ))
  done
}

for w in $(seq 1 "$WORKERS"); do
  s=$(( (w - 1) * per + 1 ))
  e=$(( w * per ))
  [ "$w" -eq "$WORKERS" ] && e=$TOTAL      # last worker absorbs any remainder
  worker "$w" "$s" "$e" &
done
wait

echo
echo "Finished $(date +%T) -- total $(( ($(date +%s) - started) / 60 )) minutes"
echo "Next: $RUNNER exec -it $CT psql -U postgres -d geo -f /sql/03_finalize_load.sql"
echo
echo "To watch progress from another shell (count(*) on a growing 500M table is"
echo "itself a minutes-long seq scan, so watch the file size instead):"
echo "  watch -n30 \"$RUNNER exec $CT psql -U postgres -d geo -tAc \\\"SELECT pg_size_pretty(pg_relation_size('locations'))\\\"\""
