from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import CompanyData, CompanyDataReturnModel
from app.database import SessionLocal
import fitz # PyMuPDF
import tempfile

from app.utils.gemini import Gemini
from app.utils.openai import Openai

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- pdf extractor --- just to test
def extract_text_from_pdf(file: UploadFile) -> str:
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    # Use PyMuPDF to read the PDF
    doc = fitz.open(tmp_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
# --- pdf extractor ---  just to test

@router.post("/documents/")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    #contents = await file.read() # commented out to add local pdf exrractor
    #pdf_text = contents.decode("utf-8", errors="ignore") # commented out to add local pdf exrractor
    pdf_text = extract_text_from_pdf(file)
    
    # step 1 ask .env which llm to use

    model = os.getenv("LLM_PROVIDER", "google")
    # Step 2 instantiate the class eg llm = Gemini(pdf_text)

    if model == "openai":
        llm = openai(pdf_text)
    else:
        llm = Gemini(pdf_text)
    # Step 3 response = llm.request()
    # Step 4 use instead of line 46 : doc = CompanyData(pdf_file_name=file.filename, pdf_string=pdf_text, ), but with response data in it!

    doc = CompanyData(pdf_file_name=file.filename, pdf_string=pdf_text)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.document_id,
        "filename": doc.pdf_file_name,
        "message": "Document uploaded successfully!"
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