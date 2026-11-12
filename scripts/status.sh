#!/usr/bin/env bash
# One-shot progress summary. Safe to run at any time, including mid-load.
#
#   bash scripts/status.sh
set -uo pipefail

cd "${PROJECT_DIR:-/root/week3-postgres-gist}"
CT=${CT:-week3-postgres}
RUNNER=${RUNNER:-docker}

echo "=== bootstrap ==="
systemctl is-active week3-bootstrap 2>/dev/null || true
echo "stage: $(cat .bootstrap-stage 2>/dev/null || echo 'not started')"
[ -f .bootstrap-stage.failed ] && cat .bootstrap-stage.failed

echo
echo "=== containers ==="
"$RUNNER" ps --format '{{.Names}}  {{.Status}}' 2>/dev/null || echo "docker not reachable"

echo
echo "=== data ==="
# Deliberately reads pg_relation_size and not count(*): counting rows on a
# growing 500M table is itself a minutes-long sequential scan.
"$RUNNER" exec "$CT" psql -U postgres -d geo -tAc "
  SELECT 'heap        ' || pg_size_pretty(pg_relation_size('locations'))
  UNION ALL
  SELECT 'indexes     ' || pg_size_pretty(pg_indexes_size('locations'))
  UNION ALL
  SELECT 'total       ' || pg_size_pretty(pg_total_relation_size('locations'))
  UNION ALL
  SELECT 'est. rows   ' || to_char(reltuples::bigint, 'FM999,999,999,999')
    FROM pg_class WHERE relname = 'locations';
" 2>/dev/null || echo "locations table not created yet"

echo
echo "=== indexes ==="
"$RUNNER" exec "$CT" psql -U postgres -d geo -tAc "
  SELECT indexrelid::regclass || '  ' || pg_size_pretty(pg_relation_size(indexrelid))
  FROM pg_index WHERE indrelid = 'locations'::regclass;
" 2>/dev/null || true

echo
echo "=== disk ==="
df -h / | tail -1
echo "(the GiST build wants ~40 GB free when it starts)"

echo
echo "=== transcripts ==="
ls -1 transcripts/ 2>/dev/null || echo "none yet"

echo
echo "=== last 15 lines of bootstrap.log ==="
tail -15 transcripts/bootstrap.log 2>/dev/null || echo "no log yet"
