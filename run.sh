#!/bin/sh

export APP_MODULE=${APP_MODULE-app.main:app}
export HOST=${API_HOST:-0.0.0.0}
export PORT=${API_PORT:-8001}

exec uvicorn --host $HOST --port $PORT "$APP_MODULE"
