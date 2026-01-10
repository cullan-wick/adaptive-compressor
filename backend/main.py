from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

# Internal imports
from database import engine, Base, get_db
import models
import crud  # <--- New! Use the logic from crud.py
from pdf_engine import extract_text_from_pdf, count_tokens, chunk_text, get_embeddings # <--- New functions
from ai_engine import summarize_chunk

from utils import calculate_word_budget, count_words
from ai_engine import summarize_chunk, reduce_summary

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
async def upload_pdf(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db) # <--- CHANGE 1: Inject Database
):
    """
    Receives a PDF, extracts text, chunks it, embeds it, and saves everything to DB.
    """
    # 1. Validation: Ensure it is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # 2. Read & Extract (RAM)
        contents = await file.read()
        full_text = extract_text_from_pdf(contents)
        token_count = count_tokens(full_text)
        
        # 3. Save Book Metadata (DB)
        # We wait for this because we need the book.id for the chunks
        book = await crud.create_book(db, file.filename, token_count)
        
        # 4. Chunking (CPU)
        # Split the massive text into smaller lists of strings
        text_chunks = chunk_text(full_text, chunk_size=1000)
        
        # 5. Embedding (API Call)
        # This sends the chunks to OpenAI to get vectors.
        # Note: This might take 5-10 seconds depending on book size.
        vectors = await get_embeddings(text_chunks)
        
        # 6. Prepare Data for DB
        chunk_data = []
        # zip() lets us loop over text and vectors at the same time
        for i, (text, vector) in enumerate(zip(text_chunks, vectors)):
            chunk_data.append({
                "book_id": book.id,
                "chunk_index": i,
                "text_content": text,
                "embedding": vector
            })
            
        # 7. Save Chunks (DB)
        await crud.create_book_chunks(db, chunk_data)
        
        # 8. Return Success
        return {
            "filename": book.filename,
            "total_tokens": book.total_tokens,
            "text_preview": full_text[:100] + "..."
        }
        
    except Exception as e:
        print(f"Error: {e}") # This prints the specific error to your terminal
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/summarize/{book_id}")
async def summarize_book(
    book_id: int, 
    time_limit: int = 15, # Default 15 minutes
    wpm: int = 250,       # Default speed
    db: AsyncSession = Depends(get_db)
):
    """
    Map-Reduce Pipeline:
    1. Fetch Chunks
    2. Map (Summarize each chunk)
    3. Reduce (Compress total to fit time limit)
    """
    # --- PHASE 0: SETUP ---
    target_word_count = calculate_word_budget(time_limit, wpm)
    print(f"Target Budget: {target_word_count} words ({time_limit} mins @ {wpm} wpm)")

    # --- PHASE 1: FETCH ---
    chunks = await crud.get_book_chunks(db, book_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # --- PHASE 2: MAP (Parallel would be better, doing sequential for safety) ---
    map_summaries = []
    print(f"Starting Map Phase for {len(chunks)} chunks...")
    
    for chunk in chunks:
        # Optimization: Don't re-summarize if we already did? 
        # For now, we just run it. In Day 7 we can add caching.
        summary = await summarize_chunk(chunk.text_content)
        map_summaries.append(summary)
        print(f"Mapped Chunk {chunk.chunk_index}/{len(chunks)}")
    
    # Join them to see how big the "Draft 1" is
    full_draft = "\n\n".join(map_summaries)
    current_words = count_words(full_draft)
    print(f"Draft 1 Length: {current_words} words")
    
    # --- PHASE 3: REDUCE ---
    final_content = full_draft
    
    # Only reduce if we are OVER budget
    if current_words > target_word_count:
        print("Draft is too long. Entering Reduce Phase...")
        final_content = await reduce_summary(full_draft, target_word_count)
        final_words = count_words(final_content)
        print(f"Draft 2 (Final) Length: {final_words} words")
    else:
        print("Draft is within budget. Skipping Reduce.")

    return {
        "book_id": book_id,
        "target_words": target_word_count,
        "original_summary_words": current_words,
        "final_summary_words": count_words(final_content),
        "condensed_content": final_content
    }