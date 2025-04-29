import pytest
import io
from fastapi import UploadFile
from unittest.mock import patch, MagicMock

def test_list_documents(client, sample_document):
    """Test listing all documents."""
    response = client.get("/documents/")
    assert response.status_code == 200
    
    # Check that the response is a list
    data = response.json()
    assert isinstance(data, list)
    
    # Check that our sample document is in the list
    assert len(data) >= 1
    
    # Find our sample document in the list
    sample_doc = next((doc for doc in data if doc["document_id"] == sample_document.document_id), None)
    assert sample_doc is not None
    assert sample_doc["pdf_file_name"] == sample_document.pdf_file_name
    assert sample_doc["company_name"] == sample_document.company_name

def test_upload_document(client):
    """Test uploading a document."""
    # Mock the PDF extraction function to avoid needing a real PDF
    with patch("app.routers.documents.extract_text_from_pdf", return_value="Mocked PDF content"):
        # Create a mock file
        file_content = b"Fake PDF content"
        file = io.BytesIO(file_content)
        
        # Send the request
        response = client.post(
            "/documents/",
            files={"file": ("test_upload.pdf", file, "application/pdf")},
            data={"company_name": "Test Upload Company"}
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test_upload.pdf"
        assert data["company_name"] == "Test Upload Company"
        assert "document_id" in data
        assert data["message"] == "Document uploaded successfully!"
        
        # Verify the document was added to the database
        doc_response = client.get("/documents/")
        docs = doc_response.json()
        uploaded_doc = next((doc for doc in docs if doc["pdf_file_name"] == "test_upload.pdf"), None)
        assert uploaded_doc is not None
        assert uploaded_doc["company_name"] == "Test Upload Company"

def test_delete_document(client, sample_document):
    """Test deleting a document."""
    # First, verify the document exists
    response = client.get("/documents/")
    initial_docs = response.json()
    assert any(doc["document_id"] == sample_document.document_id for doc in initial_docs)
    
    # Delete the document
    response = client.delete(f"/documents/{sample_document.document_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Document {sample_document.document_id} deleted successfully."
    
    # Verify the document was deleted
    response = client.get("/documents/")
    remaining_docs = response.json()
    assert not any(doc["document_id"] == sample_document.document_id for doc in remaining_docs)

def test_delete_nonexistent_document(client):
    """Test deleting a document that doesn't exist."""
    # Use a very large ID that's unlikely to exist
    nonexistent_id = 9999
    
    # Try to delete the nonexistent document
    response = client.delete(f"/documents/{nonexistent_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Document not found"

def test_upload_invalid_file(client):
    """Test uploading an invalid file (not a PDF)."""
    # Create a non-PDF file
    file_content = b"This is not a PDF file"
    file = io.BytesIO(file_content)
    
    # Mock the extract_text_from_pdf function to raise an exception
    with patch("app.routers.documents.extract_text_from_pdf", side_effect=Exception("Invalid PDF")):
        # Send the request
        response = client.post(
            "/documents/",
            files={"file": ("invalid.txt", file, "text/plain")},
            data={"company_name": "Invalid File Company"}
        )
        
        # Check that the request fails
        assert response.status_code == 500  # Internal server error

def test_documents_page_html(client):
    """Test the HTML documents page."""
    response = client.get("/documents", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that the HTML contains expected elements
    html_content = response.text
    assert "<title>Documents - Credit Lense</title>" in html_content
    assert "Financial Documents" in html_content
    assert "Upload New Document" in html_content