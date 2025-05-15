from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models import FinancialMemo, CompanyData
from app.database import SessionLocal
from app.analyzer import financial_analyzer
from app.formatter import memo_formatter
import os
import logging

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/memos/")
def list_memos(request: Request, db: Session = Depends(get_db)):
    logger.info(f"GET /memos/ - Request from {request.client.host}")
    memos = db.query(FinancialMemo).all()
    logger.info(f"GET /memos/ - Returning {len(memos)} memos")
    return memos

@router.get("/memos/{document_id}")
def get_memo_by_document_id(document_id: int, request: Request, db: Session = Depends(get_db)):
    logger.info(f"GET /memos/{document_id} - Request from {request.client.host}")
    memos = db.query(FinancialMemo).filter_by(document_id=document_id).all()
    if not memos:
        logger.warning(f"GET /memos/{document_id} - No memo found for document ID {document_id}")
        raise HTTPException(status_code=404, detail="No memo found for that document ID")
    logger.info(f"GET /memos/{document_id} - Returning {len(memos)} memos")
    return memos

@router.post("/memos/")
def create_memo(request: Request, db: Session = Depends(get_db), document_id: int = None, memo_string: str = None):
    # Get parameters from query params if not provided directly
    if document_id is None or memo_string is None:
        params = request.query_params
        document_id = int(params.get("document_id")) if params.get("document_id") else None
        memo_string = params.get("memo_string")

    if not document_id or not memo_string:
        logger.error("POST /memos/ - Missing required parameters: document_id and memo_string")
        raise HTTPException(status_code=400, detail="Missing required parameters: document_id and memo_string")
    logger.info(f"POST /memos/ - Request from {request.client.host} for document ID {document_id}")
    try:
        memo = FinancialMemo(document_id=document_id, memo_string=memo_string)
        db.add(memo)
        db.commit()
        db.refresh(memo)
        logger.info(f"POST /memos/ - Memo created successfully with ID {memo.memo_id}")
        return {
            "memo_id": memo.memo_id,
            "message": "Memo created successfully!"
        }
    except Exception as e:
        logger.error(f"POST /memos/ - Error creating memo: {str(e)}")
        raise

@router.post("/generate-memo/{document_id}")
def generate_memo(document_id: int, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db), provider: str = None):
    logger.info(f"POST /generate-memo/{document_id} - Request from {request.client.host} with provider {provider or 'default'}")

    # Get the document
    document = db.query(CompanyData).get(document_id)
    if not document:
        logger.warning(f"POST /generate-memo/{document_id} - Document not found")
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate the provider
    if provider and provider not in ["google", "openai"]:
        logger.warning(f"POST /generate-memo/{document_id} - Unsupported LLM provider: {provider}")
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}. Use 'google' or 'openai'.")

    # Generate the memo in the background
    logger.info(f"POST /generate-memo/{document_id} - Starting background task for memo generation")
    background_tasks.add_task(
        _generate_and_save_memo, 
        document_id=document_id, 
        document_text=document.pdf_string,
        company_name=document.company_name or "Company",
        provider=provider,
        db=db
    )

    logger.info(f"POST /generate-memo/{document_id} - Background task initiated successfully")
    return {"message": f"Memo generation started using {provider or 'default'} provider. Check back soon."}

@router.get("/view-memo/{memo_id}", response_class=HTMLResponse)
def view_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    """
    View a memo in the browser.

    Args:
        memo_id: The ID of the memo to view
        request: The request object
        db: The database session

    Returns:
        The memo view page
    """
    logger.info(f"GET /view-memo/{memo_id} - Request from {request.client.host}")

    # Get the memo
    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        logger.warning(f"GET /view-memo/{memo_id} - Memo not found")
        raise HTTPException(status_code=404, detail="Memo not found")

    # Get the company name
    document = db.query(CompanyData).get(memo.document_id)
    company_name = document.company_name if document else "Unknown Company"

    logger.info(f"GET /view-memo/{memo_id} - Returning memo view for company {company_name}")

    return templates.TemplateResponse(
        "view_memo.html", 
        {
            "request": request, 
            "memo": memo,
            "company_name": company_name
        }
    )

