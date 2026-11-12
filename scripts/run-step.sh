#!/usr/bin/env bash
# Run one SQL step and save a timestamped transcript for the report.
#
#   bash scripts/run-step.sh 04_baseline
#   bash scripts/run-step.sh --cold 04_baseline
#   bash scripts/run-step.sh 06_after_gist
#
# --cold restarts PostgreSQL and drops the OS page cache first, so the "before"
# numbers are genuinely cold. Without it you are partly measuring what happened
# to still be in RAM from the previous step, which is the flaw in the tutorial's
# own 5997 ms vs 10 ms comparison. Needs root (you are root on the VM).
set -euo pipefail

CT=${CT:-week3-postgres}
RUNNER=${RUNNER:-docker}
COLD=0
STEP=""

for arg in "$@"; do
  case "$arg" in
    --cold) COLD=1 ;;
    *)      STEP="$arg" ;;
  esac
done

if [ -z "$STEP" ]; then
  echo "usage: bash scripts/run-step.sh [--cold] <step>   e.g. 04_baseline" >&2
  exit 1
fi

if [ "$COLD" = "1" ]; then
  echo "== restarting postgres and dropping the OS page cache =="
  "$RUNNER" restart "$CT" >/dev/null
  sync
  echo 3 > /proc/sys/vm/drop_caches
  # -h 127.0.0.1: TCP, not the socket, so a server still starting up is not
  # mistaken for a ready one. Same reasoning as wait_for_postgres in bootstrap.sh.
  until "$RUNNER" exec "$CT" pg_isready -h 127.0.0.1 -U postgres -d geo >/dev/null 2>&1; do sleep 2; done
  echo "   ready"
fi

mkdir -p transcripts
OUT="transcripts/${STEP}-$(date +%Y%m%d-%H%M%S).txt"

# -e echoes each statement before its output, so the transcript reads like a
# real psql session and can be screenshotted straight into the PDF.
"$RUNNER" exec "$CT" psql -U postgres -d geo -e \
    -v ON_ERROR_STOP=1 \
    -f "/sql/${STEP}.sql" 2>&1 | tee "$OUT"

echo
echo "Saved: $OUT"
