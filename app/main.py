from fastapi import FastAPI
from app.models import Base
from app.database import engine
from app.routers import documents, memos

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(documents.router)
app.include_router(memos.router)

@app.get("/")
def root():
    return {"message": "Financial Memo App is running!"}