#!/bin/bash

echo "🚀 Starting FastAPI server..."

# Check if `uv` is installed
if command -v uv &> /dev/null
then
    echo "✅ Using uv environment"
    cd ..
    uv run uvicorn app.main:app --reload --port 5001
else
    echo "⚠️ uv not found, using system Python environment"
    cd ..
    uvicorn app.main:app --reload --port 5001
fi