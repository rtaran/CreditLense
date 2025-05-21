"""
Script to run the Credit Lense FastAPI application.
"""
import os
import sys
import uvicorn

def main():
    """Run the FastAPI application using uvicorn."""
    # Add the project root to the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    
    # Run the application
    uvicorn.run("app.main:app", host="127.0.0.1", port=5002, reload=True)

if __name__ == "__main__":
    main()
