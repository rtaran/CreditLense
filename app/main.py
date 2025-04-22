from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
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

@app.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.join("static", "favicon.ico"))

# app/routes/upload_html.py
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/upload", response_class=HTMLResponse)
def upload_form():
    return """
    <html>
        <body>
            <h2>Upload PDF</h2>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file">
                <input type="submit">
            </form>
        </body>
    </html>
    """

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    contents = file.file.read()
    output_path = UPLOAD_DIR / file.filename
    with open(output_path, "wb") as f:
        f.write(contents)
    return {"filename": file.filename, "message": "Upload successful!"}
