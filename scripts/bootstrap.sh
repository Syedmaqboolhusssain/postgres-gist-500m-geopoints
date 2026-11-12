#!/usr/bin/env bash
# The whole pipeline, unattended. Started by the week3-bootstrap systemd unit
# that Terraform installs, so it survives SSH disconnects and reboots.
#
# Environment (set by the unit):
#   PROJECT_DIR    where the project lives
#   TOTAL_POINTS   how many points to generate
#   AUTO_PIPELINE  load | full | none
#
# set -e is important here. If the baseline step fails, the run must stop BEFORE
# the GiST index is built -- the "before" numbers can only be measured once, and
# recovering them after the index exists means a 40-minute rebuild.
set -euo pipefail

cd "${PROJECT_DIR:-/root/week3-postgres-gist}"

TOTAL_POINTS=${TOTAL_POINTS:-500000000}
AUTO_PIPELINE=${AUTO_PIPELINE:-full}
STAGE_FILE=".bootstrap-stage"
START=$(date +%s)
RUNNER=${RUNNER:-docker}

log()   { echo "[$(date +%FT%T)] $*"; }
stage() { echo "$1" >"$STAGE_FILE"; log "===== STAGE: $1 ====="; }
fail()  { echo "FAILED at stage: $(cat "$STAGE_FILE" 2>/dev/null)" >"$STAGE_FILE.failed"; }
trap fail ERR

# On a fresh volume the postgres image runs initdb, then a TEMPORARY server that
# listens only on the Unix socket, shuts it down, and starts the real one. A
# socket-based pg_isready reports "ready" during that temporary phase, and the
# next command lands in the restart gap with "rejecting connections". Checking
# over TCP skips the temporary server, which never listens on TCP, and requiring
# several consecutive successes covers the restart itself.
wait_for_postgres() {
  local ok=0
  log "waiting for postgres to accept TCP connections"
  for _ in $(seq 1 120); do
    if "$RUNNER" exec week3-postgres pg_isready -h 127.0.0.1 -U postgres -d geo >/dev/null 2>&1; then
      ok=$((ok + 1))
      if [ "$ok" -ge 3 ]; then log "postgres ready"; return 0; fi
    else
      ok=0
    fi
    sleep 2
  done
  log "postgres never became ready"
  return 1
}

mkdir -p transcripts
rm -f "$STAGE_FILE.failed"      # a previous failed run must not look current
log "bootstrap starting: TOTAL_POINTS=$TOTAL_POINTS AUTO_PIPELINE=$AUTO_PIPELINE"
df -h / | tail -1

# --------------------------------------------------------------------------
stage "starting containers"
docker compose up -d
wait_for_postgres

# --------------------------------------------------------------------------
stage "creating schema"
bash scripts/run-step.sh 01_schema

# --------------------------------------------------------------------------
# A 5M smoke load first. It costs a few minutes and catches a typo in the SQL or
# a bad mount before the real load has burned an hour. Then the schema is
# recreated, which drops the smoke data.
stage "smoke test (5M points)"
TOTAL=5000000 WORKERS=2 bash scripts/run-load.sh
bash scripts/run-step.sh 01_schema

# --------------------------------------------------------------------------
stage "loading ${TOTAL_POINTS} points"
TOTAL="$TOTAL_POINTS" bash scripts/run-load.sh

stage "finalizing load (primary key, sequence, ANALYZE)"
bash scripts/run-step.sh 03_finalize_load

if [ "$AUTO_PIPELINE" != "full" ]; then
  stage "DONE (data loaded; measurement steps left for you)"
  log "run these yourself, in this order:"
  log "  bash scripts/run-step.sh --cold 04_baseline"
  log "  bash scripts/run-step.sh 05_index"
  log "  bash scripts/run-step.sh --cold 06_after_gist"
  log "  bash scripts/run-step.sh 07_verify"
  log "  bash scripts/run-step.sh 08_geohash"
  exit 0
fi

# --------------------------------------------------------------------------
stage "baseline: BEFORE GiST (one shot only)"
bash scripts/run-step.sh --cold 04_baseline

stage "building GiST index"
bash scripts/run-step.sh 05_index

stage "AFTER GiST"
bash scripts/run-step.sh --cold 06_after_gist

stage "verifying index usage, sizes, correctness"
bash scripts/run-step.sh 07_verify

stage "geohash vs GiST comparison"
bash scripts/run-step.sh 08_geohash

# --------------------------------------------------------------------------
trap - ERR
stage "DONE"
log "total elapsed: $(( ($(date +%s) - START) / 60 )) minutes"
log "transcripts:"
ls -la transcripts/
df -h / | tail -1
