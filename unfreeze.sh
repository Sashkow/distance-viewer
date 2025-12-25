#!/bin/bash
# Unfreeze app - kills all uvicorn and python processes related to this app

echo "Killing uvicorn processes..."
pkill -9 -f "uvicorn app:app"

echo "Killing python app.py processes..."
pkill -9 -f "python app.py"

echo "Killing processes on port 5000..."
lsof -ti:5000 | xargs -r kill -9

echo "All app processes killed. You can now restart with:"
echo "  uv run uvicorn app:app --host 0.0.0.0 --port 5000 --reload"
