# --- Standard Library ---
import asyncio
from contextlib import asynccontextmanager

# --- Third Party ---
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# --- Internal Modules ---
from database import engine, Base, get_db
import crud
from pdf_engine import extract_text_from_pdf, count_tokens, chunk_text, get_embeddings
from ai_engine import summarize_chunk, reduce_summary
from utils import calculate_word_budget, count_words

# --- Lifespan (Startup/Shutdown Logic) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# --- App Definition ---
app = FastAPI(
    title="Adaptive Compressor API",
    version="1.0.0",
    description="An AI-powered system to recursively compress books into time-boxed summaries.",
    lifespan=lifespan
)

# --- Middleware (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models (Pydantic) ---
class HealthCheck(BaseModel):
    status: str
    version: str

class UploadResponse(BaseModel):
    book_id: int
    filename: str
    total_tokens: int
    text_preview: str

# --- API Routes ---

@app.get("/", response_model=HealthCheck)
async def health_check():
    """
    Simple heartbeat endpoint to verify server status.
    """
    return {"status": "ok", "version": "1.0.0"}

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Ingestion Pipeline:
    1. Reads PDF bytes.
    2. Extracts text & counts tokens.
    3. Chunks text into semantic paragraphs.
    4. Embeds chunks via OpenAI.
    5. Saves everything to Postgres.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # Phase 1: Processing (In-Memory)
        contents = await file.read()
        full_text, _, _ = extract_text_from_pdf(contents) # Unpack tuple (text, toc, count)
        token_count = count_tokens(full_text)
        
        # Phase 2: Metadata Storage
        book = await crud.create_book(db, file.filename, token_count)
        
        # Phase 3: AI Transformation
        # We pass empty TOC/page_count for now as we use naive chunking
        text_chunks = chunk_text(full_text, toc=[], doc_page_count=0, chunk_size=1000)
        vectors = await get_embeddings(text_chunks)
        
        # Phase 4: Vector Storage
        chunk_data = []
        for i, (text, vector) in enumerate(zip(text_chunks, vectors)):
            chunk_data.append({
                "book_id": book.id,
                "chunk_index": i,
                "text_content": text,
                "embedding": vector
            })
            
        await crud.create_book_chunks(db, chunk_data)
        
        return {
            "book_id": book.id,
            "filename": book.filename,
            "total_tokens": book.total_tokens,
            "text_preview": full_text[:100] + "..."
        }
        
    except Exception as e:
        print(f"Error during upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize/{book_id}")
async def summarize_book(
    book_id: int, 
    time_limit: int = 15, 
    wpm: int = 250,       
    db: AsyncSession = Depends(get_db)
):
    """
    The Core Engine:
    1. Fetches chunks.
    2. Groups them (Macro-Chunking).
    3. Maps (Summarizes) them in parallel with Dynamic Density.
    4. Reduces (Compresses) them recursively to fit the time budget.
    """
    # Setup
    target_word_count = calculate_word_budget(time_limit, wpm)
    print(f"--- Starting Job: Book {book_id} | Target: {target_word_count} words ---")

    # Step 1: Retrieve Data
    chunks = await crud.get_book_chunks(db, book_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Step 1.5: Macro-Chunking (Optimization)
    print(f"Fetched {len(chunks)} raw chunks. Grouping into Macro-Blocks...")
    macro_chunks = []
    current_block = ""
    BLOCK_SIZE_LIMIT = 15000 

    for chunk in chunks:
        if len(current_block) + len(chunk.text_content) > BLOCK_SIZE_LIMIT:
            macro_chunks.append(current_block)
            current_block = chunk.text_content
        else:
            separator = "\n\n" if current_block else ""
            current_block += separator + chunk.text_content
    
    if current_block:
        macro_chunks.append(current_block)
        
    print(f" Optimization: Reduced {len(chunks)} DB chunks to {len(macro_chunks)} API calls.")

    # Step 2: Map Phase (Parallel + Dynamic Density)
    print(f"Starting Map Phase for {len(macro_chunks)} blocks...")
    
    # Determine Density Mode based on user time limit
    # If they want > 20 mins, we keep more detail.
    density_mode = "detailed" if time_limit > 20 else "concise"
    print(f"Density Mode: {density_mode.upper()}")

    # Semaphore controls concurrency
    semaphore = asyncio.Semaphore(35) 

    async def processed_chunk(text):
        async with semaphore:
            return await summarize_chunk(text, density=density_mode)

    tasks = [processed_chunk(text) for text in macro_chunks]
    map_summaries = await asyncio.gather(*tasks)
    
    full_draft = "\n\n".join(map_summaries)
    current_words = count_words(full_draft)
    print(f"Draft 1 Length: {current_words} words")
    
    # Step 3: Reduce Phase (Recursive)
    final_content = full_draft
    
    if current_words > target_word_count:
        print("Draft exceeds budget. Entering Recursive Reduce...")
        final_content = await reduce_summary(full_draft, target_word_count)
        print(f"Final Length: {count_words(final_content)} words")
    else:
        print("Draft fits budget. Skipping Reduce.")

    return {
        "book_id": book_id,
        "target_words": target_word_count,
        "original_summary_words": current_words,
        "final_summary_words": count_words(final_content),
        "condensed_content": final_content
    }