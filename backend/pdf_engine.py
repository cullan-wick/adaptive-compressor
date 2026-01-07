import fitz  # This is PyMuPDF
import tiktoken
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv() # Load the API Key from .env
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Converts raw PDF bytes into a single string of text.
    """
    # 1. Open the PDF from memory (we don't save it to disk first, which is faster)
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    full_text = []
    
    # 2. Iterate through every page
    for page in doc:
        # 3. Extract text
        text = page.get_text()
        full_text.append(text)
        
    # 4. Join all pages into one massive string with newlines
    return "\n".join(full_text)


def count_tokens(text: str) -> int:
    """
    Counts the absolute number of tokens in a string using OpenAI's encoding.
    """
    # 1. Load the specific "vocabulary" used by GPT-4 (cl100k_base) in the BPE Dictionary (Hash Map)
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # 2. Encode the text (turn string "hello" into numbers [15339]) (Greedy BPE Algorithm)
    tokens = encoding.encode(text)
    
    # 3. Return the count
    return len(tokens)

def chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    """
    Splits text into chunks of roughly 'chunk_size' characters.
    Strategy: Split by Double Newlines (\n\n) first to keep paragraphs together.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph makes the chunk too big, save the current one
        if len(current_chunk) + len(para) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            # Otherwise, add it to the current chunk
            current_chunk += "\n\n" + para
            
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

async def get_embeddings(text_chunks: list[str]):
    """
    Calls OpenAI to turn text into vectors.
    """
    # OpenAI allows up to 2048 dimensions, but 'text-embedding-3-small' is usually 1536.
    response = await client.embeddings.create(
        input=text_chunks,
        model="text-embedding-3-small"
    )
    
    # Extract just the vector lists from the response object
    # The response is a list of objects, we map them to just the 'embedding' field
    return [data.embedding for data in response.data]