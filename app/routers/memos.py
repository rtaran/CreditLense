from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import FinancialMemo
from app.database import SessionLocal

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

@router.delete("/memos/{memo_id}")
def delete_memo(memo_id: int, db: Session = Depends(get_db)):
    memo = db.query(FinancialMemo).get(memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    db.delete(memo)
    db.commit()
    return {"message": f"Memo {memo_id} deleted successfully."}