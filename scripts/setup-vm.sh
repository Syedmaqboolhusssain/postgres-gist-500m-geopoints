#!/usr/bin/env bash
# Provision a fresh Hetzner Ubuntu 24.04 server for this assignment.
# Run as root:  bash scripts/setup-vm.sh
set -euo pipefail

echo "== installing Docker and utilities =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-v2 tmux jq

echo "== Docker version =="
docker --version
docker compose version

echo "== disk check =="
df -h /
echo
echo "You need roughly 120 GB free for the full 500M run:"
echo "  ~36 GB heap + ~33 GB GiST + ~11 GB primary key + sort and WAL headroom."
echo "  The geohash comparison table adds another ~10 GB."

echo
echo "== next =="
cat <<'EOF'
  cd <this directory>
  docker compose up -d
  docker compose ps

  # pgAdmin is on port 5050. Do NOT expose it to the internet unchanged --
  # tunnel it instead, from your laptop:
  #     ssh -L 5050:localhost:5050 -L 5432:localhost:5432 root@<server-ip>
  # then open http://localhost:5050

  # Work inside tmux so a dropped SSH session does not kill a 40-minute load:
  tmux new -s week3
EOF
