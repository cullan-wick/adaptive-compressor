from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
# Import the engine functions we just wrote
from pdf_engine import extract_text_from_pdf, count_tokens
# For PostgreSQL
from contextlib import asynccontextmanager
from database import engine, Base, get_db
import models

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs BEFORE the app starts receiving requests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # (Code after yield runs when app shuts down)

app = FastAPI(
    title="Adaptive Compressor API",
    version="0.1",
    lifespan=lifespan # <--- Register the logic here
)

# --- Data Models ---
class HealthCheck(BaseModel):
    status: str
    version: str

class UploadResponse(BaseModel):
    filename: str
    total_tokens: int
    text_preview: str  # First 100 characters, just to check

# --- Routes ---

@app.get("/", response_model=HealthCheck)
async def health_check():
    return {"status": "ok", "version": "0.1"}

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Receives a PDF file, extracts text, and returns the token count.
    """
    # 1. Validation: Ensure it is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # 2. Read the raw bytes (Async read)
        contents = await file.read()
        
        # 3. Process the file using our Engine
        text = extract_text_from_pdf(contents)
        token_count = count_tokens(text)
        
        # 4. Return the stats
        return {
            "filename": file.filename,
            "total_tokens": token_count,
            "text_preview": text[:100] + "..." # Just show the beginning
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))