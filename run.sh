echo "🚀 Starting FastAPI server..."

# Check if `uv` is installed
if command -v uv &> /dev/null
then
    echo "✅ Using uv environment"
    uv run uvicorn app.main:app --reload --port 5000
else
    echo "⚠️ uv not found, using system Python environment"
    uvicorn app.main:app --reload --port 5000
fi