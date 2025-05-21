"""
Script to run the Credit Lense tests with coverage.
"""
import os
import sys
import subprocess

def main():
    """Run the tests with coverage using pytest."""
    # Add the project root to the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    
    # Create output directory for test reports
    os.makedirs("test_reports", exist_ok=True)
    
    # Run the tests with coverage
    subprocess.run([
        "pytest", 
        "tests/", 
        "-v", 
        "--cov=app", 
        "--cov-report=term", 
        "--cov-report=html:test_reports/coverage"
    ], check=True)

if __name__ == "__main__":
    main()
