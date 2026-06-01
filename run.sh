#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv
source venv/bin/activate

# Find free port
PORT=5000
for p in $(seq 5000 5010); do
  if ! nc -z localhost $p 2>/dev/null; then
    PORT=$p
    break
  fi
done

if [ $PORT -gt 5010 ]; then
  echo "Error: No free port found (5000-5010)"
  exit 1
fi

echo "Starting Pokédex Tracker on port $PORT..."

# Start Flask
FLASK_PORT=$PORT python app.py &
FLASK_PID=$!

# Wait for Flask to be ready (max 5s)
for i in $(seq 1 10); do
  sleep 0.5
  if nc -z localhost $PORT 2>/dev/null; then
    break
  fi
done

if ! nc -z localhost $PORT 2>/dev/null; then
  echo "Error: Flask failed to start on port $PORT"
  kill $FLASK_PID 2>/dev/null
  exit 1
fi

echo "App running at http://localhost:$PORT"
open "http://localhost:$PORT"

# Keep running
wait $FLASK_PID
