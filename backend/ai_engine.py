from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import math
import os
from dotenv import load_dotenv

load_dotenv()

# Keep temperature low for formatting strictness
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# ==========================================
# PHASE 1: THE FILTERING MAP
# ==========================================

map_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are the original author rewriting your book. 
    
    CRITICAL RULES:
    1. IGNORE & SKIP: Copyright pages, Table of Contents, Dedications, "Notes from the Author," "Forewords," and "How to read this book."
    2. If the chunk is fluff/skipped, return the string "SKIP".

    WRITING RULES:
    1. Write in the first person ("I argue...", "I found...").
    2. Be dense and actionable.
    """),
    ("human", "Rewrite this section concisely:\n\n{text}")
])

map_chain = map_prompt | llm | StrOutputParser()

async def summarize_chunk(text: str) -> str:
    try:
        response = await map_chain.ainvoke({"text": text})
        if "SKIP" in response:
            return "" 
        return response
    except Exception as e:
        print(f"AI Map Error: {e}")
        return text 

# ==========================================
# PHASE 2: THE CLEAN REDUCE
# ==========================================

reduce_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert editor. Your goal is to tighten the prose, format it for readability, and fix structural repetition."),
    ("human", """
    Here is a book draft composed of several merged chunks:
    {text}
    
    Please rewrite this to be approximately {target_words} words.
    
    STYLE GUIDE:
    1. **Voice:** Keep the author's voice (First Person).
    2. **Structure (CRITICAL):**
       - The input text may have REPEATED headers (e.g., "Rule #1" appearing 3 times).
       - **MERGE** these duplicate sections. Do not list "Rule #1" multiple times. Group all content that belongs to Rule #1 under a SINGLE header.
       - Correct mislabeled headers. If the text looks like an Intro, don't label it "Rule #1".
    3. **Formatting:**
       - Use `### ` for section headers.
       - STRICTLY NO BOLDING.
       - STRICTLY NO INDENTATION.
       - Separate paragraphs with double newlines.
    4. **Content:** Drop all "Notes from the author."
    
    Output purely Markdown.
    """)
])

reduce_chain = reduce_prompt | llm | StrOutputParser()

async def recursive_reduce(text: str, target_words: int) -> str:
    word_count = len(text.split())
    
    # Base case: Text is small enough to process
    if word_count < 2500:
        print(f"   -> Reducing block ({word_count} words) to target ({target_words} words)...")
        return await reduce_chain.ainvoke({"text": text, "target_words": target_words})

    # Recursive step
    print(f"   -> Splitting large block ({word_count} words)...")
    
    paragraphs = text.split("\n\n")
    mid_point = len(paragraphs) // 2
    
    if mid_point == 0:
        paragraphs = text.split("\n")
        mid_point = len(paragraphs) // 2

    part1 = "\n\n".join(paragraphs[:mid_point])
    part2 = "\n\n".join(paragraphs[mid_point:])
    
    total_len = len(part1) + len(part2)
    if total_len == 0: return ""

    target1 = math.floor(target_words * (len(part1) / total_len))
    target2 = target_words - target1
    
    reduced_part1 = await recursive_reduce(part1, target1)
    reduced_part2 = await recursive_reduce(part2, target2)
    
    return reduced_part1 + "\n\n" + reduced_part2

# Wrapper
async def reduce_summary(text: str, target_words: int) -> str:
    return await recursive_reduce(text, target_words)