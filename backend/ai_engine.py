from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import math
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Keep temperature low for formatting strictness
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# ==========================================
# PHASE 1: THE ADAPTIVE MAP (Dynamic Density)
# ==========================================

# 1. High Density Prompt (For Long Summaries > 20 mins)
# Goal: Preserve detail, stories, and nuance.
detailed_map_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are the original author rewriting your book. 
    
    GOAL: Preserve maximum detail while improving flow.
    
    RULES:
    1. IGNORE: Copyright, TOC, Dedications, "Notes from Author", "Forewords".
    2. VOICE: Write in the first person ("I argue...", "I found...").
    3. CONTENT: Keep all stories, data points, specific numbers, and examples. Do not summarize; just rewrite for clarity.
    4. If the chunk is fluff/metadata, return "SKIP".
    """),
    ("human", "Rewrite this section:\n\n{text}")
])

# 2. Low Density Prompt (For Short Summaries < 20 mins)
# Goal: Aggressively compress.
concise_map_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are the original author rewriting your book. 
    
    GOAL: Aggressively compress the content.
    
    RULES:
    1. IGNORE: Copyright, TOC, Dedications, "Notes from Author", "Forewords".
    2. VOICE: Write in the first person ("I argue...", "I found...").
    3. CONTENT: Keep only the main thesis and key tactics. Drop anecdotes and fluff.
    4. If the chunk is fluff/metadata, return "SKIP".
    """),
    ("human", "Rewrite this section concisely:\n\n{text}")
])

# Create Chains
detailed_chain = detailed_map_prompt | llm | StrOutputParser()
concise_chain = concise_map_prompt | llm | StrOutputParser()

async def summarize_chunk(text: str, density: str = "concise") -> str:
    """
    Summarizes a chunk.
    density: 'concise' (default) or 'detailed'
    """
    try:
        # Select the correct chain based on density request
        if density == "detailed":
            response = await detailed_chain.ainvoke({"text": text})
        else:
            response = await concise_chain.ainvoke({"text": text})
            
        # Filter garbage
        if "SKIP" in response:
            return "" 
        return response
    except Exception as e:
        print(f"AI Map Error: {e}")
        return text 

# ==========================================
# PHASE 2: THE CLEAN REDUCE (Parallel Recursive)
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
    
    # BASE CASE: Process small blocks directly
    # GPT-4o-mini works best when input is under ~3000 tokens for complex logic.
    if word_count < 2500:
        print(f"   -> Reducing block ({word_count} words) to target ({target_words} words)...")
        return await reduce_chain.ainvoke({"text": text, "target_words": target_words})

    # RECURSIVE STEP: Split and Parallelize
    print(f"   -> Splitting large block ({word_count} words)...")
    
    paragraphs = text.split("\n\n")
    mid_point = len(paragraphs) // 2
    
    if mid_point == 0: # Handle edge case of single giant paragraph
        paragraphs = text.split("\n")
        mid_point = len(paragraphs) // 2

    part1 = "\n\n".join(paragraphs[:mid_point])
    part2 = "\n\n".join(paragraphs[mid_point:])
    
    total_len = len(part1) + len(part2)
    if total_len == 0: return ""

    # Calculate proportional targets
    target1 = math.floor(target_words * (len(part1) / total_len))
    target2 = target_words - target1
    
    # --- THE SPEED OPTIMIZATION (Async Recursion) ---
    # Create the tasks but don't await them yet
    task1 = recursive_reduce(part1, target1)
    task2 = recursive_reduce(part2, target2)
    
    # Run both branches simultaneously
    results = await asyncio.gather(task1, task2)
    
    # Stitch results together
    return results[0] + "\n\n" + results[1]

# Wrapper
async def reduce_summary(text: str, target_words: int) -> str:
    # FINAL TUNING BASED ON BENCHMARKS:
    # 5 min (1250w):  Factor 0.80 -> -16% (Too low). Needs ~0.95
    # 15 min (3750w): Factor 0.70 -> -18% (Too low). Needs ~0.85
    # 30 min (7500w): Factor 0.75 -> -16% (Too low). Needs ~0.85
    # 60 min (15000w): Factor 0.75 -> +7% (Perfect). Keep 0.75
    
    if target_words < 1500:
        # Short summaries need very little calibration
        calibration_factor = 0.95
    elif target_words < 10000:
        # Medium summaries need mild calibration
        calibration_factor = 0.85
    else:
        # Long summaries bloat easily, keep strict calibration
        calibration_factor = 0.75
        
    calibrated_target = int(target_words * calibration_factor)
    
    print(f"DEBUG: Target: {target_words} | Factor: {calibration_factor} | Calibrated: {calibrated_target}")
    
    return await recursive_reduce(text, calibrated_target)