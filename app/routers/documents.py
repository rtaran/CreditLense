from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.models import CompanyData
from app.database import SessionLocal
from app.financial_data import FinancialDataExtractor, store_financial_data
import fitz # PyMuPDF
import tempfile
import os
import logging

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

def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Extract text from a PDF file.

    Args:
        file: The uploaded PDF file

    Returns:
        The extracted text from the PDF
    """
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        # Use PyMuPDF to read the PDF
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def process_financial_data(db: Session, document_id: int, pdf_text: str):
    """
    Process and store financial data from a PDF.

    Args:
        db: The database session
        document_id: The ID of the document to associate the data with
        pdf_text: The text content of the PDF
    """
    try:
        # Extract financial data from the PDF text
        extractor = FinancialDataExtractor(pdf_text)
        financial_data = extractor.extract_all_data()

        # Store the extracted data in the database
        store_financial_data(db, document_id, financial_data)

        logger.info(f"Financial data processed and stored for document {document_id}")

        # Update the CompanyData record with summary information
        document = db.query(CompanyData).get(document_id)
        if document and financial_data["years"]:
            # Get the most recent year
            latest_year = max(financial_data["years"])

            # Update the CompanyData record with summary information from the latest year
            if latest_year in financial_data["balance_sheet"]:
                balance_sheet = financial_data["balance_sheet"][latest_year]

                # Extract total assets if available
                if "Current Assets" in balance_sheet and "Total Current Assets" in balance_sheet["Current Assets"]:
                    current_assets = balance_sheet["Current Assets"]["Total Current Assets"]
                    if "Non-Current Assets" in balance_sheet and "Total Non-Current Assets" in balance_sheet["Non-Current Assets"]:
                        non_current_assets = balance_sheet["Non-Current Assets"]["Total Non-Current Assets"]
                        document.total_assets = current_assets + non_current_assets

                # Extract total liabilities if available
                if "Current Liabilities" in balance_sheet and "Total Current Liabilities" in balance_sheet["Current Liabilities"]:
                    current_liabilities = balance_sheet["Current Liabilities"]["Total Current Liabilities"]
                    if "Non-Current Liabilities" in balance_sheet and "Total Non-Current Liabilities" in balance_sheet["Non-Current Liabilities"]:
                        non_current_liabilities = balance_sheet["Non-Current Liabilities"]["Total Non-Current Liabilities"]
                        document.total_liabilities = current_liabilities + non_current_liabilities

            # Extract revenue and net income if available
            if latest_year in financial_data["income_statement"]:
                income_statement = financial_data["income_statement"][latest_year]

                if "Revenue" in income_statement and "Total Revenue" in income_statement["Revenue"]:
                    document.revenue = income_statement["Revenue"]["Total Revenue"]

                if "Profit" in income_statement and "Net Income" in income_statement["Profit"]:
                    document.net_income = income_statement["Profit"]["Net Income"]

            # Extract cash flow if available
            if latest_year in financial_data["cash_flow"]:
                cash_flow = financial_data["cash_flow"][latest_year]

                if "Operating Activities" in cash_flow and "Net Cash from Operating Activities" in cash_flow["Operating Activities"]:
                    document.cash_flow = cash_flow["Operating Activities"]["Net Cash from Operating Activities"]

            db.commit()
            logger.info(f"Updated CompanyData record with summary information for document {document_id}")

    except Exception as e:
        logger.error(f"Error processing financial data: {str(e)}")
        # Don't raise an exception here, as this is run in the background

@router.post("/documents/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    company_name: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a financial document and process it.

    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded PDF file
        company_name: The name of the company (optional)
        db: The database session

    Returns:
        Information about the uploaded document
    """
    # Extract text from the PDF
    pdf_text = extract_text_from_pdf(file)

    # Create a new CompanyData record
    doc = CompanyData(
        pdf_file_name=file.filename, 
        pdf_string=pdf_text,
        company_name=company_name
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process financial data in the background
    background_tasks.add_task(
        process_financial_data,
        db=db,
        document_id=doc.document_id,
        pdf_text=pdf_text
    )

    return {
        "document_id": doc.document_id,
        "filename": doc.pdf_file_name,
        "company_name": doc.company_name,
        "message": "Document uploaded successfully! Financial data is being processed in the background."
    }

@router.get("/documents/")
def list_documents(db: Session = Depends(get_db)):
    return db.query(CompanyData).all()

@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(CompanyData).get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": f"Document {document_id} deleted successfully."}
