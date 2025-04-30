from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sqlite3
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

from app.models import Base, CompanyData, FinancialMemo
from app.database import engine, SessionLocal, DATABASE_URL
from app.routers import documents, memos
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
    # Extract the database file path from the DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the financial_memos table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financial_memos'")
    if cursor.fetchone():
        # Check if the required columns exist
        cursor.execute(f"PRAGMA table_info(financial_memos)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'file_path' not in columns:
            print("Adding file_path column to financial_memos table...")
            cursor.execute("ALTER TABLE financial_memos ADD COLUMN file_path TEXT")
            conn.commit()
            print("file_path column added successfully.")

        if 'llm_provider' not in columns:
            print("Adding llm_provider column to financial_memos table...")
            cursor.execute("ALTER TABLE financial_memos ADD COLUMN llm_provider TEXT")
            conn.commit()
            print("llm_provider column added successfully.")

    conn.close()

# Create tables and ensure schema is up to date
Base.metadata.create_all(bind=engine)
ensure_required_columns()

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

app.include_router(documents.router)
app.include_router(memos.router)

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.join("static", "favicon.ico"))

# Routes for HTML templates
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request, db: Session = Depends(get_db)):
    documents = db.query(CompanyData).all()
    return templates.TemplateResponse("documents.html", {"request": request, "documents": documents})

@app.get("/memos", response_class=HTMLResponse)
def memos_page(request: Request, db: Session = Depends(get_db)):
    memos = db.query(FinancialMemo).all()
    return templates.TemplateResponse("memos.html", {"request": request, "memos": memos})

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
    # Get the document
    document = db.query(CompanyData).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get the financial data for the document
    financial_data = get_financial_data_for_document(db, document_id)

    # Determine the selected year (default to the most recent year)
    selected_year = max(financial_data.get("years", [0])) if financial_data.get("years") else None

    return templates.TemplateResponse(
        "financial_data.html", 
        {
            "request": request, 
            "document": document, 
            "financial_data": financial_data,
            "selected_year": selected_year
        }
    )

# Add a route to redirect from document view to financial data view
@app.get("/view-financial-data/{document_id}")
def view_financial_data(document_id: int):
    """
    Redirect to the financial data page for a document.

    Args:
        document_id: The ID of the document to view financial data for

    Returns:
        A redirect to the financial data page
    """
    return RedirectResponse(url=f"/financial-data/{document_id}")

# Create uploads directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
