#!/bin/bash

echo "🚀 Starting FastAPI server..."

# Get the absolute path to the project root
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Change to the project root
cd "$PROJECT_ROOT"

# Set up environment
export PYTHONPATH="$PROJECT_ROOT"

echo "✅ Using uv environment"
# Just run uvicorn directly 
uvicorn app.main:app --reload --port 5002
