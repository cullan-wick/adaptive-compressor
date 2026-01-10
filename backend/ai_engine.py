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