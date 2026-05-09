#!/bin/bash
set -eu

exec celery -A procollab worker --beat --loglevel="${CELERY_LOG_LEVEL:-info}"
