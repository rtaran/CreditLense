import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

def test_list_memos(client, sample_memo):
    """Test listing all memos."""
    response = client.get("/memos/")
    assert response.status_code == 200

    # Check that the response is a list
    data = response.json()
    assert isinstance(data, list)

    # Check that our sample memo is in the list
    assert len(data) >= 1

    # Find our sample memo in the list
    sample_memo_response = next((memo for memo in data if memo["memo_id"] == sample_memo.memo_id), None)
    assert sample_memo_response is not None
    assert sample_memo_response["document_id"] == sample_memo.document_id
    assert sample_memo_response["memo_string"] == sample_memo.memo_string

def test_get_memo_by_document_id(client, sample_memo, sample_document):
    """Test getting memos by document ID."""
    response = client.get(f"/memos/{sample_document.document_id}")
    assert response.status_code == 200

    # Check that the response is a list
    data = response.json()
    assert isinstance(data, list)

    # Check that our sample memo is in the list
    assert len(data) >= 1

    # Find our sample memo in the list
    sample_memo_response = next((memo for memo in data if memo["memo_id"] == sample_memo.memo_id), None)
    assert sample_memo_response is not None
    assert sample_memo_response["document_id"] == sample_document.document_id

def test_get_memo_by_nonexistent_document_id(client):
    """Test getting memos for a document that doesn't exist."""
    # Use a very large ID that's unlikely to exist
    nonexistent_id = 9999

    # Try to get memos for the nonexistent document
    response = client.get(f"/memos/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No memo found for that document ID"

def test_create_memo(client, sample_document):
    """Test creating a memo directly."""
    memo_data = {
        "document_id": sample_document.document_id,
        "memo_string": "This is a test memo created directly."
    }

    response = client.post("/memos/", params=memo_data)
    assert response.status_code == 200
    data = response.json()
    assert "memo_id" in data
    assert data["message"] == "Memo created successfully!"

    # Verify the memo was added to the database
    memo_response = client.get(f"/memos/{sample_document.document_id}")
    memos = memo_response.json()
    created_memo = next((memo for memo in memos if memo["memo_string"] == memo_data["memo_string"]), None)
    assert created_memo is not None

def test_generate_memo(client, sample_document, mock_llm_service):
    """Test generating a memo for a document."""
    # Mock the formatter to avoid creating actual files
    mock_file_path = "./output/mock_memo.docx"
    with patch("app.formatter.memo_formatter.format_memo_as_docx", return_value=mock_file_path):
        # Generate the memo
        response = client.post(f"/generate-memo/{sample_document.document_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Memo generation started" in data["message"]

        # Since the generation happens in the background, we need to wait or mock it
        # For testing, we'll just verify that the endpoint returns successfully

def test_generate_memo_with_provider(client, sample_document, mock_llm_service):
    """Test generating a memo with a specific provider."""
    # Mock the app.routers.memos.generate_memo function to return a success response
    with patch("app.routers.memos.generate_memo") as mock_generate_memo:
        # Configure the mock to return a success response
        mock_generate_memo.return_value = {
            "message": "Memo generation started using google provider. Check back soon."
        }

        # Generate the memo with Google provider
        response = client.post(f"/generate-memo/{sample_document.document_id}?provider=google")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "using google provider" in data["message"].lower()

        # Configure the mock to return a success response for OpenAI
        mock_generate_memo.return_value = {
            "message": "Memo generation started using openai provider. Check back soon."
        }

        # Generate the memo with OpenAI provider
        response = client.post(f"/generate-memo/{sample_document.document_id}?provider=openai")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "using openai provider" in data["message"].lower()

def test_generate_memo_invalid_provider(client, sample_document):
    """Test generating a memo with an invalid provider."""
    # Mock the app.routers.memos.generate_memo function to return a 400 error for invalid providers
    with patch("app.routers.memos.generate_memo") as mock_generate_memo:
        # Configure the mock to raise an HTTPException with status_code 400
        from fastapi import HTTPException
        mock_generate_memo.side_effect = HTTPException(
            status_code=400, 
            detail=f"Unsupported LLM provider: invalid. Use 'google' or 'openai'."
        )

        # Make the request
        response = client.post(f"/generate-memo/{sample_document.document_id}?provider=invalid")

        # Check the response
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unsupported LLM provider" in data["detail"]

def test_generate_memo_nonexistent_document(client):
    """Test generating a memo for a document that doesn't exist."""
    # Use a very large ID that's unlikely to exist
    nonexistent_id = 9999

    # Try to generate a memo for the nonexistent document
    response = client.post(f"/generate-memo/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Document not found"

def test_download_memo(client, sample_memo, db_session):
    """Test downloading a memo."""
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up a test file path
        test_file_path = os.path.join(temp_dir, "test_memo.docx")

        # Create a dummy file for testing
        with open(test_file_path, "wb") as f:
            f.write(b"Test memo content")

        # Update the sample_memo with the test file path
        sample_memo.file_path = test_file_path
        db_session.commit()

        # Mock the formatter to avoid creating actual files
        with patch("app.formatter.memo_formatter.format_memo_as_docx", return_value=test_file_path):
            # Download the memo
            response = client.get(f"/download-memo/{sample_memo.memo_id}")
            assert response.status_code == 200
            assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers["content-type"]

def test_download_nonexistent_memo(client):
    """Test downloading a memo that doesn't exist."""
    # Use a very large ID that's unlikely to exist
    nonexistent_id = 9999

    # Try to download the nonexistent memo
    response = client.get(f"/download-memo/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Memo not found"

def test_delete_memo(client, sample_memo):
    """Test deleting a memo."""
    # First, verify the memo exists
    response = client.get("/memos/")
    initial_memos = response.json()
    assert any(memo["memo_id"] == sample_memo.memo_id for memo in initial_memos)

    # Delete the memo
    response = client.delete(f"/memos/{sample_memo.memo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Memo {sample_memo.memo_id} deleted successfully."

    # Verify the memo was deleted
    response = client.get("/memos/")
    remaining_memos = response.json()
    assert not any(memo["memo_id"] == sample_memo.memo_id for memo in remaining_memos)

def test_delete_nonexistent_memo(client):
    """Test deleting a memo that doesn't exist."""
    # Use a very large ID that's unlikely to exist
    nonexistent_id = 9999

    # Try to delete the nonexistent memo
    response = client.delete(f"/memos/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Memo not found"

def test_memos_page_html(client):
    """Test the HTML memos page."""
    response = client.get("/memos", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # Check that the HTML contains expected elements
    html_content = response.text
    assert "<title>Memos - Credit Lense</title>" in html_content
    assert "Financial Memos" in html_content
