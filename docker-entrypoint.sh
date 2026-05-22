#!/usr/bin/env bash
set -euo pipefail

JOB="${JOB:-ingest}"
python -m flights.db init

case "$JOB" in
  ingest)
    exec python -m flights.ingest --once --provider "${INGEST_PROVIDER:-google}" \
      --max-days "${INGEST_MAX_DAYS:-14}" \
      --start-offset-days "${INGEST_START_OFFSET_DAYS:-3}"
    ;;
  alert)
    exec python -m flights.alert_job
    ;;
  *)
    echo "Unknown JOB=$JOB (use ingest or alert)" >&2
    exit 1
    ;;
esac
