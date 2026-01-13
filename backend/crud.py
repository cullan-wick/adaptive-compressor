from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Book, BookChunk

async def create_book(db: AsyncSession, filename: str, total_tokens: int):
    """
    Creates a metadata row for the book.
    """
    # 1. Create the Object (Like 'new Book()' in Java)
    new_book = Book(filename=filename, total_tokens=total_tokens)
    
    # 2. Add to Session (Staging area)
    db.add(new_book)
    
    # 3. Commit (Save to Disk)
    await db.commit()
    
    # 4. Refresh (Get the generated ID back from the DB)
    await db.refresh(new_book)
    return new_book

async def create_book_chunks(db: AsyncSession, chunks_data: list):
    """
    Bulk inserts many chunks at once.
    chunks_data = [{'book_id': 1, 'text': '...', 'vector': [...]}, ...]
    """
    # We use a loop to create objects, but in production, we'd use bulk_insert_mappings
    # For simplicity and clarity now:
    for item in chunks_data:
        new_chunk = BookChunk(
            book_id=item['book_id'],
            chunk_index=item['chunk_index'],
            text_content=item['text_content'],
            embedding=item['embedding'] # This is the Vector!
        )
        db.add(new_chunk)
    
    await db.commit()

async def get_book_chunks(db: AsyncSession, book_id: int):
    """
    Retrieves all chunks for a specific book, ordered by index.
    """
    # SQL: SELECT * FROM book_chunks WHERE book_id = X ORDER BY chunk_index ASC
    result = await db.execute(
        select(BookChunk)
        .where(BookChunk.book_id == book_id)
        .order_by(BookChunk.chunk_index)
    )
    return result.scalars().all()
