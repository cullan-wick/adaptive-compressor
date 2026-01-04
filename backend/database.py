from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 1. The Connection String
# The format is: driver://user@host/database_name
DATABASE_URL = "postgresql+asyncpg://cullanwickramasuriya@localhost/adaptive_compressor_db"


# 2. The Engine ( The "Socket" )
# This creates the pool of connections to the DB.
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. The Session Factory
# When a user requests data, we give them a specific "Session" from the pool.
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 4. The Base Class
# All our Database Models will inherit from this.
Base = declarative_base()

# 5. Dependency Injection helper
# This is what we pass into our FastAPI routes so they can use the DB.
async def get_db():
    async with SessionLocal() as session:
        yield session