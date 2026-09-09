#!/usr/bin/env sh
set -eu

mkdir -p /data

refresh_report() {
  etl run
  dashboard --output /data/index.html
}

refresh_report

python -m http.server 8000 --directory /data &

idle_timeout_ms=$((${ETL_INTERVAL_SECONDS:-60} * 1000))
while true; do
  kafka-sink --max-messages 100 --idle-timeout-ms "$idle_timeout_ms" || true
  refresh_report || true
done
