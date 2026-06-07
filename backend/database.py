"""Database connection and ORM models using SQLAlchemy.

This module provides the database layer for the Sudoku Research Platform,
supporting SQLite for local development and PostgreSQL for production.
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database URL - defaults to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sudoku_research.db")

# Handle PostgreSQL URL format from Render/Railway (they use postgres:// but SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
# SQLite needs check_same_thread=False for FastAPI's async context
# PostgreSQL (Supabase) requires SSL
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL with SSL for Supabase
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10
        },
        pool_pre_ping=True,  # Handle connection drops
        pool_size=5,
        max_overflow=10
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for email-based identification."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to puzzles
    puzzles = relationship("Puzzle", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Puzzle(Base):
    """Puzzle model storing analyzed puzzle submissions."""
    __tablename__ = "puzzles"

    id = Column(Integer, primary_key=True, index=True)
    puzzle_id = Column(String(20), unique=True, nullable=False)  # SDK-XXXX format
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Puzzle content
    grid = Column(Text, nullable=False)  # 81-character string
    clues = Column(Integer, nullable=False)

    # Publisher claim
    publisher = Column(String(100), nullable=False, index=True)
    publisher_short = Column(String(20), nullable=False)
    claimed_difficulty = Column(String(50), nullable=False)
    claimed_score = Column(Integer, nullable=False)

    # Measured results
    measured_score = Column(Integer, nullable=False)
    mismatch = Column(Integer, nullable=False)
    verdict = Column(String(50), nullable=False)
    hardest_technique = Column(String(100), nullable=False)

    # Additional metadata
    composite_score = Column(Integer, nullable=True)
    difficulty_tier = Column(String(20), nullable=True)  # Easy/Medium/Hard
    out_of_scope = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship to user
    user = relationship("User", back_populates="puzzles")

    def __repr__(self):
        return f"<Puzzle(id={self.puzzle_id}, publisher={self.publisher}, measured={self.measured_score})>"

    def to_dict(self) -> dict:
        """Convert puzzle to dictionary for API responses."""
        return {
            "id": self.puzzle_id,
            "publisher": self.publisher,
            "publisherShort": self.publisher_short,
            "claimed": self.claimed_difficulty,
            "claimedScore": self.claimed_score,
            "measuredScore": self.measured_score,
            "mismatch": self.mismatch,
            "verdict": self.verdict,
            "tech": self.hardest_technique,
            "clues": self.clues,
            "grid": self.grid,
            "date": self.created_at.strftime("%Y-%m-%d") if self.created_at else None,
            "ts": self.created_at.isoformat() if self.created_at else None,
            "composite": self.composite_score,
            "difficulty": self.difficulty_tier,
            "outOfScope": self.out_of_scope,
        }


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency for FastAPI to get database session.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Module exports
__all__ = [
    'DATABASE_URL',
    'engine',
    'SessionLocal',
    'Base',
    'User',
    'Puzzle',
    'init_db',
    'get_db',
]
