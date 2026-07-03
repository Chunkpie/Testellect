#!/bin/bash
set -e

echo "Waiting for Ollama to be ready..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
  sleep 2
done
echo "Ollama is ready."

echo "Starting backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
