from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

# 1. The Model
# We use 'gpt-4o-mini' because it is cheap and fast for summarizing 300 chunks.
# temperature=0 means "be strict and factual, don't be creative."
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. The "Map" Prompt
# This instructs the AI on how to handle a SINGLE chunk.
map_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that summarizes sections of a book."),
    ("human", "Summarize the following text efficiently. Capture the main arguments and key details. Do not use intro phrases like 'this section discusses'. Just give the summary.\n\nTEXT:\n{text}")
])

# 3. The Chain
# This connects the Prompt -> Model -> Output Parser (converts AI object to string)
map_chain = map_prompt | llm | StrOutputParser()

async def summarize_chunk(text: str) -> str:
    """
    Takes a raw text chunk and returns a condensed summary.
    """
    try:
        # We use ainvoke (Async Invoke) because we are running in FastAPI
        response = await map_chain.ainvoke({"text": text})
        return response
    except Exception as e:
        print(f"AI Error: {e}")
        return text # If AI fails, just return original text so we don't lose data
    

# 1. The Reduce Prompt
# We inject 'target_words' as a variable so the AI knows the constraint.
reduce_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a ruthless editor. Your goal is to compress text without losing the core thesis."),
    ("human", """
    Here is a long summary of a book:
    {text}
    
    Please rewrite this to be roughly {target_words} words. 
    Focus on the most actionable tactics and the central argument. 
    Drop all anecdotes, fluff, and repetitive examples. 
    Keep the tone professional and dense.
    """)
])

# 2. The Reduce Chain
reduce_chain = reduce_prompt | llm | StrOutputParser()

async def reduce_summary(text: str, target_words: int) -> str:
    """
    Takes a long summary and compresses it to fit the budget.
    """
    # Simple whitespace split to guess word count for debug log
    current_count = len(text.split())
    print(f"DEBUG: Reducing text from {current_count} words to {target_words} words...")
    
    try:
        # We pass BOTH the text and the target number to the prompt
        response = await reduce_chain.ainvoke({
            "text": text, 
            "target_words": target_words
        })
        return response
    except Exception as e:
        print(f"AI Reduce Error: {e}")
        return text