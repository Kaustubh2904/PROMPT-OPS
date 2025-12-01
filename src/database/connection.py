"""
Database Connection and Session Management

This module handles database connections, session creation,
and provides utilities for database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from config import settings
from .models import Base


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    This class provides a clean interface for database operations,
    including connection pooling and session management.
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize the database manager.
        
        Args:
            database_url: Database connection string. If None, uses config.
        """
        self.database_url = database_url or settings.database_url
        
        # Configure engine based on database type
        if self.database_url.startswith("sqlite"):
            # SQLite configuration
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            # PostgreSQL/MySQL configuration
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """Drop all tables in the database."""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            A new SQLAlchemy session
        """
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        This context manager ensures that the session is properly
        closed and transactions are committed or rolled back.
        
        Yields:
            A database session
            
        Example:
            with db_manager.session_scope() as session:
                session.add(new_record)
                # Automatically commits on success, rolls back on error
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


def init_database():
    """
    Initialize the database by creating all tables.
    
    This should be called once when setting up the application.
    """
    db_manager.create_tables()
    print(f"✓ Database initialized at: {settings.database_url}")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI or similar frameworks.
    
    Yields:
        A database session
        
    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
