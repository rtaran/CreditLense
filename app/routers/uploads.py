from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

from app.models import Methodology, MemoFormat
from app.database import SessionLocal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create directories for uploads
METHODOLOGY_DIR = Path("./data/uploads/methodology")
MEMO_FORMAT_DIR = Path("./data/uploads/memo_format")

METHODOLOGY_DIR.mkdir(parents=True, exist_ok=True)
MEMO_FORMAT_DIR.mkdir(parents=True, exist_ok=True)

# Routes for methodology files
@router.post("/methodology/")
async def upload_methodology(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a methodology file for credit analysis.
    
    Args:
        request: The request object
        file: The uploaded file
        name: The name of the methodology
        description: A description of the methodology
        db: The database session
        
    Returns:
        A message indicating the file was uploaded successfully
    """
    logger.info(f"POST /methodology/ - Request from {request.client.host}")
    
    # Save the file
    file_path = METHODOLOGY_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"POST /methodology/ - File saved to {file_path}")
    except Exception as e:
        logger.error(f"POST /methodology/ - Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Read the file content
    try:
        with open(file_path, "r") as f:
            content = f.read()
        logger.info(f"POST /methodology/ - File content read successfully")
    except Exception as e:
        logger.error(f"POST /methodology/ - Error reading file content: {str(e)}")
        content = None  # Set to None if reading fails
    
    # Create a new methodology record
    try:
        methodology = Methodology(
            name=name,
            file_name=file.filename,
            file_path=str(file_path),
            content=content,
            description=description,
            uploaded_at=datetime.utcnow(),
            is_active=1
        )
        db.add(methodology)
        db.commit()
        db.refresh(methodology)
        logger.info(f"POST /methodology/ - Methodology record created with ID {methodology.methodology_id}")
        
        return {
            "methodology_id": methodology.methodology_id,
            "message": "Methodology uploaded successfully!"
        }
    except Exception as e:
        logger.error(f"POST /methodology/ - Error creating methodology record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating methodology record: {str(e)}")

@router.get("/methodology/")
def list_methodologies(request: Request, db: Session = Depends(get_db)):
    """
    List all methodology files.
    
    Args:
        request: The request object
        db: The database session
        
    Returns:
        A list of methodology files
    """
    logger.info(f"GET /methodology/ - Request from {request.client.host}")
    
    methodologies = db.query(Methodology).all()
    logger.info(f"GET /methodology/ - Returning {len(methodologies)} methodologies")
    
    return methodologies

@router.get("/methodology/{methodology_id}")
def get_methodology(methodology_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Get a methodology file by ID.
    
    Args:
        methodology_id: The ID of the methodology to get
        request: The request object
        db: The database session
        
    Returns:
        The methodology file
    """
    logger.info(f"GET /methodology/{methodology_id} - Request from {request.client.host}")
    
    methodology = db.query(Methodology).get(methodology_id)
    if not methodology:
        logger.warning(f"GET /methodology/{methodology_id} - Methodology not found")
        raise HTTPException(status_code=404, detail="Methodology not found")
    
    logger.info(f"GET /methodology/{methodology_id} - Returning methodology {methodology.name}")
    
    return methodology

@router.get("/download-methodology/{methodology_id}")
def download_methodology(methodology_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Download a methodology file.
    
    Args:
        methodology_id: The ID of the methodology to download
        request: The request object
        db: The database session
        
    Returns:
        The methodology file
    """
    logger.info(f"GET /download-methodology/{methodology_id} - Request from {request.client.host}")
    
    methodology = db.query(Methodology).get(methodology_id)
    if not methodology:
        logger.warning(f"GET /download-methodology/{methodology_id} - Methodology not found")
        raise HTTPException(status_code=404, detail="Methodology not found")
    
    file_path = methodology.file_path
    if not os.path.exists(file_path):
        logger.error(f"GET /download-methodology/{methodology_id} - File not found at {file_path}")
        raise HTTPException(status_code=404, detail="Methodology file not found")
    
    logger.info(f"GET /download-methodology/{methodology_id} - Returning file {os.path.basename(file_path)}")
    
    return FileResponse(
        path=file_path,
        filename=methodology.file_name,
        media_type="application/octet-stream"
    )

@router.delete("/methodology/{methodology_id}")
def delete_methodology(methodology_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Delete a methodology file.
    
    Args:
        methodology_id: The ID of the methodology to delete
        request: The request object
        db: The database session
        
    Returns:
        A message indicating the methodology was deleted successfully
    """
    logger.info(f"DELETE /methodology/{methodology_id} - Request from {request.client.host}")
    
    methodology = db.query(Methodology).get(methodology_id)
    if not methodology:
        logger.warning(f"DELETE /methodology/{methodology_id} - Methodology not found")
        raise HTTPException(status_code=404, detail="Methodology not found")
    
    # Delete the file if it exists
    if os.path.exists(methodology.file_path):
        try:
            os.remove(methodology.file_path)
            logger.info(f"DELETE /methodology/{methodology_id} - Deleted file at {methodology.file_path}")
        except Exception as e:
            logger.error(f"DELETE /methodology/{methodology_id} - Error deleting file: {str(e)}")
            # Continue with methodology deletion even if file deletion fails
    
    try:
        db.delete(methodology)
        db.commit()
        logger.info(f"DELETE /methodology/{methodology_id} - Methodology deleted successfully")
        
        return {"message": f"Methodology {methodology_id} deleted successfully."}
    except Exception as e:
        logger.error(f"DELETE /methodology/{methodology_id} - Error deleting methodology from database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting methodology: {str(e)}")

# Routes for memo format files
@router.post("/memo-format/")
async def upload_memo_format(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a memo format file.
    
    Args:
        request: The request object
        file: The uploaded file
        name: The name of the memo format
        description: A description of the memo format
        db: The database session
        
    Returns:
        A message indicating the file was uploaded successfully
    """
    logger.info(f"POST /memo-format/ - Request from {request.client.host}")
    
    # Save the file
    file_path = MEMO_FORMAT_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"POST /memo-format/ - File saved to {file_path}")
    except Exception as e:
        logger.error(f"POST /memo-format/ - Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create a new memo format record
    try:
        memo_format = MemoFormat(
            name=name,
            file_name=file.filename,
            file_path=str(file_path),
            description=description,
            uploaded_at=datetime.utcnow(),
            is_active=1
        )
        db.add(memo_format)
        db.commit()
        db.refresh(memo_format)
        logger.info(f"POST /memo-format/ - Memo format record created with ID {memo_format.format_id}")
        
        return {
            "format_id": memo_format.format_id,
            "message": "Memo format uploaded successfully!"
        }
    except Exception as e:
        logger.error(f"POST /memo-format/ - Error creating memo format record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating memo format record: {str(e)}")

@router.get("/memo-format/")
def list_memo_formats(request: Request, db: Session = Depends(get_db)):
    """
    List all memo format files.
    
    Args:
        request: The request object
        db: The database session
        
    Returns:
        A list of memo format files
    """
    logger.info(f"GET /memo-format/ - Request from {request.client.host}")
    
    memo_formats = db.query(MemoFormat).all()
    logger.info(f"GET /memo-format/ - Returning {len(memo_formats)} memo formats")
    
    return memo_formats

@router.get("/memo-format/{format_id}")
def get_memo_format(format_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Get a memo format file by ID.
    
    Args:
        format_id: The ID of the memo format to get
        request: The request object
        db: The database session
        
    Returns:
        The memo format file
    """
    logger.info(f"GET /memo-format/{format_id} - Request from {request.client.host}")
    
    memo_format = db.query(MemoFormat).get(format_id)
    if not memo_format:
        logger.warning(f"GET /memo-format/{format_id} - Memo format not found")
        raise HTTPException(status_code=404, detail="Memo format not found")
    
    logger.info(f"GET /memo-format/{format_id} - Returning memo format {memo_format.name}")
    
    return memo_format

@router.get("/download-memo-format/{format_id}")
def download_memo_format(format_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Download a memo format file.
    
    Args:
        format_id: The ID of the memo format to download
        request: The request object
        db: The database session
        
    Returns:
        The memo format file
    """
    logger.info(f"GET /download-memo-format/{format_id} - Request from {request.client.host}")
    
    memo_format = db.query(MemoFormat).get(format_id)
    if not memo_format:
        logger.warning(f"GET /download-memo-format/{format_id} - Memo format not found")
        raise HTTPException(status_code=404, detail="Memo format not found")
    
    file_path = memo_format.file_path
    if not os.path.exists(file_path):
        logger.error(f"GET /download-memo-format/{format_id} - File not found at {file_path}")
        raise HTTPException(status_code=404, detail="Memo format file not found")
    
    logger.info(f"GET /download-memo-format/{format_id} - Returning file {os.path.basename(file_path)}")
    
    return FileResponse(
        path=file_path,
        filename=memo_format.file_name,
        media_type="application/octet-stream"
    )

@router.delete("/memo-format/{format_id}")
def delete_memo_format(format_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Delete a memo format file.
    
    Args:
        format_id: The ID of the memo format to delete
        request: The request object
        db: The database session
        
    Returns:
        A message indicating the memo format was deleted successfully
    """
    logger.info(f"DELETE /memo-format/{format_id} - Request from {request.client.host}")
    
    memo_format = db.query(MemoFormat).get(format_id)
    if not memo_format:
        logger.warning(f"DELETE /memo-format/{format_id} - Memo format not found")
        raise HTTPException(status_code=404, detail="Memo format not found")
    
    # Delete the file if it exists
    if os.path.exists(memo_format.file_path):
        try:
            os.remove(memo_format.file_path)
            logger.info(f"DELETE /memo-format/{format_id} - Deleted file at {memo_format.file_path}")
        except Exception as e:
            logger.error(f"DELETE /memo-format/{format_id} - Error deleting file: {str(e)}")
            # Continue with memo format deletion even if file deletion fails
    
    try:
        db.delete(memo_format)
        db.commit()
        logger.info(f"DELETE /memo-format/{format_id} - Memo format deleted successfully")
        
        return {"message": f"Memo format {format_id} deleted successfully."}
    except Exception as e:
        logger.error(f"DELETE /memo-format/{format_id} - Error deleting memo format from database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting memo format: {str(e)}")