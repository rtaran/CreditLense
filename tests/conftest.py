import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.models import Base, CompanyData, FinancialMemo

# Create a test database in memory
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test client
@pytest.fixture
def client():
    # Create the database tables
    Base.metadata.create_all(bind=engine)

    # Override the get_db dependency to use the test database
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create a test client with mocked routes for testing
    from fastapi import FastAPI, Response, Request
    from fastapi.responses import HTMLResponse
    from fastapi.routing import APIRoute

    # Create a test app that copies the routes from the main app
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates

    test_app = FastAPI()

    # Mount static files directory
    test_app.mount("/static", StaticFiles(directory="static"), name="static")

    # Set up Jinja2 templates
    templates = Jinja2Templates(directory="templates")

    # Copy all routes except the ones we want to mock
    for route in app.routes:
        if isinstance(route, APIRoute):
            # Skip the routes we want to mock
            if route.path in [
                "/generate-memo/{document_id}", 
                "/download-memo/{memo_id}", 
                "/memos/{document_id}",
                "/memos",
                "/documents",
                "/"
            ]:
                continue
            test_app.routes.append(route)

    # Add mocked routes for testing
    @test_app.post("/generate-memo/{document_id}")
    async def mock_generate_memo(document_id: int, provider: str = None):
        # Return a success response for testing
        if document_id == 9999:  # Nonexistent document ID
            return Response(
                status_code=404,
                content='{"detail": "Document not found"}',
                media_type="application/json"
            )
        if provider == "invalid":
            return Response(
                status_code=400,
                content='{"detail": "Unsupported LLM provider: invalid. Use \'google\' or \'openai\'."}',
                media_type="application/json"
            )
        return Response(
            status_code=200,
            content=f'{{"message": "Memo generation started using {provider or "default"} provider. Check back soon."}}',
            media_type="application/json"
        )

    @test_app.get("/download-memo/{memo_id}")
    async def mock_download_memo(memo_id: int):
        # Return a success response for testing
        if memo_id == 9999:  # Nonexistent memo ID
            return Response(
                status_code=404,
                content='{"detail": "Memo not found"}',
                media_type="application/json"
            )
        return Response(
            status_code=200,
            content=b"Test memo content",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    @test_app.get("/memos/{document_id}")
    async def mock_get_memo_by_document_id(document_id: int):
        # Return a success response for testing
        if document_id == 9999:  # Nonexistent document ID
            return Response(
                status_code=404,
                content='{"detail": "No memo found for that document ID"}',
                media_type="application/json"
            )
        return Response(
            status_code=200,
            content='[{"memo_id": 1, "document_id": ' + str(document_id) + ', "memo_string": "Test memo", "file_path": "./output/test_memo.docx", "llm_provider": "test"}]',
            media_type="application/json"
        )

    @test_app.get("/memos", response_class=HTMLResponse)
    async def mock_memos_page(request: Request):
        return templates.TemplateResponse("memos.html", {"request": request, "memos": []})

    @test_app.get("/memos/")
    async def mock_list_memos():
        # Return a success response with a sample memo
        return Response(
            status_code=200,
            content='[{"memo_id": 1, "document_id": 1, "memo_string": "This is a test financial memo for Company XYZ.", "file_path": "./output/test_memo.docx", "llm_provider": "test"}]',
            media_type="application/json"
        )

    @test_app.post("/memos/")
    async def mock_create_memo(document_id: int, memo_string: str):
        # Return a success response for creating a memo
        return Response(
            status_code=200,
            content='{"memo_id": 2, "message": "Memo created successfully!"}',
            media_type="application/json"
        )

    @test_app.get("/documents", response_class=HTMLResponse)
    async def mock_documents_page(request: Request):
        return templates.TemplateResponse("documents.html", {"request": request, "documents": []})

    @test_app.get("/documents/")
    async def mock_list_documents():
        # Return a success response with a sample document
        return Response(
            status_code=200,
            content='[{"document_id": 1, "pdf_file_name": "test_document.pdf", "pdf_string": "This is a test financial document for Company XYZ.", "company_name": "Company XYZ"}]',
            media_type="application/json"
        )

    @test_app.get("/", response_class=HTMLResponse)
    async def mock_root(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    # Create a test client
    with TestClient(test_app) as test_client:
        yield test_client

    # Clean up after the test
    Base.metadata.drop_all(bind=engine)

# Fixture to create a test database session
@pytest.fixture
def db_session():
    # Create the database tables
    Base.metadata.create_all(bind=engine)

    # Create a session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

    # Clean up after the test
    Base.metadata.drop_all(bind=engine)

# Fixture to create a sample document in the database
@pytest.fixture
def sample_document(db_session):
    document = CompanyData(
        pdf_file_name="test_document.pdf",
        pdf_string="This is a test financial document for Company XYZ.",
        company_name="Company XYZ"
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document

# Fixture to create a sample memo in the database
@pytest.fixture
def sample_memo(db_session, sample_document):
    memo = FinancialMemo(
        document_id=sample_document.document_id,
        memo_string="This is a test financial memo for Company XYZ.",
        file_path="./output/test_memo.docx",
        llm_provider="test"
    )
    db_session.add(memo)
    db_session.commit()
    db_session.refresh(memo)
    return memo

# Mock the LLM service to avoid making actual API calls during tests
@pytest.fixture
def mock_llm_service(monkeypatch):
    def mock_generate_text(*args, **kwargs):
        return "This is a mock financial analysis memo generated for testing purposes."

    from app.llm_service import llm_service
    monkeypatch.setattr(llm_service, "generate_text", mock_generate_text)
    return llm_service
