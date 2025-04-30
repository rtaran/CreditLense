#!/bin/bash

echo "🧪 Running Credit Lense tests..."

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if ! command -v pytest &> /dev/null
then
    echo "📥 Installing pytest and test dependencies..."
    pip install pytest pytest-cov httpx
fi

# Check for google.generativeai
if ! python -c "import google.generativeai" &> /dev/null
then
    echo "📥 Installing google-generativeai..."
    pip install google-generativeai
fi

# Check for other required packages
if ! python -c "import openai" &> /dev/null
then
    echo "📥 Installing openai..."
    pip install openai
fi

if ! python -c "import docx" &> /dev/null
then
    echo "📥 Installing python-docx..."
    pip install python-docx
fi

# Create output directory for test reports
mkdir -p test_reports

# Run the tests with coverage
echo "🚀 Running tests with coverage..."
# Add the current directory to PYTHONPATH to ensure app module can be found
PYTHONPATH=. pytest tests/ -v --cov=app --cov-report=term --cov-report=html:test_reports/coverage

# Check the exit code
if [ $? -eq 0 ]
then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi

echo "📊 Coverage report generated in test_reports/coverage/"
echo "📝 To view the coverage report, open test_reports/coverage/index.html in a browser."
