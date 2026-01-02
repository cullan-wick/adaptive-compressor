from fastapi import FastAPI
from pydantic import BaseModel

# 1. Initialize the App
# This is the entry point for all API requests.
app = FastAPI(
    title="Adaptive Compressor API",
    version="0.1",
    description="A map-reduce system for constraint-based summarization."
)

# 2. Define Data Models (First Principles: Strict Typing)
# We use Pydantic to enforce the shape of data. 
# If the frontend sends text, this will explode, ensuring data integrity.
class HealthCheck(BaseModel):
    status: str
    version: str

# 3. Define Routes (Endpoints)
# The @app.get decorator tells FastAPI to listen for GET requests at "/"
@app.get("/", response_model=HealthCheck)
async def health_check():
    # "async" is critical here. It means this function won't block 
    # the server while it runs.
    return {"status": "ok", "version": "0.1"}

# 4. Run instructions:
# In terminal: uvicorn main:app --reload