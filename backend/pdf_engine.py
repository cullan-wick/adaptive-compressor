import fitz  # This is PyMuPDF
import tiktoken

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
    # 1. Load the specific "vocabulary" used by GPT-4 (cl100k_base)
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # 2. Encode the text (turn string "hello" into numbers [15339])
    tokens = encoding.encode(text)
    
    # 3. Return the count
    return len(tokens)