#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

uvicorn app:app --reload --host "$APP_HOST" --port "$APP_PORT" --log-level info --workers 1
