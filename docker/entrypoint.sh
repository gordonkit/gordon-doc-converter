#!/bin/sh
set -eu

if [ "${1:-}" = "api" ]; then
    if [ -z "${GORDON_DOC_API_KEY:-}" ]; then
        echo "GORDON_DOC_API_KEY must be set when starting the API" >&2
        exit 64
    fi
    shift
    exec uvicorn gordon_doc_converter.api.app:create_app \
        --factory --host 0.0.0.0 --port 8000 "$@"
fi

exec gordon-doc "$@"