# Credit Lense Test Suite

This directory contains tests for the Credit Lense application. The tests are organized into unit tests and integration tests.

## Test Structure

```
tests/
├── conftest.py           # Test fixtures and configuration
├── unit/                 # Unit tests
│   ├── test_models.py    # Tests for database models
│   ├── test_llm_service.py # Tests for LLM service
│   └── test_formatter.py # Tests for memo formatter
└── integration/          # Integration tests
    ├── test_document_endpoints.py # Tests for document API endpoints
    └── test_memo_endpoints.py     # Tests for memo API endpoints
```

## Test Fixtures

The `conftest.py` file contains fixtures that are used across multiple test files:

- `client`: A test client for making requests to the FastAPI application
- `db_session`: A database session for interacting with the test database
- `sample_document`: A sample document in the database
- `sample_memo`: A sample memo in the database
- `mock_llm_service`: A mock of the LLM service to avoid making actual API calls

## Running Tests

You can run the tests using the provided `run_tests.sh` script:

```bash
./run_tests.sh
```

This will run all tests and generate a coverage report in the `test_reports/coverage` directory.

### Running Specific Tests

To run specific tests, you can use pytest directly:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run tests for a specific file
pytest tests/unit/test_models.py

# Run a specific test
pytest tests/unit/test_models.py::test_company_data_model
```

## Test Coverage

The tests aim to cover all critical functionality of the application:

1. **Database Models**: Tests for creating, reading, updating, and deleting records
2. **LLM Service**: Tests for text generation with different providers and error handling
3. **Memo Formatter**: Tests for formatting memos as Word documents
4. **API Endpoints**: Tests for all API endpoints, including error handling

## Adding New Tests

When adding new tests, follow these guidelines:

1. Place unit tests in the `tests/unit/` directory
2. Place integration tests in the `tests/integration/` directory
3. Use descriptive test names that indicate what is being tested
4. Use fixtures from `conftest.py` when possible
5. Mock external services to avoid making actual API calls
6. Add appropriate assertions to verify the expected behavior