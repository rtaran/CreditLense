from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
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
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def process_financial_data(document_id: int, pdf_text: str):
    """
    Process and store financial data from a PDF.

    Args:
        document_id: The ID of the document to associate the data with
        pdf_text: The text content of the PDF
    """
    # Create a new database session for this background task
    db = SessionLocal()
    try:
        # Extract financial data from the PDF text
        extractor = FinancialDataExtractor(pdf_text)

        # Try to extract data using LLM first, fall back to regex-based extraction if it fails
        try:
            logger.info(f"Extracting financial data using LLM with OpenAI provider for document {document_id}")
            financial_data = extractor.extract_data_with_llm(provider="openai")
            logger.info(f"Successfully extracted financial data using LLM with OpenAI provider for document {document_id}")
        except Exception as e:
            logger.error(f"Error extracting financial data using LLM: {str(e)}")
            logger.info(f"Falling back to regex-based extraction for document {document_id}")
            financial_data = extractor.extract_all_data()
            logger.info(f"Successfully extracted financial data using regex for document {document_id}")

        # Store the extracted data in the database
        logger.info(f"Storing financial data for document {document_id}")
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
                        if current_assets is not None and non_current_assets is not None:
                            document.total_assets = current_assets + non_current_assets
                        elif current_assets is not None:
                            document.total_assets = current_assets
                        elif non_current_assets is not None:
                            document.total_assets = non_current_assets
                    elif current_assets is not None:
                        document.total_assets = current_assets

                # Extract total liabilities if available
                if "Current Liabilities" in balance_sheet and "Total Current Liabilities" in balance_sheet["Current Liabilities"]:
                    current_liabilities = balance_sheet["Current Liabilities"]["Total Current Liabilities"]
                    if "Non-Current Liabilities" in balance_sheet and "Total Non-Current Liabilities" in balance_sheet["Non-Current Liabilities"]:
                        non_current_liabilities = balance_sheet["Non-Current Liabilities"]["Total Non-Current Liabilities"]
                        if current_liabilities is not None and non_current_liabilities is not None:
                            document.total_liabilities = current_liabilities + non_current_liabilities
                        elif current_liabilities is not None:
                            document.total_liabilities = current_liabilities
                        elif non_current_liabilities is not None:
                            document.total_liabilities = non_current_liabilities
                    elif current_liabilities is not None:
                        document.total_liabilities = current_liabilities

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
    finally:
        # Always close the database session
        db.close()
        logger.info(f"Closed database session for background task processing document {document_id}")

@router.post("/documents/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    company_name: str = Form(None),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Upload a financial document and process it.

    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded PDF file
        company_name: The name of the company (optional)
        db: The database session
        request: The request object

    Returns:
        Information about the uploaded document
    """
    client_host = request.client.host if request else "unknown"
    logger.info(f"POST /documents/ - Request from {client_host} to upload file: {file.filename}")

    try:
        # Extract text from the PDF
        logger.info(f"Extracting text from PDF: {file.filename}")
        pdf_text = extract_text_from_pdf(file)
        logger.info(f"Successfully extracted {len(pdf_text)} characters from PDF")

        # Create a new CompanyData record
        logger.info(f"Creating new CompanyData record for {company_name or 'unnamed company'}")
        doc = CompanyData(
            pdf_file_name=file.filename, 
            pdf_string=pdf_text,
            company_name=company_name
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info(f"Created document record with ID: {doc.document_id}")

        # Process financial data in the background
        logger.info(f"Starting background task to process financial data for document {doc.document_id}")
        background_tasks.add_task(
            process_financial_data,
            document_id=doc.document_id,
            pdf_text=pdf_text
        )

        logger.info(f"Document upload completed successfully for document {doc.document_id}")
        return {
            "document_id": doc.document_id,
            "filename": doc.pdf_file_name,
            "company_name": doc.company_name,
            "message": "Document uploaded successfully!"
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise

@router.get("/documents/")
def list_documents(db: Session = Depends(get_db), request: Request = None):
    client_host = request.client.host if request else "unknown"
    logger.info(f"GET /documents/ - Request from {client_host}")

    try:
        documents = db.query(CompanyData).all()
        logger.info(f"GET /documents/ - Returning {len(documents)} documents")
        return documents
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        raise

@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), request: Request = None):
    client_host = request.client.host if request else "unknown"
    logger.info(f"DELETE /documents/{document_id} - Request from {client_host}")

    try:
        doc = db.query(CompanyData).get(document_id)
        if not doc:
            logger.warning(f"DELETE /documents/{document_id} - Document not found")
            raise HTTPException(status_code=404, detail="Document not found")

        logger.info(f"DELETE /documents/{document_id} - Deleting document: {doc.pdf_file_name}")
        db.delete(doc)
        db.commit()
        logger.info(f"DELETE /documents/{document_id} - Document deleted successfully")

        return {"message": f"Document {document_id} deleted successfully."}
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"DELETE /documents/{document_id} - Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.delete("/documents/batch")
async def delete_multiple_documents(request: Request, db: Session = Depends(get_db)):
    client_host = request.client.host if request else "unknown"

    # Parse the request body to get document_ids
    body = await request.json()
    document_ids = body.get("document_ids", [])

    logger.info(f"DELETE /documents/batch - Request from {client_host} to delete documents: {document_ids}")

    deleted_ids = []
    not_found_ids = []

    try:
        for document_id in document_ids:
            doc = db.query(CompanyData).get(document_id)
            if not doc:
                logger.warning(f"DELETE /documents/batch - Document {document_id} not found")
                not_found_ids.append(document_id)
                continue

            logger.info(f"DELETE /documents/batch - Deleting document: {doc.pdf_file_name}")
            db.delete(doc)
            deleted_ids.append(document_id)

        db.commit()
        logger.info(f"DELETE /documents/batch - {len(deleted_ids)} documents deleted successfully")

        result = {"message": f"{len(deleted_ids)} documents deleted successfully."}
        if deleted_ids:
            result["deleted_ids"] = deleted_ids
        if not_found_ids:
            result["not_found_ids"] = not_found_ids

        return result
    except Exception as e:
        logger.error(f"DELETE /documents/batch - Error deleting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting documents: {str(e)}")
