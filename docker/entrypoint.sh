#!/bin/sh
set -eu

if [ "${1:-}" = "api" ]; then
    shift
    exec uvicorn gordon_doc_converter.api.app:create_app \
        --factory --host 0.0.0.0 --port 8000 "$@"
fi

exec gordon-doc "$@"