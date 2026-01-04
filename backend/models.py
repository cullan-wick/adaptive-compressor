from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    total_tokens = Column(Integer)
    
    # Relationship: A book has many chunks
    chunks = relationship("BookChunk", back_populates="book")

class BookChunk(Base):
    __tablename__ = "book_chunks"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    chunk_index = Column(Integer)  # e.g., 0, 1, 2 (Order matters!)
    text_content = Column(Text)    # The actual text of the paragraph
    
    # THE MAGIC COLUMN
    # We store a vector of size 1536 (Standard for OpenAI's model)
    embedding = Column(Vector(1536)) 
    
    book = relationship("Book", back_populates="chunks")