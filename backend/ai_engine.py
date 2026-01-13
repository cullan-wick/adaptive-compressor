from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import math
import os
from dotenv import load_dotenv

load_dotenv()

# 1. The Model
# We use temperature=0.2 to allow for slightly better writing flow while staying factual.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# ==========================================
# PHASE 1: THE SMART MAP (Fixing Voice & Noise)
# ==========================================

map_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are the original author of this book. You are rewriting your book to be concise, fast-paced, and dense with information.
    
    RULES:
    1. Write in the first person (or matching the book's original voice). 
    2. NEVER say "The author says" or "The text discusses." Just write the content directly.
    3. IGNORE: Copyright pages, table of contents, dedication pages, and legal disclaimers. 
    4. If the chunk is purely "fluff" (legal/metadata) or empty, return the string "SKIP".
    """),
    ("human", "Rewrite this section concisely:\n\n{text}")
])

map_chain = map_prompt | llm | StrOutputParser()

async def summarize_chunk(text: str) -> str:
    """
    Summarizes a single chunk. Returns empty string if it's garbage.
    """
    try:
        response = await map_chain.ainvoke({"text": text})
        # If the AI detects garbage, it returns "SKIP". We filter that out.
        if "SKIP" in response:
            return "" 
        return response
    except Exception as e:
        print(f"AI Map Error: {e}")
        return text 

# ==========================================
# PHASE 2: THE RECURSIVE REDUCE (Fixing Over-Compression)
# ==========================================

reduce_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert editor. Your goal is to tighten the prose without losing detail."),
    ("human", """
    Here is a section of a book draft:
    {text}
    
    Please rewrite this to be approximately {target_words} words.
    - Keep the voice identical to the input.
    - Do not summarize high-level concepts; keep specific tactics, numbers, and lists.
    - If the text is already short enough, just polish it.
    """)
])

reduce_chain = reduce_prompt | llm | StrOutputParser()

async def recursive_reduce(text: str, target_words: int) -> str:
    """
    Intelligently splits the text if it's too big for one pass, 
    reduces the parts, and stitches them back together.
    """
    word_count = len(text.split())
    
    # BASE CASE: If text is small enough (approx 2500 words), process it directly.
    # GPT-4o-mini works best when input is under ~3000 tokens for complex logic.
    if word_count < 2500:
        print(f"   -> Reducing block ({word_count} words) to target ({target_words} words)...")
        return await reduce_chain.ainvoke({"text": text, "target_words": target_words})

    # RECURSIVE STEP: Split text in half and conquer
    print(f"   -> Splitting large block ({word_count} words)...")
    
    # 1. Split text roughly in half by double newline (paragraphs) to avoid cutting sentences
    paragraphs = text.split("\n\n")
    mid_point = len(paragraphs) // 2
    
    # Safety check: if no paragraphs, split by single newline
    if mid_point == 0:
        paragraphs = text.split("\n")
        mid_point = len(paragraphs) // 2

    part1 = "\n\n".join(paragraphs[:mid_point])
    part2 = "\n\n".join(paragraphs[mid_point:])
    
    # 2. Calculate proportional targets
    # If Part 1 is 60% of the text, it gets 60% of the word budget.
    total_len = len(part1) + len(part2)
    
    # Avoid division by zero
    if total_len == 0:
        return ""

    target1 = math.floor(target_words * (len(part1) / total_len))
    target2 = target_words - target1
    
    # 3. Recurse (Call this function again on the parts)
    reduced_part1 = await recursive_reduce(part1, target1)
    reduced_part2 = await recursive_reduce(part2, target2)
    
    return reduced_part1 + "\n\n" + reduced_part2

# Wrapper for compatibility with main.py
async def reduce_summary(text: str, target_words: int) -> str:
    print(f"DEBUG: Starting Recursive Reduce. Input: {len(text.split())} words. Target: {target_words}")
    return await recursive_reduce(text, target_words)