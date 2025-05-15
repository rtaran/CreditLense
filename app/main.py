from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sqlite3
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
logger.info("Loading environment variables from .env file")
load_dotenv()

from app.models import Base, CompanyData, FinancialMemo, Methodology, MemoFormat
from app.database import engine, SessionLocal, DATABASE_URL
from app.routers import documents, memos, uploads
from app.financial_data import get_financial_data_for_document

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Check if required columns exist in the financial_memos table
def ensure_required_columns():
    logger.info("Checking if required columns exist in the financial_memos table")
    # Extract the database file path from the DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    logger.debug(f"Database path: {db_path}")

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.debug("Connected to SQLite database")

        # Check if the financial_memos table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financial_memos'")
        if cursor.fetchone():
            logger.debug("financial_memos table exists")
            # Check if the required columns exist
            cursor.execute(f"PRAGMA table_info(financial_memos)")
            columns = [column[1] for column in cursor.fetchall()]
            logger.debug(f"Existing columns: {columns}")

            if 'file_path' not in columns:
                logger.info("Adding file_path column to financial_memos table")
                cursor.execute("ALTER TABLE financial_memos ADD COLUMN file_path TEXT")
                conn.commit()
                logger.info("file_path column added successfully")

            if 'llm_provider' not in columns:
                logger.info("Adding llm_provider column to financial_memos table")
                cursor.execute("ALTER TABLE financial_memos ADD COLUMN llm_provider TEXT")
                conn.commit()
                logger.info("llm_provider column added successfully")
        else:
            logger.info("financial_memos table does not exist yet, will be created with Base.metadata.create_all")

        conn.close()
        logger.debug("Database connection closed")
    except Exception as e:
        logger.error(f"Error ensuring required columns: {str(e)}")
        raise

# Create tables and ensure schema is up to date
logger.info("Creating database tables if they don't exist")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    ensure_required_columns()
    logger.info("Database schema is up to date")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

logger.info("Initializing FastAPI application")
app = FastAPI(
    title="CreditLense",
    description="AI-Powered Credit Memo Co-Pilot Web App",
    version="1.0.0"
)

# Mount static files directory
logger.info("Mounting static files directory")
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.debug("Static files directory mounted successfully")
except Exception as e:
    logger.error(f"Error mounting static files directory: {str(e)}")
    raise

# Set up Jinja2 templates
logger.info("Setting up Jinja2 templates")
try:
    templates = Jinja2Templates(directory="templates")
    logger.debug("Jinja2 templates set up successfully")
except Exception as e:
    logger.error(f"Error setting up Jinja2 templates: {str(e)}")
    raise

# Include routers
logger.info("Including API routers")
app.include_router(documents.router)
app.include_router(memos.router)
app.include_router(uploads.router)
logger.info("API routers included successfully")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    logger.info(f"GET / - Request from {request.client.host}")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
def favicon():
    logger.debug("GET /favicon.ico - Serving favicon")
    return FileResponse(os.path.join("static", "favicon.ico"))

# Routes for HTML templates
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    logger.info(f"GET /upload - Request from {request.client.host}")
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request, db: Session = Depends(get_db)):
    logger.info(f"GET /documents - Request from {request.client.host}")
    try:
        documents = db.query(CompanyData).all()
        logger.info(f"GET /documents - Retrieved {len(documents)} documents")
        return templates.TemplateResponse("documents.html", {"request": request, "documents": documents})
    except Exception as e:
        logger.error(f"GET /documents - Error retrieving documents: {str(e)}")
        raise

@app.get("/memos", response_class=HTMLResponse)
def memos_page(request: Request, db: Session = Depends(get_db)):
    logger.info(f"GET /memos - Request from {request.client.host}")
    try:
        memos = db.query(FinancialMemo).all()
        logger.info(f"GET /memos - Retrieved {len(memos)} memos")
        return templates.TemplateResponse("memos.html", {"request": request, "memos": memos})
    except Exception as e:
        logger.error(f"GET /memos - Error retrieving memos: {str(e)}")
        raise

@app.get("/methodology", response_class=HTMLResponse)
def methodology_page(request: Request):
    logger.info(f"GET /methodology - Request from {request.client.host}")
    return templates.TemplateResponse("methodology.html", {"request": request})

@app.get("/memo-format", response_class=HTMLResponse)
def memo_format_page(request: Request):
    logger.info(f"GET /memo-format - Request from {request.client.host}")
    return templates.TemplateResponse("memo_format.html", {"request": request})

@app.get("/financial-data/{document_id}", response_class=HTMLResponse)
def financial_data_page(request: Request, document_id: int, db: Session = Depends(get_db)):
    """
    Display financial data for a document.

    Args:
        request: The request object
        document_id: The ID of the document to display financial data for
        db: The database session

    Returns:
        The financial data page
    """
    logger.info(f"GET /financial-data/{document_id} - Request from {request.client.host}")

    try:
        # Get the document
        document = db.query(CompanyData).get(document_id)
        if not document:
            logger.warning(f"GET /financial-data/{document_id} - Document not found")
            raise HTTPException(status_code=404, detail="Document not found")

        logger.info(f"GET /financial-data/{document_id} - Retrieved document: {document.pdf_file_name}")

        # Get the financial data for the document
        logger.info(f"GET /financial-data/{document_id} - Retrieving financial data")
        financial_data = get_financial_data_for_document(db, document_id)

        # Log the amount of financial data retrieved
        years = financial_data.get("years", [])
        logger.info(f"GET /financial-data/{document_id} - Retrieved financial data for {len(years)} years")

        # Determine the selected year (default to the most recent year)
        selected_year = max(years or [0]) if years else None
        logger.info(f"GET /financial-data/{document_id} - Selected year: {selected_year}")

        return templates.TemplateResponse(
            "financial_data.html", 
            {
                "request": request, 
                "document": document, 
                "financial_data": financial_data,
                "selected_year": selected_year
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"GET /financial-data/{document_id} - Error retrieving financial data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving financial data: {str(e)}")

# Add a route to redirect from document view to financial data view
@app.get("/view-financial-data/{document_id}")
def view_financial_data(document_id: int, request: Request = None):
    """
    Redirect to the financial data page for a document.

    Args:
        document_id: The ID of the document to view financial data for
        request: The request object

    Returns:
        A redirect to the financial data page
    """
    client_host = request.client.host if request else "unknown"
    logger.info(f"GET /view-financial-data/{document_id} - Request from {client_host}")
    logger.info(f"GET /view-financial-data/{document_id} - Redirecting to /financial-data/{document_id}")
    return RedirectResponse(url=f"/financial-data/{document_id}")

# Create uploads directory
logger.info("Ensuring uploads directory exists")
UPLOAD_DIR = Path("./data/uploads")
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Uploads directory created/verified at {UPLOAD_DIR}")
except Exception as e:
    logger.error(f"Error creating uploads directory: {str(e)}")
    raise

logger.info("Application startup complete")
