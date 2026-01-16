"""
Database Connection Module
Handles PostgreSQL connection and session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.settings import Settings
from utils.logger import logger

Base = declarative_base()

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.settings = Settings()
        # Convert postgres:// to postgresql+asyncpg:// for async support
        db_url = self.settings.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        self.engine = create_async_engine(
            db_url,
            echo=self.settings.is_development,
            pool_size=5,
            max_overflow=10
        )
        
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database connection initialized")
    
    async def get_session(self) -> AsyncSession:
        """Get async database session"""
        async with self.async_session_maker() as session:
            yield session
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
