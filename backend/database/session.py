import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Get the database URL and ensure it uses a sync driver
raw_url = os.getenv("DATABASE_URL", "sqlite:///sutrix_science.db")
if raw_url.startswith("sqlite+aiosqlite://"):
    DATABASE_URL = raw_url.replace("sqlite+aiosqlite://", "sqlite://")
elif raw_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = raw_url.replace("postgresql+asyncpg://", "postgresql://")
else:
    DATABASE_URL = raw_url

# Standard sync engine with optimized connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"timeout": 30} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db():
    from .models import Base
    # Create tables synchronously
    Base.metadata.create_all(bind=engine)
    
    # Enable WAL (Write-Ahead Logging) mode optimization for SQLite to enhance concurrent batch speeds
    if "sqlite" in DATABASE_URL:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA synchronous=NORMAL;"))
            conn.commit()

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
