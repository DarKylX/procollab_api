#!/usr/bin/env bash
set -euo pipefail

mkdir -p /procollab/log

TIMEOUT="${TELEGRAM_POLLING_TIMEOUT:-10}"
SLEEP="${TELEGRAM_POLLING_SLEEP:-1}"

echo "Starting Telegram polling with timeout=${TIMEOUT}, sleep=${SLEEP}"

python manage.py poll_telegram_updates \
  --keep-webhook \
  --timeout "${TIMEOUT}" \
  --sleep "${SLEEP}" \
  2>&1 | tee -a /procollab/log/telegram_polling.log
