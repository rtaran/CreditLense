from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models import FinancialMemo, CompanyData
from app.database import SessionLocal
from app.analyzer import financial_analyzer
from app.formatter import memo_formatter
import os

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/memos/")
def list_memos(db: Session = Depends(get_db)):
    return db.query(FinancialMemo).all()

@router.get("/memos/{document_id}")
def get_memo_by_document_id(document_id: int, db: Session = Depends(get_db)):
    memos = db.query(FinancialMemo).filter_by(document_id=document_id).all()
    if not memos:
        raise HTTPException(status_code=404, detail="No memo found for that document ID")
    return memos

@router.post("/memos/")
def create_memo(document_id: int, memo_string: str, db: Session = Depends(get_db)):
    memo = FinancialMemo(document_id=document_id, memo_string=memo_string)
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return {
        "memo_id": memo.memo_id,
        "message": "Memo created successfully!"
    }

@router.post("/generate-memo/{document_id}")
def generate_memo(document_id: int, background_tasks: BackgroundTasks, provider: str = None, db: Session = Depends(get_db)):
    # Get the document
    document = db.query(CompanyData).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate the provider
    if provider and provider not in ["google", "openai"]:
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}. Use 'google' or 'openai'.")

    # Generate the memo in the background
    background_tasks.add_task(
        _generate_and_save_memo, 
        document_id=document_id, 
        document_text=document.pdf_string,
        company_name=document.company_name or "Company",
        provider=provider,
        db=db
    )

    return {"message": f"Memo generation started using {provider or 'default'} provider. Check back soon."}

@router.get("/download-memo/{memo_id}")
def download_memo(memo_id: int, db: Session = Depends(get_db)):
    # Get the memo
    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    # Check if the memo has a file path
    if not hasattr(memo, 'file_path') or not memo.file_path:
        # Generate the file on demand if it doesn't exist
        document = db.query(CompanyData).get(memo.document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Associated document not found")

        company_name = document.company_name or "Company"
        file_path = memo_formatter.format_memo_as_docx(memo.memo_string, company_name)

        # Update the memo with the file path
        memo.file_path = file_path
        db.commit()
    else:
        file_path = memo.file_path

    # Check if the file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Memo file not found")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.delete("/memos/{memo_id}")
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    # Delete the file if it exists
    if hasattr(memo, 'file_path') and memo.file_path and os.path.exists(memo.file_path):
        os.remove(memo.file_path)

    db.delete(memo)
    db.commit()
    return {"message": f"Memo {memo_id} deleted successfully."}

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
    # Generate the memo using the specified provider and passing document_id and db
    # This allows the analyzer to use the extracted financial data
    memo_text = financial_analyzer.analyze_financial_document(
        document_text, 
        provider=provider,
        document_id=document_id,
        db=db
    )

    # Format the memo as a Word document
    file_path = memo_formatter.format_memo_as_docx(memo_text, company_name)

    # Save the memo to the database with the provider information
    memo = FinancialMemo(
        document_id=document_id, 
        memo_string=memo_text, 
        file_path=file_path,
        llm_provider=provider
    )
    db.add(memo)
    db.commit()