@router.get("/download-memo/{memo_id}")
def download_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    logger.info(f"GET /download-memo/{memo_id} - Request from {request.client.host}")

    # Get the memo
    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        logger.warning(f"GET /download-memo/{memo_id} - Memo not found")
        raise HTTPException(status_code=404, detail="Memo not found")

    # Check if the memo has a file path
    if not hasattr(memo, 'file_path') or not memo.file_path:
        logger.info(f"GET /download-memo/{memo_id} - No file path found, generating file on demand")
        # Generate the file on demand if it doesn't exist
        document = db.query(CompanyData).get(memo.document_id)
        if not document:
            logger.warning(f"GET /download-memo/{memo_id} - Associated document not found for document ID {memo.document_id}")
            raise HTTPException(status_code=404, detail="Associated document not found")

        company_name = document.company_name or "Company"
        try:
            file_path = memo_formatter.format_memo_as_docx(memo.memo_string, company_name)
            logger.info(f"GET /download-memo/{memo_id} - File generated successfully at {file_path}")

            # Update the memo with the file path
            memo.file_path = file_path
            db.commit()
            logger.info(f"GET /download-memo/{memo_id} - Updated memo with file path")
        except Exception as e:
            logger.error(f"GET /download-memo/{memo_id} - Error generating file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating memo file: {str(e)}")
    else:
        file_path = memo.file_path
        logger.info(f"GET /download-memo/{memo_id} - Using existing file at {file_path}")

    # Check if the file exists
    if not os.path.exists(file_path):
        logger.error(f"GET /download-memo/{memo_id} - File not found at {file_path}")
        raise HTTPException(status_code=404, detail="Memo file not found")

    logger.info(f"GET /download-memo/{memo_id} - Returning file {os.path.basename(file_path)}")
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.delete("/memos/{memo_id}")
def delete_memo(memo_id: int, request: Request, db: Session = Depends(get_db)):
    logger.info(f"DELETE /memos/{memo_id} - Request from {request.client.host}")

    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        logger.warning(f"DELETE /memos/{memo_id} - Memo not found")
        raise HTTPException(status_code=404, detail="Memo not found")

    # Delete the file if it exists
    if hasattr(memo, 'file_path') and memo.file_path and os.path.exists(memo.file_path):
        try:
            os.remove(memo.file_path)
            logger.info(f"DELETE /memos/{memo_id} - Deleted file at {memo.file_path}")
        except Exception as e:
            logger.error(f"DELETE /memos/{memo_id} - Error deleting file: {str(e)}")
            # Continue with memo deletion even if file deletion fails

    try:
        db.delete(memo)
        db.commit()
        logger.info(f"DELETE /memos/{memo_id} - Memo deleted successfully")
        return {"message": f"Memo {memo_id} deleted successfully."}
    except Exception as e:
        logger.error(f"DELETE /memos/{memo_id} - Error deleting memo from database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting memo: {str(e)}")

def _generate_and_save_memo(document_id: int, document_text: str, company_name: str, provider: str = None, db: Session = None):
    """
    Generate a memo using the financial analyzer and save it to the database.
    This function is meant to be run in the background.

    Args:
        document_id: The ID of the document to analyze
        document_text: The text content of the document
        company_name: The name of the company
        provider: The LLM provider to use (optional)
        db: The database session
    """
    logger.info(f"Background task: Generating memo for document {document_id} using {provider or 'default'} provider")

    try:
        # Generate the memo using the specified provider and passing document_id and db
        # This allows the analyzer to use the extracted financial data
        logger.info(f"Background task: Analyzing financial document {document_id}")
        memo_text = financial_analyzer.analyze_financial_document(
            document_text, 
            provider=provider,
            document_id=document_id,
            db=db
        )
        logger.info(f"Background task: Financial analysis completed for document {document_id}")

        # Format the memo as a Word document
        logger.info(f"Background task: Formatting memo as Word document for {company_name}")
        try:
            file_path = memo_formatter.format_memo_as_docx(memo_text, company_name)
            logger.info(f"Background task: Memo formatted and saved to {file_path}")
        except Exception as e:
            logger.error(f"Background task: Error formatting memo as Word document: {str(e)}")
            file_path = None  # Set to None if formatting fails, but continue to save the text

        # Save the memo to the database with the provider information
        logger.info(f"Background task: Saving memo to database for document {document_id}")
        memo = FinancialMemo(
            document_id=document_id, 
            memo_string=memo_text, 
            file_path=file_path,
            llm_provider=provider
        )
        db.add(memo)
        db.commit()
        logger.info(f"Background task: Memo saved successfully to database with provider {provider or 'default'}")
    except Exception as e:
        logger.error(f"Background task: Error generating or saving memo: {str(e)}")
        # Don't re-raise the exception as this is a background task
